"""Read-only product monitoring: explicit demo prices, persistent snapshots, no repricing."""
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import logging
from typing import Protocol
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from app.db import fetch_all, pool

WORKFLOW_ID = 'operations_competitor_analysis'
APP_ID = 'automation-competitor_analysis'
MONITOR_TIMEZONE = ZoneInfo('Asia/Shanghai')
INSPECTION_HOURS = (8, 11, 14, 16)


def latest_due_slot(now: datetime) -> datetime | None:
    local = now.astimezone(MONITOR_TIMEZONE)
    slots = [datetime.combine(local.date(), time(hour), MONITOR_TIMEZONE)
             for hour in INSPECTION_HOURS]
    return max((slot for slot in slots if slot <= local), default=None)


def next_inspection(now: datetime) -> datetime:
    local = now.astimezone(MONITOR_TIMEZONE)
    for day in (local.date(), local.date() + timedelta(days=1)):
        for hour in INSPECTION_HOURS:
            candidate = datetime.combine(day, time(hour), MONITOR_TIMEZONE)
            if candidate > local:
                return candidate
    raise AssertionError('next inspection must exist')


class PriceProvider(Protocol):
    """Official adapters return comparable currency/specification and source evidence."""
    name: str

    def collect(self, captured_at: datetime) -> dict: ...


class MockPriceProvider:
    name = 'mock'

    def collect(self, captured_at: datetime) -> dict:
        # Stable within a minute, varying across observations. No official claims.
        seed = captured_at.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M')
        samples = (
            ('DEMO-BOTTLE-500', '保温杯', '500ml · 单只', 2499, ('暖物 A', '轻饮 B', '悦行 C')),
            ('DEMO-CHARGER-65', '氮化镓充电器', '65W · 双口 · 单只', 3299, ('闪充 A', '能量 B', '速电 C')),
            ('DEMO-ORGANIZER-3', '桌面收纳盒', '三件套 · 同尺寸', 1899, ('简纳 A', '方格 B', '整序 C')),
        )
        products = []
        for sku, name, specification, own_cents, brands in samples:
            offers = []
            for index, brand in enumerate(brands):
                digest = hashlib.sha256(f'{seed}:{sku}:{brand}'.encode()).digest()
                cents = max(100, own_cents + (-350, 90, 450)[index] + (digest[0] - 128) * 2)
                offers.append({'id': f'{sku}-COMP-{index + 1}', 'name': brand,
                               'price_cents': cents, 'heat_score': 70 + digest[1] % 30,
                               'source_label': '模拟热点样本', 'source_url': None})
            offers.sort(key=lambda offer: (-offer['heat_score'], offer['id']))
            lowest = min(offer['price_cents'] for offer in offers)
            gap = own_cents - lowest
            percent = (Decimal(gap) / lowest * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            products.append({'sku': sku, 'name': name, 'specification': specification,
                             'currency': 'USD', 'own_price_cents': own_cents,
                             'competitors': offers, 'lowest_competitor_cents': lowest,
                             'gap_cents': gap, 'gap_percent': float(percent)})
        return {'provider': self.name, 'is_mock': True, 'currency': 'USD',
                'marketplace': '模拟美国站', 'products': products,
                'summary': {'product_count': len(products),
                            'competitor_count': sum(len(p['competitors']) for p in products),
                            'above_lowest_count': sum(p['gap_cents'] > 0 for p in products)},
                'notice': '自家商品、竞品价格和热度均为模拟数据；热度为演示评分，不代表平台真实排名。价格按同币种、同规格比较，暂不含运费、税费与优惠券。'}


def _authorize(conn, user_id: str) -> dict:
    row = conn.execute('''SELECT u.id,u.role,u.position,u.username FROM users u
        WHERE u.id=%s AND (u.role='admin' OR (u.position='operations' AND NOT EXISTS (
            SELECT 1 FROM user_ai_app_permissions p WHERE p.user_id=u.id AND p.app_id=%s
            AND NOT p.enabled)))''', (user_id, APP_ID)).fetchone()
    if not row:
        raise HTTPException(status_code=403, detail='无权访问商品与竞品监控')
    return dict(zip(('id', 'role', 'position', 'username'), row))


def _snapshot(row) -> dict:
    return {'id': str(row[0]), 'run_id': str(row[1]), 'trigger_type': row[2],
            'scheduled_for': row[3].isoformat() if row[3] else None,
            'captured_at': row[4].isoformat(), **row[5]}


def analyze_prices(current_user: dict, *, scheduled_for: datetime | None = None) -> dict:
    owner_id = str(current_user['id'])
    trigger = 'schedule' if scheduled_for else 'manual'
    with pool.connection() as conn, conn.transaction():
        # One transaction per owner: snapshot and run record commit together.
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('competitor:' + owner_id,))
        user = _authorize(conn, owner_id)
        if scheduled_for:
            prior = conn.execute('''SELECT id,run_id,trigger_type,scheduled_for,captured_at,result
                FROM competitor_monitor_snapshots WHERE owner_user_id=%s AND scheduled_for=%s''',
                (owner_id, scheduled_for)).fetchone()
            if prior:
                return _snapshot(prior)
        captured_at = datetime.now(timezone.utc)
        provider: PriceProvider = MockPriceProvider()
        result = provider.collect(captured_at)
        summary = f'模拟价格分析完成：{result["summary"]["product_count"]} 件自家商品、{result["summary"]["competitor_count"]} 个竞品样本。'
        run_id = conn.execute('''INSERT INTO automation_runs
            (run_type,app_id,app_name,entrypoint,status,user_id,username,role,position,
             resource_type,resource_id,output_preview,metadata,finished_at)
            VALUES ('ai_workflow',%s,'商品与竞品监控',%s,'succeeded',%s,%s,%s,'operations',
                    'ai_workflow',%s,%s,%s,%s) RETURNING id''',
            (WORKFLOW_ID, '/competitor-monitor/analyze', owner_id, user['username'], user['role'],
             WORKFLOW_ID, summary, Jsonb({'provider': 'mock', 'trigger_type': trigger,
             'scheduled_for': scheduled_for.isoformat() if scheduled_for else None}), captured_at)).fetchone()[0]
        row = conn.execute('''INSERT INTO competitor_monitor_snapshots
            (owner_user_id,run_id,trigger_type,provider,scheduled_for,captured_at,result)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id,run_id,trigger_type,scheduled_for,captured_at,result''',
            (owner_id, run_id, trigger, provider.name, scheduled_for, captured_at, Jsonb(result))).fetchone()
        return _snapshot(row)


def monitoring_dashboard(current_user: dict) -> dict:
    from app.cache import cache_get
    now = datetime.now(timezone.utc)
    with pool.connection() as conn:
        _authorize(conn, str(current_user['id']))
        rows = conn.execute('''SELECT id,run_id,trigger_type,scheduled_for,captured_at,result
            FROM competitor_monitor_snapshots WHERE owner_user_id=%s
            ORDER BY captured_at DESC,id DESC LIMIT 28''', (current_user['id'],)).fetchall()
        today = now.astimezone(MONITOR_TIMEZONE).date()
        start = datetime.combine(today, time(), MONITOR_TIMEZONE)
        count = conn.execute('''SELECT count(*) FROM competitor_monitor_snapshots
            WHERE owner_user_id=%s AND trigger_type='schedule' AND scheduled_for >= %s
            AND scheduled_for < %s''', (current_user['id'], start, start + timedelta(days=1))).fetchone()[0]
    scheduler = cache_get('health', 'scheduler_dispatch')
    worker = cache_get('health', 'worker')
    monitor = cache_get('health', 'competitor_monitor')
    healthy = all(isinstance(item, dict) and 0 <= now.timestamp() - item.get('at', 0) < 120
                  for item in (scheduler, worker, monitor)) and monitor.get('failed', 0) == 0
    history = [_snapshot(row) for row in reversed(rows)]
    return {'provider': 'mock', 'latest': history[-1] if history else None, 'history': history,
            'schedule': {'timezone': 'Asia/Shanghai', 'times': [f'{h:02}:00' for h in INSPECTION_HOURS],
                         'next_run_at': next_inspection(now).isoformat(), 'completed_today': count,
                         'scheduler_healthy': healthy,
                         'status_label': '后台调度在线' if healthy else '后台调度待就绪'},
            'official_api': {'status': 'not_connected', 'label': '官方开放 API 尚未接入'}}


def run_scheduled_inspections(now: datetime | None = None) -> dict:
    """Minute tick catches up the latest due slot, deduplicated per owner.

    Recovery collects current prices, never fabricated historical observations.
    Operations users participate automatically; admins after their first analysis.
    """
    slot = latest_due_slot(now or datetime.now(timezone.utc))
    if slot is None:
        return {'processed': 0, 'failed': 0}
    users = fetch_all('''SELECT u.id FROM users u WHERE u.created_at <= %s
        AND (u.position='operations' OR (u.role='admin' AND EXISTS (
            SELECT 1 FROM competitor_monitor_snapshots s WHERE s.owner_user_id=u.id)))
        AND (u.role='admin' OR NOT EXISTS (SELECT 1 FROM user_ai_app_permissions p
            WHERE p.user_id=u.id AND p.app_id=%s AND NOT p.enabled))
        AND NOT EXISTS (SELECT 1 FROM competitor_monitor_snapshots s
            WHERE s.owner_user_id=u.id AND s.scheduled_for=%s)''', (slot, APP_ID, slot))
    processed, failed = 0, 0
    for (user_id,) in users:
        try:
            analyze_prices({'id': str(user_id)}, scheduled_for=slot)
            processed += 1
        except HTTPException as error:
            if error.status_code != 403:
                raise
        except Exception:
            # Rollback leaves the slot eligible next minute. Other owners continue.
            logging.getLogger(__name__).exception('Competitor inspection failed for an owner')
            failed += 1
    return {'processed': processed, 'failed': failed, 'scheduled_for': slot.isoformat()}
