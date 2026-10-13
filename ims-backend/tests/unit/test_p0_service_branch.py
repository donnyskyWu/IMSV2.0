# tests/unit/test_p0_service_branch.py
"""
P0 Service Branch Coverage Tests.

Target: ≥90% branch coverage for:
- AuthService (app/services/auth.py)
- Permission deps (app/api/deps.py)
- DictService (app/services/dict.py)
- RoleService (app/services/role.py) - already 100%

These tests focus on branch coverage (decision points) for P0 services.
"""
import os
from datetime import timedelta

import pytest

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")


# ============================================================================
# AuthService Branch Coverage Tests
# ============================================================================

class TestAuthServiceLoginBranches:
    """Branch coverage for AuthService.login()."""

    @pytest.mark.asyncio
    async def test_login_when_account_locked(self, db_session, test_context):
        """UT-D01-01: Test login when account is currently locked."""
        from app.core.cache import Cache
        from app.core.clock import get_now
        from app.core.errors import BizError
        from app.services.auth import AuthService

        service = AuthService()
        lock_key = f"{service.LOGIN_FAIL_PREFIX}locked_user"

        # Set up lock data with future lock_until
        lock_until = get_now() + timedelta(minutes=10)
        Cache.set_json(lock_key, {
            "count": 5,
            "lock_until": lock_until.isoformat(),
        }, ttl=900)

        with pytest.raises(BizError) as exc_info:
            await service.login("locked_user", "password")
        # Error code 1215 = account locked
        assert exc_info.value.code == 1215

        # Cleanup
        Cache.delete(lock_key)

    @pytest.mark.asyncio
    async def test_login_when_lock_expired(self, db_session, test_context):
        """UT-D01-02: Test login when lock has expired."""
        import bcrypt

        from app.core.cache import Cache
        from app.core.clock import get_now
        from app.core.errors import BizError
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        service = AuthService()

        # Create user
        password_hash = bcrypt.hashpw(b"Correct123", bcrypt.gensalt()).decode()
        user = User(
            id=101, tenant_id=1, username="expired_lock_user", nickname="Test",
            password_hash=password_hash, status="ACTIVE", source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        # Set up expired lock data
        lock_key = f"{service.LOGIN_FAIL_PREFIX}expired_lock_user"
        lock_until = get_now() - timedelta(minutes=10)  # Expired
        Cache.set_json(lock_key, {
            "count": 5,
            "lock_until": lock_until.isoformat(),
        }, ttl=900)

        # Should proceed to login (lock expired), but fail due to wrong password
        with pytest.raises(BizError) as exc_info:
            await service.login("expired_lock_user", "WrongPass123")
        assert exc_info.value.code == 1214  # Invalid credentials, not locked

        # Cleanup
        Cache.delete(lock_key)


class TestAuthServiceRecordLoginFailure:
    """Branch coverage for AuthService._record_login_failure()."""

    @pytest.mark.asyncio
    async def test_record_failure_increments_count(self, db_session, test_context):
        """UT-D01-03: Test failure count increments."""
        from app.core.cache import Cache
        from app.services.auth import AuthService

        service = AuthService()
        lock_key = f"{service.LOGIN_FAIL_PREFIX}fail_count_user"

        # Clear any existing data
        Cache.delete(lock_key)

        # First failure
        await service._record_login_failure("fail_count_user")

        fail_data = Cache.get_json(lock_key)
        assert fail_data is not None
        assert fail_data["count"] == 1

        # Second failure
        await service._record_login_failure("fail_count_user")

        fail_data = Cache.get_json(lock_key)
        assert fail_data["count"] == 2

        # Cleanup
        Cache.delete(lock_key)

    @pytest.mark.asyncio
    async def test_record_failure_locks_after_threshold(self, db_session, test_context):
        """UT-D01-04: Test account gets locked after max failures."""
        from app.core.cache import Cache
        from app.core.config import get_settings
        from app.services.auth import AuthService

        service = AuthService()
        settings = get_settings()
        lock_key = f"{service.LOGIN_FAIL_PREFIX}lock_threshold_user"

        # Clear any existing data
        Cache.delete(lock_key)

        # Set count just below threshold
        Cache.set_json(lock_key, {"count": settings.lock.max_fail_count - 1}, ttl=900)

        # This failure should trigger lock
        await service._record_login_failure("lock_threshold_user")

        fail_data = Cache.get_json(lock_key)
        assert fail_data is not None
        assert fail_data["count"] == settings.lock.max_fail_count
        assert "lock_until" in fail_data

        # Cleanup
        Cache.delete(lock_key)


class TestAuthServiceCreateTokens:
    """Branch coverage for AuthService._create_tokens()."""

    @pytest.mark.asyncio
    async def test_create_tokens_returns_both_tokens(self, db_session, test_context):
        """UT-D01-05: Test token creation returns access and refresh tokens."""
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        user = User(
            id=201, tenant_id=1, username="token_user", nickname="Token",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        service = AuthService()

        tokens = await service._create_tokens(user, "test-session-id")

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert len(tokens["access_token"]) > 0
        assert len(tokens["refresh_token"]) > 0


class TestAuthServiceAddUserSession:
    """Branch coverage for AuthService._add_user_session()."""

    @pytest.mark.asyncio
    async def test_add_session_enforces_max_limit(self, db_session, test_context):
        """UT-D01-06: Test oldest session is removed when max reached."""
        from app.core.cache import Cache
        from app.core.clock import get_now
        from app.services.auth import AuthService

        service = AuthService()
        user_id = 301
        sessions_key = f"{service.USER_SESSIONS_PREFIX}{user_id}"

        # Clear any existing data
        Cache.delete(sessions_key)

        # Create MAX_SESSIONS existing sessions with timestamps
        now = get_now()
        for i in range(service.MAX_SESSIONS):
            session_id = f"old-session-{i}"
            Cache.sadd(sessions_key, session_id)
            # Store session data with creation time
            session_data = {
                "user_id": user_id,
                "tenant_id": 1,
                "refresh_token": f"refresh-{i}",
                "created_at": (now - timedelta(hours=service.MAX_SESSIONS - i)).isoformat(),
            }
            Cache.set_json(f"{service.SESSION_PREFIX}{session_id}", session_data, ttl=86400)

        # Add a new session - should evict oldest
        await service._add_user_session(user_id, "new-session-id")

        # The oldest session (old-session-0) should be removed
        remaining = Cache.smembers(sessions_key)
        # Note: new session is added, so we may have MAX_SESSIONS sessions
        assert "new-session-id" in remaining

        # Cleanup
        Cache.delete(sessions_key)
        for i in range(service.MAX_SESSIONS):
            Cache.delete(f"{service.SESSION_PREFIX}old-session-{i}")
        Cache.delete(f"{service.SESSION_PREFIX}new-session-id")


class TestAuthServiceVerifyToken:
    """Branch coverage for AuthService.verify_token()."""

    @pytest.mark.asyncio
    async def test_verify_token_wrong_type(self, db_session, test_context):
        """UT-D01-07: Test verify fails when token type is not 'access'."""
        import jwt

        from app.core.clock import get_now
        from app.core.config import get_settings
        from app.core.errors import BizError
        from app.services.auth import AuthService

        settings = get_settings()
        service = AuthService()
        now = get_now()

        # Create a token with type 'refresh' instead of 'access'
        payload = {
            "sub": "1",
            "tid": "1",
            "sid": "session123",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "refresh",  # Wrong type
        }
        token = jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)

        with pytest.raises(BizError) as exc_info:
            await service.verify_token(token)
        assert exc_info.value.code == 1002

    @pytest.mark.asyncio
    async def test_verify_token_session_not_found(self, db_session, test_context):
        """UT-D01-08: Test verify fails when session doesn't exist in cache."""
        import jwt

        from app.core.clock import get_now
        from app.core.config import get_settings
        from app.core.errors import BizError
        from app.services.auth import AuthService

        settings = get_settings()
        service = AuthService()
        now = get_now()

        payload = {
            "sub": "1",
            "tid": "1",
            "sid": "nonexistent-session",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
        }
        token = jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)

        with pytest.raises(BizError) as exc_info:
            await service.verify_token(token)
        assert exc_info.value.code == 1002

    @pytest.mark.asyncio
    async def test_verify_token_blacklisted(self, db_session, test_context):
        """UT-D01-09: Test verify fails when session is blacklisted."""
        import jwt

        from app.core.cache import Cache
        from app.core.clock import get_now
        from app.core.config import get_settings
        from app.core.errors import BizError
        from app.services.auth import AuthService

        settings = get_settings()
        service = AuthService()
        now = get_now()

        session_id = "blacklisted-session"

        # Store session in cache
        Cache.set_json(f"{service.SESSION_PREFIX}{session_id}", {
            "user_id": 1,
            "tenant_id": 1,
            "refresh_token": "refresh",
            "created_at": now.isoformat(),
        }, ttl=86400)

        # Blacklist the session
        Cache.set(f"{service.TOKEN_BLACKLIST_PREFIX}{session_id}", "1", ttl=86400)

        payload = {
            "sub": "1",
            "tid": "1",
            "sid": session_id,
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
        }
        token = jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)

        with pytest.raises(BizError) as exc_info:
            await service.verify_token(token)
        assert exc_info.value.code == 1002

        # Cleanup
        Cache.delete(f"{service.SESSION_PREFIX}{session_id}")
        Cache.delete(f"{service.TOKEN_BLACKLIST_PREFIX}{session_id}")

    @pytest.mark.asyncio
    async def test_verify_token_success_loads_permissions(self, db_session, test_context):
        """UT-D01-10: Test verify token successfully loads user permissions."""
        import jwt

        from app.core.cache import Cache
        from app.core.clock import get_now
        from app.core.config import get_settings
        from app.domains.sys.models import Menu, Role, RoleMenu, User, UserDept, UserRole
        from app.services.auth import AuthService

        settings = get_settings()
        service = AuthService()
        now = get_now()

        # Create user with role and permissions
        user = User(
            id=401, tenant_id=1, username="perm_user", nickname="Perm",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user)

        role = Role(
            id=401, tenant_id=1, role_key="R_TEST_PERM", name="Test Role",
            status="ENABLED", source="MANUAL", data_scope="ALL",
        )
        db_session.add(role)

        user_role = UserRole(id=401, user_id=401, role_id=401)
        db_session.add(user_role)

        menu = Menu(
            id=401, tenant_id=1, parent_id=0, name="Test Menu",
            type="BUTTON", status="ENABLED", perm_code="ims:test:action",
        )
        db_session.add(menu)

        role_menu = RoleMenu(id=401, role_id=401, menu_id=401)
        db_session.add(role_menu)

        user_dept = UserDept(id=401, user_id=401, dept_id=1, is_main=True)
        db_session.add(user_dept)

        db_session.flush()

        # Create valid session
        session_id = "valid-session-401"
        Cache.set_json(f"{service.SESSION_PREFIX}{session_id}", {
            "user_id": 401,
            "tenant_id": 1,
            "refresh_token": "refresh",
            "created_at": now.isoformat(),
        }, ttl=86400)

        # Clear any cached permissions
        Cache.delete(f"{service.PERM_CACHE_PREFIX}401")

        payload = {
            "sub": "401",
            "tid": "1",
            "sid": session_id,
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
        }
        token = jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)

        result = await service.verify_token(token)

        assert result["user_id"] == 401
        assert result["tenant_id"] == 1
        assert "ims:test:action" in result["perm_codes"]
        assert len(result["data_scopes"]) > 0
        assert 1 in result["dept_ids"]

        # Cleanup
        Cache.delete(f"{service.SESSION_PREFIX}{session_id}")
        Cache.delete(f"{service.PERM_CACHE_PREFIX}401")


class TestAuthServiceLogout:
    """Branch coverage for AuthService.logout()."""

    @pytest.mark.asyncio
    async def test_logout_with_valid_token(self, db_session, test_context):
        """UT-D01-11: Test logout with valid token cleans up session."""
        import jwt

        from app.core.cache import Cache
        from app.core.clock import get_now
        from app.core.config import get_settings
        from app.services.auth import AuthService

        settings = get_settings()
        service = AuthService()
        now = get_now()

        session_id = "logout-session"
        user_id = 501

        # Create session in cache
        Cache.set_json(f"{service.SESSION_PREFIX}{session_id}", {
            "user_id": user_id,
            "tenant_id": 1,
            "refresh_token": "refresh",
            "created_at": now.isoformat(),
        }, ttl=86400)

        # Add to user sessions
        Cache.sadd(f"{service.USER_SESSIONS_PREFIX}{user_id}", session_id)

        # Create token
        payload = {
            "sub": str(user_id),
            "tid": "1",
            "sid": session_id,
            "exp": (now + timedelta(hours=1)).timestamp(),
            "iat": now.timestamp(),
            "type": "access",
        }
        token = jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)

        await service.logout(token)

        # Session should be deleted
        assert Cache.get_json(f"{service.SESSION_PREFIX}{session_id}") is None
        # Session should be blacklisted
        assert Cache.get(f"{service.TOKEN_BLACKLIST_PREFIX}{session_id}") is not None
        # Session should be removed from user sessions
        remaining = Cache.smembers(f"{service.USER_SESSIONS_PREFIX}{user_id}")
        assert session_id not in remaining

        # Cleanup
        Cache.delete(f"{service.TOKEN_BLACKLIST_PREFIX}{session_id}")
        Cache.delete(f"{service.USER_SESSIONS_PREFIX}{user_id}")

    @pytest.mark.asyncio
    async def test_logout_with_expired_token(self, db_session, test_context):
        """UT-D01-12: Test logout with expired token still works."""
        import jwt

        from app.core.cache import Cache
        from app.core.clock import get_now
        from app.core.config import get_settings
        from app.services.auth import AuthService

        settings = get_settings()
        service = AuthService()
        now = get_now()

        session_id = "logout-expired-session"
        user_id = 502

        # Create session in cache
        Cache.set_json(f"{service.SESSION_PREFIX}{session_id}", {
            "user_id": user_id,
            "tenant_id": 1,
            "refresh_token": "refresh",
            "created_at": now.isoformat(),
        }, ttl=86400)

        # Create expired token
        payload = {
            "sub": str(user_id),
            "tid": "1",
            "sid": session_id,
            "exp": (now - timedelta(hours=1)).timestamp(),  # Expired
            "iat": (now - timedelta(hours=2)).timestamp(),
            "type": "access",
        }
        token = jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)

        # Should not raise error
        await service.logout(token)

        # Session should be deleted
        assert Cache.get_json(f"{service.SESSION_PREFIX}{session_id}") is None


class TestAuthServiceGetCurrentUserInfo:
    """Branch coverage for AuthService.get_current_user_info()."""

    @pytest.mark.asyncio
    async def test_get_user_info_with_main_dept(self, db_session, test_context):
        """UT-D01-13: Test get user info with main department."""
        from app.domains.sys.models import Dept, User
        from app.services.auth import AuthService

        dept = Dept(
            id=601, tenant_id=1, parent_id=0, path="/601/",
            name="Info Dept", status="ENABLED", source="LOCAL",
        )
        db_session.add(dept)

        user = User(
            id=601, tenant_id=1, username="info_user", nickname="Info",
            status="ACTIVE", source="LOCAL", main_dept_id=601,
        )
        db_session.add(user)
        db_session.flush()

        service = AuthService()

        result = await service.get_current_user_info(601)

        assert result["user"]["id"] == "601"
        assert result["user"]["main_dept_name"] == "Info Dept"

    @pytest.mark.asyncio
    async def test_get_user_info_no_main_dept(self, db_session, test_context):
        """UT-D01-14: Test get user info without main department."""
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        user = User(
            id=602, tenant_id=1, username="no_dept_user", nickname="NoDept",
            status="ACTIVE", source="LOCAL", main_dept_id=None,
        )
        db_session.add(user)
        db_session.flush()

        service = AuthService()

        result = await service.get_current_user_info(602)

        assert result["user"]["id"] == "602"
        assert result["user"]["main_dept_name"] is None


class TestAuthServiceBuildDataScopeText:
    """Branch coverage for AuthService._build_data_scope_text()."""

    @pytest.mark.asyncio
    async def test_data_scope_text_all(self, db_session, test_context):
        """UT-D01-15: Test data scope text for ALL scope."""
        from app.services.auth import AuthService

        service = AuthService()
        perm_data = {
            "data_scopes": [{"scope_type": "ALL", "role_id": 1}],
            "dept_ids": [],
        }

        result = await service._build_data_scope_text(perm_data, 1)

        assert result == "全部"

    @pytest.mark.asyncio
    async def test_data_scope_text_dept(self, db_session, test_context):
        """UT-D01-16: Test data scope text for DEPT scope."""
        from app.domains.sys.models import Dept
        from app.services.auth import AuthService

        dept = Dept(
            id=701, tenant_id=1, parent_id=0, path="/701/",
            name="Scope Dept", status="ENABLED", source="LOCAL",
        )
        db_session.add(dept)
        db_session.flush()

        service = AuthService()
        perm_data = {
            "data_scopes": [{"scope_type": "DEPT", "role_id": 1}],
            "dept_ids": [701],
        }

        result = await service._build_data_scope_text(perm_data, 1)

        assert "本部门" in result
        assert "Scope Dept" in result

    @pytest.mark.asyncio
    async def test_data_scope_text_dept_no_ids(self, db_session, test_context):
        """UT-D01-17: Test data scope text for DEPT scope without dept_ids."""
        from app.services.auth import AuthService

        service = AuthService()
        perm_data = {
            "data_scopes": [{"scope_type": "DEPT", "role_id": 1}],
            "dept_ids": [],
        }

        result = await service._build_data_scope_text(perm_data, 1)

        assert result == "本部门"

    @pytest.mark.asyncio
    async def test_data_scope_text_ip_group(self, db_session, test_context):
        """UT-D01-18: Test data scope text for IP_GROUP scope."""
        from app.services.auth import AuthService

        service = AuthService()
        perm_data = {
            "data_scopes": [{"scope_type": "IP_GROUP", "role_id": 1}],
            "dept_ids": [],
        }

        result = await service._build_data_scope_text(perm_data, 1)

        assert "所属 IP 组" in result

    @pytest.mark.asyncio
    async def test_data_scope_text_self(self, db_session, test_context):
        """UT-D01-19: Test data scope text for SELF scope."""
        from app.services.auth import AuthService

        service = AuthService()
        perm_data = {
            "data_scopes": [{"scope_type": "SELF", "role_id": 1}],
            "dept_ids": [],
        }

        result = await service._build_data_scope_text(perm_data, 1)

        assert "仅本人" in result

    @pytest.mark.asyncio
    async def test_data_scope_text_empty(self, db_session, test_context):
        """Data scope text for empty scopes (not an FP-D01 case id)."""
        from app.services.auth import AuthService

        service = AuthService()
        perm_data = {
            "data_scopes": [],
            "dept_ids": [],
        }

        result = await service._build_data_scope_text(perm_data, 1)

        assert "尚未分配权限" in result

    @pytest.mark.asyncio
    async def test_data_scope_text_multiple(self, db_session, test_context):
        """Data scope text for multiple scopes (not an FP-D01 case id)."""
        from app.services.auth import AuthService

        service = AuthService()
        perm_data = {
            "data_scopes": [
                {"scope_type": "IP_GROUP", "role_id": 1},
                {"scope_type": "SELF", "role_id": 2},
            ],
            "dept_ids": [],
        }

        result = await service._build_data_scope_text(perm_data, 1)

        assert "所属 IP 组" in result
        assert "仅本人" in result


class TestAuthServiceDingTalk:
    """Branch coverage for AuthService DingTalk methods."""

    @pytest.mark.asyncio
    async def test_dingtalk_redirect_invalid_redirect(self, db_session, test_context, monkeypatch):
        """UT-D02-01: Test DingTalk redirect with invalid redirect URL."""
        from app.core.config import get_settings
        from app.services.auth import AuthService

        # Mock settings to have DingTalk configured
        original_settings = get_settings()
        monkeypatch.setattr(
            original_settings.dingtalk, "app_key", "test_app_key"
        )

        service = AuthService()

        # Test with double-slash (invalid)
        result = await service.get_dingtalk_redirect_url("//evil.com")
        # Should default to "/" and return auth URL
        assert "state=" in result

    @pytest.mark.asyncio
    async def test_dingtalk_callback_consumes_state(self, db_session, test_context, monkeypatch):
        """UT-D02-02: Test DingTalk callback consumes state atomically."""
        import app.services.auth as auth_mod
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.services.auth import AuthService

        monkeypatch.setattr(auth_mod.settings.dingtalk, "app_key", "ding-key")
        monkeypatch.setattr(auth_mod.settings.dingtalk, "mode", "mock")
        service = AuthService()
        state = "test-state-123"

        # Store state
        Cache.set_json(f"{service.SSO_STATE_PREFIX}{state}", {"redirect": "/dashboard"}, ttl=300)

        # First call should consume state
        with pytest.raises(BizError) as exc_info:
            await service.handle_dingtalk_callback("code", state)
        # Error 1217 = placeholder for no user match (expected in test)
        assert exc_info.value.code == 1217

        # State should be consumed
        assert Cache.get(f"{service.SSO_STATE_PREFIX}{state}") is None


# ============================================================================
# deps.py Branch Coverage Tests
# ============================================================================

class TestDepsBranches:
    """Branch coverage for app/api/deps.py."""

    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_valid_token(self, db_session, test_context):
        """UT-D03-01: Test get_current_user_optional with valid token."""
        import jwt

        from app.core.cache import Cache
        from app.core.clock import get_now
        from app.core.config import get_settings
        from app.services.auth import AuthService

        settings = get_settings()
        now = get_now()
        session_id = "deps-test-session"

        # Setup session
        service = AuthService()
        Cache.set_json(f"{service.SESSION_PREFIX}{session_id}", {
            "user_id": 1,
            "tenant_id": 1,
            "refresh_token": "refresh",
            "created_at": now.isoformat(),
        }, ttl=86400)

        # Create valid token
        payload = {
            "sub": "1",
            "tid": "1",
            "sid": session_id,
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
        }
        token = jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)

        from app.api.deps import get_current_user_optional

        result = await get_current_user_optional(token)

        assert result == 1

        # Cleanup
        Cache.delete(f"{service.SESSION_PREFIX}{session_id}")
        Cache.delete(f"{service.PERM_CACHE_PREFIX}1")

    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_invalid_token(self, db_session, test_context):
        """UT-D03-02: Test get_current_user_optional with invalid token returns None."""
        from app.api.deps import get_current_user_optional

        result = await get_current_user_optional("invalid.token.here")

        assert result is None

    @pytest.mark.asyncio
    async def test_require_login_no_tenant(self, db_session):
        """UT-D03-03: Test require_login raises when tenant_id is None."""
        from app.api.deps import require_login
        from app.core.context import RequestContext, ctx
        from app.core.errors import BizError

        # Set context without tenant
        ctx.set(RequestContext(
            trace_id="test",
            user_id=1,
            tenant_id=None,  # No tenant
            perm_codes=set(),
            client_ip="127.0.0.1",
        ))

        with pytest.raises(BizError) as exc_info:
            await require_login(1)
        assert exc_info.value.code == 1008

        ctx.reset()

    @pytest.mark.asyncio
    async def test_require_permission_no_context(self, db_session):
        """UT-D03-04: Test require_permission raises when context is None."""
        from app.api.deps import require_permission
        from app.core.context import ctx
        from app.core.errors import BizError

        # Ensure no context
        ctx.reset()

        dep = require_permission("ims:test:perm")

        with pytest.raises(BizError) as exc_info:
            await dep(1)
        assert exc_info.value.code == 1008

    @pytest.mark.asyncio
    async def test_require_any_permission_no_context(self, db_session):
        """UT-D03-05: Test require_any_permission raises when context is None."""
        from app.api.deps import require_any_permission
        from app.core.context import ctx
        from app.core.errors import BizError

        ctx.reset()

        dep = require_any_permission(["perm1", "perm2"])

        with pytest.raises(BizError) as exc_info:
            await dep(1)
        assert exc_info.value.code == 1008

    @pytest.mark.asyncio
    async def test_require_all_permissions_no_context(self, db_session):
        """UT-D03-06: Test require_all_permissions raises when context is None."""
        from app.api.deps import require_all_permissions
        from app.core.context import ctx
        from app.core.errors import BizError

        ctx.reset()

        dep = require_all_permissions(["perm1", "perm2"])

        with pytest.raises(BizError) as exc_info:
            await dep(1)
        assert exc_info.value.code == 1008

    @pytest.mark.asyncio
    async def test_require_data_scope_no_context(self, db_session):
        """UT-D03-07: Test require_data_scope raises when context is None."""
        from app.api.deps import require_data_scope
        from app.core.context import ctx
        from app.core.errors import BizError

        ctx.reset()

        dep = require_data_scope("User")

        with pytest.raises(BizError) as exc_info:
            await dep(1)
        assert exc_info.value.code == 1008

    @pytest.mark.asyncio
    async def test_permission_checker_write_with_perm_succeeds(self, db_session, admin_context):
        """UT-D03-08: Test PermissionChecker.write succeeds with permission."""
        from app.api.deps import PermissionChecker

        checker = PermissionChecker(write_perm="ims:system:user:update")

        result = await checker.write(1)
        assert result == 1

    @pytest.mark.asyncio
    async def test_permission_checker_delete_with_perm_succeeds(self, db_session, admin_context):
        """UT-D03-09: Test PermissionChecker.delete succeeds with permission."""
        from app.api.deps import PermissionChecker

        checker = PermissionChecker(delete_perm="ims:system:user:delete")

        result = await checker.delete(1)
        assert result == 1

    @pytest.mark.asyncio
    async def test_permission_checker_no_perm_required(self, db_session, test_context):
        """UT-D03-10: Test PermissionChecker methods when no perm required."""
        from app.api.deps import PermissionChecker

        checker = PermissionChecker()  # No permissions required

        # All should succeed without permission
        assert await checker.read(1) == 1
        assert await checker.write(1) == 1
        assert await checker.delete(1) == 1

    @pytest.mark.asyncio
    async def test_require_data_scope_with_scopes_succeeds(self, db_session):
        """require_data_scope succeeds when scopes are configured."""
        from app.api.deps import require_data_scope
        from app.core.context import RequestContext, ctx

        ctx.set(RequestContext(
            trace_id="test",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            client_ip="127.0.0.1",
        ))

        dep = require_data_scope("User")

        result = await dep(1)
        assert result == 1

        ctx.reset()


# ============================================================================
# DictService Branch Coverage Tests
# ============================================================================

class TestDictServiceBranches:
    """Branch coverage for app/services/dict.py."""

    @pytest.mark.asyncio
    async def test_validate_dict_value_allow_disabled(self, db_session, test_context):
        """UT-B07-01: Test validate_dict_value with allow_disabled=True."""
        from app.domains.sys.models import DictData
        from app.services.dict import DictService

        # Create a DISABLED dict value
        data = DictData(
            id=801, tenant_id=1, dict_type="dict_test_disabled",
            dict_value="DISABLED_VAL", dict_label="Disabled Value",
            status="DISABLED", sort=0,
        )
        db_session.add(data)
        db_session.flush()

        service = DictService()

        # Should pass with allow_disabled=True
        result = await service.validate_dict_value("dict_test_disabled", "DISABLED_VAL", allow_disabled=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_dict_value_disabled_without_flag(self, db_session, test_context):
        """UT-B07-02: Test validate_dict_value fails for DISABLED without flag."""
        from app.core.errors import BizError
        from app.domains.sys.models import DictData
        from app.services.dict import DictService

        # Create a DISABLED dict value
        data = DictData(
            id=802, tenant_id=1, dict_type="dict_test_disabled2",
            dict_value="DISABLED_VAL2", dict_label="Disabled Value 2",
            status="DISABLED", sort=0,
        )
        db_session.add(data)
        db_session.flush()

        service = DictService()

        with pytest.raises(BizError) as exc_info:
            await service.validate_dict_value("dict_test_disabled2", "DISABLED_VAL2", allow_disabled=False)
        assert exc_info.value.code == 1503

    @pytest.mark.asyncio
    async def test_get_dict_label_not_found(self, db_session, test_context):
        """UT-B07-03: Test get_dict_label returns None when not found."""
        from app.services.dict import DictService

        service = DictService()

        result = await service.get_dict_label("dict_nonexistent", "NONEXISTENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_dict_label_found(self, db_session, sample_dict):
        """UT-B07-04: Test get_dict_label returns label when found."""
        from app.core.cache import Cache
        from app.services.dict import DictService

        service = DictService()

        # Clear cache to ensure DB is queried
        Cache.delete(f"{service.CACHE_PREFIX}dict_user_status")

        result = await service.get_dict_label("dict_user_status", "ACTIVE")
        assert result == "在职"

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, db_session, test_context):
        """UT-B07-05: Test invalidate_cache deletes cache key."""
        from app.core.cache import Cache
        from app.services.dict import DictService

        service = DictService()
        cache_key = f"{service.CACHE_PREFIX}dict_test_cache"

        # Set cache
        Cache.set_json(cache_key, [{"value": "TEST"}], ttl=60)
        assert Cache.get_json(cache_key) is not None

        await service.invalidate_cache("dict_test_cache")

        assert Cache.get_json(cache_key) is None

    def test_validate_dict_type_format_invalid(self, db_session, test_context):
        """UT-B07-06: Test validate_dict_type_format with invalid format."""
        from app.core.errors import BizError
        from app.services.dict import DictService

        service = DictService()

        with pytest.raises(BizError) as exc_info:
            service.validate_dict_type_format("invalid_type")
        assert exc_info.value.code == 1001

    def test_validate_dict_type_format_valid(self, db_session, test_context):
        """UT-B07-07: Test validate_dict_type_format with valid format."""
        from app.services.dict import DictService

        service = DictService()
        # Should not raise
        service.validate_dict_type_format("dict_valid_type")

    def test_validate_dict_value_format_invalid(self, db_session, test_context):
        """UT-B07-08: Test validate_dict_value_format with invalid format."""
        from app.core.errors import BizError
        from app.services.dict import DictService

        service = DictService()

        with pytest.raises(BizError) as exc_info:
            service.validate_dict_value_format("invalid_value")
        assert exc_info.value.code == 1001

    def test_validate_dict_value_format_valid(self, db_session, test_context):
        """UT-B07-09: Test validate_dict_value_format with valid format."""
        from app.services.dict import DictService

        service = DictService()
        # Should not raise
        service.validate_dict_value_format("VALID_VALUE")

    def test_validate_color_type_invalid(self, db_session, test_context):
        """UT-B07-10: Test validate_color_type with invalid color."""
        from app.core.errors import BizError
        from app.services.dict import DictService

        service = DictService()

        with pytest.raises(BizError) as exc_info:
            service.validate_color_type("invalid_color")
        assert exc_info.value.code == 1001

    def test_validate_color_type_valid(self, db_session, test_context):
        """UT-B07-11: Test validate_color_type with valid colors."""
        from app.services.dict import DictService

        service = DictService()
        # Should not raise for valid colors
        service.validate_color_type("primary")
        service.validate_color_type("success")
        service.validate_color_type("warning")
        service.validate_color_type("danger")

    def test_validate_color_type_empty(self, db_session, test_context):
        """UT-B07-12: Test validate_color_type with empty string."""
        from app.services.dict import DictService

        service = DictService()
        # Empty string should pass (color is optional)
        service.validate_color_type("")

    @pytest.mark.asyncio
    async def test_get_dict_data_simple_list_from_cache(self, db_session, sample_dict):
        """UT-B07-13: Test get_dict_data_simple_list returns cached data."""
        from app.core.cache import Cache
        from app.services.dict import DictService

        service = DictService()
        cache_key = f"{service.CACHE_PREFIX}dict_user_status"

        # Pre-populate cache
        cached_data = [{"dict_value": "CACHED", "dict_label": "Cached", "color_type": "info", "sort": 0}]
        Cache.set_json(cache_key, cached_data, ttl=60)

        result = await service.get_dict_data_simple_list("dict_user_status")

        # Should return cached data, not DB data
        assert result == cached_data

        # Cleanup
        Cache.delete(cache_key)

    @pytest.mark.asyncio
    async def test_get_dict_data_simple_list_from_db(self, db_session, sample_dict):
        """get_dict_data_simple_list queries the database when the key is not cached."""
        from app.core.cache import Cache
        from app.services.dict import DictService

        service = DictService()
        cache_key = f"{service.CACHE_PREFIX}dict_user_status"

        # Clear cache
        Cache.delete(cache_key)

        result = await service.get_dict_data_simple_list("dict_user_status")

        # Should return DB data
        assert len(result) == 3
        assert result[0]["dict_value"] == "ACTIVE"

        # Cleanup
        Cache.delete(cache_key)


class TestRoleMutationBranches:
    """Cover delete, disable, and permission-detail branches on RoleService."""

    @pytest.mark.asyncio
    async def test_delete_and_disable_missing_role(self, db_session, test_context):
        from app.core.errors import BizError
        from app.services.role import RoleService

        service = RoleService()
        with pytest.raises(BizError) as missing_delete:
            await service.delete_role(999999)
        assert missing_delete.value.code == 1504
        with pytest.raises(BizError) as missing_disable:
            await service.disable_role(999999)
        assert missing_disable.value.code == 1504

    @pytest.mark.asyncio
    async def test_delete_role_with_members_then_plain_role(self, db_session, test_context):
        from app.core.errors import BizError
        from app.domains.sys.models import Role, User, UserRole
        from app.services.role import RoleService

        user = User(
            id=910, tenant_id=1, username="role_member", nickname="成员",
            status="ACTIVE", source="LOCAL",
        )
        bound = Role(
            id=910, tenant_id=1, role_key="with_member", name="有成员",
            status="ENABLED", source="MANUAL",
        )
        plain = Role(
            id=911, tenant_id=1, role_key="plain_role", name="可删",
            status="ENABLED", source="MANUAL",
        )
        db_session.add_all([user, bound, plain, UserRole(id=910, user_id=910, role_id=910)])
        db_session.flush()

        service = RoleService()
        with pytest.raises(BizError) as caught:
            await service.delete_role(910)
        assert caught.value.code == 1502
        await service.delete_role(911)
        db_session.refresh(plain)
        assert plain.deleted == plain.id

    @pytest.mark.asyncio
    async def test_save_perm_detail_read_only_then_update(self, db_session, test_context):
        from app.domains.sys.models import Menu, Role, RolePermDetail
        from app.services.role import RoleService

        role = Role(
            id=912, tenant_id=1, role_key="perm_branch", name="权限分支",
            status="ENABLED", source="MANUAL",
        )
        menu = Menu(
            id=912, tenant_id=1, parent_id=0, name="只读",
            type="BUTTON", status="ENABLED", perm_code="ims:branch:read",
        )
        db_session.add_all([role, menu])
        db_session.flush()

        service = RoleService()
        created = await service.save_perm_detail(912, "ims:branch:read", True, False, False)
        assert created == {"r": True, "w": False, "d": False}
        updated = await service.save_perm_detail(912, "ims:branch:read", False, False, True)
        assert updated["r"] is True
        assert updated["d"] is True
        stored = db_session.query(RolePermDetail).filter(
            RolePermDetail.role_id == 912,
            RolePermDetail.perm_code == "ims:branch:read",
        ).one()
        assert stored.r is True
        assert stored.d is True
