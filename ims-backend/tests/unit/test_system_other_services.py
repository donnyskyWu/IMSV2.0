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
