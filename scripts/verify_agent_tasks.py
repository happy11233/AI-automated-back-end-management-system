"""Real login/API/PostgreSQL verification in a disposable database; no model calls."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
import json
import os
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['LANGSMITH_TRACING'] = 'false'


def main():
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from app.config import settings

    original_url = settings.database_url
    database_name = 'company_rag_tasks_verification_' + uuid4().hex[:12]
    with psycopg.connect(original_url, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database_name)))
    verify_url = make_conninfo(original_url, dbname=database_name)
    settings.database_url = verify_url
    settings.langsmith_tracing = False
    try:
        with psycopg.connect(verify_url) as conn:
            conn.execute((ROOT / 'sql/schema.sql').read_text())
            # Replay the new migration twice to verify idempotence on new installs.
            for _ in range(2):
                conn.execute((ROOT / 'sql/024_agent_tasks.sql').read_text())
        verify_http(verify_url)
        env = {**os.environ, 'DATABASE_URL': verify_url, 'LANGSMITH_TRACING': 'false'}
        result = subprocess.run([sys.executable, str(ROOT/'scripts/verify_sql_migrations.py'), '--mode', 'all'],
                                env=env, cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stderr or result.stdout)
        report = json.loads(result.stdout)
        assert report['ok']
        print(json.dumps({'ok': True, 'migration_replay': report['runtime']['migration_count'],
                          'tables': report['runtime']['table_count'], 'database_isolated': True}))
    finally:
        from app.db import close_pool
        close_pool()
        with psycopg.connect(original_url, autocommit=True) as admin:
            admin.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s', (database_name,))
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database_name)))
        print('Cleaned disposable verification database; existing demo database unchanged.')


def verify_http(url):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.auth.security import hash_password
    from app.api.auth import router as auth_router
    from app.api.agent_tasks import router as task_router
    from app.api.files import router as files_router
    from app.db import open_pool, pool
    from app.services.run_record_service import start_run, finish_run, record_step
    from app.services.generated_file_service import save_generated_file
    from app.artifact_storage import delete_artifact

    open_pool()
    marker = 'task-check-' + uuid4().hex[:8]
    password = uuid4().hex
    accounts = {}
    storage_reference = None
    with pool.connection() as conn:
        for name in ('admin', 'operations', 'other_operations', 'finance', 'customer_service'):
            uid = str(uuid4())
            position = 'operations' if name == 'other_operations' else None if name == 'admin' else name
            conn.execute('INSERT INTO users(id,username,role,position,password_hash) VALUES (%s,%s,%s,%s,%s)',
                         (uid, marker+name, 'admin' if name == 'admin' else 'employee', position, hash_password(password)))
            accounts[name] = {'id': uid, 'username': marker+name,
                              'role': 'admin' if name == 'admin' else 'employee', 'position': position}
        conn.commit()

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(task_router)
    app.include_router(files_router)
    with TestClient(app) as client:
        for account in accounts.values():
            response = client.post('/auth/login', data={'username': account['username'], 'password': password})
            response.raise_for_status()
            account['headers'] = {'Authorization': 'Bearer ' + response.json()['access_token']}

        def request(name, method, path, expected=200, key=None, **kwargs):
            headers = {**accounts[name]['headers']}
            if key:
                headers['Idempotency-Key'] = key
            response = client.request(method, path, headers=headers, **kwargs)
            assert response.status_code == expected, (method, path, response.status_code, response.text[:700])
            return response.json()

        assert client.get('/agent-tasks').status_code == 401
        assert client.get('/agent-tasks/stores').status_code == 401
        store_data = dict(platform='amazon', external_store_id=marker, marketplace='US', name='隔离验收店铺 A')
        request('operations', 'POST', '/agent-tasks/stores', 403, json=store_data)
        store_a = request('admin', 'POST', '/agent-tasks/stores', 201, json=store_data)['item']['id']
        store_b = request('admin', 'POST', '/agent-tasks/stores', 201,
                          json={**store_data, 'external_store_id': marker+'-b', 'name': '隔离验收店铺 B'})['item']['id']
        request('admin', 'POST', '/agent-tasks/stores', 409, json=store_data)
        grant = dict(user_id=accounts['operations']['id'], position='operations', enabled=True)
        for store_id in (store_a, store_b):
            request('admin', 'PUT', f'/agent-tasks/stores/{store_id}/grants', json=grant)
        request('admin', 'PUT', f'/agent-tasks/stores/{store_a}/grants', 422,
                json={**grant, 'position': 'finance'})
        assert len(request('operations', 'GET', '/agent-tasks/stores')['items']) == 2
        assert request('other_operations', 'GET', '/agent-tasks/stores')['items'] == []

        body = dict(workflow_id='operations_listing_launch', goal='准备验收 SKU 的上架资料',
                    store_id=store_a, objects=[dict(object_type='order', external_id='SAME-ORDER-001')],
                    expected_outputs=['上架草稿'], completion_criteria=['平台接受并可追溯'])
        request('finance', 'POST', '/agent-tasks', 404, key=marker+'-deny', json=body)
        request('other_operations', 'POST', '/agent-tasks', 404, key=marker+'-deny', json=body)
        request('operations', 'POST', '/agent-tasks', 422, key=marker+'-bad', json={**body, 'goal': ' '})
        request('operations', 'POST', '/agent-tasks', 422, key=marker+'-bad', json={**body, 'store_id': None})
        request('operations', 'POST', '/agent-tasks', 422, key=marker+'-bad',
                json={**body, 'objects': [{'object_type': 'order_line', 'external_id': 'O-1'}]})
        request('operations', 'POST', '/agent-tasks', 422, key=marker+'-bad', json={**body, 'source': 'schedule'})
        created = request('operations', 'POST', '/agent-tasks', 201, key=marker+'-first', json=body)
        task_id = created['item']['id']
        assert created['item']['status'] == 'draft' and not created['reused']
        assert created['item']['policy_snapshot']['external_execution_enabled'] is False
        repeated = request('operations', 'POST', '/agent-tasks', 201, key=marker+'-first', json=body)
        assert repeated['reused'] and repeated['item']['id'] == task_id
        request('operations', 'POST', '/agent-tasks', 409, key=marker+'-first', json={**body, 'goal': '改动目标'})
        other_task = request('operations', 'POST', '/agent-tasks', 201, key=marker+'-second',
                             json={**body, 'store_id': store_b})['item']['id']
        detail = request('operations', 'GET', f'/agent-tasks/{task_id}')
        other_detail = request('operations', 'GET', f'/agent-tasks/{other_task}')
        assert detail['objects'][0]['id'] != other_detail['objects'][0]['id']
        assert detail['store']['id'] == store_a and other_detail['store']['id'] == store_b
        assert detail['runs'] == [] and detail['artifacts'] == []
        for name in ('other_operations', 'finance'):
            request(name, 'GET', f'/agent-tasks/{task_id}', 404)
            assert request(name, 'GET', '/agent-tasks')['total'] == 0
        request('operations', 'GET', '/agent-tasks/not-a-uuid', 422)
        for query in ('status=unknown', 'offset=-1', 'limit=0', 'limit=101'):
            request('operations', 'GET', '/agent-tasks?'+query, 422)
        page = request('operations', 'GET', '/agent-tasks?limit=1&offset=1')
        assert page['total'] == 2 and len(page['items']) == 1
        assert request('operations', 'GET', '/agent-tasks?status=succeeded')['total'] == 0

        def new_run(account='operations', app_id='operations_listing_launch', store=store_a):
            return start_run(run_type='task_verification', app_id=app_id, app_name='隔离运行证据',
                             entrypoint='verification', current_user=accounts[account],
                             metadata={'store_id': store} if store else {})

        wrong = new_run('other_operations')
        request('operations', 'POST', f'/agent-tasks/{task_id}/runs', 404, json={'run_id': wrong})
        wrong_store = new_run(store=store_b)
        request('operations', 'POST', f'/agent-tasks/{task_id}/runs', 409, json={'run_id': wrong_store})
        missing_store = new_run(store=None)
        request('operations', 'POST', f'/agent-tasks/{task_id}/runs', 409, json={'run_id': missing_store})
        runs = [new_run() for _ in range(2)]
        for index, run_id in enumerate(runs, 1):
            finish_run(run_id, status_value='succeeded', output_text='只证明运行结果，不证明上架已完成')
            record_step(run_id=run_id, step_name='verify.input', status_value='succeeded', step_order=1)
            linked = request('operations', 'POST', f'/agent-tasks/{task_id}/runs', json={'run_id': run_id})
            assert linked['attempt_number'] == index
        assert request('operations', 'POST', f'/agent-tasks/{task_id}/runs', json={'run_id': runs[0]})['reused']

        artifact_id = save_generated_file(run_id=runs[0], content=b'isolated artifact evidence', filename='task-evidence.txt',
            artifact_type='report_file', mime_type='text/plain', current_user=accounts['operations'])
        with pool.connection() as conn:
            storage_reference = conn.execute('SELECT storage_path FROM automation_run_artifacts WHERE id=%s',
                                             (artifact_id,)).fetchone()[0]
        try:
            detail = request('operations', 'GET', f'/agent-tasks/{task_id}')
            assert len(detail['runs']) == 2 and len(detail['steps']) == 2 and len(detail['artifacts']) == 1
            assert detail['item']['status'] == 'draft'
            assert client.get(f'/files/{artifact_id}/download', headers=accounts['operations']['headers']).content == b'isolated artifact evidence'
            request('other_operations', 'GET', f'/files/{artifact_id}/download', 403)
        finally:
            delete_artifact(storage_reference)

        # A revoked store or AI application grant must immediately hide tasks.
        request('admin', 'PUT', f'/agent-tasks/stores/{store_a}/grants', json={**grant, 'enabled': False})
        request('operations', 'GET', f'/agent-tasks/{task_id}', 404)
        request('operations', 'POST', '/agent-tasks', 404, key=marker+'-first', json=body)
        assert request('operations', 'GET', '/agent-tasks')['total'] == 1
        request('admin', 'PUT', f'/agent-tasks/stores/{store_a}/grants', json=grant)
        with pool.connection() as conn:
            conn.execute('INSERT INTO user_ai_app_permissions(user_id,app_id,enabled) VALUES (%s,%s,false)',
                         (accounts['operations']['id'], 'automation-listing'))
            conn.commit()
        request('operations', 'GET', f'/agent-tasks/{task_id}', 404)
        assert request('operations', 'GET', '/agent-tasks')['total'] == 0
        with pool.connection() as conn:
            conn.execute('DELETE FROM user_ai_app_permissions WHERE user_id=%s', (accounts['operations']['id'],))
            conn.commit()

        # Real concurrent HTTP requests share a real PostgreSQL uniqueness constraint.
        def register_concurrent(_):
            return request('operations', 'POST', '/agent-tasks', 201, key=marker+'-concurrent', json=body)
        with ThreadPoolExecutor(max_workers=4) as executor:
            responses = list(executor.map(register_concurrent, range(8)))
        assert len({r['item']['id'] for r in responses}) == 1
        assert sum(not r['reused'] for r in responses) == 1
        for name, workflow in [('finance','finance_reconciliation'), ('customer_service','customer_service_message_loop')]:
            result = request(name, 'POST', '/agent-tasks', 201, key=marker+'-'+name,
                             json={'workflow_id': workflow, 'goal': '隔离岗位任务验收'})
            assert result['item']['position'] == name
        print(json.dumps({'ok': True, 'checks': ['real_login_5_roles', 'store_grants', 'object_scope',
            'cross_store_same_order', 'idempotency', 'concurrent_creation', 'input_validation', 'pagination',
            'run_attempts', 'store_evidence', 'artifact_ownership', 'revocation', 'three_positions',
            'run_success_is_not_business_success'], 'external_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
