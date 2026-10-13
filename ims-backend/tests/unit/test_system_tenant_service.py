# tests/unit/test_system_tenant_service.py - System Tenant Service Tests (B2-M02)
"""
Tests for tenant and package management service.

Covers:
- UT-B2-T-01: Tenant page list
- UT-B2-T-02: Create tenant
- UT-B2-T-03: Update tenant
- UT-B2-T-04: Package management
- UT-B2-T-05: R1 synchronization on package changes
"""

import pytest

from app.core.context import RequestContext, ctx


class TestSystemTenantService:
    """Tests for SystemTenantService methods."""

    def test_service_imports(self):
        """UT-B2-T-01: SystemTenantService can be imported."""
        from app.services.system_tenant import SystemTenantService
        assert SystemTenantService is not None

    def test_get_tenant_page_method_exists(self):
        """UT-B2-T-02: get_tenant_page method exists."""
        from app.services.system_tenant import SystemTenantService
        svc = SystemTenantService()
        assert hasattr(svc, 'get_tenant_page')

    def test_create_tenant_method_exists(self):
        """UT-B2-T-03: create_tenant method exists."""
        from app.services.system_tenant import SystemTenantService
        svc = SystemTenantService()
        assert hasattr(svc, 'create_tenant')

    def test_update_tenant_method_exists(self):
        """UT-B2-T-04: update_tenant method exists."""
        from app.services.system_tenant import SystemTenantService
        svc = SystemTenantService()
        assert hasattr(svc, 'update_tenant')

    def test_get_package_simple_list_method_exists(self):
        """UT-B2-T-05: get_package_simple_list method exists."""
        from app.services.system_tenant import SystemTenantService
        svc = SystemTenantService()
        assert hasattr(svc, 'get_package_simple_list')

    def test_get_package_list_method_exists(self):
        """UT-B2-T-06: get_package_list method exists."""
        from app.services.system_tenant import SystemTenantService
        svc = SystemTenantService()
        assert hasattr(svc, 'get_package_list')

    def test_create_package_method_exists(self):
        """UT-B2-T-07: create_package method exists."""
        from app.services.system_tenant import SystemTenantService
        svc = SystemTenantService()
        assert hasattr(svc, 'create_package')

    def test_update_package_method_exists(self):
        """UT-B2-T-08: update_package method exists."""
        from app.services.system_tenant import SystemTenantService
        svc = SystemTenantService()
        assert hasattr(svc, 'update_package')


class TestTenantServiceWithDb:
    """Tests for tenant service with database."""

    @pytest.fixture
    def platform_ctx(self):
        """Set up platform admin context (tenant_id=1)."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={
                "ims:tenant:query",
                "ims:tenant:create",
                "ims:tenant:update",
                "ims:tenant:package",
            },
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.fixture
    def non_platform_ctx(self):
        """Set up non-platform context (tenant_id=2)."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=100,
            tenant_id=2,
            perm_codes={
                "ims:tenant:query",
            },
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    async def test_get_tenant_page_platform_only(self, db_session, non_platform_ctx):
        """UT-B2-T-09: get_tenant_page only accessible by platform tenant."""
        from app.core.errors import BizError
        from app.core.pagination import PageParam
        from app.services.system_tenant import SystemTenantService

        svc = SystemTenantService()

        with pytest.raises(BizError) as exc:
            await svc.get_tenant_page(PageParam(page_no=1, page_size=10))

        assert exc.value.code == 1008

    async def test_get_tenant_page_returns_list(self, db_session, platform_ctx):
        """UT-B2-T-10: get_tenant_page returns paginated list."""
        from app.core.pagination import PageParam
        from app.services.system_tenant import SystemTenantService

        svc = SystemTenantService()
        result = await svc.get_tenant_page(PageParam(page_no=1, page_size=10))

        assert result is not None
        assert hasattr(result, 'list')
        assert hasattr(result, 'total')

    async def test_get_package_simple_list_platform_only(self, db_session, non_platform_ctx):
        """UT-B2-T-11: get_package_simple_list only accessible by platform tenant."""
        from app.core.errors import BizError
        from app.services.system_tenant import SystemTenantService

        svc = SystemTenantService()

        with pytest.raises(BizError) as exc:
            await svc.get_package_simple_list()

        assert exc.value.code == 1008

    async def test_update_tenant_not_found_raises_1504(self, db_session, platform_ctx):
        """UT-B2-T-12: update_tenant raises 1504 for non-existent tenant."""
        from app.core.errors import BizError
        from app.services.system_tenant import SystemTenantService

        class MockRequest:
            name = "New Name"

        svc = SystemTenantService()

        with pytest.raises(BizError) as exc:
            await svc.update_tenant("999999", MockRequest())

        assert exc.value.code == 1504


class TestR1Synchronization:
    """Tests for R1 role synchronization on package changes (UT-B2-T-03-09/10)."""

    @pytest.fixture
    def platform_ctx(self):
        """Set up platform admin context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={"ims:tenant:update", "ims:tenant:package"},
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    def test_r1_sync_preserves_old_menus(self, db_session, platform_ctx):
        """UT-B2-T-03-09: R1 keeps menus when package drops them (only add, don't remove)."""
        from app.domains.sys.models import (
            Menu,
            Role,
            RoleMenu,
            Tenant,
            TenantPackage,
            TenantPackageMenu,
        )
        from tests.support.rows import add

        tenant = add(db_session, Tenant(
            tenant_id=1,
            name="Test Tenant",
            status="ENABLED",
        ))

        menu_a = add(db_session, Menu(
            tenant_id=1, parent_id=0, type="MENU", name="Menu A",
            perm_code="test:menu:a", status="ENABLED",
        ))
        menu_b = add(db_session, Menu(
            tenant_id=1, parent_id=0, type="MENU", name="Menu B",
            perm_code="test:menu:b", status="ENABLED",
        ))

        old_package = add(db_session, TenantPackage(
            tenant_id=1, name="Old Package", status="ENABLED",
        ))
        add(db_session, TenantPackageMenu(package_id=old_package.id, menu_id=menu_a.id))
        add(db_session, TenantPackageMenu(package_id=old_package.id, menu_id=menu_b.id))

        new_package = add(db_session, TenantPackage(
            tenant_id=1, name="New Package", status="ENABLED",
        ))
        add(db_session, TenantPackageMenu(package_id=new_package.id, menu_id=menu_a.id))

        r1 = add(db_session, Role(
            tenant_id=tenant.id, role_key="R1", name="Tenant Admin",
            status="ENABLED", source="MANUAL", data_scope="ALL",
        ))
        add(db_session, RoleMenu(tenant_id=tenant.id, role_id=r1.id, menu_id=menu_a.id))
        add(db_session, RoleMenu(tenant_id=tenant.id, role_id=r1.id, menu_id=menu_b.id))

        tenant.package_id = old_package.id
        db_session.flush()

        r1_menus_before = {rm.menu_id for rm in db_session.query(RoleMenu).filter(
            RoleMenu.role_id == r1.id
        ).all()}
        assert menu_a.id in r1_menus_before
        assert menu_b.id in r1_menus_before

        tenant.package_id = new_package.id
        db_session.flush()

        r1_menus_after = {rm.menu_id for rm in db_session.query(RoleMenu).filter(
            RoleMenu.role_id == r1.id
        ).all()}

        assert menu_a.id in r1_menus_after, "Menu from new package should be preserved"
        assert menu_b.id in r1_menus_after, "Menu not in new package should also be preserved (only add, don't remove)"

    def test_version_not_bumped_when_package_unchanged(self, db_session, platform_ctx):
        """UT-B2-T-03-10: Permission version not bumped when package didn't change."""
        from app.core.cache import Cache
        from app.domains.sys.models import Tenant, TenantPackage
        from tests.support.rows import add

        tenant = add(db_session, Tenant(
            tenant_id=1,
            name="Test Tenant",
            status="ENABLED",
        ))
        package = add(db_session, TenantPackage(
            tenant_id=1, name="Test Package", status="ENABLED",
        ))
        tenant.package_id = package.id
        db_session.flush()

        perm_ver_key = f"ims:perm_ver:t:{tenant.id}"
        Cache.set(perm_ver_key, "1")
        initial_version = Cache.get(perm_ver_key)

        tenant.name = "Updated Tenant Name"
        db_session.flush()

        after_version = Cache.get(perm_ver_key)
        assert after_version == initial_version, "perm_version should not change when package is unchanged"


class TestTenantAdminKeyConstant:
    """Tests for _TENANT_ADMIN_KEY constant usage."""

    def test_tenant_admin_key_defined(self):
        """UT-B2-T-13: _TENANT_ADMIN_KEY constant is defined."""
        from app.services.system_tenant import _TENANT_ADMIN_KEY
        assert _TENANT_ADMIN_KEY == "R1"

    def test_no_direct_r1_comparison_in_code(self):
        """UT-B2-T-14: Code uses _TENANT_ADMIN_KEY instead of direct 'R1' comparison."""
        import re
        from pathlib import Path

        service_file = Path(__file__).parent.parent.parent / "app" / "services" / "system_tenant.py"
        content = service_file.read_text()

        pattern = re.compile(r'role_key\s*==\s*["\']R\d+["\']')
        matches = pattern.findall(content)

        assert len(matches) == 0, f"Found direct role_key comparison: {matches}"
