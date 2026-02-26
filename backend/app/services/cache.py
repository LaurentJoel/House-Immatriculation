"""
Cache service with decorator and invalidation support.
Uses Redis for backend storage.
"""
import json
import functools
import hashlib
from typing import Optional

import redis


# Module-level Redis client (set during app init or overridden in tests)
_redis_client: Optional[redis.Redis] = None


def init_cache(redis_url: str) -> None:
    """Initialise the module-level Redis client."""
    global _redis_client
    _redis_client = redis.from_url(redis_url, decode_responses=True)


def set_client(client: redis.Redis) -> None:
    """Override the Redis client (used in tests with fakeredis)."""
    global _redis_client
    _redis_client = client


def get_client() -> redis.Redis:
    """Return the current Redis client."""
    if _redis_client is None:
        raise RuntimeError('Cache not initialised. Call init_cache() first.')
    return _redis_client


def _make_key(prefix: str, args, kwargs) -> str:
    """Build a deterministic cache key from function arguments."""
    raw = json.dumps({'a': list(args), 'k': kwargs}, sort_keys=True, default=str)
    h = hashlib.md5(raw.encode()).hexdigest()
    return f'{prefix}:{h}'


def cached(ttl: int = 300, prefix: str = 'cache'):
    """Decorator that caches function results in Redis.

    Args:
        ttl: Time-to-live in seconds.
        prefix: Key prefix for grouping / invalidation.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            client = get_client()
            key = _make_key(prefix, args, kwargs)
            hit = client.get(key)
            if hit is not None:
                return json.loads(hit)
            result = fn(*args, **kwargs)
            client.setex(key, ttl, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix: str) -> int:
    """Delete all keys matching a prefix. Returns number of keys deleted."""
    client = get_client()
    pattern = f'{prefix}:*'
    keys = list(client.scan_iter(match=pattern))
    if keys:
        return client.delete(*keys)
    return 0
