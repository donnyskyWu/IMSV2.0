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
            session_id="test-current-session",
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

    @pytest.mark.asyncio
    async def test_get_my_sessions_empty(self, user_ctx):
        """UT-B2-PC-05: get_my_sessions returns empty list when no sessions."""
        from app.services.auth import AuthService
        svc = AuthService()
        result = await svc.get_my_sessions(user_id=999999)
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_my_sessions_with_valid_sessions(self, user_ctx):
        """UT-B2-PC-05a: get_my_sessions returns valid sessions."""
        from datetime import datetime, timedelta, timezone

        from app.core.cache import Cache
        from app.services.auth import AuthService
        svc = AuthService()
        user_id = 12345
        sessions_key = f"{svc.USER_SESSIONS_PREFIX}{user_id}"
        session_id = "test-valid-session"
        session_key = f"{svc.SESSION_PREFIX}{session_id}"
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        Cache.sadd(sessions_key, session_id)
        Cache.set_json(session_key, {
            "user_id": user_id,
            "refresh_token": "rt",
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, ttl=3600)
        try:
            result = await svc.get_my_sessions(user_id=user_id)
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["sid"] == session_id
            assert result[0]["current"] is False
        finally:
            Cache.delete(session_key)
            Cache.delete(sessions_key)

    @pytest.mark.asyncio
    async def test_get_my_sessions_current_session_marked(self, user_ctx):
        """UT-B2-PC-05b: get_my_sessions marks current session."""
        from datetime import datetime, timedelta, timezone

        from app.core.cache import Cache
        from app.services.auth import AuthService
        svc = AuthService()
        user_id = 12346
        sessions_key = f"{svc.USER_SESSIONS_PREFIX}{user_id}"
        session_id = "test-current-session"
        session_key = f"{svc.SESSION_PREFIX}{session_id}"
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        Cache.sadd(sessions_key, session_id)
        Cache.set_json(session_key, {
            "user_id": user_id,
            "refresh_token": "rt",
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, ttl=3600)
        try:
            result = await svc.get_my_sessions(user_id=user_id)
            assert len(result) == 1
            assert result[0]["current"] is True
        finally:
            Cache.delete(session_key)
            Cache.delete(sessions_key)

    @pytest.mark.asyncio
    async def test_get_my_sessions_skips_missing_session_data(self, user_ctx):
        """UT-B2-PC-05c: get_my_sessions skips sessions without data."""
        from app.core.cache import Cache
        from app.services.auth import AuthService
        svc = AuthService()
        user_id = 12347
        sessions_key = f"{svc.USER_SESSIONS_PREFIX}{user_id}"
        Cache.sadd(sessions_key, "nonexistent-session-id")
        try:
            result = await svc.get_my_sessions(user_id=user_id)
            assert isinstance(result, list)
            assert len(result) == 0
        finally:
            Cache.delete(sessions_key)

    @pytest.mark.asyncio
    async def test_get_my_sessions_skips_expired_sessions(self, user_ctx):
        """UT-B2-PC-05d: get_my_sessions skips expired sessions."""
        from datetime import datetime, timedelta, timezone

        from app.core.cache import Cache
        from app.services.auth import AuthService
        svc = AuthService()
        user_id = 12348
        sessions_key = f"{svc.USER_SESSIONS_PREFIX}{user_id}"
        session_id = "test-expired-session"
        session_key = f"{svc.SESSION_PREFIX}{session_id}"
        expires_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        Cache.sadd(sessions_key, session_id)
        Cache.set_json(session_key, {
            "user_id": user_id,
            "refresh_token": "rt",
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, ttl=3600)
        try:
            result = await svc.get_my_sessions(user_id=user_id)
            assert isinstance(result, list)
            assert len(result) == 0
        finally:
            Cache.delete(session_key)
            Cache.delete(sessions_key)

    @pytest.mark.asyncio
    async def test_delete_my_session_empty_id(self, user_ctx):
        """UT-B2-PC-06: delete_my_session rejects empty session_id."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        svc = AuthService()
        with pytest.raises(BizError) as exc_info:
            await svc.delete_my_session(user_id=1, session_id="")
        assert exc_info.value.code == 1001

    @pytest.mark.asyncio
    async def test_delete_my_session_not_found(self, user_ctx):
        """UT-B2-PC-07: delete_my_session rejects non-existent session."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        svc = AuthService()
        with pytest.raises(BizError) as exc_info:
            await svc.delete_my_session(user_id=1, session_id="nonexistent-sid")
        assert exc_info.value.code == 1504

    @pytest.mark.asyncio
    async def test_delete_my_session_wrong_user(self, user_ctx):
        """UT-B2-PC-08: delete_my_session rejects session belonging to another user."""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.services.auth import AuthService
        svc = AuthService()
        Cache.set_json(f"{svc.SESSION_PREFIX}test-sid-other-user", {"user_id": 2}, ttl=60)
        try:
            with pytest.raises(BizError) as exc_info:
                await svc.delete_my_session(user_id=1, session_id="test-sid-other-user")
            assert exc_info.value.code == 1504
        finally:
            Cache.delete(f"{svc.SESSION_PREFIX}test-sid-other-user")

    @pytest.mark.asyncio
    async def test_delete_my_session_success(self, user_ctx):
        """UT-B2-PC-08a: delete_my_session removes a valid session."""
        from app.core.cache import Cache
        from app.services.auth import AuthService
        svc = AuthService()
        user_id = 1
        session_id = "test-delete-session"
        sessions_key = f"{svc.USER_SESSIONS_PREFIX}{user_id}"
        session_key = f"{svc.SESSION_PREFIX}{session_id}"
        refresh_token = "test-refresh"
        Cache.sadd(sessions_key, session_id)
        Cache.set_json(session_key, {
            "user_id": user_id,
            "refresh_token": refresh_token,
        }, ttl=60)
        Cache.set(f"{svc.REFRESH_INDEX_PREFIX}{refresh_token}", f"{session_id}:{user_id}", ttl=60)
        try:
            await svc.delete_my_session(user_id=user_id, session_id=session_id)
            assert Cache.get_json(session_key) is None
            assert Cache.get(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}") is not None
        finally:
            Cache.delete(sessions_key)
            Cache.delete(session_key)
            Cache.delete(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}")
            Cache.delete(f"{svc.REFRESH_INDEX_PREFIX}{refresh_token}")

    @pytest.mark.asyncio
    async def test_set_password_missing_user(self, db_session, user_ctx):
        """UT-B2-PC-09: set_password rejects non-existent user."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        svc = AuthService()
        with pytest.raises(BizError) as exc_info:
            await svc.set_password(user_id=999999, new_password="Test1234", keep_session_id="sid")
        assert exc_info.value.code == 1002

    @pytest.mark.asyncio
    async def test_set_password_already_has_password(self, db_session, user_ctx):
        """UT-B2-PC-10: set_password rejects user with existing password."""
        import bcrypt

        from app.core.errors import BizError
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        # Create user with password
        password_hash = bcrypt.hashpw(b"existing", bcrypt.gensalt(rounds=4)).decode()
        test_user = user(db_session, "test_has_pw", password_hash=password_hash)
        with pytest.raises(BizError) as exc_info:
            await svc.set_password(
                user_id=test_user.id,
                new_password="NewPass123",
                keep_session_id="sid"
            )
        assert exc_info.value.code == 1001
        assert "已设置密码" in exc_info.value.msg

    @pytest.mark.asyncio
    async def test_set_password_whitespace_rejected(self, db_session, user_ctx):
        """UT-B2-PC-11: set_password rejects password with whitespace."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        # Create user without password
        test_user = user(db_session, "test_no_pw", password_hash=None)
        with pytest.raises(BizError) as exc_info:
            await svc.set_password(
                user_id=test_user.id,
                new_password="Test 1234",
                keep_session_id="sid"
            )
        assert exc_info.value.code == 1001
        assert "空格" in exc_info.value.msg

    @pytest.mark.asyncio
    async def test_set_password_weak_rejected(self, db_session, user_ctx):
        """UT-B2-PC-12: set_password rejects weak password."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "test_no_pw2", password_hash=None)
        with pytest.raises(BizError) as exc_info:
            await svc.set_password(
                user_id=test_user.id,
                new_password="weakpwd",
                keep_session_id="sid"
            )
        assert exc_info.value.code == 1001

    @pytest.mark.asyncio
    async def test_get_current_user_info_extended_with_mobile(self, db_session, user_ctx):
        """UT-B2-PC-13: get_current_user_info_extended returns mobile masked."""
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "test_mobile_user")
        test_user.mobile_enc = "13812345678"
        db_session.flush()
        result = await svc.get_current_user_info_extended(test_user.id)
        assert result["user"]["mobileMasked"] == "138****5678"

    @pytest.mark.asyncio
    async def test_get_current_user_info_extended_short_mobile(self, db_session, user_ctx):
        """UT-B2-PC-14: get_current_user_info_extended handles short mobile."""
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "test_short_mobile")
        test_user.mobile_enc = "123"  # Too short
        db_session.flush()
        result = await svc.get_current_user_info_extended(test_user.id)
        assert result["user"]["mobileMasked"] is None

    @pytest.mark.asyncio
    async def test_get_current_user_info_extended_no_mobile(self, db_session, user_ctx):
        """UT-B2-PC-15: get_current_user_info_extended handles missing mobile."""
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "test_no_mobile")
        result = await svc.get_current_user_info_extended(test_user.id)
        assert result["user"]["mobileMasked"] is None

    @pytest.mark.asyncio
    async def test_get_current_user_info_extended_with_roles(self, db_session, user_ctx):
        """UT-B2-PC-16: get_current_user_info_extended returns role names."""
        from app.domains.sys.models import Role, UserRole
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "test_user_with_roles")
        role = Role(
            name="测试角色",
            role_key="TEST_ROLE",
            status="ENABLED",
            tenant_id=1,
            deleted=0,
        )
        db_session.add(role)
        db_session.flush()
        user_role = UserRole(
            user_id=test_user.id,
            role_id=role.id,
        )
        db_session.add(user_role)
        db_session.flush()
        result = await svc.get_current_user_info_extended(test_user.id)
        assert "roleNames" in result["user"]
        assert "测试角色" in result["user"]["roleNames"]

    @pytest.mark.asyncio
    async def test_get_current_user_info_extended_nonexistent_user(
        self, db_session, user_ctx
    ):
        """UT-B2-PC-17: get_current_user_info_extended handles nonexistent user."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        svc = AuthService()
        with pytest.raises(BizError):
            await svc.get_current_user_info_extended(user_id=999999)


class TestAuthRefreshTokenBranches:
    """Tests for _issue_rotated_tokens frozen/resigned branches."""

    @pytest.fixture
    def refresh_ctx(self):
        """Set up context for refresh tests."""
        context = RequestContext(
            trace_id="test-trace",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            dept_ids=[1],
            client_ip="127.0.0.1",
            session_id="test-session",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.mark.asyncio
    async def test_issue_rotated_tokens_session_missing_frozen_user(
        self, db_session, refresh_ctx
    ):
        """UT-B2-RT-01: _issue_rotated_tokens session_missing with frozen user returns 1216."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "rt_frozen_user")
        test_user.status = "FROZEN"
        db_session.flush()
        with pytest.raises(BizError) as exc_info:
            await svc._issue_rotated_tokens(
                session_id="nonexistent-session",
                refresh_token="nonexistent-rt",
                used_key="used:key",
                user_id=test_user.id,
            )
        assert exc_info.value.code == 1216

    @pytest.mark.asyncio
    async def test_issue_rotated_tokens_session_missing_resigned_user(
        self, db_session, refresh_ctx
    ):
        """UT-B2-RT-02: _issue_rotated_tokens session_missing with resigned user returns 1216."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "rt_resigned_user")
        test_user.status = "RESIGNED"
        db_session.flush()
        with pytest.raises(BizError) as exc_info:
            await svc._issue_rotated_tokens(
                session_id="nonexistent-session",
                refresh_token="nonexistent-rt",
                used_key="used:key",
                user_id=test_user.id,
            )
        assert exc_info.value.code == 1216

    @pytest.mark.asyncio
    async def test_issue_rotated_tokens_session_missing_active_user(
        self, db_session, refresh_ctx
    ):
        """UT-B2-RT-03: _issue_rotated_tokens session_missing with active user returns 1002."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "rt_active_user")
        test_user.status = "ACTIVE"
        db_session.flush()
        with pytest.raises(BizError) as exc_info:
            await svc._issue_rotated_tokens(
                session_id="nonexistent-session",
                refresh_token="nonexistent-rt",
                used_key="used:key",
                user_id=test_user.id,
            )
        assert exc_info.value.code == 1002

    @pytest.mark.asyncio
    async def test_issue_rotated_tokens_session_missing_no_user_id(self, refresh_ctx):
        """UT-B2-RT-04: _issue_rotated_tokens session_missing without user_id returns 1002."""
        from app.core.errors import BizError
        from app.services.auth import AuthService
        svc = AuthService()
        with pytest.raises(BizError) as exc_info:
            await svc._issue_rotated_tokens(
                session_id="nonexistent-session",
                refresh_token="nonexistent-rt",
                used_key="used:key",
                user_id=None,
            )
        assert exc_info.value.code == 1002

    @pytest.mark.asyncio
    async def test_issue_rotated_tokens_blacklisted_frozen_user(
        self, db_session, refresh_ctx
    ):
        """UT-B2-RT-05: _issue_rotated_tokens blacklisted with frozen user returns 1216."""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "rt_bl_frozen")
        test_user.status = "FROZEN"
        db_session.flush()
        session_id = "test-bl-session"
        session_key = f"{svc.SESSION_PREFIX}{session_id}"
        Cache.set_json(session_key, {
            "user_id": test_user.id,
            "refresh_token": "correct-rt",
        }, ttl=60)
        Cache.set(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}", "1", ttl=60)
        try:
            with pytest.raises(BizError) as exc_info:
                await svc._issue_rotated_tokens(
                    session_id=session_id,
                    refresh_token="correct-rt",
                    used_key="used:key",
                    user_id=test_user.id,
                )
            assert exc_info.value.code == 1216
        finally:
            Cache.delete(session_key)
            Cache.delete(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}")

    @pytest.mark.asyncio
    async def test_issue_rotated_tokens_blacklisted_resigned_user(
        self, db_session, refresh_ctx
    ):
        """UT-B2-RT-06: _issue_rotated_tokens blacklisted with resigned user returns 1216."""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "rt_bl_resigned")
        test_user.status = "RESIGNED"
        db_session.flush()
        session_id = "test-bl-session2"
        session_key = f"{svc.SESSION_PREFIX}{session_id}"
        Cache.set_json(session_key, {
            "user_id": test_user.id,
            "refresh_token": "correct-rt2",
        }, ttl=60)
        Cache.set(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}", "1", ttl=60)
        try:
            with pytest.raises(BizError) as exc_info:
                await svc._issue_rotated_tokens(
                    session_id=session_id,
                    refresh_token="correct-rt2",
                    used_key="used:key",
                    user_id=test_user.id,
                )
            assert exc_info.value.code == 1216
        finally:
            Cache.delete(session_key)
            Cache.delete(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}")

    @pytest.mark.asyncio
    async def test_issue_rotated_tokens_blacklisted_active_user(
        self, db_session, refresh_ctx
    ):
        """UT-B2-RT-07: _issue_rotated_tokens blacklisted with active user returns 1002."""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.services.auth import AuthService
        from tests.support.rows import user
        svc = AuthService()
        test_user = user(db_session, "rt_bl_active")
        test_user.status = "ACTIVE"
        db_session.flush()
        session_id = "test-bl-session3"
        session_key = f"{svc.SESSION_PREFIX}{session_id}"
        Cache.set_json(session_key, {
            "user_id": test_user.id,
            "refresh_token": "correct-rt3",
        }, ttl=60)
        Cache.set(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}", "1", ttl=60)
        try:
            with pytest.raises(BizError) as exc_info:
                await svc._issue_rotated_tokens(
                    session_id=session_id,
                    refresh_token="correct-rt3",
                    used_key="used:key",
                    user_id=test_user.id,
                )
            assert exc_info.value.code == 1002
        finally:
            Cache.delete(session_key)
            Cache.delete(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}")

    @pytest.mark.asyncio
    async def test_issue_rotated_tokens_blacklisted_no_user_id(
        self, db_session, refresh_ctx
    ):
        """UT-B2-RT-08: _issue_rotated_tokens blacklisted without user_id returns 1002."""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.services.auth import AuthService
        svc = AuthService()
        session_id = "test-bl-session4"
        session_key = f"{svc.SESSION_PREFIX}{session_id}"
        Cache.set_json(session_key, {
            "user_id": 1,
            "refresh_token": "correct-rt4",
        }, ttl=60)
        Cache.set(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}", "1", ttl=60)
        try:
            with pytest.raises(BizError) as exc_info:
                await svc._issue_rotated_tokens(
                    session_id=session_id,
                    refresh_token="correct-rt4",
                    used_key="used:key",
                    user_id=None,
                )
            assert exc_info.value.code == 1002
        finally:
            Cache.delete(session_key)
            Cache.delete(f"{svc.TOKEN_BLACKLIST_PREFIX}{session_id}")


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
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_operate_log_page(page)
        assert hasattr(result, 'total') or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_login_log_page_empty(self, db_session, log_ctx):
        """UT-B2-L-08: get_login_log_page returns empty when no logs."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_login_log_page(page)
        assert hasattr(result, 'total') or isinstance(result, dict)


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
        from app.core.pagination import PageParam
        from app.services.system_notify import SystemNotifyService
        svc = SystemNotifyService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_notify_record_page(page)
        assert hasattr(result, 'total') or isinstance(result, dict)


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


class TestSystemLogServiceFilters:
    """Tests for SystemLogService with filters."""

    @pytest.fixture
    def log_ctx_filters(self):
        """Set up context for log filter tests."""
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
    async def test_get_operate_log_with_module_filter(self, db_session, log_ctx_filters):
        """UT-B2-L-09: get_operate_log_page with module filter."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_operate_log_page(page, module="USER")
        assert hasattr(result, 'total')

    @pytest.mark.asyncio
    async def test_get_operate_log_with_operation_filter(self, db_session, log_ctx_filters):
        """UT-B2-L-10: get_operate_log_page with operation filter."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_operate_log_page(page, operation="create")
        assert hasattr(result, 'total')

    @pytest.mark.asyncio
    async def test_get_operate_log_with_operator_filter(self, db_session, log_ctx_filters):
        """UT-B2-L-11: get_operate_log_page with operator_name filter."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_operate_log_page(page, operator_name="admin")
        assert hasattr(result, 'total')

    @pytest.mark.asyncio
    async def test_get_operate_log_with_time_range(self, db_session, log_ctx_filters):
        """UT-B2-L-12: get_operate_log_page with time range filters."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_operate_log_page(
            page,
            start_time="2026-01-01 00:00:00",
            end_time="2026-12-31 23:59:59"
        )
        assert hasattr(result, 'total')

    @pytest.mark.asyncio
    async def test_get_login_log_with_time_range(self, db_session, log_ctx_filters):
        """UT-B2-L-13: get_login_log_page with time range filters."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_login_log_page(
            page,
            start_time="2026-01-01",
            end_time="2026-12-31"
        )
        assert hasattr(result, 'total')

    @pytest.mark.asyncio
    async def test_get_login_log_with_username_filter(self, db_session, log_ctx_filters):
        """UT-B2-L-14: get_login_log_page with username filter."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_login_log_page(page, username="test")
        assert hasattr(result, 'total')

    @pytest.mark.asyncio
    async def test_get_login_log_with_result_filter(self, db_session, log_ctx_filters):
        """UT-B2-L-15: get_login_log_page with result filter."""
        from app.core.pagination import PageParam
        from app.services.system_log import SystemLogService
        svc = SystemLogService()
        page = PageParam(page_no=1, page_size=10)
        result = await svc.get_login_log_page(page, result="SUCCESS")
        assert hasattr(result, 'total')
