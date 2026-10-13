# tests/unit/test_b2_refresh_regression.py
"""B2 系统管理模块刷新令牌回归测试。

Covers:
- UT-B2-BG-07-07: Login → freeze → refresh → 1216
- UT-B2-BG-07-08: Replay old refresh_token → entire session revoked
- UT-B2-BG-07-09: Rotation → logout → new refresh_token rejected
- UT-B2-BG-07-10: Inject get_now past 7-day limit → 1002, no sliding renewal
"""
import asyncio
import os
from datetime import timedelta

import pytest

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")


def _run(coro):
    """Run coroutine and restore event loop for legacy tests."""
    try:
        return asyncio.run(coro)
    finally:
        asyncio.set_event_loop(asyncio.new_event_loop())


def _password_hash() -> str:
    import bcrypt

    return bcrypt.hashpw(b"Test1234", bcrypt.gensalt(rounds=4)).decode()


def _add_user(db_session, username: str, status: str = "ACTIVE"):
    from tests.support.rows import user

    return user(db_session, username, password_hash=_password_hash(), status=status)


class TestB2RefreshRegression:
    """B2 刷新令牌回归测试。"""

    def test_ut_b2_bg_07_07_login_freeze_refresh_returns_1216(
        self, db_session, test_context
    ):
        """UT-B2-BG-07-07: Login → freeze → refresh → 1216

        用户登录成功后被冻结，刷新令牌时返回 1216 而非 1002。
        """
        from app.core.errors import BizError
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        _add_user(db_session, "freeze_after_login")
        db_session.flush()
        service = AuthService()

        tokens = _run(service.login("freeze_after_login", "Test1234"))
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        row = db_session.query(User).filter(User.username == "freeze_after_login").one()
        row.status = "FROZEN"
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            _run(service.refresh(tokens["refresh_token"]))
        assert exc_info.value.code == 1216

    def test_ut_b2_bg_07_07_login_resign_refresh_returns_1216(
        self, db_session, test_context
    ):
        """UT-B2-BG-07-07 补充: Login → resign → refresh → 1216

        用户登录成功后离职，刷新令牌时返回 1216 而非 1002。
        """
        from app.core.errors import BizError
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        _add_user(db_session, "resign_after_login")
        db_session.flush()
        service = AuthService()

        tokens = _run(service.login("resign_after_login", "Test1234"))
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        row = db_session.query(User).filter(User.username == "resign_after_login").one()
        row.status = "RESIGNED"
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            _run(service.refresh(tokens["refresh_token"]))
        assert exc_info.value.code == 1216

    def test_ut_b2_bg_07_08_replay_old_refresh_returns_1002_and_revokes_session(
        self, db_session, test_context
    ):
        """UT-B2-BG-07-08: Replaying an old refresh token returns 1002 AND the session's newly issued access and refresh tokens are both invalid.

        重放旧刷新令牌返回 1002，且该会话刚换发的 access 和 refresh 令牌都失效。
        """
        from app.core.errors import BizError
        from app.services.auth import AuthService

        person = _add_user(db_session, "replay_user")
        db_session.flush()
        service = AuthService()

        tokens = _run(service.login("replay_user", "Test1234"))
        old_refresh = tokens["refresh_token"]

        rotated = _run(service.refresh(old_refresh))
        new_access = rotated["access_token"]
        new_refresh = rotated["refresh_token"]
        assert new_refresh != old_refresh

        verified = _run(service.verify_token(new_access))
        assert verified["user_id"] == person.id

        with pytest.raises(BizError) as exc_info:
            _run(service.refresh(old_refresh))
        assert exc_info.value.code == 1002

        with pytest.raises(BizError) as exc_info:
            _run(service.verify_token(new_access))
        assert exc_info.value.code == 1002

        with pytest.raises(BizError) as exc_info:
            _run(service.refresh(new_refresh))
        assert exc_info.value.code == 1002

    def test_ut_b2_bg_07_09_rotation_logout_new_refresh_rejected(
        self, db_session, test_context
    ):
        """UT-B2-BG-07-09: Rotation → logout → new refresh_token rejected

        轮换后登出，新换发的刷新令牌也不能再用。
        """
        from app.core.errors import BizError
        from app.services.auth import AuthService

        _add_user(db_session, "logout_after_rotate")
        db_session.flush()
        service = AuthService()

        tokens = _run(service.login("logout_after_rotate", "Test1234"))
        old_refresh = tokens["refresh_token"]

        rotated = _run(service.refresh(old_refresh))
        new_access = rotated["access_token"]
        new_refresh = rotated["refresh_token"]
        assert new_refresh != old_refresh

        _run(service.logout(new_access))

        with pytest.raises(BizError) as exc_info:
            _run(service.refresh(new_refresh))
        assert exc_info.value.code == 1002

    def test_ut_b2_bg_07_10_seven_day_limit_no_sliding_renewal(
        self, db_session, test_context, fixed_time
    ):
        """UT-B2-BG-07-10: Inject get_now past 7-day limit → 1002, no sliding renewal

        注入时钟超过 7 天绝对期限后，刷新返回 1002，不做滑动续期。
        """
        from app.core.clock import get_now
        from app.core.config import get_settings
        from app.core.errors import BizError
        from app.services.auth import AuthService

        settings = get_settings()
        full_ttl = settings.jwt.refresh_token_ttl
        _add_user(db_session, "seven_day_user")
        db_session.flush()
        service = AuthService()

        start = get_now()
        fixed_time(start)

        tokens = _run(service.login("seven_day_user", "Test1234"))
        refresh_token = tokens["refresh_token"]

        near_end = start + timedelta(seconds=full_ttl - 2)
        fixed_time(near_end)
        near_result = _run(service.refresh(refresh_token))
        assert "access_token" in near_result
        new_refresh = near_result["refresh_token"]
        assert new_refresh != refresh_token

        past_end = start + timedelta(seconds=full_ttl + 1)
        fixed_time(past_end)
        with pytest.raises(BizError) as exc_info:
            _run(service.refresh(new_refresh))
        assert exc_info.value.code == 1002


class TestB2RefreshSessionMissingAndBlacklistReturns1216:
    """refresh 的 _issue_rotated_tokens 会话失效分支返回 1216（差异 c）。

    根据实现理解 v2.1 的 4 处允许差异：
    (c) refresh 里会话缺失/黑名单分支冻结离职→1216、否则 1002

    注意：这只影响 refresh，verify_token 保持 main 行为（返回 1002）。
    """

    def test_session_missing_frozen_returns_1216(self, db_session, test_context):
        """refresh 会话缺失 + 用户冻结 → 1216（差异 c）。"""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        _add_user(db_session, "session_missing_frozen")
        db_session.flush()
        service = AuthService()

        tokens = _run(service.login("session_missing_frozen", "Test1234"))
        refresh_token = tokens["refresh_token"]

        index_val = Cache.get(f"{service.REFRESH_INDEX_PREFIX}{refresh_token}")
        assert index_val
        session_id = index_val.split(":")[0]
        Cache.delete(f"{service.SESSION_PREFIX}{session_id}")

        row = db_session.query(User).filter(User.username == "session_missing_frozen").one()
        row.status = "FROZEN"
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            _run(service.refresh(refresh_token))
        assert exc_info.value.code == 1216

    def test_blacklist_resigned_returns_1216(self, db_session, test_context):
        """refresh 会话被拉黑 + 用户离职 → 1216（差异 c）。"""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        _add_user(db_session, "blacklist_resigned")
        db_session.flush()
        service = AuthService()

        tokens = _run(service.login("blacklist_resigned", "Test1234"))
        refresh_token = tokens["refresh_token"]

        index_val = Cache.get(f"{service.REFRESH_INDEX_PREFIX}{refresh_token}")
        assert index_val
        session_id = index_val.split(":")[0]
        Cache.set(f"{service.TOKEN_BLACKLIST_PREFIX}{session_id}", "1", ttl=60)

        row = db_session.query(User).filter(User.username == "blacklist_resigned").one()
        row.status = "RESIGNED"
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            _run(service.refresh(refresh_token))
        assert exc_info.value.code == 1216

    def test_session_missing_active_returns_1002(self, db_session, test_context):
        """refresh 会话缺失 + 用户正常 → 1002。"""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.services.auth import AuthService

        _add_user(db_session, "session_missing_active")
        db_session.flush()
        service = AuthService()

        tokens = _run(service.login("session_missing_active", "Test1234"))
        refresh_token = tokens["refresh_token"]

        index_val = Cache.get(f"{service.REFRESH_INDEX_PREFIX}{refresh_token}")
        assert index_val
        session_id = index_val.split(":")[0]
        Cache.delete(f"{service.SESSION_PREFIX}{session_id}")

        with pytest.raises(BizError) as exc_info:
            _run(service.refresh(refresh_token))
        assert exc_info.value.code == 1002


class TestB2VerifyTokenReturns1002:
    """verify_token 在会话失效分支返回 1002（保持 main 行为）。

    根据代码评审要求，verify_token 保持 main 的行为：
    会话缺失或被拉黑时返回 1002，不检查用户状态返回 1216。
    """

    def test_verify_session_missing_frozen_returns_1002(self, db_session, test_context):
        """verify_token 会话缺失时，返回 1002（保持 main 行为）。"""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        _add_user(db_session, "verify_missing_frozen")
        db_session.flush()
        service = AuthService()

        tokens = _run(service.login("verify_missing_frozen", "Test1234"))
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        index_val = Cache.get(f"{service.REFRESH_INDEX_PREFIX}{refresh_token}")
        assert index_val
        session_id = index_val.split(":")[0]
        Cache.delete(f"{service.SESSION_PREFIX}{session_id}")

        row = db_session.query(User).filter(User.username == "verify_missing_frozen").one()
        row.status = "FROZEN"
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            _run(service.verify_token(access_token))
        assert exc_info.value.code == 1002

    def test_verify_blacklist_resigned_returns_1002(self, db_session, test_context):
        """verify_token 会话被拉黑时，返回 1002（保持 main 行为）。"""
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        _add_user(db_session, "verify_blacklist_resigned")
        db_session.flush()
        service = AuthService()

        tokens = _run(service.login("verify_blacklist_resigned", "Test1234"))
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        index_val = Cache.get(f"{service.REFRESH_INDEX_PREFIX}{refresh_token}")
        assert index_val
        session_id = index_val.split(":")[0]
        Cache.set(f"{service.TOKEN_BLACKLIST_PREFIX}{session_id}", "1", ttl=60)

        row = db_session.query(User).filter(User.username == "verify_blacklist_resigned").one()
        row.status = "RESIGNED"
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            _run(service.verify_token(access_token))
        assert exc_info.value.code == 1002
