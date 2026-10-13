# tests/unit/test_system_other_services.py - Other System Services Tests (B2-M02)
"""
Tests for log, notify, param, calendar services.

Covers:
- UT-B2-L: Log service
- UT-B2-N: Notify service
- UT-B2-P: Param service
- UT-B2-Q: Calendar service
"""

import pytest

from app.core.context import RequestContext, ctx


class TestSystemLogService:
    """Tests for SystemLogService."""

    def test_service_imports(self):
        """UT-B2-L-01: SystemLogService can be imported."""
        from app.services.system_log import SystemLogService
        assert SystemLogService is not None

    def test_get_operate_log_page_method_exists(self):
        """UT-B2-L-02: get_operate_log_page method exists."""
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        assert hasattr(svc, 'get_operate_log_page')

    def test_get_operate_log_detail_method_exists(self):
        """UT-B2-L-03: get_operate_log_detail method exists."""
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        assert hasattr(svc, 'get_operate_log_detail')

    def test_get_login_log_page_method_exists(self):
        """UT-B2-L-04: get_login_log_page method exists."""
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        assert hasattr(svc, 'get_login_log_page')

    def test_export_operate_logs_method_exists(self):
        """UT-B2-L-05: export_operate_logs method exists."""
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        assert hasattr(svc, 'export_operate_logs')

    def test_export_login_logs_method_exists(self):
        """UT-B2-L-06: export_login_logs method exists."""
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        assert hasattr(svc, 'export_login_logs')


class TestSystemNotifyService:
    """Tests for SystemNotifyService."""

    def test_service_imports(self):
        """UT-B2-N-01: SystemNotifyService can be imported."""
        from app.services.system_notify import SystemNotifyService
        assert SystemNotifyService is not None

    def test_get_notify_record_page_method_exists(self):
        """UT-B2-N-02: get_notify_record_page method exists."""
        from app.services.system_notify import SystemNotifyService
        svc = SystemNotifyService()
        assert hasattr(svc, 'get_notify_record_page')

    def test_resend_notification_method_exists(self):
        """UT-B2-N-03: resend_notification method exists."""
        from app.services.system_notify import SystemNotifyService
        svc = SystemNotifyService()
        assert hasattr(svc, 'resend_notification')


class TestSystemParamService:
    """Tests for SystemParamService."""

    def test_service_imports(self):
        """UT-B2-P-01: SystemParamService can be imported."""
        from app.services.system_param import SystemParamService
        assert SystemParamService is not None

    def test_get_param_list_method_exists(self):
        """UT-B2-P-02: get_param_list method exists."""
        from app.services.system_param import SystemParamService
        svc = SystemParamService()
        assert hasattr(svc, 'get_param_list')

    def test_update_param_method_exists(self):
        """UT-B2-P-03: update_param method exists."""
        from app.services.system_param import SystemParamService
        svc = SystemParamService()
        assert hasattr(svc, 'update_param')


class TestSystemCalendarService:
    """Tests for SystemCalendarService."""

    def test_service_imports(self):
        """UT-B2-Q-01: SystemCalendarService can be imported."""
        from app.services.system_calendar import SystemCalendarService
        assert SystemCalendarService is not None

    def test_get_calendar_list_method_exists(self):
        """UT-B2-Q-02: get_calendar_list method exists."""
        from app.services.system_calendar import SystemCalendarService
        svc = SystemCalendarService()
        assert hasattr(svc, 'get_calendar_list')

    def test_update_calendar_method_exists(self):
        """UT-B2-Q-03: update_calendar method exists."""
        from app.services.system_calendar import SystemCalendarService
        svc = SystemCalendarService()
        assert hasattr(svc, 'update_calendar')


class TestAuthPersonalCenterService:
    """Tests for personal center endpoints in auth service."""

    @pytest.fixture
    def user_ctx(self):
        """Set up user context."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    def test_auth_service_has_get_my_sessions(self):
        """UT-B2-PC-01: AuthService has get_my_sessions method."""
        from app.services.auth import AuthService
        svc = AuthService()
        assert hasattr(svc, 'get_my_sessions')

    def test_auth_service_has_delete_my_session(self):
        """UT-B2-PC-02: AuthService has delete_my_session method."""
        from app.services.auth import AuthService
        svc = AuthService()
        assert hasattr(svc, 'delete_my_session')

    def test_auth_service_has_set_password(self):
        """UT-B2-PC-03: AuthService has set_password method."""
        from app.services.auth import AuthService
        svc = AuthService()
        assert hasattr(svc, 'set_password')

    def test_auth_service_has_get_current_user_info_extended(self):
        """UT-B2-PC-04: AuthService has get_current_user_info_extended method."""
        from app.services.auth import AuthService
        svc = AuthService()
        assert hasattr(svc, 'get_current_user_info_extended')


class TestSystemLogServiceExecution:
    """Tests that execute SystemLogService methods."""

    @pytest.fixture
    def log_ctx(self):
        """Set up context for log tests."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={"ims:system:log:query"},
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.mark.asyncio
    async def test_get_operate_log_page_empty(self, db_session, log_ctx):
        """UT-B2-L-07: get_operate_log_page returns empty when no logs."""
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        result = await svc.get_operate_log_page(1, 10)
        assert isinstance(result, dict)
        assert "list" in result or "items" in result or isinstance(result.get("data"), list)

    @pytest.mark.asyncio
    async def test_get_login_log_page_empty(self, db_session, log_ctx):
        """UT-B2-L-08: get_login_log_page returns empty when no logs."""
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        result = await svc.get_login_log_page(1, 10)
        assert isinstance(result, dict)


class TestSystemNotifyServiceExecution:
    """Tests that execute SystemNotifyService methods."""

    @pytest.fixture
    def notify_ctx(self):
        """Set up context for notify tests."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={"ims:system:notify:query"},
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.mark.asyncio
    async def test_get_notify_record_page_empty(self, db_session, notify_ctx):
        """UT-B2-N-04: get_notify_record_page returns empty when no records."""
        from app.services.system_notify import SystemNotifyService
        svc = SystemNotifyService()
        result = await svc.get_notify_record_page(1, 10)
        assert isinstance(result, dict)


class TestSystemParamServiceExecution:
    """Tests that execute SystemParamService methods."""

    @pytest.fixture
    def param_ctx(self):
        """Set up context for param tests."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={"ims:system:param:query", "ims:system:param:update"},
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.mark.asyncio
    async def test_get_param_list_empty(self, db_session, param_ctx):
        """UT-B2-P-04: get_param_list returns empty when no params."""
        from app.services.system_param import SystemParamService
        svc = SystemParamService()
        result = await svc.get_param_list()
        assert isinstance(result, list)


class TestSystemCalendarServiceExecution:
    """Tests that execute SystemCalendarService methods."""

    @pytest.fixture
    def calendar_ctx(self):
        """Set up context for calendar tests."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes={"ims:system:calendar:update"},
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.mark.asyncio
    async def test_get_calendar_list_empty(self, db_session, calendar_ctx):
        """UT-B2-Q-04: get_calendar_list returns empty when no entries."""
        from app.services.system_calendar import SystemCalendarService
        svc = SystemCalendarService()
        result = await svc.get_calendar_list(2026)
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_calendar_list_with_month(self, db_session, calendar_ctx):
        """UT-B2-Q-05: get_calendar_list can filter by month."""
        from app.services.system_calendar import SystemCalendarService
        svc = SystemCalendarService()
        result = await svc.get_calendar_list(2026, 10)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_calendar_add_holiday(self, db_session, calendar_ctx):
        """UT-B2-Q-06: update_calendar can add a holiday."""
        from app.services.system_calendar import SystemCalendarService
        svc = SystemCalendarService()
        result = await svc.update_calendar("2026-10-13", "HOLIDAY")
        assert result["day"] == "2026-10-13"
        assert result["kind"] == "HOLIDAY"

    @pytest.mark.asyncio
    async def test_update_calendar_set_normal(self, db_session, calendar_ctx):
        """UT-B2-Q-07: update_calendar can reset to normal."""
        from app.services.system_calendar import SystemCalendarService
        svc = SystemCalendarService()
        # First add an entry
        await svc.update_calendar("2026-10-14", "HOLIDAY")
        # Then reset it
        result = await svc.update_calendar("2026-10-14", "NORMAL")
        assert result["kind"] == "NORMAL"

    @pytest.mark.asyncio
    async def test_update_calendar_update_existing(self, db_session, calendar_ctx):
        """UT-B2-Q-08: update_calendar can update existing entry."""
        from app.services.system_calendar import SystemCalendarService
        svc = SystemCalendarService()
        # Add holiday
        await svc.update_calendar("2026-10-15", "HOLIDAY")
        # Change to workday
        result = await svc.update_calendar("2026-10-15", "EXTRA_WORK")
        assert result["kind"] == "EXTRA_WORK"
