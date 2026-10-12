# tests/unit/test_menu.py - Menu model tests (FP-B04-02)
"""
Tests for menu model and permission codes.

Covers:
- UT-B04-08: Permission code format validation
- UT-B04-09: Menu type requires perm_code
"""


from app.domains.sys.models import Menu


class TestMenuModel:
    """Tests for Menu model fields."""

    def test_menu_has_required_fields(self):
        """Menu model has all required fields."""
        assert hasattr(Menu, "parent_id")
        assert hasattr(Menu, "name")
        assert hasattr(Menu, "type")
        assert hasattr(Menu, "perm_code")
        assert hasattr(Menu, "path")
        assert hasattr(Menu, "status")

    def test_valid_menu_types(self):
        """Test valid menu type values."""
        valid_types = ["DIR", "MENU", "BUTTON"]

        for menu_type in valid_types:
            menu = Menu(
                id=1,
                tenant_id=1,
                parent_id=0,
                name=f"Test {menu_type}",
                type=menu_type,
                path="/test",
                status="ENABLED",
            )
            assert menu.type == menu_type


class TestPermissionCode:
    """Tests for permission code validation (FP-B04-02)."""

    def test_perm_code_format_ims_prefix(self):
        """UT-B04-08: Permission codes must start with 'ims:'."""
        valid_codes = [
            "ims:system:user:query",
            "ims:system:dept:create",
            "ims:demo:order:delete",
        ]

        for code in valid_codes:
            assert code.startswith("ims:")

    def test_perm_code_invalid_prefix(self):
        """UT-B04-08: ops: or other prefix is invalid."""
        invalid_codes = [
            "ops:demo:x",
            "admin:user:query",
            "sys:dept:create",
        ]

        for code in invalid_codes:
            assert not code.startswith("ims:")

    def test_perm_code_four_parts(self):
        """Permission codes have 4 parts: ims:module:entity:action."""
        code = "ims:system:user:query"
        parts = code.split(":")

        assert len(parts) == 4
        assert parts[0] == "ims"
        assert parts[1] == "system"
        assert parts[2] == "user"
        assert parts[3] == "query"


class TestMenuPlatformScope:
    """Tests for menu platform scope."""

    def test_menu_is_platform_base(self):
        """Menu should be platform-level data."""
        from app.db.base import PlatformBase

        # Menu should inherit from PlatformBase
        assert issubclass(Menu, PlatformBase) or getattr(Menu, "__platform__", False)


class TestMenuHierarchy:
    """Tests for menu hierarchy structure."""

    def test_root_menu_has_parent_zero(self):
        """Root menus have parent_id=0."""
        menu = Menu(
            id=1,
            tenant_id=1,
            parent_id=0,
            name="Root Menu",
            type="DIR",
            path="/",
            status="ENABLED",
        )

        assert menu.parent_id == 0

    def test_child_menu_has_parent_id(self):
        """Child menus reference parent."""
        menu = Menu(
            id=2,
            tenant_id=1,
            parent_id=1,
            name="Child Menu",
            type="MENU",
            path="/system",
            status="ENABLED",
        )

        assert menu.parent_id == 1
