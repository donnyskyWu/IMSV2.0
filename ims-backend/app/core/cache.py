# app/core/cache.py - Redis cache and in-memory fallback
"""
Cache management with Redis and in-memory fallback for dev.

Rules per FP-A01-01:
- dev allows Redis fallback to in-memory
- test/e2e/prod require Redis
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Cache backends
_redis_client: Optional[Any] = None
_memory_cache: dict[str, tuple[Any, Optional[float]]] = {}
_cache_mode: str = "MEMORY"  # MEMORY or REDIS


def init_cache() -> None:
    """Initialize cache backend."""
    global _redis_client, _cache_mode

    from app.core.config import get_settings
    settings = get_settings()

    # Try to connect to Redis
    if settings.redis.url:
        try:
            import redis
            _redis_client = redis.from_url(
                settings.redis.url,
                password=settings.redis.password,
                max_connections=settings.redis.max_connections,
                decode_responses=True,
            )
            # Test connection
            _redis_client.ping()
            _cache_mode = "UP"
            logger.info("Redis connection established")
        except Exception as e:
            if settings.env == "dev":
                logger.warning(f"Redis unavailable, using in-memory cache: {e}")
                _redis_client = None
                _cache_mode = "MEMORY"
            else:
                raise RuntimeError(
                    f"Redis connection required for {settings.env} environment"
                ) from e
    elif settings.env == "dev":
        logger.info("Redis not configured, using in-memory cache")
        _cache_mode = "MEMORY"
    else:
        raise RuntimeError(
            f"Redis configuration required for {settings.env} environment"
        )


class CacheHealth:
    """Cache health check utilities."""

    @staticmethod
    def check() -> tuple[bool, str]:
        """
        Check cache health.

        Returns:
            (is_up, status): status is UP/DOWN/MEMORY
        """
        global _redis_client, _cache_mode

        if _redis_client is not None:
            try:
                _redis_client.ping()
                return True, "UP"
            except Exception:
                return False, "DOWN"

        return True, _cache_mode


class Cache:
    """Cache interface with Redis and memory fallback."""

    @staticmethod
    def get(key: str) -> Optional[str]:
        """Get value from cache."""
        if _redis_client is not None:
            try:
                return _redis_client.get(key)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                return None
        else:
            import time
            item = _memory_cache.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and time.time() > expires_at:
                del _memory_cache[key]
                return None
            return value

    @staticmethod
    def set(key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL (seconds)."""
        if _redis_client is not None:
            try:
                if ttl:
                    _redis_client.setex(key, ttl, value)
                else:
                    _redis_client.set(key, value)
                return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                return False
        else:
            import time
            expires_at = time.time() + ttl if ttl else None
            _memory_cache[key] = (value, expires_at)
            return True

    @staticmethod
    def delete(key: str) -> bool:
        """Delete key from cache."""
        if _redis_client is not None:
            try:
                _redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
                return False
        else:
            _memory_cache.pop(key, None)
            return True

    @staticmethod
    def setnx(key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set if not exists (for locks). Returns True if set."""
        if _redis_client is not None:
            try:
                if ttl:
                    return bool(_redis_client.set(key, value, nx=True, ex=ttl))
                else:
                    return bool(_redis_client.setnx(key, value))
            except Exception as e:
                logger.error(f"Redis setnx error: {e}")
                return False
        else:
            if key not in _memory_cache:
                import time
                expires_at = time.time() + ttl if ttl else None
                _memory_cache[key] = (value, expires_at)
                return True
            return False

    @staticmethod
    def incr(key: str) -> int:
        """Increment counter. Returns new value."""
        if _redis_client is not None:
            try:
                return _redis_client.incr(key)
            except Exception as e:
                logger.error(f"Redis incr error: {e}")
                return 0
        else:
            item = _memory_cache.get(key)
            if item is None:
                _memory_cache[key] = ("1", None)
                return 1
            value, expires_at = item
            new_val = int(value) + 1
            _memory_cache[key] = (str(new_val), expires_at)
            return new_val

    @staticmethod
    def get_json(key: str) -> Optional[Any]:
        """Get JSON value from cache."""
        value = Cache.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def set_json(key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set JSON value in cache."""
        return Cache.set(key, json.dumps(value), ttl)

    @staticmethod
    def getdel(key: str) -> Optional[str]:
        """Get and delete (atomic for Redis)."""
        if _redis_client is not None:
            try:
                return _redis_client.getdel(key)
            except Exception as e:
                logger.error(f"Redis getdel error: {e}")
                return None
        else:
            item = _memory_cache.pop(key, None)
            if item is None:
                return None
            return item[0]

    @staticmethod
    def sadd(key: str, *members: str) -> int:
        """Add members to set."""
        if _redis_client is not None:
            try:
                return _redis_client.sadd(key, *members)
            except Exception as e:
                logger.error(f"Redis sadd error: {e}")
                return 0
        else:
            item = _memory_cache.get(key)
            if item is None:
                s = set(members)
            else:
                s = set(item[0] if isinstance(item[0], set) else [item[0]])
                s.update(members)
            _memory_cache[key] = (s, None)
            return len(members)

    @staticmethod
    def smembers(key: str) -> set[str]:
        """Get all members of set."""
        if _redis_client is not None:
            try:
                return _redis_client.smembers(key)
            except Exception as e:
                logger.error(f"Redis smembers error: {e}")
                return set()
        else:
            item = _memory_cache.get(key)
            if item is None:
                return set()
            return item[0] if isinstance(item[0], set) else set()

    @staticmethod
    def srem(key: str, *members: str) -> int:
        """Remove members from set."""
        if _redis_client is not None:
            try:
                return _redis_client.srem(key, *members)
            except Exception as e:
                logger.error(f"Redis srem error: {e}")
                return 0
        else:
            item = _memory_cache.get(key)
            if item is None:
                return 0
            s = item[0] if isinstance(item[0], set) else set()
            removed = 0
            for m in members:
                if m in s:
                    s.discard(m)
                    removed += 1
            _memory_cache[key] = (s, None)
            return removed

    @staticmethod
    def expire(key: str, ttl: int) -> bool:
        """Set TTL on existing key."""
        if _redis_client is not None:
            try:
                return bool(_redis_client.expire(key, ttl))
            except Exception as e:
                logger.error(f"Redis expire error: {e}")
                return False
        else:
            import time
            item = _memory_cache.get(key)
            if item is None:
                return False
            value, _ = item
            _memory_cache[key] = (value, time.time() + ttl)
            return True
