# tests/unit/test_cache.py
"""
Unit tests for cache layer.

Tests both Redis (when available in CI) and memory fallback.
Covers app/core/cache.py
"""
import os

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")

import pytest


@pytest.fixture(autouse=True)
def setup_cache():
    """Initialize cache before each test."""
    from app.core.cache import init_cache
    init_cache()


class TestCacheBasics:
    """Basic tests for cache."""

    def test_cache_import(self):
        """Test cache module can be imported."""
        from app.core.cache import Cache
        assert Cache is not None

    def test_cache_has_methods(self):
        """Test cache has required methods."""
        from app.core.cache import Cache

        methods = ["get", "set", "delete", "get_json", "set_json", "getdel",
                   "sadd", "smembers", "srem", "expire", "setnx", "incr"]
        for method in methods:
            assert hasattr(Cache, method), f"Cache missing method: {method}"


class TestCacheHealth:
    """Tests for cache health check."""

    def test_health_check_returns_tuple(self):
        """Test health check returns (bool, str) tuple."""
        from app.core.cache import CacheHealth

        result = CacheHealth.check()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_health_check_status_values(self):
        """Test health check status is UP, DOWN, or MEMORY."""
        from app.core.cache import CacheHealth

        is_up, status = CacheHealth.check()
        assert status in ("UP", "DOWN", "MEMORY")


class TestCacheStringOperations:
    """Tests for string cache operations."""

    def test_set_and_get(self):
        """Test basic set and get."""
        from app.core.cache import Cache

        Cache.set("test_key_1", "test_value")
        result = Cache.get("test_key_1")
        assert result == "test_value"

    def test_get_nonexistent_key(self):
        """Test get returns None for nonexistent key."""
        from app.core.cache import Cache

        result = Cache.get("nonexistent_key_xyz_123")
        assert result is None

    def test_set_with_ttl(self):
        """Test set with TTL."""
        from app.core.cache import Cache

        result = Cache.set("test_ttl_key", "value", ttl=3600)
        assert result is True

    def test_delete(self):
        """Test delete operation."""
        from app.core.cache import Cache

        Cache.set("delete_test_key", "value")
        result = Cache.delete("delete_test_key")
        assert result is True
        assert Cache.get("delete_test_key") is None


class TestCacheJsonOperations:
    """Tests for JSON cache operations."""

    def test_set_json_and_get_json(self):
        """Test JSON set and get."""
        from app.core.cache import Cache

        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        Cache.set_json("json_test_key", data, ttl=60)
        result = Cache.get_json("json_test_key")
        assert result == data

    def test_get_json_nonexistent(self):
        """Test get_json returns None for nonexistent key."""
        from app.core.cache import Cache

        result = Cache.get_json("nonexistent_json_key_123")
        assert result is None

    def test_get_json_invalid_json(self):
        """Test get_json returns None for invalid JSON."""
        from app.core.cache import Cache

        Cache.set("invalid_json_key", "not valid json {")
        result = Cache.get_json("invalid_json_key")
        assert result is None


class TestCacheAtomicOperations:
    """Tests for atomic cache operations."""

    def test_getdel(self):
        """Test atomic get and delete."""
        from app.core.cache import Cache

        Cache.set("getdel_test_key", "value")
        result = Cache.getdel("getdel_test_key")
        assert result == "value"
        assert Cache.get("getdel_test_key") is None

    def test_getdel_nonexistent(self):
        """Test getdel returns None for nonexistent key."""
        from app.core.cache import Cache

        result = Cache.getdel("nonexistent_getdel_key")
        assert result is None

    def test_setnx_new_key(self):
        """Test setnx on new key succeeds."""
        from app.core.cache import Cache

        # Delete first to ensure it's new
        Cache.delete("setnx_test_key")
        result = Cache.setnx("setnx_test_key", "value", ttl=60)
        assert result is True

    def test_setnx_existing_key(self):
        """Test setnx on existing key fails."""
        from app.core.cache import Cache

        Cache.set("setnx_existing_key", "old_value")
        result = Cache.setnx("setnx_existing_key", "new_value")
        assert result is False
        assert Cache.get("setnx_existing_key") == "old_value"

    def test_incr_new_key(self):
        """Test incr on new key starts at 1."""
        from app.core.cache import Cache

        Cache.delete("incr_test_key")
        result = Cache.incr("incr_test_key")
        assert result == 1

    def test_incr_existing_key(self):
        """Test incr increments existing value."""
        from app.core.cache import Cache

        Cache.delete("incr_test_key_2")
        Cache.incr("incr_test_key_2")  # 1
        Cache.incr("incr_test_key_2")  # 2
        result = Cache.incr("incr_test_key_2")  # 3
        assert result == 3


class TestCacheSetOperations:
    """Tests for Redis set operations."""

    def test_sadd_and_smembers(self):
        """Test set add and members."""
        from app.core.cache import Cache

        Cache.delete("set_test_key")
        Cache.sadd("set_test_key", "member1", "member2", "member3")
        result = Cache.smembers("set_test_key")
        assert isinstance(result, set)
        assert "member1" in result
        assert "member2" in result

    def test_smembers_nonexistent(self):
        """Test smembers returns empty set for nonexistent key."""
        from app.core.cache import Cache

        result = Cache.smembers("nonexistent_set_key_123")
        assert result == set()

    def test_srem(self):
        """Test set remove."""
        from app.core.cache import Cache

        Cache.delete("srem_test_key")
        Cache.sadd("srem_test_key", "member1", "member2")
        Cache.srem("srem_test_key", "member1")
        result = Cache.smembers("srem_test_key")
        assert "member1" not in result
        assert "member2" in result


class TestCacheTTL:
    """Tests for TTL operations."""

    def test_expire(self):
        """Test expire sets TTL on key."""
        from app.core.cache import Cache

        Cache.set("expire_test_key", "value")
        result = Cache.expire("expire_test_key", 3600)
        assert result is True

    def test_expire_nonexistent(self):
        """Test expire on nonexistent key returns False."""
        from app.core.cache import Cache

        result = Cache.expire("nonexistent_expire_key", 60)
        assert result is False


class TestMemoryCacheDirectly:
    """Tests that force memory cache code paths (for CI coverage)."""

    def test_memory_cache_get_set(self):
        """UT-C03-07: Test memory cache get/set directly."""
        import app.core.cache as cache_module

        # Save original redis client
        original_client = cache_module._redis_client

        try:
            # Force memory cache mode
            cache_module._redis_client = None
            cache_module._cache_mode = "MEMORY"

            # Test set
            result = cache_module.Cache.set("mem_test_key", "mem_value")
            assert result is True

            # Test get
            result = cache_module.Cache.get("mem_test_key")
            assert result == "mem_value"

            # Test delete
            result = cache_module.Cache.delete("mem_test_key")
            assert result is True

            # Test get after delete
            result = cache_module.Cache.get("mem_test_key")
            assert result is None

        finally:
            cache_module._redis_client = original_client

    def test_memory_cache_ttl_expiry(self):
        """UT-C03-07b: Test memory cache TTL expiry."""
        import time
        import app.core.cache as cache_module

        original_client = cache_module._redis_client

        try:
            cache_module._redis_client = None
            cache_module._cache_mode = "MEMORY"

            # Set with very short TTL
            cache_module.Cache.set("ttl_test_key", "ttl_value", ttl=1)

            # Should exist immediately
            result = cache_module.Cache.get("ttl_test_key")
            assert result == "ttl_value"

            # Wait for expiry
            time.sleep(1.5)

            # Should be expired now
            result = cache_module.Cache.get("ttl_test_key")
            assert result is None

        finally:
            cache_module._redis_client = original_client

    def test_memory_cache_json_operations(self):
        """UT-C03-08: Test memory cache JSON operations."""
        import app.core.cache as cache_module

        original_client = cache_module._redis_client

        try:
            cache_module._redis_client = None
            cache_module._cache_mode = "MEMORY"

            # Test set_json
            data = {"key": "value", "number": 42}
            result = cache_module.Cache.set_json("json_test_key", data)
            assert result is True

            # Test get_json
            result = cache_module.Cache.get_json("json_test_key")
            assert result == data
            assert result["key"] == "value"
            assert result["number"] == 42

            # Test get_json nonexistent
            result = cache_module.Cache.get_json("nonexistent_json_key")
            assert result is None

        finally:
            cache_module._redis_client = original_client

    def test_memory_cache_set_operations(self):
        """UT-C03-08b: Test memory cache set operations (sadd, smembers, srem)."""
        import app.core.cache as cache_module

        original_client = cache_module._redis_client

        try:
            cache_module._redis_client = None
            cache_module._cache_mode = "MEMORY"

            # Clean up first
            cache_module.Cache.delete("mem_set_key")

            # Test sadd
            cache_module.Cache.sadd("mem_set_key", "a", "b", "c")

            # Test smembers
            result = cache_module.Cache.smembers("mem_set_key")
            assert isinstance(result, set)
            assert "a" in result
            assert "b" in result
            assert "c" in result

            # Test srem
            cache_module.Cache.srem("mem_set_key", "b")
            result = cache_module.Cache.smembers("mem_set_key")
            assert "b" not in result
            assert "a" in result

        finally:
            cache_module._redis_client = original_client

    def test_memory_cache_incr(self):
        """UT-C03-08c: Test memory cache incr operation."""
        import app.core.cache as cache_module

        original_client = cache_module._redis_client

        try:
            cache_module._redis_client = None
            cache_module._cache_mode = "MEMORY"

            # Set initial value
            cache_module.Cache.set("incr_test_key", "10")

            # Test incr
            result = cache_module.Cache.incr("incr_test_key")
            assert result == 11

            result = cache_module.Cache.incr("incr_test_key")
            assert result == 12

        finally:
            cache_module._redis_client = original_client

    def test_memory_cache_getdel(self):
        """UT-C03-08d: Test memory cache getdel operation."""
        import app.core.cache as cache_module

        original_client = cache_module._redis_client

        try:
            cache_module._redis_client = None
            cache_module._cache_mode = "MEMORY"

            # Set value
            cache_module.Cache.set("getdel_key", "getdel_value")

            # Get and delete
            result = cache_module.Cache.getdel("getdel_key")
            assert result == "getdel_value"

            # Should be gone now
            result = cache_module.Cache.get("getdel_key")
            assert result is None

        finally:
            cache_module._redis_client = original_client

    def test_memory_cache_setnx(self):
        """UT-C03-08e: Test memory cache setnx operation."""
        import app.core.cache as cache_module

        original_client = cache_module._redis_client

        try:
            cache_module._redis_client = None
            cache_module._cache_mode = "MEMORY"

            # Delete any existing
            cache_module.Cache.delete("setnx_key")

            # First setnx should succeed
            result = cache_module.Cache.setnx("setnx_key", "original")
            assert result is True
            assert cache_module.Cache.get("setnx_key") == "original"

            # Second setnx should fail (key exists)
            result = cache_module.Cache.setnx("setnx_key", "new")
            assert result is False
            assert cache_module.Cache.get("setnx_key") == "original"

        finally:
            cache_module._redis_client = original_client

    def test_memory_cache_expire(self):
        """UT-C03-08f: Test memory cache expire operation."""
        import app.core.cache as cache_module

        original_client = cache_module._redis_client

        try:
            cache_module._redis_client = None
            cache_module._cache_mode = "MEMORY"

            # Set value without TTL
            cache_module.Cache.set("expire_mem_key", "value")

            # Set expire
            result = cache_module.Cache.expire("expire_mem_key", 3600)
            assert result is True

            # Expire on nonexistent key
            result = cache_module.Cache.expire("nonexistent_mem_key", 60)
            assert result is False

        finally:
            cache_module._redis_client = original_client

    def test_cache_health_check_memory_mode(self):
        """UT-C03-06b: Test cache health check in memory mode."""
        import app.core.cache as cache_module

        original_client = cache_module._redis_client
        original_mode = cache_module._cache_mode

        try:
            cache_module._redis_client = None
            cache_module._cache_mode = "MEMORY"

            is_up, status = cache_module.CacheHealth.check()
            assert is_up is True
            assert status == "MEMORY"

        finally:
            cache_module._redis_client = original_client
            cache_module._cache_mode = original_mode
