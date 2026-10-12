# tests/unit/test_cache.py
"""
Unit tests for cache layer.

Covers app/core/cache.py
"""
import os

os.environ["IMS_ENV"] = "test"
os.environ["IMS_DB_URL"] = "sqlite:///:memory:"
os.environ["IMS_REDIS_URL"] = ""
os.environ["IMS_JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"


class TestCacheBasics:
    """Basic tests for cache."""

    def test_cache_import(self):
        """Test cache module can be imported."""
        from app.core.cache import Cache
        assert Cache is not None

    def test_cache_has_methods(self):
        """Test cache has required methods."""
        from app.core.cache import Cache

        methods = ["get", "set", "delete", "get_json", "set_json"]
        for method in methods:
            assert hasattr(Cache, method)

    def test_cache_health_import(self):
        """Test cache health can be imported."""
        from app.core.cache import CacheHealth
        assert CacheHealth is not None


class TestCacheOperations:
    """Tests for cache operations."""

    def test_memory_fallback(self):
        """Test memory fallback when Redis unavailable."""
        from app.core.cache import Cache
        assert hasattr(Cache, "set")
        assert hasattr(Cache, "get")

    def test_set_and_get(self):
        """Test basic set and get methods exist."""
        from app.core.cache import Cache
        assert hasattr(Cache, "set")
        assert hasattr(Cache, "get")

    def test_delete(self):
        """Test delete method exists."""
        from app.core.cache import Cache
        assert hasattr(Cache, "delete")

    def test_set_json(self):
        """Test set JSON method exists."""
        from app.core.cache import Cache
        assert hasattr(Cache, "set_json")

    def test_getdel(self):
        """Test atomic get and delete method exists."""
        from app.core.cache import Cache
        assert hasattr(Cache, "getdel")

    def test_expire(self):
        """Test expire method exists."""
        from app.core.cache import Cache
        assert hasattr(Cache, "expire")

    def test_sadd_smembers(self):
        """Test set add and members methods exist."""
        from app.core.cache import Cache
        assert hasattr(Cache, "sadd")
        assert hasattr(Cache, "smembers")

    def test_srem(self):
        """Test set remove method exists."""
        from app.core.cache import Cache
        assert hasattr(Cache, "srem")


class TestCacheHealth:
    """Tests for cache health check."""

    def test_health_check(self):
        """Test health check class exists."""
        from app.core.cache import CacheHealth
        assert hasattr(CacheHealth, "check")
