"""Shared cache; outages fall back locally, never log credentials or keys."""
import json
import logging
from functools import lru_cache
from hashlib import sha256

from redis import Redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def redis_client() -> Redis | None:
    if not settings.redis_url:
        return None
    return Redis.from_url(settings.redis_url, decode_responses=True,
                          socket_connect_timeout=0.5, socket_timeout=0.5,
                          retry_on_timeout=False, health_check_interval=30)


def cache_key(namespace: str, identity: str) -> str:
    return f'{settings.redis_key_prefix}:{namespace}:{sha256(identity.encode()).hexdigest()}'


def cache_get(namespace: str, identity: str):
    client = redis_client()
    if client is None:
        return None
    try:
        value = client.get(cache_key(namespace, identity))
        return json.loads(value) if value is not None else None
    except (RedisError, ValueError):
        return None


def cache_set(namespace: str, identity: str, value, ttl: int) -> None:
    client = redis_client()
    if client is None or ttl <= 0:
        return
    try:
        client.set(cache_key(namespace, identity), json.dumps(value), ex=ttl)
    except RedisError:
        pass


def cache_delete(namespace: str, identity: str) -> None:
    client = redis_client()
    if client:
        try:
            client.delete(cache_key(namespace, identity))
        except RedisError:
            pass
