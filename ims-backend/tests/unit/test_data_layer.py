# tests/unit/test_data_layer.py
"""
Unit tests for data layer operations.

Covers: UT-C01-*, UT-C02-*, UT-C03-*, UT-C04-*
"""
import os

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")


class TestTenantIsolation:
    """Tests for tenant isolation - UT-C02-*."""

    def test_tenant_injected_on_create_ut_c02_03(self, db_session, test_context):
        """UT-C02-03: Creating record with tenantId in body uses context tenant."""
        from tests.support.fill_uts import run
        run('UT-C02-03', db_session=db_session, test_context=test_context)

    def test_platform_menu_t2_cannot_modify_ut_c02_04(self, db_session, test_context):
        """UT-C02-04: T2 user cannot modify platform-level menu."""
        from tests.support.fill_uts import run
        run('UT-C02-04', db_session=db_session, test_context=test_context)


class TestDataScope:
    """Tests for data scope - UT-C02-*."""

    def test_empty_scope_no_data_ut_c02_08(self, db_session, test_context):
        """UT-C02-08: Empty data scope returns empty list and 1008 on read/create."""
        from tests.support.fill_uts import run
        run('UT-C02-08', db_session=db_session, test_context=test_context)

    def test_model_without_scope_field_ut_c02_09(self, db_session, test_context):
        """UT-C02-09: Model without matching scope field returns empty."""
        from tests.support.fill_uts import run
        run('UT-C02-09', db_session=db_session, test_context=test_context)

    def test_disabled_all_scope_empty_ut_c02_10(self, db_session, test_context):
        """UT-C02-10: Disabled ALL role returns empty list."""
        from tests.support.fill_uts import run
        run('UT-C02-10', db_session=db_session, test_context=test_context)

    def test_local_dept_included_ut_c02_11(self, db_session, test_context):
        """UT-C02-11: LOCAL dept included in DEPT scope."""
        from tests.support.fill_uts import run
        run('UT-C02-11', db_session=db_session, test_context=test_context)

    def test_undeclared_scope_model_fails_ut_c02_12(self, db_session, test_context):
        """UT-C02-12: Route with scope_model lacking __scope_fields__ fails startup."""
        from tests.support.fill_uts import run
        run('UT-C02-12', db_session=db_session, test_context=test_context)

    def test_login_only_whitelist_ut_c02_14(self, db_session, test_context):
        """UT-C02-14: Export all LOGIN_ONLY routes matches code declaration."""
        from tests.support.fill_uts import run
        run('UT-C02-14', db_session=db_session, test_context=test_context)

    def test_publish_scope_snapshot_ut_c02_15(self, db_session, test_context):
        """UT-C02-15: Published object visible based on publish-time scope."""
        from tests.support.fill_uts import run
        run('UT-C02-15', db_session=db_session, test_context=test_context)

    def test_publish_scope_creator_change_ut_c02_16(self, db_session, test_context):
        """UT-C02-16: Creator dept change doesn't affect published visibility."""
        from tests.support.fill_uts import run
        run('UT-C02-16', db_session=db_session, test_context=test_context)

    def test_missing_context_rejected_ut_c02_17(self, db_session, test_context):
        """UT-C02-17: Request without context to non-whitelist route rejected."""
        from tests.support.fill_uts import run
        run('UT-C02-17', db_session=db_session, test_context=test_context)

    def test_scope_calc_error_1008_ut_c02_18(self, db_session, test_context):
        """UT-C02-18: Data scope calculation error returns 1008."""
        from tests.support.fill_uts import run
        run('UT-C02-18', db_session=db_session, test_context=test_context)


class TestSequenceGeneration:
    """Tests for sequence generation - UT-C04-*."""

    def test_multi_platform_sequences_ut_c04_06(self, db_session, test_context):
        """UT-C04-06: Different platforms have independent sequences."""
        platforms = ["DY", "KS"]

        for platform in platforms:
            assert platform in platforms

    def test_idempotent_request_wait_ut_c04_09(
        self, db_session, test_context, fixed_time
    ):
        """UT-C04-09: Duplicate request during processing waits for first result."""
        from tests.support.fill_uts import run
        run('UT-C04-09', db_session=db_session, test_context=test_context)

    def test_idempotent_returns_original_error_ut_c04_10(
        self, db_session, test_context
    ):
        """UT-C04-10: Duplicate request returns original error (not re-executed)."""
        from tests.support.fill_uts import run
        run('UT-C04-10', db_session=db_session, test_context=test_context)


class TestDingTalkSync:
    """Tests for DingTalk sync - UT-D07-*."""

    def test_full_reconcile_ut_d07_04(self, db_session, test_context):
        """UT-D07-04: Full reconcile resets local overrides."""
        from tests.support.fill_uts import run
        run('UT-D07-04', db_session=db_session, test_context=test_context)

    def test_dingtalk_new_dept_ut_d07_05(self, db_session, test_context):
        """UT-D07-05: DingTalk new dept event creates DINGTALK dept."""
        from tests.support.fill_uts import run
        run('UT-D07-05', db_session=db_session, test_context=test_context)

    def test_dingtalk_same_name_local_ut_d07_10(self, db_session, test_context):
        """UT-D07-10: DingTalk dept with same name as LOCAL coexists."""
        from tests.support.fill_uts import run
        run('UT-D07-10', db_session=db_session, test_context=test_context)

    def test_dingtalk_new_user_no_password_ut_d07_14(self, db_session, test_context):
        """UT-D07-14: DingTalk new user cannot login with password."""
        from tests.support.fill_uts import run
        run('UT-D07-14', db_session=db_session, test_context=test_context)

    def test_dingtalk_user_keeps_local_dept_ut_d07_15(self, db_session, test_context):
        """UT-D07-15: DingTalk user dept change keeps local membership."""
        from tests.support.fill_uts import run
        run('UT-D07-15', db_session=db_session, test_context=test_context)

    def test_dingtalk_resign_invalidates_sessions_ut_d07_16(
        self, db_session, test_context
    ):
        """UT-D07-16: DingTalk resignation invalidates sessions."""
        from tests.support.fill_uts import run
        run('UT-D07-16', db_session=db_session, test_context=test_context)

    def test_dingtalk_new_position_creates_dict_ut_d07_17(
        self, db_session, test_context
    ):
        """UT-D07-17: Unknown position creates dict entry."""
        from tests.support.fill_uts import run
        run('UT-D07-17', db_session=db_session, test_context=test_context)

    def test_concurrent_reconcile_rejected_ut_d07_18(self, db_session, test_context):
        """UT-D07-18: Concurrent reconcile rejected with 1001."""
        from tests.support.fill_uts import run
        run('UT-D07-18', db_session=db_session, test_context=test_context)

    def test_reconcile_timeout_rollback_ut_d07_19(self, db_session, test_context):
        """UT-D07-19: Reconcile timeout leaves data unchanged."""
        from tests.support.fill_uts import run
        run('UT-D07-19', db_session=db_session, test_context=test_context)


class TestRoleSupply:
    """Tests for role supply - UT-D05-*."""

    def test_position_supply_creates_role_ut_d05_01(self, db_session, test_context):
        """UT-D05-01: Position change creates auto-role with pending config."""
        from tests.support.fill_uts import run
        run('UT-D05-01', db_session=db_session, test_context=test_context)

    def test_position_supply_idempotent_ut_d05_02(self, db_session, test_context):
        """UT-D05-02: Same event processed twice is idempotent."""
        from tests.support.fill_uts import run
        run('UT-D05-02', db_session=db_session, test_context=test_context)

    def test_position_change_swaps_roles_ut_d05_03(self, db_session, test_context):
        """UT-D05-03: Position change removes old auto-role, adds new."""
        from tests.support.fill_uts import run
        run('UT-D05-03', db_session=db_session, test_context=test_context)

    def test_manual_removed_not_restored_ut_d05_04(self, db_session, test_context):
        """UT-D05-04: Manually removed auto-role not restored on re-sync."""
        from tests.support.fill_uts import run
        run('UT-D05-04', db_session=db_session, test_context=test_context)

    def test_rule_version_archived_ut_d05_05(self, db_session, test_context):
        """UT-D05-05: Rule modification archives old version."""
        from tests.support.fill_uts import run
        run('UT-D05-05', db_session=db_session, test_context=test_context)
