"""Local PostgreSQL fault injection for Celery job retry state transitions."""
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from celery.exceptions import Retry
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import close_pool, execute, fetch_one, open_pool
from app.services.background_job_service import get_job, list_jobs
from app.tasks import execute_job


def create_fixture(user_id: str, *, max_attempts: int) -> str:
    job_id = str(uuid4())
    execute("""INSERT INTO background_jobs
        (id,user_id,position,kind,idempotency_key,payload_hash,payload,request_id,max_attempts,next_attempt_at)
        VALUES (%s,%s,'finance','finance_reconciliation',%s,'test',%s,%s,%s,now())""",
        (job_id, user_id, f'verify-retries-{job_id}',
         Jsonb({'files': [], 'instruction': 'verify', 'base_currency': 'USD'}),
         f'retry-test-{job_id}', max_attempts))
    execute('INSERT INTO task_outbox(job_id) VALUES (%s)', (job_id,))
    return job_id


def state(job_id: str):
    return fetch_one('''SELECT status,attempt_count,error_code,next_attempt_at,
        (SELECT published_at FROM task_outbox WHERE job_id=background_jobs.id)
        FROM background_jobs WHERE id=%s''', (job_id,))


def run_check():
    open_pool()
    job_ids = []
    try:
        user = fetch_one("SELECT id,username,role,position FROM users WHERE role='admin' LIMIT 1")
        assert user, 'local verification requires an admin fixture'
        current_user = {'id': str(user[0]), 'username': user[1], 'role': 'admin', 'position': 'finance'}
        result = SimpleNamespace(content=b'fixture', filename='review.xlsx',
                                 metadata={'review_status': 'requires_input'})
        with patch('app.auth.security.get_user_by_id', return_value=current_user), \
             patch('app.services.generated_file_service.save_generated_file', return_value=str(uuid4())):
            job_id = create_fixture(current_user['id'], max_attempts=3)
            job_ids.append(job_id)
            reconciliation = Mock(side_effect=[TimeoutError('once'), result])
            with patch('app.services.finance_reconciliation_service.reconcile_finance_workbooks', reconciliation), \
                 patch.object(execute_job, 'retry', side_effect=Retry()) as retry:
                try:
                    outcome = execute_job.run(job_id)
                    raise AssertionError(f'transient error was not retried: outcome={outcome!r}, state={state(job_id)!r}')
                except Retry:
                    pass
                first = state(job_id)
                assert first[0] == 'queued' and first[1] == 1, first
                assert first[2] == 'temporary_TimeoutError' and first[3] is not None and first[4] is None
                visible = get_job(job_id, current_user)
                assert visible['next_attempt_at'] == first[3] and visible['max_attempts'] == 3
                assert any(item['id'] == job_id and item['next_attempt_at'] == first[3]
                           for item in list_jobs(current_user)['items'])
                assert retry.call_count == 1
                execute_job.run(job_id)
                assert state(job_id)[1] == 1 and reconciliation.call_count == 1, 'early redelivery ran before due time'
                execute('UPDATE background_jobs SET next_attempt_at=now() WHERE id=%s', (job_id,))
                execute_job.run(job_id)
                success = state(job_id)
                assert success[0] == 'succeeded' and success[1] == 2
                assert success[2] is None and success[3] is None and reconciliation.call_count == 2

            permanent_id = create_fixture(current_user['id'], max_attempts=3)
            job_ids.append(permanent_id)
            with patch('app.services.finance_reconciliation_service.reconcile_finance_workbooks', side_effect=ValueError('bad input')), \
                 patch.object(execute_job, 'retry', side_effect=Retry()) as retry:
                try:
                    execute_job.run(permanent_id)
                    raise AssertionError('permanent error was accepted')
                except ValueError:
                    pass
                permanent = state(permanent_id)
                assert permanent[0] == 'failed' and permanent[1] == 1 and permanent[2] == 'ValueError'
                assert retry.call_count == 0

            exhausted_id = create_fixture(current_user['id'], max_attempts=2)
            job_ids.append(exhausted_id)
            with patch('app.services.finance_reconciliation_service.reconcile_finance_workbooks', side_effect=TimeoutError('always')), \
                 patch.object(execute_job, 'retry', side_effect=Retry()) as retry:
                try:
                    execute_job.run(exhausted_id)
                    raise AssertionError('first transient error was accepted')
                except Retry:
                    pass
                execute('UPDATE background_jobs SET next_attempt_at=now() WHERE id=%s', (exhausted_id,))
                try:
                    execute_job.run(exhausted_id)
                    raise AssertionError('exhausted job was accepted')
                except TimeoutError:
                    pass
                exhausted = state(exhausted_id)
                assert exhausted[0] == 'failed' and exhausted[1] == 2
                assert exhausted[2] == 'attempts_exhausted_TimeoutError' and exhausted[3] is None
                assert retry.call_count == 1
        print('background job retry checks passed: recovery, permanent failure, exhausted attempts')
    finally:
        for job_id in job_ids:
            execute("DELETE FROM automation_runs WHERE resource_type='background_job' AND resource_id=%s", (job_id,))
            execute('DELETE FROM background_jobs WHERE id=%s', (job_id,))
        close_pool()


if __name__ == '__main__':
    run_check()
