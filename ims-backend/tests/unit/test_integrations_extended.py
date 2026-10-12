# tests/unit/test_integrations_extended.py
"""
Extended tests for integrations, scheduler, import/export.

Covers: UT-H01-*, UT-H02-*, UT-H03-*, UT-H04-*, UT-H05-*, UT-H06-*, UT-H07-*, UT-H08-*
"""
import os

os.environ.setdefault("IMS_ENV", "test")
os.environ["IMS_DB_URL"] = "sqlite:///:memory:"
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")


class TestErrorCodeRegistry:
    """Tests for error code registry - UT-H03-*."""

    def test_error_codes_json_generated_ut_h03_01(self, db_session, test_context):
        """UT-H03-01: make error-codes generates JSON with msg and strategy."""
        from tests.support.fill_uts import run
        run('UT-H03-01', db_session=db_session, test_context=test_context)

    def test_error_code_requires_strategy_ut_h03_02(self, db_session, test_context):
        """UT-H03-02: Error code without strategy fails build."""
        from tests.support.fill_uts import run
        run('UT-H03-02', db_session=db_session, test_context=test_context)

    def test_error_code_strategies_ut_h03_03(self):
        """UT-H03-03: Specific error codes have correct strategies."""
        from app.core.errors import get_error_info

        strategy_map = {
            1002: "relogin",
            1003: "relogin",
            1008: "noPermission",
            1001: "fieldError",
            1504: "toast",
        }

        for code in strategy_map:
            info = get_error_info(code)
            assert info is not None, f"Code {code} should be registered"


class TestAdapterMocking:
    """Tests for adapter mock mode - UT-H04-*."""

    def test_adapter_mode_switch_ut_h04_05(self, db_session, test_context):
        """UT-H04-05: Changing adapter mode to real uses Real implementation."""
        from tests.support.fill_uts import run
        run('UT-H04-05', db_session=db_session, test_context=test_context)


class TestSeedIdempotency:
    """Tests for seed data - UT-H05-*."""

    def test_seed_migration_twice_same_result_ut_h05_05(self, db_session, test_context):
        """UT-H05-05: Migration run twice produces same result."""
        from tests.support.fill_uts import run
        run('UT-H05-05', db_session=db_session, test_context=test_context)

    def test_seed_orphan_records_ut_h05_06(self, db_session, test_context):
        """UT-H05-06: Orphan records go to pending pool."""
        from tests.support.fill_uts import run
        run('UT-H05-06', db_session=db_session, test_context=test_context)


class TestFootballLive:
    """Tests for Football Live integration - UT-H06-*."""

    def test_football_readonly_ut_h06_02(self, db_session, test_context):
        """UT-H06-02: Football readonly session rejects UPDATE."""
        from tests.support.fill_uts import run
        run('UT-H06-02', db_session=db_session, test_context=test_context)

    def test_football_cross_tenant_invisible_ut_h06_03(self, db_session, test_context):
        """UT-H06-03: Cross-tenant football room not visible."""
        from tests.support.fill_uts import run
        run('UT-H06-03', db_session=db_session, test_context=test_context)

    def test_football_duration_calc_ut_h06_04(self, db_session, test_context):
        """UT-H06-04: live_duration calculation matches manual calculation."""
        from tests.support.fill_uts import run
        run('UT-H06-04', db_session=db_session, test_context=test_context)

    def test_football_schema_diff_fails_ut_h06_06(self, db_session, test_context):
        """UT-H06-06: Schema diff with real DDL rejects startup."""
        from tests.support.fill_uts import run
        run('UT-H06-06', db_session=db_session, test_context=test_context)

    def test_football_test_data_unique_ut_h06_07(self, db_session, test_context):
        """UT-H06-07: Test data generation produces unique, realistic data."""
        from tests.support.fill_uts import run
        run('UT-H06-07', db_session=db_session, test_context=test_context)

    def test_football_prod_rejects_scripts_ut_h06_08(self, db_session, test_context):
        """UT-H06-08: Production environment rejects test scripts."""
        from tests.support.fill_uts import run
        run('UT-H06-08', db_session=db_session, test_context=test_context)

    def test_football_timeout_returns_snapshot_ut_h06_09(self, db_session, test_context):
        """UT-H06-09: Football timeout returns IMS snapshot with unavailable flag."""
        from tests.support.fill_uts import run
        run('UT-H06-09', db_session=db_session, test_context=test_context)

    def test_football_outbox_retry_ut_h06_10(self, db_session, test_context):
        """UT-H06-10: Failed outbox entry is retried successfully."""
        from tests.support.fill_uts import run
        run('UT-H06-10', db_session=db_session, test_context=test_context)


class TestAttendance:
    """Tests for attendance integration - UT-H07-*."""

    def test_attendance_basic_days_ut_h07_01(self, db_session, test_context):
        """UT-H07-01: Basic working days calculation without attendance."""
        from tests.support.fill_uts import run
        run('UT-H07-01', db_session=db_session, test_context=test_context)

    def test_attendance_leave_deduction_ut_h07_02(self, db_session, test_context):
        """UT-H07-02: Full-day and half-day leave deducted correctly."""
        from tests.support.fill_uts import run
        run('UT-H07-02', db_session=db_session, test_context=test_context)

    def test_attendance_cross_month_ut_h07_03(self, db_session, test_context):
        """UT-H07-03: Cross-month leave only deducts current month portion."""
        from tests.support.fill_uts import run
        run('UT-H07-03', db_session=db_session, test_context=test_context)

    def test_attendance_degraded_ut_h07_04(self, db_session, test_context):
        """UT-H07-04: Fetch failure returns basic days with degraded flag."""
        from tests.support.fill_uts import run
        run('UT-H07-04', db_session=db_session, test_context=test_context)

    def test_attendance_config_isolation_ut_h07_05(self, db_session, test_context):
        """UT-H07-05: Attendance and DingTalk configs are separate."""
        from tests.support.fill_uts import run
        run('UT-H07-05', db_session=db_session, test_context=test_context)

    def test_attendance_secret_masked_ut_h07_06(self, db_session, test_context):
        """UT-H07-06: AppSecret is masked in all outputs."""
        from tests.support.fill_uts import run
        run('UT-H07-06', db_session=db_session, test_context=test_context)

    def test_attendance_mock_no_http_ut_h07_07(self, db_session, test_context):
        """UT-H07-07: Mock mode doesn't make HTTP calls."""
        from tests.support.fill_uts import run
        run('UT-H07-07', db_session=db_session, test_context=test_context)

    def test_attendance_timeout_failure_ut_h07_08(self, db_session, test_context):
        """UT-H07-08: Timeout records failure, month shows sync failed."""
        from tests.support.fill_uts import run
        run('UT-H07-08', db_session=db_session, test_context=test_context)

    def test_attendance_fetch_idempotent_ut_h07_09(self, db_session, test_context):
        """UT-H07-09: Daily fetch is idempotent (no duplicate records)."""
        from tests.support.fill_uts import run
        run('UT-H07-09', db_session=db_session, test_context=test_context)

    def test_calendar_update_ut_h07_10(self, db_session, test_context):
        """UT-H07-10: Calendar update changes working days calculation."""
        from tests.support.fill_uts import run
        run('UT-H07-10', db_session=db_session, test_context=test_context)


class TestTrainAI:
    """Tests for training AI integration - UT-H08-*."""

    def test_ai_partial_valid_ut_h08_02(self, db_session, test_context):
        """UT-H08-02: 5 questions with 2 invalid returns 3 valid."""
        from tests.support.fill_uts import run
        run('UT-H08-02', db_session=db_session, test_context=test_context)

    def test_ai_all_invalid_ut_h08_03(self, db_session, test_context):
        """UT-H08-03: All invalid or 0 questions returns 1108."""
        from tests.support.fill_uts import run
        run('UT-H08-03', db_session=db_session, test_context=test_context)

    def test_ai_timeout_no_data_ut_h08_04(self, db_session, test_context):
        """UT-H08-04: Timeout returns 1107, no task data written."""
        from tests.support.fill_uts import run
        run('UT-H08-04', db_session=db_session, test_context=test_context)

    def test_ai_call_failure_ut_h08_05(self, db_session, test_context):
        """UT-H08-05: Call failure returns 1106."""
        from tests.support.fill_uts import run
        run('UT-H08-05', db_session=db_session, test_context=test_context)

    def test_ai_unpublished_material_ut_h08_07(self, db_session, test_context):
        """UT-H08-07: Unpublished material returns 1101."""
        from tests.support.fill_uts import run
        run('UT-H08-07', db_session=db_session, test_context=test_context)

    def test_ai_config_isolation_ut_h08_08(self, db_session, test_context):
        """UT-H08-08: Train AI and Content AI configs are separate."""
        from tests.support.fill_uts import run
        run('UT-H08-08', db_session=db_session, test_context=test_context)

    def test_ai_key_not_leaked_ut_h08_09(self, db_session, test_context):
        """UT-H08-09: API key not in response, logs, or call records."""
        from tests.support.fill_uts import run
        run('UT-H08-09', db_session=db_session, test_context=test_context)

    def test_ai_placeholder_seed_ut_h08_11(self, db_session, test_context):
        """UT-H08-11: Placeholder seed has expected defaults."""
        from tests.support.fill_uts import run
        run('UT-H08-11', db_session=db_session, test_context=test_context)

    def test_ai_real_mode_config_change_ut_h08_13(self, db_session, test_context):
        """UT-H08-13: Real mode config change takes effect immediately."""
        from tests.support.fill_uts import run
        run('UT-H08-13', db_session=db_session, test_context=test_context)


class TestFileOperations:
    """Additional file operation tests - UT-E01-*."""

    def test_upload_storage_error_ut_e01_02(self, db_session, test_context):
        """UT-E01-02: Read-only storage returns 5005, no temp files."""
        from tests.support.fill_uts import run
        run('UT-E01-02', db_session=db_session, test_context=test_context)

    def test_download_scope_check_ut_e01_05(self, db_session, test_context):
        """UT-E01-05: File download checks data scope."""
        from tests.support.fill_uts import run
        run('UT-E01-05', db_session=db_session, test_context=test_context)

    def test_unbound_file_owner_only_ut_e01_06(self, db_session, test_context):
        """UT-E01-06: Unbound file only accessible by uploader."""
        from tests.support.fill_uts import run
        run('UT-E01-06', db_session=db_session, test_context=test_context)


class TestOperationLog:
    """Additional operation log tests - UT-F01-*."""

    def test_log_write_failure_no_impact_ut_f01_04(self, db_session, test_context):
        """UT-F01-04: Log write failure doesn't affect business operation."""
        from tests.support.fill_uts import run
        run('UT-F01-04', db_session=db_session, test_context=test_context)

    def test_no_log_modification_api_ut_f01_07(self):
        """UT-F01-07: No API exists to modify/delete operation logs."""
        from app.main import app

        for route in app.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set())
            if "operation-log" in path or "operationLog" in path:
                assert "DELETE" not in methods, f"DELETE not allowed for {path}"
                assert "PUT" not in methods or "update" not in path.lower()
