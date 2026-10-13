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

# 刷新令牌一次领走：加锁、GETDEL 索引、查看已轮换标记在同一条 Lua 里完成。
# Redis 单线程执行脚本，并发的第二个调用只能得到 concurrent，不会双发。
CLAIM_REFRESH_LUA = """
local locked = redis.call('SET', KEYS[1], '1', 'NX', 'EX', ARGV[1])
if not locked then
  return {'', 'concurrent'}
end
local sid = redis.call('GETDEL', KEYS[2])
if sid and sid ~= '' then
  return {sid, 'ok'}
end
local used = redis.call('GET', KEYS[3])
if used and used ~= '' then
  return {used, 'reuse'}
end
return {'', 'missing'}
"""


def _claim_text(value: Any) -> str:
    """把 Redis 返回值收成字符串。空值保持空串，避免把 None 收成 'None'。"""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _parse_claim(raw: Any) -> tuple[str, int | None, str]:
    """解析 Lua 返回的 {value, status}。

    - ok: value 是 session_id:user_id（索引值），解析出 user_id
    - reuse: value 是 session_id（used_key 只存 sid），user_id 为 None
    - concurrent/missing: value 为空
    """
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        status = _claim_text(raw[1])
        if not status:
            status = "missing"
        val = _claim_text(raw[0])
        if val:
            # ok 分支的索引值是 session_id:user_id，reuse 分支只有 session_id
            parts = val.split(":", 1)
            session_id = parts[0]
            if status == "ok" and len(parts) > 1 and parts[1]:
                try:
                    user_id = int(parts[1])
                except ValueError:
                    user_id = None
            else:
                user_id = None
            return session_id, user_id, status
        return "", None, status
    return "", None, "missing"


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
            if settings.env in ("dev", "test"):
                logger.warning(f"Redis unavailable, using in-memory cache: {e}")
                _redis_client = None
                _cache_mode = "MEMORY"
            else:
                raise RuntimeError(
                    f"Redis connection required for {settings.env} environment"
                ) from e
    elif settings.env in ("dev", "test"):
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
                    # redis-py 8 起 setex 已弃用，改用 set(..., ex=)。
                    _redis_client.set(key, value, ex=ttl)
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
    def claim_refresh(
        lock_key: str,
        index_key: str,
        used_key: str,
        lock_ttl: int,
    ) -> tuple[str, int | None, str]:
        """原子领取刷新令牌。

        Redis 走 CLAIM_REFRESH_LUA（SET NX + GETDEL）。
        返回 (session_id, user_id, status)，status 为 ok / concurrent / reuse / missing。
        missing 表示 GETDEL 为空，且没有已轮换记录。
        索引值格式为 session_id:user_id。
        """
        if _redis_client is not None:
            try:
                raw = _redis_client.eval(
                    CLAIM_REFRESH_LUA,
                    3,
                    lock_key,
                    index_key,
                    used_key,
                    int(lock_ttl),
                )
            except Exception as e:
                logger.error(f"Redis claim refresh error: {e}")
                return "", None, "missing"
            return _parse_claim(raw)

        # 内存后端只给单测兜底。并发正确性以真实 Redis 的 Lua 为准。
        if not Cache.setnx(lock_key, "1", lock_ttl):
            return "", None, "concurrent"
        val = Cache.getdel(index_key)
        if val:
            parts = str(val).split(":", 1)
            session_id = parts[0]
            user_id = int(parts[1]) if len(parts) > 1 and parts[1] else None
            return session_id, user_id, "ok"
        used = Cache.get(used_key)
        if used:
            # used_key 只存 session_id，reuse 分支不返回 user_id
            return str(used), None, "reuse"
        return "", None, "missing"

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
