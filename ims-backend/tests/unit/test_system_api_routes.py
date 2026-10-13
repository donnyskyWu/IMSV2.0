# tests/unit/test_system_api_routes.py - API Route Tests for B2 System Management
"""
API route tests for B2 system management endpoints.

Tests the API layer endpoints and route declarations.
"""

import pytest
from fastapi.testclient import TestClient


class TestRouteDeclarations:
    """Tests for route policy compliance."""

    def test_all_login_only_routes_declared(self, client):
        """Test that all login-only routes are properly declared."""
        from app.core.route_policy import DECLARED_LOGIN_ONLY
        
        # Personal center routes should be in login-only list
        assert "/admin-api/ims/auth/session/my" in DECLARED_LOGIN_ONLY
        assert "/admin-api/ims/auth/password/set" in DECLARED_LOGIN_ONLY

    def test_anonymous_routes_in_whitelist(self, client):
        """Test anonymous routes are in whitelist."""
        from app.core.route_policy import ANONYMOUS_WHITELIST
        
        # Health check is always anonymous
        assert "/health" in ANONYMOUS_WHITELIST
        # Login is anonymous
        assert "/admin-api/ims/auth/login" in ANONYMOUS_WHITELIST
