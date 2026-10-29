"""Real PostgreSQL + authenticated HTTP checks; prices use the product's mock adapter.

Run with the project environment. Creates a private schema and removes it on exit.
--serve leaves the isolated HTTP API running for browser verification until interrupted.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from dotenv import dotenv_values
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()
    url = os.environ.get('VERIFY_DATABASE_URL') or os.environ.get('DATABASE_URL') or dotenv_values(ROOT / '.env')['DATABASE_URL']
    url = url.replace('host.docker.internal', '127.0.0.1')
    schema = 'verify_competitor_' + uuid4().hex[:12]
    with psycopg.connect(url, connect_timeout=6) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    scoped_url = make_conninfo(url, options=f'-c search_path={schema},public', connect_timeout=6)
    os.environ.update({'DATABASE_URL': scoped_url, 'VECTOR_DATABASE_URL': scoped_url,
                      'DASHSCOPE_API_KEY': 'unused-competitor-mock',
                      'JWT_SECRET_KEY': secrets.token_hex(32), 'REDIS_URL': '',
                      'LANGSMITH_TRACING': 'false', 'RATE_LIMIT_ENABLED': 'false'})
    server = thread = None
    from app.db import open_pool, close_pool, pool
    try:
        # Use the actual full schema, including the new snapshot migration.
        with psycopg.connect(scoped_url) as conn:
            conn.execute((ROOT / 'sql/schema.sql').read_text())
            conn.execute((ROOT / 'sql/025_competitor_monitor.sql').read_text())
            conn.execute((ROOT / 'sql/025_competitor_monitor.sql').read_text())
        from app.auth.security import hash_password
        password = secrets.token_hex(16)
        accounts = {}
        with psycopg.connect(scoped_url) as conn:
            for name in ('operations', 'other', 'denied', 'finance', 'customer_service', 'admin'):
                uid, username = str(uuid4()), schema + '_' + name
                position = 'operations' if name in ('operations', 'other', 'denied') else None if name == 'admin' else name
                conn.execute('''INSERT INTO users(id,username,role,position,password_hash,created_at)
                    VALUES (%s,%s,%s,%s,%s,now()-interval '1 day')''',
                    (uid, username, 'admin' if name == 'admin' else 'employee', position, hash_password(password)))
                accounts[name] = {'id': uid, 'username': username}
            conn.execute('INSERT INTO user_ai_app_permissions(user_id,app_id,enabled) VALUES (%s,%s,false)',
                         (accounts['denied']['id'], 'automation-competitor_analysis'))
        from contextlib import asynccontextmanager
        from fastapi import Depends, FastAPI, HTTPException
        from fastapi.security import OAuth2PasswordRequestForm
        from fastapi.middleware.cors import CORSMiddleware
        from app.auth.security import authenticate_user, create_access_token
        from app.api.competitor_monitor import router as monitor_router
        from app.services.competitor_monitor_service import (
            INSPECTION_HOURS, MONITOR_TIMEZONE, MockPriceProvider, analyze_prices,
            latest_due_slot, next_inspection, run_scheduled_inspections)
        import requests
        import uvicorn

        @asynccontextmanager
        async def lifespan(app):
            open_pool()
            yield
            close_pool()

        app = FastAPI(lifespan=lifespan)
        app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5173'], allow_headers=['*'], allow_methods=['*'])
        app.include_router(monitor_router)

        @app.post('/auth/login')
        def login(form=Depends(OAuth2PasswordRequestForm)):
            # Production password verification, token creation and get_current_user.
            # Keep the test app independent of unrelated LLM/ERP startup effects.
            user = authenticate_user(form.username, form.password)
            if not user:
                raise HTTPException(401, 'Invalid credentials')
            return {**{key: value for key, value in user.items() if key != 'password_hash'},
                    'access_token': create_access_token({'sub': user['id']}), 'token_type': 'bearer'}
        sock = socket.socket()
        sock.bind((os.environ.get('VERIFY_HTTP_HOST', '127.0.0.1'), int(os.environ.get('VERIFY_HTTP_PORT', '0'))))
        base = f'http://127.0.0.1:{sock.getsockname()[1]}'
        server = uvicorn.Server(uvicorn.Config(app, log_level='error', access_log=False))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 20
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError('Isolated HTTP server did not start')
            time.sleep(.05)
        session = requests.Session()
        for account in accounts.values():
            response = session.post(base + '/auth/login', data={'username': account['username'], 'password': password}, timeout=15)
            assert response.status_code == 200, response.status_code
            account['session'] = response.json()
            account['headers'] = {'Authorization': 'Bearer ' + response.json()['access_token']}

        def call(method, path='', name='operations', expected=200):
            response = session.request(method, base + '/competitor-monitor' + path,
                                       headers=accounts[name]['headers'], timeout=15)
            assert response.status_code == expected, (response.status_code, response.text[:200])
            return response.json()

        assert session.get(base + '/competitor-monitor', timeout=10).status_code == 401
        for name in ('denied', 'finance', 'customer_service'):
            call('GET', name=name, expected=403)
            call('POST', '/analyze', name=name, expected=403)
        assert call('GET')['latest'] is None
        manual = call('POST', '/analyze')
        assert manual['is_mock'] and manual['summary']['product_count'] == 3
        assert manual['summary']['competitor_count'] == 9
        assert call('GET')['latest']['id'] == manual['id']
        assert call('GET', name='other')['latest'] is None
        assert call('GET', name='admin')['latest'] is None
        for product in manual['products']:
            assert product['currency'] == 'USD'
            assert product['gap_cents'] == product['own_price_cents'] - min(c['price_cents'] for c in product['competitors'])
            assert product['competitors'] == sorted(product['competitors'], key=lambda c: (-c['heat_score'], c['id']))
        date = datetime.now(MONITOR_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
        assert INSPECTION_HOURS == (8, 11, 14, 16)
        assert latest_due_slot(date + timedelta(hours=7, minutes=59)) is None
        for hour in INSPECTION_HOURS:
            at = date + timedelta(hours=hour)
            assert latest_due_slot(at) == at
            assert next_inspection(at) > at
            first = run_scheduled_inspections(at)
            assert first['failed'] == 0
            assert run_scheduled_inspections(at)['processed'] == 0
        assert next_inspection(date + timedelta(hours=16)) == date + timedelta(days=1, hours=8)
        latest = call('GET')
        assert latest['schedule']['completed_today'] == 4
        assert len(latest['history']) == 5
        slot = date + timedelta(hours=16)
        with ThreadPoolExecutor(max_workers=3) as executor:
            repeated = list(executor.map(lambda _: analyze_prices(accounts['operations'], scheduled_for=slot), range(3)))
        assert len({item['id'] for item in repeated}) == 1
        # Revoke after enrollment: the next slot must not read or create snapshots.
        with pool.connection() as conn:
            conn.execute('INSERT INTO user_ai_app_permissions(user_id,app_id,enabled) VALUES (%s,%s,false)',
                         (accounts['other']['id'], 'automation-competitor_analysis'))
            conn.commit()
        tomorrow = date + timedelta(days=1, hours=8)
        run_scheduled_inspections(tomorrow)
        with pool.connection() as conn:
            assert conn.execute('SELECT count(*) FROM competitor_monitor_snapshots WHERE owner_user_id=%s AND scheduled_for=%s',
                                (accounts['other']['id'], tomorrow)).fetchone()[0] == 0
        print(json.dumps({'ok': True, 'checks': ['real_login_and_HTTP', 'migration_idempotency',
            'role_and_app_permission', 'owner_isolation', 'manual_persistence', 'same_currency_price_math',
            'four_Shanghai_slots', 'duplicate_delivery', 'concurrent_slot_dedup', 'revocation_before_schedule'],
            'official_api': 'not_connected'}, ensure_ascii=False), flush=True)
        if args.serve:
            # Local ignored state only; never print bearer tokens to tool output.
            state = ROOT / 'data/competitor-monitor-verification.json'
            state.parent.mkdir(exist_ok=True)
            state.write_text(json.dumps({'base': base, 'accounts': {name: {'session': value['session']} for name, value in accounts.items()}}))
            state.chmod(0o600)
            print('Browser API ready; state: data/competitor-monitor-verification.json', flush=True)
            while thread.is_alive():
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.should_exit = True
        if thread:
            thread.join(10)
        with psycopg.connect(url, connect_timeout=6) as conn:
            conn.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
        (ROOT / 'data/competitor-monitor-verification.json').unlink(missing_ok=True)


if __name__ == '__main__':
    main()
