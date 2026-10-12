# tests/unit/test_health_endpoint.py - Health endpoint tests
"""
Unit tests for app/api/health.py.

Tests cover:
- UT-A01-03-01: Health check returns UP status
- UT-A01-03-02: Health check returns DEGRADED when Redis is down
- UT-A01-03-03: Health check returns DOWN when DB is down
- UT-A01-03-04: Health check never exposes connection strings
- UT-A01-03-05: Health check includes version
"""

import os

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")

from unittest.mock import patch

import pytest

from app import __version__
from app.api.health import HealthData, health_check


class TestHealthCheckEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_up_all_healthy(self):
        """UT-A01-03-01: Health check returns UP when all services healthy."""
        with patch('app.db.session.DatabaseHealth') as mock_db:
            with patch('app.core.cache.CacheHealth') as mock_cache:
                mock_db.check_ims.return_value = True
                mock_db.check_football.return_value = (True, "UP")
                mock_cache.check.return_value = (True, "UP")

                result = await health_check()

                assert result.data.status == "UP"
                assert result.data.db == "UP"
                assert result.data.redis == "UP"

    @pytest.mark.asyncio
    async def test_health_returns_degraded_redis_down(self):
        """UT-A01-03-02: Health check returns DEGRADED when Redis is down."""
        with patch('app.db.session.DatabaseHealth') as mock_db:
            with patch('app.core.cache.CacheHealth') as mock_cache:
                mock_db.check_ims.return_value = True
                mock_db.check_football.return_value = (True, "UP")
                mock_cache.check.return_value = (False, "DOWN")

                result = await health_check()

                assert result.data.status == "DEGRADED"
                assert result.data.redis == "DOWN"

    @pytest.mark.asyncio
    async def test_health_returns_degraded_football_down(self):
        """UT-A01-03-02b: Health check returns DEGRADED when Football is down."""
        with patch('app.db.session.DatabaseHealth') as mock_db:
            with patch('app.core.cache.CacheHealth') as mock_cache:
                mock_db.check_ims.return_value = True
                mock_db.check_football.return_value = (False, "DOWN")
                mock_cache.check.return_value = (True, "UP")

                result = await health_check()

                assert result.data.status == "DEGRADED"
                assert result.data.football_live == "DOWN"

    @pytest.mark.asyncio
    async def test_health_returns_503_db_down(self):
        """UT-A01-03-03: Health check returns 503 when DB is down."""
        with patch('app.db.session.DatabaseHealth') as mock_db:
            with patch('app.core.cache.CacheHealth') as mock_cache:
                mock_db.check_ims.return_value = False
                mock_db.check_football.return_value = (False, "DOWN")
                mock_cache.check.return_value = (True, "UP")

                result = await health_check()

                # When DB is down, result is JSONResponse with 503
                assert result.status_code == 503
                assert b'"DOWN"' in result.body

    @pytest.mark.asyncio
    async def test_health_never_exposes_connection_strings(self):
        """UT-A01-03-04: Health check never exposes connection strings."""
        with patch('app.db.session.DatabaseHealth') as mock_db:
            with patch('app.core.cache.CacheHealth') as mock_cache:
                mock_db.check_ims.return_value = True
                mock_db.check_football.return_value = (True, "UP")
                mock_cache.check.return_value = (True, "UP")

                result = await health_check()

                # Convert to JSON and verify no URLs
                data_dict = result.model_dump()
                data_str = str(data_dict)

                # Should not contain any connection patterns
                assert "mysql" not in data_str.lower()
                assert "redis://" not in data_str.lower()
                assert "password" not in data_str.lower()

    @pytest.mark.asyncio
    async def test_health_includes_version(self):
        """UT-A01-03-05: Health check includes version."""
        with patch('app.db.session.DatabaseHealth') as mock_db:
            with patch('app.core.cache.CacheHealth') as mock_cache:
                mock_db.check_ims.return_value = True
                mock_db.check_football.return_value = (True, "UP")
                mock_cache.check.return_value = (True, "UP")

                result = await health_check()

                assert result.data.version == __version__


class TestHealthData:
    """Tests for HealthData model."""

    def test_health_data_fields(self):
        """Test HealthData has required fields."""
        data = HealthData(
            status="UP",
            db="UP",
            redis="UP",
            football_live="UP",
            version="1.0.0",
        )

        assert data.status == "UP"
        assert data.db == "UP"
        assert data.redis == "UP"
        assert data.football_live == "UP"
        assert data.version == "1.0.0"

    def test_health_data_degraded_states(self):
        """Test HealthData with degraded states."""
        data = HealthData(
            status="DEGRADED",
            db="UP",
            redis="DOWN",
            football_live="DISABLED",
            version="1.0.0",
        )

        assert data.status == "DEGRADED"
        assert data.redis == "DOWN"
        assert data.football_live == "DISABLED"
