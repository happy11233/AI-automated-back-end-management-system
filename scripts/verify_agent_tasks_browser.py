"""Run real browser/login/API checks on a disposable PostgreSQL database and ports."""
from pathlib import Path
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['LANGSMITH_TRACING'] = 'false'


def unused_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def ready(url, process, log):
    import httpx
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Verification service exited: ' + log.read_text()[-3000:])
        try:
            if httpx.get(url, timeout=2, trust_env=False).status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(0.3)
    raise TimeoutError('Verification service did not become ready: ' + log.read_text()[-1500:])


def verification_app():
    """Serve the real task/auth/workflow routers and built UI in one isolated process."""
    from fastapi import FastAPI
    from app.db import open_pool
    from app.api.auth import router as auth_router
    from app.api.agent_tasks import router as task_router
    from app.api.ai_workflows import router as workflow_router
    from app.api.notifications import router as notification_router
    from app.api.files import router as files_router
    from starlette.responses import FileResponse
    from starlette.staticfiles import StaticFiles
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(task_router)
    app.include_router(workflow_router)
    app.include_router(notification_router)
    app.include_router(files_router)
    open_pool()
    @app.get('/health')
    def health():
        return {'status': 'ok'}

    assets = StaticFiles(directory=ROOT/'frontend/dist/assets')

    async def combined(scope, receive, send):
        if scope['type'] != 'http':
            return await app(scope, receive, send)
        path = scope['path']
        if path.startswith('/api/'):
            forwarded = {**scope, 'path': path[4:], 'raw_path': path[4:].encode()}
            return await app(forwarded, receive, send)
        if path.startswith('/assets/'):
            return await assets({**scope, 'path': path[7:]}, receive, send)
        return await FileResponse(ROOT/'frontend/dist/index.html')(scope, receive, send)

    return combined


def main():
    import httpx
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from app.config import settings
    from app.auth.security import hash_password

    original_url = settings.database_url
    database_name = 'company_rag_browser_verification_' + uuid4().hex[:12]
    with psycopg.connect(original_url, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database_name)))
    verify_url = make_conninfo(original_url, dbname=database_name)
    processes, handles = [], []
    try:
        with tempfile.TemporaryDirectory(prefix='company-agent-tasks-') as directory:
            work = Path(directory)
            api_port = unused_port()
            frontend = f'http://127.0.0.1:{api_port}'
            api = frontend + '/api'
            password = secrets.token_urlsafe(24)
            accounts = {}
            with psycopg.connect(verify_url) as conn:
                conn.execute((ROOT/'sql/schema.sql').read_text())
                for name in ('admin', 'operations', 'other_operations', 'finance', 'customer_service'):
                    uid = str(uuid4())
                    position = 'operations' if name == 'other_operations' else None if name == 'admin' else name
                    username = 'task-browser-' + uuid4().hex[:8]
                    conn.execute('INSERT INTO users(id,username,role,position,password_hash) VALUES (%s,%s,%s,%s,%s)',
                                 (uid, username, 'admin' if name == 'admin' else 'employee', position, hash_password(password)))
                    accounts[name] = {'id': uid, 'username': username, 'password': password}
            env = {**os.environ, 'DATABASE_URL': verify_url, 'LANGSMITH_TRACING': 'false',
                   'LANGSMITH_API_KEY': '', 'LANGCHAIN_TRACING_V2': 'false',
                   'JWT_SECRET_KEY': secrets.token_urlsafe(48), 'APP_ENVIRONMENT': 'development',
                   'BACKGROUND_JOBS_ENABLED': 'false', 'CONTEXT_CLEANUP_SCHEDULER': 'celery',
                   'RATE_LIMIT_ENABLED': 'false', 'REDIS_URL': '',
                   'DASHSCOPE_API_KEY': 'unused-browser-verification',
                   'BAILIAN_BASE_URL': 'http://127.0.0.1:9/v1',
                   'CORS_ALLOWED_ORIGINS': frontend, 'ARTIFACT_STORAGE_BACKEND': 'local',
                   'GENERATED_FILE_STORAGE_DIR': str(work/'files'),
                   'ERP_BASE_URL': '', 'ERP_API_KEY': '', 'ERP_API_SECRET': '',
                   'ERP_KINGDEE_BASE_URL': '', 'ERP_YONYOU_BASE_URL': '',
                   'ENTERPRISE_WECHAT_WEBHOOK_URL': '', 'FINANCE_WECHAT_MAC_RPA_ENABLED': 'false',
                   'DESKTOP_AGENT_MAC_AUTOMATION_ENABLED': 'false', 'AMAZON_PLAYWRIGHT_ENABLED': 'false',
                   'MESSAGE_SENDER_REAL_SEND_ENABLED': 'false',
                   'VITE_API_BASE_URL': api}
            for cmd, cwd, log_name in (
                ([sys.executable, '-m', 'uvicorn', 'scripts.verify_agent_tasks_browser:verification_app', '--factory', '--host', '127.0.0.1', '--port', str(api_port)], ROOT, 'api.log'),
            ):
                handle = (work/log_name).open('w')
                handles.append(handle)
                processes.append(subprocess.Popen(cmd, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT))
            ready(frontend+'/health', processes[0], work/'api.log')
            ready(frontend, processes[0], work/'api.log')
            workflows = {'operations': 'operations_listing_launch', 'finance': 'finance_reconciliation',
                         'customer_service': 'customer_service_message_loop'}
            with httpx.Client(base_url=api, timeout=15, trust_env=False) as client:
                tokens = {}
                for name, account in accounts.items():
                    response = client.post('/auth/login', data={'username': account['username'], 'password': password})
                    response.raise_for_status()
                    tokens[name] = {'Authorization': 'Bearer ' + response.json()['access_token']}
                response = client.post('/agent-tasks/stores', headers=tokens['admin'], json={
                    'platform': 'amazon', 'external_store_id': 'browser-verification', 'marketplace': 'US', 'name': '浏览器隔离验收店铺'})
                response.raise_for_status()
                store_id = response.json()['item']['id']
                for name, workflow in workflows.items():
                    response = client.put(f'/agent-tasks/stores/{store_id}/grants', headers=tokens['admin'],
                                          json={'user_id': accounts[name]['id'], 'position': name})
                    response.raise_for_status()
                    for index in range(12 if name == 'operations' else 1):
                        response = client.post('/agent-tasks', headers={**tokens[name], 'Idempotency-Key': uuid4().hex}, json={
                            'workflow_id': workflow, 'goal': f'隔离验收 {name} 任务 {index + 1}', 'store_id': store_id})
                        response.raise_for_status()
                        if index == 0:
                            accounts[name]['task_id'] = response.json()['item']['id']
            state = work/'state.json'
            state.write_text(json.dumps({'accounts': accounts, 'api': api, 'frontend': frontend,
                                         'store_id': store_id, 'evidence_dir': str(work)}, ensure_ascii=False))
            state.chmod(0o600)
            result = subprocess.run(['node', str(ROOT/'scripts/verify_agent_tasks_frontend.mjs'), str(state)],
                                    cwd=ROOT, env=env, text=True, capture_output=True, timeout=240)
            if result.returncode:
                raise AssertionError(result.stdout[-2500:] + result.stderr[-3500:])
            print(result.stdout)
            # Keep credential-free screenshots for an explicit visual review.
            for screenshot in work.glob('tasks-*.png'):
                destination = Path(tempfile.gettempdir()) / screenshot.name
                destination.write_bytes(screenshot.read_bytes())
            print(json.dumps({'database_isolated': True, 'full_app': True, 'model_calls': 0,
                              'platform_actions': 0, 'evidence': '/tmp/tasks-*.png'}))
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for handle in handles:
            handle.close()
        with psycopg.connect(original_url, autocommit=True) as admin:
            admin.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s', (database_name,))
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database_name)))
        print('Cleaned isolated services and database; existing services unchanged.')


if __name__ == '__main__':
    main()
