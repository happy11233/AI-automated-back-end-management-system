from app.celery_app import celery_app
from app.db import pool
from app.observability import observed
from celery.signals import heartbeat_sent
import time

_last_heartbeat = 0.0


def _is_transient_job_error(error: Exception) -> bool:
    from psycopg import InterfaceError, OperationalError
    from psycopg.errors import DeadlockDetected, SerializationFailure
    from botocore.exceptions import (
        ClientError, ConnectTimeoutError, ConnectionClosedError,
        EndpointConnectionError, ReadTimeoutError,
    )
    if isinstance(error, (ConnectionError, TimeoutError, OperationalError, InterfaceError,
                          DeadlockDetected, SerializationFailure,
                          ConnectTimeoutError, ConnectionClosedError,
                          EndpointConnectionError, ReadTimeoutError)):
        return True
    if isinstance(error, ClientError):
        response = error.response or {}
        code = str((response.get('Error') or {}).get('Code') or '')
        status_code = int((response.get('ResponseMetadata') or {}).get('HTTPStatusCode') or 0)
        return status_code == 429 or status_code >= 500 or code in {'SlowDown', 'RequestTimeout'}
    return False


def _retry_delay_seconds(attempt_count: int) -> int:
    return min(300, 5 * (2 ** max(0, attempt_count - 1)))


@heartbeat_sent.connect
def record_worker_heartbeat(**kwargs):
    global _last_heartbeat
    if time.monotonic() - _last_heartbeat < 10:
        return
    from app.cache import cache_set
    cache_set('health', 'worker', {'at': time.time()}, 120)
    _last_heartbeat = time.monotonic()


@celery_app.task(name='maintenance.scheduler_heartbeat', ignore_result=True, expires=30)
def scheduler_heartbeat():
    from app.cache import cache_set
    cache_set('health', 'scheduler_dispatch', {'at': time.time()}, 120)


@celery_app.task(name='maintenance.publish_outbox', ignore_result=True)
def publish_outbox():
    from app.config import settings
    if not settings.background_jobs_enabled:
        return
    # Re-publish stranded deliveries periodically. Active jobs are protected by
    # their advisory lock; completed/failed jobs are ignored by the consumer.
    with pool.connection() as conn:
        conn.execute('''UPDATE task_outbox o SET published_at=NULL, next_attempt_at=now()
            FROM background_jobs j WHERE j.id=o.job_id AND j.status IN ('queued','running')
              AND o.published_at < now()-interval '15 minutes' ''')
        conn.commit()
    # Publishing and marking cannot be atomic. Redelivery is deduplicated below.
    with pool.connection() as conn:
        with conn.transaction():
            rows = conn.execute('''SELECT id,job_id FROM task_outbox
                WHERE published_at IS NULL AND next_attempt_at <= now()
                ORDER BY created_at LIMIT 20 FOR UPDATE SKIP LOCKED''').fetchall()
            for event_id, job_id in rows:
                try:
                    celery_app.send_task('jobs.execute', args=[str(job_id)],
                                         task_id=str(event_id), retry=False)
                except Exception:
                    conn.execute('''UPDATE task_outbox SET attempt_count=attempt_count+1,
                        next_attempt_at=now()+interval '30 seconds' WHERE id=%s''', (event_id,))
                    continue
                conn.execute('UPDATE task_outbox SET published_at=now(),attempt_count=attempt_count+1 WHERE id=%s', (event_id,))


@celery_app.task(name='maintenance.publish_approval_tickets', ignore_result=True)
@observed('maintenance.publish_approval_tickets')
def publish_approval_tickets():
    from app.services.approval_ticket_outbox_service import dispatch_approval_tickets
    return dispatch_approval_tickets()


@celery_app.task(name='maintenance.competitor_monitor', ignore_result=True)
@observed('maintenance.competitor_monitor')
def competitor_monitor():
    from app.cache import cache_set
    from app.services.competitor_monitor_service import run_scheduled_inspections
    result = run_scheduled_inspections()
    cache_set('health', 'competitor_monitor', {'at': time.time(), 'failed': result['failed']}, 180)
    return result


@celery_app.task(name='jobs.execute', bind=True, max_retries=3)
@observed('jobs.execute')
def execute_job(self, job_id: str):
    from psycopg.types.json import Jsonb
    from app.artifact_storage import read_artifact
    from app.auth.security import get_user_by_id
    from app.services.user_ai_app_permission_service import is_ai_app_allowed
    from app.services.run_record_service import start_run, finish_run
    from app.services.generated_file_service import save_generated_file
    from app.services.finance_reconciliation_service import FinanceReconciliationInputFile, reconcile_finance_workbooks
    from app.observability import request_id_var, annotate_trace
    with pool.connection() as conn:
        locked = conn.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))', (job_id,)).fetchone()[0]
        conn.commit()
        if not locked:
            raise self.retry(countdown=30)
        token = None
        run_id = None
        attempt_count = None
        max_attempts = None
        try:
            row = conn.execute('''SELECT user_id,position,status,payload,attempt_count,max_attempts,request_id,
                                         (status='running' OR next_attempt_at IS NULL OR next_attempt_at<=now()) AS due
                                  FROM background_jobs WHERE id=%s''', (job_id,)).fetchone()
            conn.commit()
            if not row or row[2] in {'succeeded', 'failed'}:
                return
            if not row[7]:
                return
            if row[4] >= row[5]:
                conn.execute("UPDATE background_jobs SET status='failed',error_code='attempts_exhausted',next_attempt_at=NULL,finished_at=now() WHERE id=%s", (job_id,))
                conn.commit()
                return
            token = request_id_var.set(row[6])
            annotate_trace(request_id=row[6], task_id=job_id, component='worker')
            attempt = conn.execute("""UPDATE background_jobs SET status='running',attempt_count=attempt_count+1,
                started_at=now(),next_attempt_at=NULL WHERE id=%s AND status IN ('queued','running')
                RETURNING attempt_count,max_attempts""", (job_id,)).fetchone()
            if not attempt:
                conn.commit()
                return
            attempt_count, max_attempts = attempt
            conn.commit()
            user = get_user_by_id(str(row[0]))
            if not user or (user['role'] != 'admin' and (user.get('position') != row[1] or
                user.get('position') != 'finance' or not is_ai_app_allowed(user, 'finance-reconciliation'))):
                conn.execute("UPDATE background_jobs SET status='failed',error_code='permission_changed',next_attempt_at=NULL,finished_at=now() WHERE id=%s", (job_id,))
                conn.commit()
                return
            # Recover the published artifact if a worker died just before marking
            # the job complete. Orphan temporary files are not published results.
            prior = conn.execute('''SELECT a.id,a.run_id,a.metadata FROM automation_run_artifacts a
                JOIN automation_runs r ON r.id=a.run_id
                WHERE r.resource_type='background_job' AND r.resource_id=%s
                  AND a.metadata->>'background_job_id'=%s AND a.downloadable=TRUE
                  AND a.storage_path IS NOT NULL AND a.expires_at>now()
                ORDER BY a.created_at DESC LIMIT 1''', (job_id, job_id)).fetchone()
            conn.commit()
            if prior:
                run_id = str(prior[1])
                finish_run(run_id, status_value='succeeded', metadata=prior[2])
                conn.execute("UPDATE background_jobs SET status='succeeded',result=%s,error_code=NULL,next_attempt_at=NULL,finished_at=now() WHERE id=%s",
                    (Jsonb({**prior[2], 'artifact_id': str(prior[0]), 'run_id': run_id,
                            'download_url': f'/files/{prior[0]}/download'}), job_id))
                conn.commit()
                return
            run_id = start_run(run_type='finance_reconciliation', app_id='finance-reconciliation',
                               app_name='后台财务对账', entrypoint='/jobs/finance-reconciliation',
                               current_user=user, resource_type='background_job', resource_id=job_id)
            payload = row[3]
            result = reconcile_finance_workbooks(
                files=[FinanceReconciliationInputFile(filename=f['filename'],
                       content=read_artifact(f['storage_reference'])) for f in payload['files']],
                instruction=payload['instruction'], base_currency=payload['base_currency'])
            artifact_id = save_generated_file(run_id=run_id, content=result.content, filename=result.filename,
                artifact_type='excel_file', mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                current_user=user, metadata={**result.metadata, 'background_job_id': job_id})
            if not artifact_id:
                raise RuntimeError('Result artifact was not persisted')
            finish_run(run_id, status_value='succeeded', metadata=result.metadata,
                       output_text='订单贡献利润复核文件已生成，待补成本资料。'
                       if result.metadata['review_status'] == 'requires_input'
                       else '订单贡献利润复核文件已生成，待财务复核。')
            conn.execute("UPDATE background_jobs SET status='succeeded',result=%s,error_code=NULL,next_attempt_at=NULL,finished_at=now() WHERE id=%s",
                         (Jsonb({**result.metadata, 'artifact_id': artifact_id, 'run_id': run_id,
                                 'download_url': f'/files/{artifact_id}/download'}), job_id))
            conn.commit()
        except Exception as error:
            conn.rollback()
            if run_id:
                finish_run(run_id, status_value='failed', error_message=type(error).__name__)
            retryable = _is_transient_job_error(error)
            if retryable and (attempt_count is None or attempt_count < max_attempts):
                delay = _retry_delay_seconds(attempt_count or 1)
                conn.execute("""UPDATE background_jobs SET status='queued',error_code=%s,
                    next_attempt_at=now()+(%s * interval '1 second'),finished_at=NULL WHERE id=%s""",
                    (f'temporary_{type(error).__name__}', delay, job_id))
                conn.execute("""UPDATE task_outbox SET published_at=NULL,next_attempt_at=now()+(%s * interval '1 second')
                    WHERE job_id=%s""", (delay, job_id))
                conn.commit()
                raise self.retry(exc=error, countdown=delay)
            code = f'attempts_exhausted_{type(error).__name__}' if retryable else type(error).__name__
            conn.execute("UPDATE background_jobs SET status='failed',error_code=%s,next_attempt_at=NULL,finished_at=now() WHERE id=%s",
                         (code, job_id))
            conn.commit()
            raise
        finally:
            if token is not None:
                request_id_var.reset(token)
            conn.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))', (job_id,))
            conn.commit()


@celery_app.task(name='maintenance.cleanup_context', autoretry_for=(ConnectionError,),
                 retry_backoff=True, max_retries=3)
@observed('maintenance.cleanup_context')
def cleanup_context():
    # One cleanup globally; the lock is released with this connection even on error.
    with pool.connection() as conn:
        locked = conn.execute('SELECT pg_try_advisory_lock(714206231)').fetchone()[0]
        conn.commit()
        if not locked:
            return {'status': 'already_running'}
        try:
            from app.services.context_service import cleanup_expired_context
            from app.services.generated_file_service import cleanup_expired_generated_files
            from app.services.background_job_service import cleanup_expired_job_inputs
            from app.artifact_storage import cleanup_materialized_files
            return {**cleanup_expired_context(),
                    'expired_generated_files': cleanup_expired_generated_files(),
                    'expired_job_inputs': cleanup_expired_job_inputs(),
                    'expired_materialized_files': cleanup_materialized_files()}
        finally:
            conn.execute('SELECT pg_advisory_unlock(714206231)')
            conn.commit()
