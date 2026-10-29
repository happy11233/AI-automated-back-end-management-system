from hmac import compare_digest

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response
from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest

from app.cache import cache_get, redis_client
from app.config import settings
from app.db import fetch_one

router = APIRouter(tags=['health'])
REQUESTS = Counter('company_rag_http_requests_total', 'HTTP requests', ['method', 'route', 'status'])
DURATION = Histogram('company_rag_http_duration_seconds', 'Full HTTP response duration including SSE', ['method', 'route'])
JOBS = Gauge('company_rag_jobs', 'Persistent background jobs by status', ['status'])
JOB_AGE = Gauge('company_rag_oldest_pending_job_seconds', 'Age of oldest unfinished job')
RUNNING_AGE = Gauge('company_rag_longest_running_job_seconds', 'Age of longest running background task')
OUTBOX_AGE = Gauge('company_rag_oldest_outbox_seconds', 'Age of oldest unpublished Outbox event')
FAILURES = Gauge('company_rag_jobs_failed_last_5m', 'Jobs that failed in the last five minutes')
HEARTBEAT = Gauge('company_rag_background_heartbeat_timestamp_seconds', 'Latest shared worker or scheduled delivery heartbeat', ['component'])
DEPENDENCIES = Gauge('company_rag_background_metrics_available', 'Whether background metrics could be collected')


def collect_background_metrics():
    if not settings.background_jobs_enabled:
        return
    import time
    from app.db import fetch_all
    try:
        redis = redis_client()
        if redis is None or not redis.ping():
            raise ConnectionError('Redis heartbeat unavailable')
        counts = dict(fetch_all('SELECT status,count(*) FROM background_jobs GROUP BY status'))
        for status in ('queued', 'running', 'succeeded', 'failed'):
            JOBS.labels(status).set(counts.get(status, 0))
        age = fetch_one("SELECT COALESCE(EXTRACT(EPOCH FROM now()-min(created_at)),0) FROM background_jobs WHERE status IN ('queued','running')")[0]
        running_age = fetch_one("SELECT COALESCE(EXTRACT(EPOCH FROM now()-min(started_at)),0) FROM background_jobs WHERE status='running'")[0]
        outbox = fetch_one('SELECT COALESCE(EXTRACT(EPOCH FROM now()-min(created_at)),0) FROM task_outbox WHERE published_at IS NULL')[0]
        failed = fetch_one("SELECT count(*) FROM background_jobs WHERE status='failed' AND finished_at>now()-interval '5 minutes'")[0]
        JOB_AGE.set(float(age)); RUNNING_AGE.set(float(running_age)); OUTBOX_AGE.set(float(outbox)); FAILURES.set(failed)
        for component in ('worker', 'scheduler_dispatch'):
            pulse = cache_get('health', component)
            stamp = pulse.get('at', 0) if isinstance(pulse, dict) else 0
            HEARTBEAT.labels(component).set(stamp if isinstance(stamp, (int, float)) and stamp <= time.time()+5 else 0)
        DEPENDENCIES.set(1)
    except Exception:
        DEPENDENCIES.set(0)


@router.get('/ready', include_in_schema=False)
def readiness():
    try:
        fetch_one('SELECT 1')
        if settings.rate_limit_enabled:
            client = redis_client()
            if client is None or not client.ping():
                raise ConnectionError('Redis unavailable')
        if settings.background_jobs_enabled:
            fetch_one('SELECT id FROM background_jobs LIMIT 1')
    except Exception:
        raise HTTPException(503, 'Dependencies are not ready') from None
    return {'status': 'ready'}


@router.get('/metrics', include_in_schema=False)
def metrics(authorization: str | None = Header(default=None)):
    if not settings.metrics_token or not compare_digest(authorization or '', 'Bearer '+settings.metrics_token):
        raise HTTPException(404, 'Not found')
    collect_background_metrics()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        from time import monotonic
        started, status = monotonic(), 500
        async def capture(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
            await send(message)
        try:
            await self.app(scope, receive, capture)
        finally:
            route = getattr(scope.get('route'), 'path', '__unmatched__')
            method = scope.get('method', 'UNKNOWN')
            REQUESTS.labels(method, route, str(status)).inc()
            DURATION.labels(method, route).observe(monotonic()-started)
