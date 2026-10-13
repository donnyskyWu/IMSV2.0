# tests/integration/test_full_api_auth.py
"""
Full integration tests for authentication API using TestClient.

These tests exercise the actual API endpoints via HTTP requests,
which provides coverage for:
- app/api/auth.py
- app/api/deps.py
- app/services/auth.py
- app/core/cache.py
- app/db/session.py

Uses TestClient to test full request/response cycle.
"""
import os

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(db_session, test_context):
    """Create test client with database session."""
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def user_with_password(db_session, test_context):
    """Create a user with a known password for login tests."""
    import bcrypt

    from app.domains.sys.models import User

    password_hash = bcrypt.hashpw(
        "Test1234".encode(), bcrypt.gensalt(rounds=10)
    ).decode()

    user = User(
        id=100,
        tenant_id=1,
        username="testlogin",
        nickname="Test Login User",
        password_hash=password_hash,
        status="ACTIVE",
        source="LOCAL",
    )
    db_session.add(user)
    db_session.flush()

    return {
        "id": user.id,
        "username": user.username,
        "password": "Test1234",
    }


@pytest.fixture
def frozen_user_with_password(db_session, test_context):
    """Create a frozen user for testing frozen login."""
    import bcrypt

    from app.domains.sys.models import User

    password_hash = bcrypt.hashpw(
        "Test1234".encode(), bcrypt.gensalt(rounds=10)
    ).decode()

    user = User(
        id=101,
        tenant_id=1,
        username="frozenuser",
        nickname="Frozen User",
        password_hash=password_hash,
        status="FROZEN",
        source="LOCAL",
    )
    db_session.add(user)
    db_session.flush()

    return {
        "id": user.id,
        "username": user.username,
        "password": "Test1234",
    }


class TestLoginEndpoint:
    """Integration tests for POST /admin-api/ims/auth/login."""

    def test_login_endpoint_exists(self, app_client):
        """Test that login endpoint is registered."""
        response = app_client.post(
            "/admin-api/ims/auth/login",
            json={"username": "x" * 4, "password": "x" * 8},
        )
        assert response.status_code == 200

    def test_login_request_validation_short_username(self, app_client):
        """Test login rejects username < 4 chars."""
        response = app_client.post(
            "/admin-api/ims/auth/login",
            json={"username": "abc", "password": "password123"},
        )
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] != 0

    def test_login_request_validation_short_password(self, app_client):
        """Test login rejects password < 8 chars."""
        response = app_client.post(
            "/admin-api/ims/auth/login",
            json={"username": "validuser", "password": "short"},
        )
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] != 0

    def test_login_nonexistent_user_returns_1214(self, app_client, db_session):
        """Test login with non-existent user returns error 1214."""
        response = app_client.post(
            "/admin-api/ims/auth/login",
            json={"username": "nonexistent", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 1214

    def test_login_wrong_password_returns_1214(
        self, app_client, user_with_password, db_session
    ):
        """Test login with wrong password returns error 1214."""
        response = app_client.post(
            "/admin-api/ims/auth/login",
            json={
                "username": user_with_password["username"],
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 1214

    def test_login_frozen_user_wrong_password_returns_1214(
        self, app_client, frozen_user_with_password, db_session
    ):
        """Test frozen user with wrong password gets 1214 not 1216."""
        response = app_client.post(
            "/admin-api/ims/auth/login",
            json={
                "username": frozen_user_with_password["username"],
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 1214

    def test_login_frozen_user_correct_password_returns_1216(
        self, app_client, frozen_user_with_password, db_session
    ):
        """Test frozen user with correct password gets 1216."""
        response = app_client.post(
            "/admin-api/ims/auth/login",
            json={
                "username": frozen_user_with_password["username"],
                "password": frozen_user_with_password["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 1216


class TestLogoutEndpoint:
    """Integration tests for POST /admin-api/ims/auth/logout."""

    def test_logout_endpoint_exists(self, app_client):
        """Test that logout endpoint is registered."""
        response = app_client.post("/admin-api/ims/auth/logout")
        assert response.status_code == 200

    def test_logout_without_token_succeeds(self, app_client):
        """Test logout without token succeeds silently."""
        response = app_client.post("/admin-api/ims/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_logout_with_invalid_token_succeeds(self, app_client):
        """Test logout with invalid token succeeds silently."""
        response = app_client.post(
            "/admin-api/ims/auth/logout",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestRefreshTokenEndpoint:
    """Integration tests for POST /admin-api/ims/auth/refresh-token."""

    def test_refresh_token_endpoint_exists(self, app_client):
        """Test that refresh token endpoint is registered."""
        response = app_client.post(
            "/admin-api/ims/auth/refresh-token",
            json={"refresh_token": "sometoken"},
        )
        assert response.status_code in [200, 401]

    def test_refresh_invalid_token_returns_error(self, app_client):
        """Test refresh with invalid token returns error."""
        response = app_client.post(
            "/admin-api/ims/auth/refresh-token",
            json={"refresh_token": "invalidtoken"},
        )
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 1002


class TestMeEndpoint:
    """Integration tests for GET /admin-api/ims/auth/me."""

    def test_me_endpoint_without_auth_fails(self, app_client):
        """未登录调用 /me 与其它接口一样：HTTP 401，业务码 1002。"""
        response = app_client.get("/admin-api/ims/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == 1002

    def test_me_endpoint_with_invalid_token_fails(self, app_client):
        """无效令牌同样是 401 + 1002，不能落成 1008。"""
        response = app_client.get(
            "/admin-api/ims/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == 1002


class TestDingtalkSSOEndpoints:
    """Integration tests for DingTalk SSO endpoints."""

    def test_dingtalk_redirect_endpoint_exists(self, app_client):
        """Test DingTalk redirect endpoint is registered."""
        response = app_client.get(
            "/admin-api/ims/auth/sso/dingtalk/redirect",
            follow_redirects=False,
        )
        assert response.status_code in [200, 302, 307]

    def test_dingtalk_callback_endpoint_exists(self, app_client):
        """Test DingTalk callback endpoint is registered."""
        response = app_client.get(
            "/admin-api/ims/auth/sso/dingtalk/callback",
            params={"auth_code": "test", "state": "test"},
            follow_redirects=False,
        )
        assert response.status_code in [200, 302, 307, 401]


class TestAuthServiceCoverage:
    """Tests to improve coverage of AuthService internal methods."""

    def test_verify_token_with_expired_token(self, app_client):
        """Test that expired tokens are rejected."""
        from datetime import datetime, timedelta, timezone

        import jwt

        expired_payload = {
            "sub": "1",
            "tid": "1",
            "sid": "test-session",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "type": "access",
        }
        expired_token = jwt.encode(
            expired_payload,
            os.environ["IMS_JWT_SECRET"],
            algorithm="HS256",
        )

        response = app_client.get(
            "/admin-api/ims/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == 1002

    def test_verify_token_with_wrong_type(self, app_client):
        """Test that tokens with wrong type are rejected."""
        from datetime import datetime, timedelta, timezone

        import jwt

        wrong_type_payload = {
            "sub": "1",
            "tid": "1",
            "sid": "test-session",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
        }
        wrong_type_token = jwt.encode(
            wrong_type_payload,
            os.environ["IMS_JWT_SECRET"],
            algorithm="HS256",
        )

        response = app_client.get(
            "/admin-api/ims/auth/me",
            headers={"Authorization": f"Bearer {wrong_type_token}"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == 1002
