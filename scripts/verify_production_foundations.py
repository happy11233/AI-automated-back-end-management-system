"""Local contracts + optional real API / Redis integration; no fake services."""
from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def verify_local():
    from app.observability import observed, request_id_var, submit_with_context, PrivateTracingClient
    from app.artifact_storage import put_artifact, read_artifact, delete_artifact, artifact_exists
    from app.config import settings

    @observed('verification.local')
    def increment(value):
        return value+1

    @observed('verification.async')
    async def increment_async(value):
        return value+1

    assert increment(2) == 3
    assert asyncio.run(increment_async(2)) == 3
    token = request_id_var.set(str(uuid4()))
    try:
        with ThreadPoolExecutor(2) as executor:
            assert submit_with_context(executor, request_id_var.get).result() == request_id_var.get()
    finally:
        request_id_var.reset(token)
    safe = PrivateTracingClient._private_fields({
        'error': 'password=secret; salary=123', 'events': [{'password': 'secret'}],
        'attachments': {'salary': 'private'}, 'extra': {'metadata': {'salary': '123', 'request_id': 'safe-id'}},
    })
    assert safe['extra'] == {'metadata': {'request_id': 'safe-id'}}
    assert 'secret' not in repr(safe) and '123' not in repr(safe)
    assert 'events' not in safe and 'attachments' not in safe
    reference = put_artifact('verification-'+uuid4().hex+'.txt', b'local storage verification', 'text/plain')
    try:
        assert artifact_exists(reference)
        assert read_artifact(reference) == b'local storage verification'
    finally:
        delete_artifact(reference)
    assert not artifact_exists(reference)
    print('PASS local: sync/async tracing wrappers, thread context, private fields, storage roundtrip')


def verify_redis():
    from app.cache import cache_get, cache_set, cache_delete, redis_client
    from app.rate_limit import check_limit
    identity = 'verification-'+uuid4().hex
    assert redis_client() is not None
    assert redis_client().ping()
    try:
        cache_set('verification', identity, {'value': 12}, 10)
        assert cache_get('verification', identity) == {'value': 12}
        with ThreadPoolExecutor(8) as executor:
            results = list(executor.map(lambda _: check_limit(identity, 'verification', 5)[0], range(20)))
        assert sum(results) == 5, results
    finally:
        cache_delete('verification', identity)
        from app.cache import cache_key
        redis_client().delete(cache_key('rate:verification', identity))
    assert cache_get('verification', identity) is None
    print('PASS real Redis: read/write/delete and concurrent atomic rate limit')


def verify_api(base_url: str):
    import httpx
    from openpyxl import Workbook, load_workbook
    with httpx.Client(base_url=base_url, timeout=45) as client:
        response = client.get('/ready')
        response.raise_for_status()
        assert response.headers.get('x-request-id')
        assert client.get('/metrics').status_code == 404
        from app.config import settings
        if settings.metrics_token:
            metrics = client.get('/metrics', headers={'Authorization': 'Bearer '+settings.metrics_token})
            metrics.raise_for_status()
            assert 'company_rag_http_requests_total' in metrics.text
        tokens = {}
        for name, password in [('finance_demo','Finance123456'), ('operations_demo','Operations123456')]:
            response = client.post('/auth/login', data={'username': name, 'password': password})
            response.raise_for_status()
            tokens[name] = response.json()['access_token']
        finance = {'Authorization': 'Bearer '+tokens['finance_demo']}
        operations = {'Authorization': 'Bearer '+tokens['operations_demo']}
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Amazon结算订单'
        sheet.append(['订单号','SKU','销售金额','数量','币种'])
        sheet.append(['VERIFICATION-ORDER', 'VERIFICATION-SKU', 100, 1, 'CNY'])
        output = BytesIO()
        workbook.save(output)
        content = output.getvalue()
        key = 'verification-'+uuid4().hex
        files = [('files', ('settlement.xlsx', content, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))]
        rejected = client.post('/jobs/finance-reconciliation', headers={**operations, 'Idempotency-Key': key}, files=files)
        assert rejected.status_code == 403, rejected.text
        response = client.post('/jobs/finance-reconciliation', headers={**finance, 'Idempotency-Key': key}, files=files)
        assert response.status_code == 202, response.text
        job = response.json()
        repeated = client.post('/jobs/finance-reconciliation', headers={**finance, 'Idempotency-Key': key}, files=files)
        assert repeated.status_code == 202 and repeated.json()['id'] == job['id'] and repeated.json()['reused']
        conflict = client.post('/jobs/finance-reconciliation', headers={**finance, 'Idempotency-Key': key},
                               data={'instruction':'different input'}, files=files)
        assert conflict.status_code == 409, conflict.text
        assert client.get(job['status_url'], headers=operations).status_code == 404
        deadline = time.monotonic()+120
        while True:
            response = client.get(job['status_url'], headers=finance)
            response.raise_for_status()
            result = response.json()
            assert result['status'] != 'failed', result
            if result['status'] == 'succeeded':
                break
            if time.monotonic() >= deadline:
                raise AssertionError('Real worker did not finish before deadline: '+repr(result))
            time.sleep(0.5)
        download = client.get(result['result']['download_url'], headers=finance)
        download.raise_for_status()
        assert load_workbook(BytesIO(download.content)).sheetnames
        assert client.get(result['result']['download_url'], headers=operations).status_code == 403
        print('PASS real API: login, RBAC, upload, idempotency, conflict, Outbox/Worker, XLSX download and ownership')
        print('Verification job:', job['id'])
        return job['id']


def verify_worker_recovery(job_id: str):
    """Real broker/worker redelivery, then Outbox recovery in an isolated test DB."""
    from urllib.parse import urlparse
    from app.config import settings
    from app.celery_app import celery_app
    from app.db import open_pool, close_pool, fetch_one, execute
    # These checks deliberately mutate a previously completed test job.
    assert urlparse(settings.database_url).path.endswith('_verification'), 'Use an isolated *_verification database'
    open_pool()
    try:
        row = fetch_one('SELECT idempotency_key,status,result FROM background_jobs WHERE id=%s', (job_id,))
        assert row[0].startswith('verification-') and row[1] == 'succeeded'
        original = row[2]
        def counts():
            return fetch_one('''SELECT count(DISTINCT r.id),count(a.id)
                FROM automation_runs r LEFT JOIN automation_run_artifacts a ON a.run_id=r.id
                WHERE r.resource_type='background_job' AND r.resource_id=%s''', (job_id,))
        original_counts = counts()
        def wait_for_recovery():
            deadline = time.monotonic()+90
            while time.monotonic() < deadline:
                state = fetch_one('SELECT status,result FROM background_jobs WHERE id=%s', (job_id,))
                assert state[0] != 'failed', state
                if state[0] == 'succeeded':
                    assert state[1] == original and counts() == original_counts
                    return
                time.sleep(0.5)
            raise AssertionError('Worker recovery deadline exceeded')
        execute("UPDATE background_jobs SET status='running',result='{}'::jsonb,attempt_count=0 WHERE id=%s", (job_id,))
        execute("UPDATE task_outbox SET published_at=now()-interval '16 minutes' WHERE job_id=%s", (job_id,))
        wait_for_recovery()
        assert fetch_one('SELECT published_at > now()-interval \'1 minute\' FROM task_outbox WHERE job_id=%s', (job_id,))[0]
        execute("UPDATE background_jobs SET status='running',result='{}'::jsonb,attempt_count=0 WHERE id=%s", (job_id,))
        celery_app.send_task('jobs.execute', args=[job_id], retry=False)
        celery_app.send_task('jobs.execute', args=[job_id], retry=False)
        wait_for_recovery()
        print('PASS real worker: duplicate delivery, published artifact recovery and stranded Outbox repair; no duplicate artifacts')
    finally:
        close_pool()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--redis', action='store_true')
    parser.add_argument('--api-base-url')
    parser.add_argument('--worker-recovery', action='store_true')
    args = parser.parse_args()
    verify_local()
    if args.redis:
        verify_redis()
    if args.api_base_url:
        job_id = verify_api(args.api_base_url)
        if args.worker_recovery:
            verify_worker_recovery(job_id)
