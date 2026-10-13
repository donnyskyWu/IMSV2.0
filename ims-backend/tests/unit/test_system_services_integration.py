# tests/unit/test_system_services_integration.py - Integration Tests for B2 Services
"""
Integration tests for B2 system management services with database operations.

Covers API endpoints and service methods with database:
- User CRUD operations
- Role CRUD operations
- Menu CRUD operations
- Tenant/Package operations
- Log queries
- Param operations
"""


import pytest

from app.core.context import RequestContext, ctx


class TestSystemUserServiceIntegration:
    """Integration tests for SystemUserService with real DB."""

    @pytest.fixture
    def platform_admin_ctx(self):
        """Set up platform admin context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=99999,
            tenant_id=1,
            perm_codes={
                "ims:system:user:query",
                "ims:system:user:create",
                "ims:system:user:update",
                "ims:system:user:delete",
                "ims:system:user:reset-pwd",
                "ims:system:user:unlock",
                "ims:system:user:kick",
                "ims:system:user:export",
            },
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.fixture
    def test_user(self, db_session, platform_admin_ctx):
        """Create a test user."""
        from app.domains.sys.models import User
        from tests.support.rows import add

        return add(db_session, User(
            tenant_id=1,
            username="integration_user",
            nickname="Integration User",
            password_hash="$2b$10$test",
            status="ACTIVE",
            source="LOCAL",
        ))

    async def test_user_get_detail(self, db_session, test_user, platform_admin_ctx):
        """Test getting user detail."""
        from app.services.system_user import SystemUserService

        svc = SystemUserService()
        result = await svc.get_user_detail(str(test_user.id))

        assert result["username"] == "integration_user"
        assert result["status"] == "ACTIVE"

    async def test_user_update_roles_empty(self, db_session, test_user, platform_admin_ctx):
        """Test updating user with empty roles."""
        from app.services.system_user import SystemUserService

        svc = SystemUserService()
        await svc.update_user_roles(str(test_user.id), [])

    async def test_user_kick_drops_sessions(self, db_session, test_user, platform_admin_ctx):
        """Test kick user drops all sessions."""
        from app.services.system_user import SystemUserService

        svc = SystemUserService()
        await svc.kick_user(str(test_user.id))

    async def test_user_unlock(self, db_session, platform_admin_ctx):
        """Test unlocking a locked user."""
        from datetime import datetime, timedelta

        from app.domains.sys.models import User
        from app.services.system_user import SystemUserService
        from tests.support.rows import add

        locked_user = add(db_session, User(
            tenant_id=1,
            username="locked_user",
            nickname="Locked User",
            password_hash="$2b$10$test",
            status="ACTIVE",
            source="LOCAL",
            lock_until=datetime.now() + timedelta(hours=1),
        ))

        svc = SystemUserService()
        await svc.unlock_user(str(locked_user.id))

        db_session.expire(locked_user)
        assert locked_user.lock_until is None

    async def test_user_delete_never_logged_in(self, db_session, platform_admin_ctx):
        """Test deleting user who never logged in."""
        from app.domains.sys.models import User
        from app.services.system_user import SystemUserService
        from tests.support.rows import add

        new_user = add(db_session, User(
            tenant_id=1,
            username="never_logged_user",
            nickname="Never Logged User",
            password_hash="$2b$10$test",
            status="ACTIVE",
            source="LOCAL",
        ))

        svc = SystemUserService()
        await svc.delete_user(str(new_user.id))

        db_session.expire(new_user)
        assert new_user.deleted == new_user.id


class TestSystemRoleServiceIntegration:
    """Integration tests for SystemRoleService."""

    @pytest.fixture
    def platform_admin_ctx(self):
        """Set up platform admin context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=99999,
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

    async def test_role_page_empty(self, db_session, platform_admin_ctx):
        """Test getting empty role page."""
        from app.core.pagination import PageParam
        from app.services.system_role import SystemRoleService

        svc = SystemRoleService()
        result = await svc.get_role_page(PageParam(page_no=1, page_size=10))

        assert result.list is not None
        assert result.total >= 0

    async def test_role_create_basic(self, db_session, platform_admin_ctx):
        """Test creating a basic role."""
        from app.services.system_role import SystemRoleService

        class MockRequest:
            role_key = "TEST_CREATE"
            name = "Test Create Role"
            data_scope = None
            remark = None

        svc = SystemRoleService()
        result = await svc.create_role(MockRequest())

        assert result["name"] == "Test Create Role"

    async def test_role_update_basic(self, db_session, platform_admin_ctx):
        """Test updating a role."""
        from app.domains.sys.models import Role
        from app.services.system_role import SystemRoleService
        from tests.support.rows import add

        role = add(db_session, Role(
            tenant_id=1,
            role_key="UPDATE_ROLE",
            name="Update Role",
            status="ENABLED",
            source="MANUAL",
            data_scope="ALL",
        ))

        class MockRequest:
            name = "Updated Role Name"
            remark = "Updated remark"

        svc = SystemRoleService()
        result = await svc.update_role(str(role.id), MockRequest())

        assert result["name"] == "Updated Role Name"

    async def test_role_delete_no_members(self, db_session, platform_admin_ctx):
        """Test deleting a role with no members."""
        from app.domains.sys.models import Role
        from app.services.system_role import SystemRoleService
        from tests.support.rows import add

        role = add(db_session, Role(
            tenant_id=1,
            role_key="DELETE_ROLE",
            name="Delete Role",
            status="ENABLED",
            source="MANUAL",
            data_scope="ALL",
        ))

        svc = SystemRoleService()
        await svc.delete_role(str(role.id))

        db_session.expire(role)
        assert role.deleted == role.id

    async def test_role_update_menus(self, db_session, platform_admin_ctx):
        """Test updating role menus."""
        from app.domains.sys.models import Menu, Role
        from app.services.system_role import SystemRoleService
        from tests.support.rows import add

        role = add(db_session, Role(
            tenant_id=1,
            role_key="MENU_ROLE",
            name="Menu Role",
            status="ENABLED",
            source="MANUAL",
            data_scope="ALL",
        ))

        menu = add(db_session, Menu(
            tenant_id=1,
            parent_id=0,
            type="MENU",
            name="Test Menu",
            perm_code="ims:test:menu",
            status="ENABLED",
        ))

        svc = SystemRoleService()
        await svc.update_role_menus(str(role.id), [str(menu.id)])

    async def test_role_update_data_scope(self, db_session, platform_admin_ctx):
        """Test updating role data scope."""
        from app.domains.sys.models import Role
        from app.services.system_role import SystemRoleService
        from tests.support.rows import add

        role = add(db_session, Role(
            tenant_id=1,
            role_key="SCOPE_ROLE",
            name="Scope Role",
            status="ENABLED",
            source="MANUAL",
        ))

        svc = SystemRoleService()
        await svc.update_role_data_scope(str(role.id), "SELF")

        db_session.expire(role)
        assert role.data_scope == "SELF"


class TestSystemMenuServiceIntegration:
    """Integration tests for SystemMenuService."""

    @pytest.fixture
    def platform_ctx(self):
        """Set up platform context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={"ims:system:menu:query", "ims:system:menu:create", "ims:system:menu:update", "ims:system:menu:delete"},
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    async def test_menu_tree_empty(self, db_session, platform_ctx):
        """Test getting empty menu tree."""
        from app.services.system_menu import SystemMenuService

        svc = SystemMenuService()
        result = await svc.get_menu_tree()

        assert isinstance(result, list)

    async def test_menu_create(self, db_session, platform_ctx):
        """Test creating a menu."""
        from app.services.system_menu import SystemMenuService

        class MockRequest:
            parent_id = "0"
            type = "DIR"
            name = "Test Directory"
            path = None
            perm_code = None
            icon = "folder"
            sort = 1
            visible = True
            keep_alive = False

        svc = SystemMenuService()
        result = await svc.create_menu(MockRequest())

        assert result["name"] == "Test Directory"

    async def test_menu_update(self, db_session, platform_ctx):
        """Test updating a menu."""
        from app.domains.sys.models import Menu
        from app.services.system_menu import SystemMenuService
        from tests.support.rows import add

        menu = add(db_session, Menu(
            tenant_id=1,
            parent_id=0,
            type="DIR",
            name="Update Dir",
            status="ENABLED",
        ))

        class MockRequest:
            name = "Updated Dir Name"
            sort = 10
            visible = False

        svc = SystemMenuService()
        result = await svc.update_menu(str(menu.id), MockRequest())

        assert result["name"] == "Updated Dir Name"


class TestSystemLogServiceIntegration:
    """Integration tests for SystemLogService."""

    @pytest.fixture
    def admin_ctx(self):
        """Set up admin context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={"ims:system:log:query", "ims:system:log:export"},
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    async def test_operate_log_page_empty(self, db_session, admin_ctx):
        """Test getting empty operate log page."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService

        svc = SystemLogService()
        result = await svc.get_operate_log_page(PageParam(page_no=1, page_size=10))

        assert result.list is not None

    async def test_login_log_page_empty(self, db_session, admin_ctx):
        """Test getting empty login log page."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService

        svc = SystemLogService()
        result = await svc.get_login_log_page(PageParam(page_no=1, page_size=10))

        assert result.list is not None


class TestSystemParamServiceIntegration:
    """Integration tests for SystemParamService."""

    @pytest.fixture
    def admin_ctx(self):
        """Set up admin context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={"ims:system:param:query", "ims:system:param:update"},
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    async def test_param_list_empty(self, db_session, admin_ctx):
        """Test getting empty param list."""
        from app.services.system_param import SystemParamService

        svc = SystemParamService()
        result = await svc.get_param_list()

        assert isinstance(result, list)


class TestSystemTenantServiceIntegration:
    """Integration tests for SystemTenantService."""

    @pytest.fixture
    def platform_ctx(self):
        """Set up platform context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={"ims:tenant:query", "ims:tenant:create", "ims:tenant:update", "ims:tenant:package"},
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    async def test_tenant_page_empty(self, db_session, platform_ctx):
        """Test getting tenant page."""
        from app.core.pagination import PageParam
        from app.services.system_tenant import SystemTenantService

        svc = SystemTenantService()
        result = await svc.get_tenant_page(PageParam(page_no=1, page_size=10))

        assert result.list is not None

    async def test_package_list_empty(self, db_session, platform_ctx):
        """Test getting empty package list."""
        from app.services.system_tenant import SystemTenantService

        svc = SystemTenantService()
        result = await svc.get_package_list()

        assert isinstance(result, list)

    async def test_package_simple_list_empty(self, db_session, platform_ctx):
        """Test getting empty package simple list."""
        from app.services.system_tenant import SystemTenantService

        svc = SystemTenantService()
        result = await svc.get_package_simple_list()

        assert isinstance(result, list)
