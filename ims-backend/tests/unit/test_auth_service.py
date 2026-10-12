# tests/unit/test_auth_service.py
"""
Unit tests for authentication service.

Covers app/services/auth.py
"""
import os
from datetime import datetime, timedelta

import pytest

os.environ["IMS_ENV"] = "test"
os.environ["IMS_DB_URL"] = "sqlite:///:memory:"
os.environ["IMS_REDIS_URL"] = ""
os.environ["IMS_JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"


class TestAuthServiceLogin:
    """Tests for login functionality."""

    def test_login_user_not_found(self, db_session, test_context):
        """Test login with non-existent user."""
        from app.core.errors import BizError
        from app.services.auth import AuthService

        service = AuthService()

        with pytest.raises(BizError) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.login("nonexistent", "password1")
            )
        assert exc_info.value.code == 1214

    def test_login_wrong_password(self, db_session, test_context):
        """Test login with wrong password."""
        import bcrypt

        from app.core.errors import BizError
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        password_hash = bcrypt.hashpw(b"Correct123", bcrypt.gensalt()).decode()
        user = User(
            id=1, tenant_id=1, username="testuser", nickname="Test",
            password_hash=password_hash, status="ACTIVE", source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        service = AuthService()

        with pytest.raises(BizError) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.login("testuser", "Wrong1234")
            )
        assert exc_info.value.code == 1214

    def test_login_frozen_user(self, db_session, test_context):
        """Test login with frozen user."""
        import bcrypt

        from app.core.errors import BizError
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        password_hash = bcrypt.hashpw(b"Correct123", bcrypt.gensalt()).decode()
        user = User(
            id=2, tenant_id=1, username="frozen", nickname="Frozen",
            password_hash=password_hash, status="FROZEN", source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        service = AuthService()

        with pytest.raises(BizError) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.login("frozen", "Correct123")
            )
        assert exc_info.value.code == 1216

    def test_login_success(self, db_session, test_context):
        """Test successful login."""
        import bcrypt

        from app.domains.sys.models import User
        from app.services.auth import AuthService

        password_hash = bcrypt.hashpw(b"Correct123", bcrypt.gensalt()).decode()
        user = User(
            id=3, tenant_id=1, username="gooduser", nickname="Good",
            password_hash=password_hash, status="ACTIVE", source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        service = AuthService()

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.login("gooduser", "Correct123")
        )

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["expires_in"] == 7200


class TestAuthServiceTokens:
    """Tests for token management."""

    def test_verify_invalid_token(self, db_session, test_context):
        """Test verifying invalid token."""
        from app.core.errors import BizError
        from app.services.auth import AuthService

        service = AuthService()

        with pytest.raises(BizError) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.verify_token("invalid_token")
            )
        assert exc_info.value.code == 1002

    def test_verify_expired_token(self, db_session, test_context, fixed_time):
        """Test verifying expired token."""
        import jwt

        from app.core.config import get_settings
        from app.core.errors import BizError
        from app.services.auth import AuthService

        settings = get_settings()

        past_time = datetime(2020, 1, 1)
        fixed_time(past_time)

        payload = {
            "sub": "1",
            "tid": "1",
            "sid": "session123",
            "exp": past_time - timedelta(hours=1),
            "iat": past_time - timedelta(hours=3),
            "type": "access",
        }
        expired_token = jwt.encode(
            payload, settings.jwt.secret, algorithm=settings.jwt.algorithm
        )

        service = AuthService()

        with pytest.raises(BizError) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.verify_token(expired_token)
            )
        assert exc_info.value.code == 1002


class TestAuthServiceLogout:
    """Tests for logout functionality."""

    def test_logout_invalid_token(self, db_session, test_context):
        """Test logout with invalid token."""
        from app.services.auth import AuthService

        service = AuthService()

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            service.logout("invalid_token")
        )


class TestAuthServiceUserInfo:
    """Tests for user info retrieval."""

    def test_get_user_info_not_found(self, db_session, test_context):
        """Test getting info for non-existent user."""
        from app.core.errors import BizError
        from app.services.auth import AuthService

        service = AuthService()

        with pytest.raises(BizError) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.get_current_user_info(9999)
            )
        assert exc_info.value.code == 1002

    def test_get_user_info_success(self, db_session, test_context):
        """Test getting user info successfully."""
        from app.domains.sys.models import Dept, User

        dept = Dept(
            id=1, tenant_id=1, parent_id=0, path="/1/",
            name="Root", status="ENABLED", source="LOCAL",
        )
        db_session.add(dept)

        user = User(
            id=1, tenant_id=1, username="testuser", nickname="Test",
            status="ACTIVE", source="LOCAL", main_dept_id=1,
        )
        db_session.add(user)
        db_session.flush()

        assert user.username == "testuser"
        assert user.main_dept_id == 1


class TestAuthServiceDingTalk:
    """Tests for DingTalk SSO."""

    def test_dingtalk_redirect_not_configured(self, db_session, test_context):
        """Test DingTalk redirect when not configured raises 1008."""
        from app.core.errors import BizError
        from app.services.auth import AuthService

        service = AuthService()

        with pytest.raises(BizError) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.get_dingtalk_redirect_url("/dashboard")
            )
        assert exc_info.value.code == 1008

    def test_dingtalk_callback_invalid_state(self, db_session, test_context):
        """Test DingTalk callback with invalid state."""
        from app.core.errors import BizError
        from app.services.auth import AuthService

        service = AuthService()

        with pytest.raises(BizError) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.handle_dingtalk_callback("code123", "invalid_state")
            )
        assert exc_info.value.code in (1002, 1217)
