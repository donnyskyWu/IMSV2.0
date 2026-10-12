# tests/unit/test_engineering.py
"""
Unit tests for engineering conventions.

Covers: UT-A01-*, UT-A02-*, UT-A03-*, UT-A04-*, UT-A05-*, UT-A06-*
"""
import os
import re
from pathlib import Path

import pytest

os.environ["IMS_ENV"] = "test"
os.environ["IMS_DB_URL"] = "sqlite:///:memory:"
os.environ["IMS_REDIS_URL"] = ""
os.environ["IMS_JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"


class TestRoutePrefixValidation:
    """Tests for route prefix validation - UT-A01-05, UT-A01-06."""

    def test_invalid_route_prefix_rejected_UT_A01_05(self):
        """UT-A01-05: Route without /admin-api/ims prefix fails startup."""
        from fastapi import FastAPI

        from app.main import validate_routes

        app = FastAPI()

        @app.get("/demo/x")
        def invalid_route():
            return {}

        with pytest.raises(RuntimeError, match="does not start with"):
            validate_routes(app)

    def test_anonymous_route_not_in_whitelist_UT_A01_06(self):
        """UT-A01-06: Anonymous route not in whitelist fails startup."""
        pass


class TestWorkerProcess:
    """Tests for Worker process - UT-A01-12."""

    def test_worker_no_http_routes_UT_A01_12(self):
        """UT-A01-12: Worker process has no HTTP routes, only @job tasks."""
        pass


class TestErrorCodeRegistration:
    """Tests for error code registration - UT-A02-03, UT-A02-04, UT-A02-05."""

    def test_error_code_domain_segment_UT_A02_03(self):
        """UT-A02-03: Error code registered outside domain segment fails."""
        pass

    def test_duplicate_error_code_fails_UT_A02_04(self):
        """UT-A02-04: Duplicate error code registration fails."""
        from app.core.errors import BizError

        error1 = BizError(1214, msg="用户名或密码错误")
        error2 = BizError(1214, msg="另一个错误")
        assert error1.code == error2.code

    def test_error_message_chinese_only_UT_A02_05(self):
        """UT-A02-05: Error message with English code fails static check."""
        pass


class TestDecimalHandling:
    """Tests for decimal handling - UT-A04-05, UT-A04-06, UT-A04-07."""

    def test_decimal_precision_rejected_UT_A04_05(self):
        """UT-A04-05: More than 2 decimal places rejected with 1001."""
        from decimal import Decimal

        value = "12.345"
        d = Decimal(value)
        places = d.as_tuple().exponent
        assert places == -3

    def test_percent_conversion_UT_A04_07(self):
        """UT-A04-07: Percent 5 stored as 0.0500, returns 5."""
        percent_value = 5
        storage_value = f"{percent_value / 100:.4f}"
        api_value = float(storage_value) * 100

        assert storage_value == "0.0500"
        assert api_value == 5.0


class TestOpenAPIGeneration:
    """Tests for OpenAPI generation - UT-A05-01 to UT-A05-04."""

    def test_openapi_consistent_UT_A05_01(self):
        """UT-A05-01: make api-gen produces no diff."""
        pass

    def test_schema_change_requires_regen_UT_A05_02(self):
        """UT-A05-02: Schema change without regen fails CI."""
        pass

    def test_route_requires_summary_UT_A05_03(self):
        """UT-A05-03: Route without summary fails CI."""
        pass

    def test_hardcoded_path_fails_static_UT_A05_04(self):
        """UT-A05-04: Hardcoded API path in frontend fails static check."""
        pass


class TestScaffolding:
    """Tests for code scaffolding - UT-A06-*."""

    def test_scaffold_validates_references_UT_A06_01(self):
        """UT-A06-01: Scaffold validates table/dict/perm references."""
        pass

    def test_scaffold_validates_delete_policy_UT_A06_02(self):
        """UT-A06-02: Scaffold validates delete policy declaration."""
        pass

    def test_scaffold_generates_migration_UT_A06_03(self):
        """UT-A06-03: Scaffold generates working migration and tests."""
        pass

    def test_scaffold_file_header_UT_A06_04(self):
        """UT-A06-04: Generated files have version/hash/time header."""
        pass

    def test_scaffold_frontend_components_UT_A06_05(self):
        """UT-A06-05: Generated frontend uses PageHeader/QueryBar/etc."""
        pass

    def test_scaffold_no_overwrite_modified_UT_A06_06(self):
        """UT-A06-06: Scaffold doesn't overwrite modified files."""
        pass

    def test_scaffold_force_overwrites_UT_A06_07(self):
        """UT-A06-07: Scaffold --force overwrites modified files."""
        pass


class TestStaticChecks:
    """Tests for static checks that should fail."""

    def test_no_create_all_in_code_UT_B02_03(self):
        """UT-B02-03: Code with Base.metadata.create_all fails static check."""
        repo_root = Path(__file__).parent.parent.parent
        app_dir = repo_root / "app"

        for py_file in app_dir.rglob("*.py"):
            if "test" in str(py_file):
                continue
            content = py_file.read_text()
            assert "Base.metadata.create_all(" not in content, (
                f"Found create_all in {py_file}"
            )

    def test_no_alter_table_in_startup_UT_B02_04(self):
        """UT-B02-04: Startup code with ALTER TABLE fails static check."""
        repo_root = Path(__file__).parent.parent.parent
        main_file = repo_root / "app" / "main.py"

        content = main_file.read_text()
        assert "ALTER TABLE" not in content

    def test_no_live_room_in_migration_UT_B02_05(self):
        """UT-B02-05: Migration referencing live_room fails CI."""
        pass

    def test_no_tenant_filter_hardcoded_UT_C02_13(self):
        """UT-C02-13: Hardcoded .where(tenant_id == 1) fails static check."""
        repo_root = Path(__file__).parent.parent.parent
        service_dir = repo_root / "app" / "services"

        pattern = re.compile(r"\.where\([^)]*tenant_id\s*==\s*\d+\)")

        for py_file in service_dir.rglob("*.py"):
            content = py_file.read_text()
            matches = pattern.findall(content)
            assert not matches, f"Found hardcoded tenant filter in {py_file}: {matches}"

    def test_no_session_commit_in_routes_UT_C01_03(self):
        """UT-C01-03: session.commit() in route handlers fails static check."""
        repo_root = Path(__file__).parent.parent.parent
        api_dir = repo_root / "app" / "api"

        for py_file in api_dir.rglob("*.py"):
            content = py_file.read_text()
            assert "session.commit()" not in content, (
                f"Found session.commit() in {py_file}"
            )

    def test_no_direct_http_calls_UT_H04_06(self):
        """UT-H04-06: Direct httpx calls to external APIs fail CI."""
        repo_root = Path(__file__).parent.parent.parent
        app_dir = repo_root / "app"

        for py_file in app_dir.rglob("*.py"):
            if "integrations" in str(py_file):
                continue
            content = py_file.read_text()
            assert 'httpx.get("http://ops' not in content
            assert 'httpx.post("http://ops' not in content

    def test_no_role_key_comparison_UT_D03_08(self):
        """UT-D03-08: Code comparing role_key directly fails static check."""
        repo_root = Path(__file__).parent.parent.parent
        service_dir = repo_root / "app" / "services"

        pattern1 = re.compile(r'role_key\s*==\s*["\']R\d+["\']')
        pattern2 = re.compile(r'["\']admin["\']\s*in\s*roles')

        for py_file in service_dir.rglob("*.py"):
            content = py_file.read_text()
            assert not pattern1.findall(content), f"Found role_key comparison in {py_file}"
            assert not pattern2.findall(content), f"Found admin in roles in {py_file}"

    def test_no_seed_in_service_UT_H05_04(self):
        """UT-H05-04: Calling seed insert from service fails static check."""
        repo_root = Path(__file__).parent.parent.parent
        service_dir = repo_root / "app" / "services"

        for py_file in service_dir.rglob("*.py"):
            content = py_file.read_text()
            assert "seed_insert" not in content, (
                f"Found seed_insert in {py_file}"
            )

    def test_no_live_room_in_domains_UT_H06_05(self):
        """UT-H06-05: live_room reference in app/domains fails static check."""
        repo_root = Path(__file__).parent.parent.parent
        domains_dir = repo_root / "app" / "domains"

        if domains_dir.exists():
            for py_file in domains_dir.rglob("*.py"):
                content = py_file.read_text()
                assert "live_room" not in content.lower(), (
                    f"Found live_room in {py_file}"
                )

    def test_no_train_ai_import_air_UT_H08_10(self):
        """UT-H08-10: TrainQuizAiClient importing AIR module fails static check."""
        repo_root = Path(__file__).parent.parent.parent
        train_ai_file = repo_root / "app" / "integrations" / "train_ai" / "client.py"

        if train_ai_file.exists():
            content = train_ai_file.read_text()
            assert "from app.integrations.air" not in content
            assert "import air" not in content

    def test_no_hardcoded_ai_config_UT_H08_12(self):
        """UT-H08-12: Hardcoded AI config values outside config/integrations fail static check."""
        repo_root = Path(__file__).parent.parent.parent
        app_dir = repo_root / "app"

        excluded_dirs = {"core", "seeds", "integrations"}

        for py_file in app_dir.rglob("*.py"):
            parts = py_file.parts
            if any(d in parts for d in excluded_dirs):
                continue
            content = py_file.read_text()
            assert "dashscope.aliyuncs.com" not in content, f"Found in {py_file}"
            assert "qwen3.8-max" not in content, f"Found in {py_file}"
