"""Transactional job/outbox persistence. No job payload is sent through RabbitMQ."""
from hashlib import sha256
import json

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from app.config import settings
from app.db import fetch_all, fetch_one, transaction
from app.observability import request_id_var


def require_jobs_enabled() -> None:
    if not settings.background_jobs_enabled:
        raise HTTPException(503, '后台任务尚未启用，请使用原有同步入口')


def create_job(*, kind: str, payload: dict, idempotency_key: str, current_user: dict) -> dict:
    require_jobs_enabled()
    digest_payload = {k: v for k, v in payload.items() if k != 'files'}
    digest_payload['files'] = [{'filename': f['filename'], 'sha256': f['sha256']} for f in payload['files']]
    digest = sha256(json.dumps(digest_payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    with transaction() as conn:
        row = conn.execute('''
            INSERT INTO background_jobs(user_id, position, kind, idempotency_key, payload_hash, payload, request_id, next_attempt_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,now())
            ON CONFLICT(user_id,idempotency_key) DO NOTHING RETURNING id
        ''', (current_user['id'], current_user.get('position'), kind, idempotency_key, digest,
              Jsonb(payload), request_id_var.get())).fetchone()
        if row:
            conn.execute('INSERT INTO task_outbox(job_id) VALUES (%s)', (row[0],))
            return {'id': str(row[0]), 'status': 'queued', 'reused': False}
        row = conn.execute('SELECT id,status,payload_hash FROM background_jobs WHERE user_id=%s AND idempotency_key=%s',
                           (current_user['id'], idempotency_key)).fetchone()
        if row[2] != digest:
            raise HTTPException(409, '该幂等键已用于不同输入，请使用新的 Idempotency-Key')
        return {'id': str(row[0]), 'status': row[1], 'reused': True}


def get_job(job_id: str, current_user: dict) -> dict:
    require_jobs_enabled()
    require_finance_access(current_user)
    row = fetch_one('''SELECT id,user_id,position,kind,status,result,error_code,attempt_count,
                       created_at,started_at,finished_at,next_attempt_at,max_attempts FROM background_jobs WHERE id=%s''', (job_id,))
    if row is None or (current_user['role'] != 'admin' and (
        str(row[1]) != current_user['id'] or row[2] != current_user.get('position')
    )):
        raise HTTPException(404, '任务不存在或无权访问')
    return {'id': str(row[0]), 'kind': row[3], 'status': row[4], 'result': row[5],
            'error_code': row[6], 'attempt_count': row[7],
            'created_at': row[8], 'started_at': row[9], 'finished_at': row[10],
            'next_attempt_at': row[11], 'max_attempts': row[12]}


def require_finance_access(current_user: dict) -> None:
    from app.services.user_ai_app_permission_service import is_ai_app_allowed
    if current_user['role'] != 'admin' and (current_user.get('position') != 'finance' or
            not is_ai_app_allowed(current_user, 'finance-reconciliation')):
        # Keep task identifiers private, matching the ownership check in get_job.
        raise HTTPException(404, '任务不存在或无权访问')


def list_jobs(current_user: dict, limit: int = 50) -> dict:
    require_jobs_enabled()
    require_finance_access(current_user)
    rows = fetch_all('''SELECT id,kind,status,result,error_code,attempt_count,
                       created_at,started_at,finished_at,next_attempt_at,max_attempts FROM background_jobs
                       WHERE user_id=%s AND position IS NOT DISTINCT FROM %s
                       AND kind='finance_reconciliation'
                       ORDER BY (status IN ('queued','running')) DESC,created_at DESC LIMIT %s''',
                     (current_user['id'], current_user.get('position'), limit))
    keys = ('id', 'kind', 'status', 'result', 'error_code', 'attempt_count',
            'created_at', 'started_at', 'finished_at', 'next_attempt_at', 'max_attempts')
    return {'items': [dict(zip(keys, (str(row[0]), *row[1:]))) for row in rows]}


def cleanup_expired_job_inputs() -> int:
    """Delete only terminal job inputs; retain hashes for idempotency validation."""
    from datetime import datetime, timezone
    import logging
    from app.artifact_storage import delete_artifact
    from app.db import fetch_all, execute
    if not settings.background_jobs_enabled:
        return 0
    rows = fetch_all('''SELECT id,payload FROM background_jobs
        WHERE status IN ('succeeded','failed')
          AND finished_at < now()-(%s * interval '1 day')
          AND payload->>'inputs_cleaned_at' IS NULL
        ORDER BY finished_at LIMIT 100''', (settings.background_job_input_retention_days,))
    cleaned = 0
    for job_id, payload in rows:
        try:
            for item in payload.get('files', []):
                if item.get('storage_reference'):
                    delete_artifact(item['storage_reference'])
        except Exception as error:
            logging.getLogger(__name__).warning('Job input cleanup failed: %s', type(error).__name__)
            continue
        payload = {**payload, 'files': [{k: v for k, v in item.items() if k != 'storage_reference'}
                                      for item in payload.get('files', [])],
                   'inputs_cleaned_at': datetime.now(timezone.utc).isoformat()}
        execute('UPDATE background_jobs SET payload=%s WHERE id=%s', (Jsonb(payload), job_id))
        cleaned += 1
    return cleaned
