# tests/unit/test_system_user_service.py - System User Service Tests (B2-M02)
"""
Tests for user lifecycle management service.

Covers:
- UT-B2-U-05: Get user detail
- UT-B2-U-06: Update user
- UT-B2-U-08: Update user roles
- UT-B2-U-09: Update user status (freeze/unfreeze)
- UT-B2-U-10: Resign user
- UT-B2-U-11: Reset password
- UT-B2-U-12: Unlock user
- UT-B2-U-13: Kick user (force logout)
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.context import RequestContext, ctx


class TestSystemUserService:
    """Tests for SystemUserService methods."""

    def test_service_imports(self):
        """UT-B2-U-01: SystemUserService can be imported."""
        from app.services.system_user import SystemUserService
        assert SystemUserService is not None

    def test_get_user_detail_method_exists(self):
        """UT-B2-U-02: get_user_detail method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'get_user_detail')

    def test_update_user_method_exists(self):
        """UT-B2-U-03: update_user method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'update_user')

    def test_update_user_roles_method_exists(self):
        """UT-B2-U-04: update_user_roles method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'update_user_roles')

    def test_update_user_status_method_exists(self):
        """UT-B2-U-05: update_user_status method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'update_user_status')

    def test_resign_user_method_exists(self):
        """UT-B2-U-06: resign_user method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'resign_user')

    def test_reset_password_method_exists(self):
        """UT-B2-U-07: reset_password method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'reset_password')

    def test_unlock_user_method_exists(self):
        """UT-B2-U-08: unlock_user method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'unlock_user')

    def test_kick_user_method_exists(self):
        """UT-B2-U-09: kick_user method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'kick_user')

    def test_delete_user_method_exists(self):
        """UT-B2-U-10: delete_user method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'delete_user')

    def test_export_users_method_exists(self):
        """UT-B2-U-11: export_users method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, 'export_users')


class TestUserLifecycleWithDb:
    """Tests for user lifecycle operations with database."""

    @pytest.fixture
    def admin_ctx(self):
        """Set up admin context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={
                "ims:system:user:query",
                "ims:system:user:update",
                "ims:system:user:reset-pwd",
                "ims:system:user:unlock",
                "ims:system:user:kick",
            },
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.fixture
    def setup_user(self, db_session, admin_ctx):
        """Create a test user."""
        from app.domains.sys.models import User, Role, UserRole
        from tests.support.rows import add
        
        user = add(db_session, User(
            tenant_id=1,
            username="testuser",
            nickname="Test User",
            password_hash="$2b$10$test",
            status="ACTIVE",
            source="LOCAL",
        ))
        
        r1 = add(db_session, Role(
            tenant_id=1,
            role_key="R1",
            name="Admin",
            status="ENABLED",
            source="MANUAL",
            data_scope="ALL",
        ))
        
        add(db_session, UserRole(
            tenant_id=1,
            user_id=user.id,
            role_id=r1.id,
            source="MANUAL",
        ))
        
        return user

    async def test_get_user_detail_returns_user(self, db_session, setup_user, admin_ctx):
        """UT-B2-U-12: get_user_detail returns user info."""
        from app.services.system_user import SystemUserService
        
        svc = SystemUserService()
        result = await svc.get_user_detail(str(setup_user.id))
        
        assert result is not None
        assert result["username"] == "testuser"

    async def test_get_user_detail_not_found_raises_1504(self, db_session, admin_ctx):
        """UT-B2-U-13: get_user_detail raises 1504 for non-existent user."""
        from app.services.system_user import SystemUserService
        from app.core.errors import BizError
        
        svc = SystemUserService()
        
        with pytest.raises(BizError) as exc:
            await svc.get_user_detail("999999")
        
        assert exc.value.code == 1504

    async def test_update_user_status_freeze(self, db_session, admin_ctx):
        """UT-B2-U-14: update_user_status can freeze user."""
        from app.domains.sys.models import User
        from app.services.system_user import SystemUserService
        from tests.support.rows import add
        
        other_user = add(db_session, User(
            tenant_id=1,
            username="otheruser",
            nickname="Other User",
            password_hash="$2b$10$test",
            status="ACTIVE",
            source="LOCAL",
        ))
        
        admin_ctx.user_id = 99999
        ctx.set(admin_ctx)
        
        svc = SystemUserService()
        await svc.update_user_status(str(other_user.id), "FROZEN")
        
        db_session.expire(other_user)
        assert other_user.status == "FROZEN"

    async def test_update_user_status_cannot_freeze_self(self, db_session, setup_user, admin_ctx):
        """UT-B2-U-15: Cannot freeze the current user."""
        from app.services.system_user import SystemUserService
        from app.core.errors import BizError
        
        admin_ctx.user_id = setup_user.id
        ctx.set(admin_ctx)
        
        svc = SystemUserService()
        
        with pytest.raises(BizError) as exc:
            await svc.update_user_status(str(setup_user.id), "FROZEN")
        
        assert exc.value.code == 1001

    async def test_resign_user_sets_status(self, db_session, admin_ctx):
        """UT-B2-U-16: resign_user sets status to RESIGNED."""
        from app.domains.sys.models import User
        from app.services.system_user import SystemUserService
        from tests.support.rows import add
        
        other_user = add(db_session, User(
            tenant_id=1,
            username="resignuser",
            nickname="Resign User",
            password_hash="$2b$10$test",
            status="ACTIVE",
            source="LOCAL",
        ))
        
        admin_ctx.user_id = 99999
        ctx.set(admin_ctx)
        
        svc = SystemUserService()
        await svc.resign_user(str(other_user.id))
        
        db_session.expire(other_user)
        assert other_user.status == "RESIGNED"

    async def test_resign_user_already_resigned_raises_1001(self, db_session, setup_user, admin_ctx):
        """UT-B2-U-17: resign_user raises 1001 for already resigned user."""
        from app.services.system_user import SystemUserService
        from app.core.errors import BizError
        
        setup_user.status = "RESIGNED"
        db_session.flush()
        
        svc = SystemUserService()
        
        with pytest.raises(BizError) as exc:
            await svc.resign_user(str(setup_user.id))
        
        assert exc.value.code == 1001

    async def test_reset_password_returns_temp_password(self, db_session, admin_ctx):
        """UT-B2-U-18: reset_password returns temporary password."""
        from app.domains.sys.models import User
        from app.services.system_user import SystemUserService
        from tests.support.rows import add
        
        target_user = add(db_session, User(
            tenant_id=1,
            username="resetpwduser",
            nickname="Reset User",
            password_hash="$2b$10$test",
            status="ACTIVE",
            source="LOCAL",
        ))
        
        svc = SystemUserService()
        result = await svc.reset_password(str(target_user.id))
        
        assert "new_password" in result
        assert len(result["new_password"]) >= 8

    async def test_reset_password_sets_pwd_reset_required(self, db_session, admin_ctx):
        """UT-B2-U-19: reset_password sets pwd_reset_required flag."""
        from app.domains.sys.models import User
        from app.services.system_user import SystemUserService
        from tests.support.rows import add
        
        target_user = add(db_session, User(
            tenant_id=1,
            username="resetpwduser2",
            nickname="Reset User 2",
            password_hash="$2b$10$test",
            status="ACTIVE",
            source="LOCAL",
        ))
        
        svc = SystemUserService()
        await svc.reset_password(str(target_user.id))
        
        db_session.expire(target_user)
        assert target_user.pwd_reset_required is True

    async def test_reset_password_not_found_raises_1504(self, db_session, admin_ctx):
        """UT-B2-U-20: reset_password raises 1504 for non-existent user."""
        from app.services.system_user import SystemUserService
        from app.core.errors import BizError
        
        svc = SystemUserService()
        
        with pytest.raises(BizError) as exc:
            await svc.reset_password("999999")
        
        assert exc.value.code == 1504


class TestDropSessionsAndPermVersion:
    """Tests for _drop_sessions and permission version."""

    def test_drop_sessions_helper_exists(self):
        """UT-B2-U-21: _drop_sessions helper method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, '_drop_sessions')

    def test_bump_perm_version_helper_exists(self):
        """UT-B2-U-22: _bump_perm_version helper method exists."""
        from app.services.system_user import SystemUserService
        svc = SystemUserService()
        assert hasattr(svc, '_bump_perm_version')


class TestR1MemberHelpers:
    """Tests for R1 member helper functions."""

    def test_count_r1_members_function_exists(self):
        """UT-B2-U-23: _count_r1_members function exists."""
        from app.services.system_user import _count_r1_members
        assert _count_r1_members is not None

    def test_is_r1_member_function_exists(self):
        """UT-B2-U-24: _is_r1_member function exists."""
        from app.services.system_user import _is_r1_member
        assert _is_r1_member is not None

    def test_count_r1_members_returns_zero_for_empty(self, db_session):
        """UT-B2-U-25: _count_r1_members returns 0 for empty tenant."""
        from app.services.system_user import _count_r1_members
        
        count = _count_r1_members(db_session, tenant_id=9999)
        assert count == 0
