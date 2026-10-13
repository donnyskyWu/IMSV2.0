# tests/unit/test_system_menu_service.py - System Menu Service Tests (B2-M02)
"""
Tests for menu management service.

Covers:
- UT-B2-M-01: Get menu tree
- UT-B2-M-02: Create menu
- UT-B2-M-03: Update menu
- UT-B2-M-04: Delete menu
"""

import pytest

from app.core.context import RequestContext, ctx


class TestSystemMenuService:
    """Tests for SystemMenuService methods."""

    def test_service_imports(self):
        """UT-B2-M-01: SystemMenuService can be imported."""
        from app.services.system_menu import SystemMenuService
        assert SystemMenuService is not None

    def test_get_menu_tree_method_exists(self):
        """UT-B2-M-02: get_menu_tree method exists."""
        from app.services.system_menu import SystemMenuService
        svc = SystemMenuService()
        assert hasattr(svc, 'get_menu_tree')

    def test_create_menu_method_exists(self):
        """UT-B2-M-03: create_menu method exists."""
        from app.services.system_menu import SystemMenuService
        svc = SystemMenuService()
        assert hasattr(svc, 'create_menu')

    def test_update_menu_method_exists(self):
        """UT-B2-M-04: update_menu method exists."""
        from app.services.system_menu import SystemMenuService
        svc = SystemMenuService()
        assert hasattr(svc, 'update_menu')

    def test_delete_menu_method_exists(self):
        """UT-B2-M-05: delete_menu method exists."""
        from app.services.system_menu import SystemMenuService
        svc = SystemMenuService()
        assert hasattr(svc, 'delete_menu')


class TestMenuServiceWithDb:
    """Tests for menu service with database."""

    @pytest.fixture
    def platform_ctx(self):
        """Set up platform admin context (tenant_id=1)."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={
                "ims:system:menu:query",
                "ims:system:menu:create",
                "ims:system:menu:update",
                "ims:system:menu:delete",
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
                "ims:system:menu:query",
            },
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    async def test_get_menu_tree_platform_only(self, db_session, non_platform_ctx):
        """UT-B2-M-06: get_menu_tree only accessible by platform tenant."""
        from app.services.system_menu import SystemMenuService
        from app.core.errors import BizError
        
        svc = SystemMenuService()
        
        with pytest.raises(BizError) as exc:
            await svc.get_menu_tree()
        
        assert exc.value.code == 1008

    async def test_get_menu_tree_returns_tree(self, db_session, platform_ctx):
        """UT-B2-M-07: get_menu_tree returns menu tree."""
        from app.services.system_menu import SystemMenuService
        
        svc = SystemMenuService()
        result = await svc.get_menu_tree()
        
        assert result is not None
        assert isinstance(result, list)

    async def test_delete_menu_with_children_raises_1502(self, db_session, platform_ctx):
        """UT-B2-M-08: delete_menu raises 1502 for menu with children."""
        from app.domains.sys.models import Menu
        from app.services.system_menu import SystemMenuService
        from app.core.errors import BizError
        from tests.support.rows import add
        
        parent = add(db_session, Menu(
            tenant_id=1,
            parent_id=0,
            type="DIR",
            name="Parent Menu",
            status="ENABLED",
        ))
        
        add(db_session, Menu(
            tenant_id=1,
            parent_id=parent.id,
            type="MENU",
            name="Child Menu",
            perm_code="ims:test:child",
            status="ENABLED",
        ))
        
        svc = SystemMenuService()
        
        with pytest.raises(BizError) as exc:
            await svc.delete_menu(str(parent.id))
        
        assert exc.value.code == 1502


class TestMenuValidation:
    """Tests for menu validation rules."""

    def test_perm_code_regex_pattern(self):
        """UT-B2-M-09: Permission code must match pattern ims:xxx:xxx."""
        import re
        pattern = re.compile(r'^ims(:[a-z][a-z0-9-]*){2,3}$')
        
        valid_codes = [
            "ims:system:user",
            "ims:system:user:query",
            "ims:system:role-admin",
        ]
        
        invalid_codes = [
            "ops:system:user",
            "system:user",
            "ims:user",
            "ims:System:user",
        ]
        
        for code in valid_codes:
            assert pattern.match(code), f"Should match: {code}"
        
        for code in invalid_codes:
            assert not pattern.match(code), f"Should not match: {code}"
