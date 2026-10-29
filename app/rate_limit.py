"""Atomic shared fixed-window rate limiting for login and expensive AI routes."""
import asyncio
from hashlib import sha256
import json

from redis.exceptions import RedisError

from app.cache import cache_key, redis_client
from app.config import settings

_SCRIPT = '''
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {n, redis.call('TTL', KEYS[1])}
'''


def check_limit(identity: str, category: str, limit: int) -> tuple[bool, int]:
    client = redis_client()
    if client is None:
        raise ConnectionError('Rate limiting requires Redis')
    count, ttl = client.eval(_SCRIPT, 1, cache_key('rate:'+category, identity), 60)
    return count <= limit, max(1, int(ttl))


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('method') == 'OPTIONS' or not settings.rate_limit_enabled:
            return await self.app(scope, receive, send)
        path = scope.get('path', '')
        category = 'login' if path == '/auth/login' else 'ai' if (
            path in {'/chat', '/chat/stream', '/agent/chat'} or
            path.startswith('/public/llm/') or
            (scope.get('method') == 'POST' and path.startswith(('/automation/', '/jobs/', '/ai-workflows/', '/competitor-monitor/')))
        ) else None
        if category is None:
            return await self.app(scope, receive, send)
        # Ignore user-supplied forwarding headers. Uvicorn trusts only the proxy network.
        identity = (scope.get('client') or ('unknown',))[0]
        limit = settings.rate_limit_login_per_minute if category == 'login' else settings.rate_limit_ai_per_minute
        try:
            allowed, retry_after = await asyncio.to_thread(check_limit, identity, category, limit)
            if allowed:
                return await self.app(scope, receive, send)
            code, detail = 429, '请求过于频繁，请稍后重试'
        except (RedisError, ConnectionError):
            code, detail, retry_after = 503, '请求保护服务暂不可用，请稍后重试', 5
        body = json.dumps({'detail': detail}, ensure_ascii=False).encode()
        await send({'type': 'http.response.start', 'status': code, 'headers': [
            (b'content-type', b'application/json; charset=utf-8'),
            (b'retry-after', str(retry_after).encode()),
        ]})
        await send({'type': 'http.response.body', 'body': body})
