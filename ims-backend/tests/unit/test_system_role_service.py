# tests/unit/test_system_role_service.py - System Role Service Tests (B2-M02)
"""
Tests for role management service.

Covers:
- UT-B2-R-01: Role page list
- UT-B2-R-02: Create role
- UT-B2-R-03: Get role detail
- UT-B2-R-04: Update role
- UT-B2-R-05: Update role status
- UT-B2-R-06: Update role menus
- UT-B2-R-07: Update role perm detail
- UT-B2-R-08: Update role data scope
- UT-B2-R-09: Role members management
- UT-B2-R-10: Delete role
"""

import pytest

from app.core.context import RequestContext, ctx


class TestSystemRoleService:
    """Tests for SystemRoleService methods."""

    def test_service_imports(self):
        """UT-B2-R-01: SystemRoleService can be imported."""
        from app.services.system_role import SystemRoleService
        assert SystemRoleService is not None

    def test_get_role_page_method_exists(self):
        """UT-B2-R-02: get_role_page method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'get_role_page')

    def test_create_role_method_exists(self):
        """UT-B2-R-03: create_role method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'create_role')

    def test_get_role_detail_method_exists(self):
        """UT-B2-R-04: get_role_detail method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'get_role_detail')

    def test_update_role_method_exists(self):
        """UT-B2-R-05: update_role method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'update_role')

    def test_update_role_status_method_exists(self):
        """UT-B2-R-06: update_role_status method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'update_role_status')

    def test_update_role_menus_method_exists(self):
        """UT-B2-R-07: update_role_menus method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'update_role_menus')

    def test_update_role_perm_detail_method_exists(self):
        """UT-B2-R-08: update_role_perm_detail method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'update_role_perm_detail')

    def test_update_role_data_scope_method_exists(self):
        """UT-B2-R-09: update_role_data_scope method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'update_role_data_scope')

    def test_get_role_members_method_exists(self):
        """UT-B2-R-10: get_role_members method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'get_role_members')

    def test_add_role_members_method_exists(self):
        """UT-B2-R-11: add_role_members method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'add_role_members')

    def test_remove_role_members_method_exists(self):
        """UT-B2-R-12: remove_role_members method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'remove_role_members')

    def test_delete_role_method_exists(self):
        """UT-B2-R-13: delete_role method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'delete_role')

    def test_export_roles_method_exists(self):
        """UT-B2-R-14: export_roles method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, 'export_roles')


class TestRoleServiceWithDb:
    """Tests for role service with database."""

    @pytest.fixture
    def admin_ctx(self):
        """Set up admin context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={
                "ims:system:role:query",
                "ims:system:role:create",
                "ims:system:role:update",
                "ims:system:role:delete",
            },
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.fixture
    def setup_role(self, db_session, admin_ctx):
        """Create a test role."""
        from app.domains.sys.models import Role
        from tests.support.rows import add
        
        role = add(db_session, Role(
            tenant_id=1,
            role_key="TEST_ROLE",
            name="Test Role",
            status="ENABLED",
            source="MANUAL",
            data_scope="ALL",
        ))
        
        return role

    async def test_get_role_page_returns_list(self, db_session, setup_role, admin_ctx):
        """UT-B2-R-15: get_role_page returns paginated list."""
        from app.services.system_role import SystemRoleService
        from app.core.pagination import PageParam
        
        svc = SystemRoleService()
        result = await svc.get_role_page(PageParam(page_no=1, page_size=10))
        
        assert result is not None
        assert hasattr(result, 'list')
        assert hasattr(result, 'total')

    async def test_get_role_detail_returns_role(self, db_session, setup_role, admin_ctx):
        """UT-B2-R-16: get_role_detail returns role info."""
        from app.services.system_role import SystemRoleService
        
        svc = SystemRoleService()
        result = await svc.get_role_detail(str(setup_role.id))
        
        assert result is not None
        assert result["name"] == "Test Role"

    async def test_get_role_detail_not_found_raises_1504(self, db_session, admin_ctx):
        """UT-B2-R-17: get_role_detail raises 1504 for non-existent role."""
        from app.services.system_role import SystemRoleService
        from app.core.errors import BizError
        
        svc = SystemRoleService()
        
        with pytest.raises(BizError) as exc:
            await svc.get_role_detail("999999")
        
        assert exc.value.code == 1504

    async def test_update_role_status_can_disable(self, db_session, setup_role, admin_ctx):
        """UT-B2-R-18: update_role_status can disable role."""
        from app.services.system_role import SystemRoleService
        
        svc = SystemRoleService()
        await svc.update_role_status(str(setup_role.id), "DISABLED")
        
        db_session.expire(setup_role)
        assert setup_role.status == "DISABLED"

    async def test_cannot_disable_r1_role(self, db_session, admin_ctx):
        """UT-B2-R-19: Cannot disable R1 (tenant admin) role."""
        from app.domains.sys.models import Role
        from app.services.system_role import SystemRoleService
        from app.core.errors import BizError
        from tests.support.rows import add
        
        r1 = add(db_session, Role(
            tenant_id=1,
            role_key="R1",
            name="Tenant Admin",
            status="ENABLED",
            source="MANUAL",
            data_scope="ALL",
        ))
        
        svc = SystemRoleService()
        
        with pytest.raises(BizError) as exc:
            await svc.update_role_status(str(r1.id), "DISABLED")
        
        assert exc.value.code == 1001

    async def test_delete_role_with_members_raises_1502(self, db_session, setup_role, admin_ctx):
        """UT-B2-R-20: delete_role raises 1502 for role with members."""
        from app.domains.sys.models import User, UserRole
        from app.services.system_role import SystemRoleService
        from app.core.errors import BizError
        from tests.support.rows import add
        
        user = add(db_session, User(
            tenant_id=1,
            username="member",
            nickname="Member",
            status="ACTIVE",
            source="LOCAL",
        ))
        
        add(db_session, UserRole(
            tenant_id=1,
            user_id=user.id,
            role_id=setup_role.id,
            source="MANUAL",
        ))
        
        svc = SystemRoleService()
        
        with pytest.raises(BizError) as exc:
            await svc.delete_role(str(setup_role.id))
        
        assert exc.value.code == 1502


class TestBumpPermVersion:
    """Tests for permission version bump helper."""

    def test_bump_perm_version_method_exists(self):
        """UT-B2-R-21: _bump_perm_version_for_role_members method exists."""
        from app.services.system_role import SystemRoleService
        svc = SystemRoleService()
        assert hasattr(svc, '_bump_perm_version_for_role_members')
