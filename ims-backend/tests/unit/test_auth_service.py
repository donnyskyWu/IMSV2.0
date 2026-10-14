# tests/unit/test_auth_service.py
"""
Unit tests for authentication service.

Covers app/services/auth.py
"""
import os
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")


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


class TestPermVersionInvalidation:
    """Tests for permission version-based cache invalidation (FP-D03-04)."""

    @pytest.mark.asyncio
    async def test_bump_perm_version_invalidates_cache(self, db_session, test_context):
        """UT-B1-PERM-VER-01: Bumping perm_ver invalidates cached permissions.

        Flow:
        1. Load user permissions (populates cache with version N)
        2. Bump user perm version (version becomes N+1)
        3. Load permissions again - should reload from DB (versions mismatch)
        """
        from app.core.cache import Cache
        from app.domains.sys.models import Menu, Role, RoleMenu, User, UserRole
        from app.services.auth import AuthService

        user = User(
            id=100,
            tenant_id=1,
            username="perm_ver_user",
            nickname="Perm Ver User",
            status="ACTIVE",
            source="LOCAL",
        )
        db_session.add(user)

        role = Role(
            id=100,
            tenant_id=1,
            role_key="test_role",
            name="Test Role",
            status="ENABLED",
            source="LOCAL",
        )
        db_session.add(role)

        menu = Menu(
            id=100,
            tenant_id=1,
            parent_id=0,
            path="/test",
            name="Test Menu",
            type="MENU",
            perm_code="test:perm:code",
            status="ENABLED",
        )
        db_session.add(menu)

        user_role = UserRole(
            id=100,
            tenant_id=1,
            user_id=100,
            role_id=100,
            source="LOCAL",
        )
        db_session.add(user_role)

        role_menu = RoleMenu(
            id=100,
            tenant_id=1,
            role_id=100,
            menu_id=100,
        )
        db_session.add(role_menu)
        db_session.flush()

        service = AuthService()
        cache_key = f"{service.PERM_CACHE_PREFIX}100"

        perms1 = await service._get_user_permissions(100)
        assert "test:perm:code" in perms1["perm_codes"]

        cached_before = Cache.get_json(cache_key)
        assert cached_before is not None
        assert "_perm_ver" in cached_before
        ver_before = cached_before["_perm_ver"]

        new_ver = AuthService.bump_user_perm_version(100)
        assert new_ver == ver_before + 1

        perms2 = await service._get_user_permissions(100)

        cached_after = Cache.get_json(cache_key)
        assert cached_after is not None
        assert cached_after["_perm_ver"] == new_ver
        assert "test:perm:code" in perms2["perm_codes"]

    @pytest.mark.asyncio
    async def test_tenant_perm_version_invalidates_cache(self, db_session, test_context):
        """A tenant perm_ver bump reloads permissions even when the user version is unchanged."""
        from app.core.cache import Cache
        from app.domains.sys.models import Menu, Role, RoleMenu, User, UserRole
        from app.services.auth import AuthService

        db_session.add(User(
            id=110, tenant_id=1, username="tenant_ver_user", nickname="T",
            status="ACTIVE", source="LOCAL",
        ))
        db_session.add(Role(
            id=110, tenant_id=1, role_key="tenant_ver_role", name="T",
            status="ENABLED", source="LOCAL",
        ))
        db_session.add(Menu(
            id=110, tenant_id=1, parent_id=0, path="/tenant-ver", name="T",
            type="MENU", perm_code="test:tenant:ver", status="ENABLED",
        ))
        db_session.add(UserRole(
            id=110, tenant_id=1, user_id=110, role_id=110, source="LOCAL",
        ))
        db_session.add(RoleMenu(id=110, tenant_id=1, role_id=110, menu_id=110))
        db_session.flush()

        service = AuthService()
        cache_key = f"{service.PERM_CACHE_PREFIX}110"
        loaded = await service._get_user_permissions(110)
        assert "test:tenant:ver" in loaded["perm_codes"]
        again = await service._get_user_permissions(110)
        assert again["_tenant_perm_ver"] == loaded["_tenant_perm_ver"]

        stale = Cache.get_json(cache_key)
        stale.pop("_tenant_id")
        Cache.set_json(cache_key, stale, ttl=1800)
        reloaded = await service._get_user_permissions(110)
        assert reloaded["_tenant_id"] == 1

        before = AuthService.get_tenant_perm_version(1)
        bumped = AuthService.bump_tenant_perm_version(1)
        assert bumped == before + 1
        after = await service._get_user_permissions(110)
        assert after["_tenant_perm_ver"] == bumped
        assert "test:tenant:ver" in after["perm_codes"]

    def test_grant_menu_bumps_perm_version(self, db_session, test_context):
        """UT-B1-PERM-VER-02: Granting menu to role bumps affected users' perm_ver."""
        from app.domains.sys.models import Menu, Role, UserRole
        from app.services.access import grant_menu
        from app.services.auth import AuthService

        role = Role(
            id=200,
            tenant_id=1,
            role_key="grant_test_role",
            name="Grant Test Role",
            status="ENABLED",
            source="LOCAL",
        )
        db_session.add(role)

        menu = Menu(
            id=200,
            tenant_id=1,
            parent_id=0,
            path="/grant-test",
            name="Grant Test Menu",
            type="MENU",
            perm_code="grant:test:perm",
            status="ENABLED",
        )
        db_session.add(menu)

        user_role = UserRole(
            id=200,
            tenant_id=1,
            user_id=200,
            role_id=200,
            source="LOCAL",
        )
        db_session.add(user_role)
        db_session.flush()

        ver_before = AuthService.get_user_perm_version(200)

        grant_menu(200, 200)

        ver_after = AuthService.get_user_perm_version(200)
        assert ver_after == ver_before + 1, "grant_menu should bump user's perm version"

    def test_revoke_menu_bumps_perm_version(self, db_session, test_context):
        """UT-B1-PERM-VER-03: Revoking menu from role bumps affected users' perm_ver."""
        from app.domains.sys.models import Menu, Role, RoleMenu, UserRole
        from app.services.access import revoke_menu
        from app.services.auth import AuthService

        role = Role(
            id=300,
            tenant_id=1,
            role_key="revoke_test_role",
            name="Revoke Test Role",
            status="ENABLED",
            source="LOCAL",
        )
        db_session.add(role)

        menu = Menu(
            id=300,
            tenant_id=1,
            parent_id=0,
            path="/revoke-test",
            name="Revoke Test Menu",
            type="MENU",
            perm_code="revoke:test:perm",
            status="ENABLED",
        )
        db_session.add(menu)

        role_menu = RoleMenu(
            id=300,
            tenant_id=1,
            role_id=300,
            menu_id=300,
        )
        db_session.add(role_menu)

        user_role = UserRole(
            id=300,
            tenant_id=1,
            user_id=300,
            role_id=300,
            source="LOCAL",
        )
        db_session.add(user_role)
        db_session.flush()

        ver_before = AuthService.get_user_perm_version(300)

        revoke_menu(300, 300)

        ver_after = AuthService.get_user_perm_version(300)
        assert ver_after == ver_before + 1, "revoke_menu should bump user's perm version"
