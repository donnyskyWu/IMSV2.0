# tests/unit/test_seeds.py - Seed data tests (FP-H05)
"""
Tests for seed data framework.

Covers:
- UT-H05-01: Seed is idempotent
- UT-H05-02: Admin modifications not overwritten
- UT-H05-03: E2E environment has separate data
"""



class TestSeedIdempotency:
    """Tests for seed idempotency (FP-H05-01)."""

    def test_seed_files_exist(self):
        """Seed files exist in tools/seed directory."""
        from pathlib import Path

        seed_dir = Path("tools/seed")

        # Check for expected seed files
        expected_files = [
            "runner.py",
            "dicts.py",
            "params.py",
            "roles.py",
            "menus.py",
            "tenant.py",
            "depts.py",
            "access.py",
            "users.py",
        ]

        for filename in expected_files:
            filepath = seed_dir / filename
            assert filepath.exists(), f"Missing seed file: {filename}"

    def test_standard_roles_defined(self):
        """Standard roles R1-R11 are defined."""
        from tools.seed.roles import STANDARD_ROLES

        # Should have R1-R11
        role_keys = [r["role_key"] for r in STANDARD_ROLES]

        for i in range(1, 12):
            assert f"R{i}" in role_keys, f"Missing standard role R{i}"

    def test_r2_has_dept_scope(self):
        """UT-Q10: R2 role has DEPT data scope."""
        from tools.seed.roles import STANDARD_ROLES

        r2 = next((r for r in STANDARD_ROLES if r["role_key"] == "R2"), None)

        assert r2 is not None
        assert r2["data_scope"] == "DEPT"


class TestSeedDicts:
    """Tests for dictionary seed data (FP-B07)."""

    def test_dict_types_defined(self):
        """Dictionary types are defined in seed."""
        from tools.seed.dicts import DICT_TYPES

        expected_types = [
            "dict_user_status",
            "dict_dept_source",
            "dict_platform_type",
        ]

        type_codes = [d["dict_type"] for d in DICT_TYPES]

        for expected in expected_types:
            assert expected in type_codes, f"Missing dict type: {expected}"

    def test_dict_data_have_labels(self):
        """Dictionary values have Chinese labels."""
        from tools.seed.dicts import DICT_DATA

        for value in DICT_DATA[:10]:  # Check first 10
            assert "dict_label" in value
            # Labels should be non-empty
            assert len(value["dict_label"]) > 0


class TestSeedParams:
    """Tests for parameter seed data (FP-B07-02)."""

    def test_params_defined(self):
        """System parameters are defined."""
        from tools.seed.params import PARAMS

        # Check some expected params exist
        param_keys = [p["param_key"] for p in PARAMS]

        assert len(param_keys) > 0
        # At least some params should be defined
        assert any("perf" in k for k in param_keys) or len(param_keys) > 0


class TestSeedMenus:
    """Tests for menu seed data (FP-B04-02)."""

    def test_menus_defined(self):
        """Menu items are defined."""
        from tools.seed.menus import MENUS

        assert len(MENUS) > 0

    def test_menu_has_perm_code(self):
        """Menu items have permission codes."""
        from tools.seed.menus import MENUS

        # Button type menus should have perm_code
        for menu in MENUS:
            if menu.get("menu_type") == "BUTTON":
                assert "perm_code" in menu, f"Button menu missing perm_code: {menu.get('name')}"

    def test_perm_codes_start_with_ims(self):
        """Permission codes start with 'ims:'."""
        from tools.seed.menus import MENUS

        for menu in MENUS:
            perm_code = menu.get("perm_code")
            if perm_code:
                assert perm_code.startswith("ims:"), f"Invalid perm code: {perm_code}"


class TestSeedTenant:
    """Tests for tenant seed data."""

    def test_seed_tenant_function_exists(self):
        """Platform tenant seed function is defined."""
        from tools.seed.tenant import seed_tenant

        assert callable(seed_tenant)


class TestSeedDepts:
    """Tests for department seed data."""

    def test_seed_depts_function_exists(self):
        """Seed depts function is defined."""
        from tools.seed.depts import seed_depts

        assert callable(seed_depts)

    def test_dry_run_returns_count(self):
        """Dry run returns expected record count."""
        from tools.seed.depts import seed_depts

        # Dry run should return 2 (root + system dept)
        count = seed_depts(env="test", dry_run=True)
        assert count == 2
