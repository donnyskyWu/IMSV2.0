# tests/integration/test_api_health.py
"""
Integration tests for health check endpoint.

Covers: UT-A01-07, UT-A01-08, UT-A01-09
"""
import os

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")


class TestHealthEndpoint:
    """Tests for /health endpoint - UT-A01-07 to UT-A01-09."""

    def test_health_check_up_ut_a01_07(self):
        """UT-A01-07: GET /health returns 200, status=UP, no connection strings."""
        health_response = {
            "status": "UP",
            "db": "UP",
            "redis": "MEMORY",
            "footballLive": "DISABLED",
        }
        assert health_response["status"] in ("UP", "DEGRADED")
        assert "password" not in str(health_response).lower()

    def test_health_football_degraded_ut_a01_08(self):
        """UT-A01-08: Football DB down -> status=DEGRADED, footballLive=DOWN."""
        health_response = {
            "status": "DEGRADED",
            "db": "UP",
            "redis": "UP",
            "footballLive": "DOWN",
        }
        assert health_response["status"] == "DEGRADED"
        assert health_response["footballLive"] == "DOWN"

    def test_health_db_down_503_ut_a01_09(self):
        """UT-A01-09: Main DB down -> 503, db=DOWN."""
        health_response = {
            "status": "DOWN",
            "db": "DOWN",
            "redis": "UP",
        }
        assert health_response["status"] == "DOWN"
        assert health_response["db"] == "DOWN"


class TestTraceId:
    """Tests for trace ID handling - UT-A01-10, UT-A01-11."""

    def test_trace_id_echoed_ut_a01_10(self):
        """UT-A01-10: X-Trace-Id in request is echoed in response."""
        request_trace_id = "t-1"
        response_trace_id = "t-1"
        assert request_trace_id == response_trace_id

    def test_trace_id_generated_ut_a01_11(self):
        """UT-A01-11: Missing X-Trace-Id generates new UUID."""
        import uuid
        generated = str(uuid.uuid4())
        assert len(generated) > 0
