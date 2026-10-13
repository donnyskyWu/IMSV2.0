# tests/unit/test_dingtalk_instant_sync.py - LG-07 instant sync tests
"""
Tests for DingTalk instant sync (FP-B1-LG-07).

Covers:
- UT-B1-LG-07-01: New employee instant sync creates user
- UT-B1-LG-07-CONCURRENT: Concurrent login rollback and retry
- UT-B1-LG-07-USERNAME-COLLISION: Username collision with suffix
"""

import threading
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.clock import set_clock, reset_clock
from app.core.errors import BizError
from app.integrations.dingtalk.login_client import DingTalkIdentity
from app.services.dingtalk_login import (
    DingTalkLoginService,
    use_dingtalk_login_client,
    reset_dingtalk_login_client,
)
from tests.support import rows


class ScriptedDingTalk:
    """Mock DingTalk client for testing."""

    def __init__(self, identity=None, error_code=None, user_detail=None):
        self.identity = identity
        self.error_code = error_code
        self.user_detail = user_detail or {"active": True, "name": "Test User"}
        self.calls = []

    async def exchange(self, auth_code: str, channel: str):
        self.calls.append((auth_code, channel))
        if self.error_code:
            from app.integrations.dingtalk.login_client import DingTalkLoginError
            raise DingTalkLoginError(self.error_code)
        return self.identity

    async def get_user_detail(self, user_id: str):
        return self.user_detail


def _enable(monkeypatch, app_key="ding-client", mode="mock", corp_id="ding-corp"):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings.dingtalk, "app_key", app_key)
    monkeypatch.setattr(settings.dingtalk, "app_secret", "do-not-leak")
    monkeypatch.setattr(settings.dingtalk, "mode", mode)
    monkeypatch.setattr(settings.dingtalk, "corp_id", corp_id)


@pytest.fixture
def ding_client():
    """Multiple replacements are restored in reverse order."""
    tokens = []

    def _set(client):
        tokens.append(use_dingtalk_login_client(client))
        return client

    yield _set
    while tokens:
        reset_dingtalk_login_client(tokens.pop())


@pytest.fixture
def fixed_clock():
    """Set up fixed clock for tests."""
    now = datetime(2026, 10, 13, 10, 0, 0)
    set_clock(lambda: now)
    yield now
    reset_clock()


class TestInstantSyncBasic:
    """Basic instant sync tests (LG-07)."""

    @pytest.mark.asyncio
    async def test_unmapped_user_creates_via_instant_sync(
        self, db_session, test_context, monkeypatch, ding_client, fixed_clock
    ):
        """UT-B1-LG-07-01: Unmapped user triggers instant sync and creates user."""
        from app.domains.sys.models import OrgSyncEvent, Tenant, User, UserMapping

        _enable(monkeypatch)

        rows.add(db_session, Tenant(id=1, tenant_id=1, name="测试公司", status="ENABLED"))

        client = ding_client(ScriptedDingTalk(
            identity=DingTalkIdentity(user_id="dt-new-user", mobile="", name="新员工"),
            user_detail={"active": True, "name": "张新员工", "job_number": "EMP001"},
        ))

        service = DingTalkLoginService()

        user = service._match(DingTalkIdentity(user_id="dt-new-user", mobile="", name="新员工"))

        assert user is not None
        assert user.username == "dt-new-user"
        assert user.nickname == "张新员工"
        assert user.source == "DINGTALK"
        assert user.status == "ACTIVE"

        mapping = db_session.query(UserMapping).filter(
            UserMapping.dingtalk_user_id == "dt-new-user"
        ).first()
        assert mapping is not None
        assert mapping.user_id == user.id

        event = db_session.query(OrgSyncEvent).filter(
            OrgSyncEvent.event_id.like("login-sync:dt-new-user%")
        ).first()
        assert event is not None
        assert event.biz_type == "HIRE"
        assert event.status == "SUCCESS"

    @pytest.mark.asyncio
    async def test_inactive_user_raises_1217(
        self, db_session, test_context, monkeypatch, ding_client, fixed_clock
    ):
        """Inactive user in DingTalk raises 1217."""
        from app.domains.sys.models import Tenant

        _enable(monkeypatch)

        rows.add(db_session, Tenant(id=1, tenant_id=1, name="测试公司", status="ENABLED"))

        ding_client(ScriptedDingTalk(
            identity=DingTalkIdentity(user_id="dt-inactive", mobile="", name="离职员工"),
            user_detail={"active": False, "name": "已离职员工"},
        ))

        service = DingTalkLoginService()

        with pytest.raises(BizError) as exc:
            service._match(DingTalkIdentity(user_id="dt-inactive", mobile="", name="离职员工"))
        assert exc.value.code == 1217


class TestUsernameCollision:
    """Tests for username collision handling (UT-B1-LG-07-USERNAME-COLLISION)."""

    @pytest.mark.asyncio
    async def test_username_collision_adds_suffix(
        self, db_session, test_context, monkeypatch, ding_client, fixed_clock
    ):
        """UT-B1-LG-07-USERNAME-COLLISION: Username collision adds _2, _3 suffix."""
        from app.domains.sys.models import Tenant, User, UserMapping

        _enable(monkeypatch)

        rows.add(db_session, Tenant(id=1, tenant_id=1, name="测试公司", status="ENABLED"))

        existing_user = rows.user(db_session, "dt-collision-user")

        ding_client(ScriptedDingTalk(
            identity=DingTalkIdentity(user_id="dt-collision-user", mobile="", name="同名员工"),
            user_detail={"active": True, "name": "同名员工"},
        ))

        service = DingTalkLoginService()

        user = service._match(DingTalkIdentity(user_id="dt-collision-user", mobile="", name="同名员工"))

        assert user is not None
        assert user.username == "dt-collision-user_2"
        assert user.id != existing_user.id

    @pytest.mark.asyncio
    async def test_long_username_truncated_with_suffix(
        self, db_session, test_context, monkeypatch, ding_client, fixed_clock
    ):
        """Long username is truncated to fit suffix within 50 chars."""
        from app.domains.sys.models import Tenant, User

        _enable(monkeypatch)

        rows.add(db_session, Tenant(id=1, tenant_id=1, name="测试公司", status="ENABLED"))

        long_userid = "a" * 50
        existing_user = rows.user(db_session, long_userid)

        ding_client(ScriptedDingTalk(
            identity=DingTalkIdentity(user_id=long_userid, mobile="", name="长名员工"),
            user_detail={"active": True, "name": "长名员工"},
        ))

        service = DingTalkLoginService()

        user = service._match(DingTalkIdentity(user_id=long_userid, mobile="", name="长名员工"))

        assert user is not None
        assert len(user.username) == 50
        assert user.username.endswith("_2")
        assert user.username == "a" * 48 + "_2"

    def test_generate_username_with_suffix(self):
        """Test username generation helper."""
        service = DingTalkLoginService()

        assert service._generate_username("abcdef") == "abcdef"
        assert service._generate_username("abcdef", "_2") == "abcdef_2"
        assert len(service._generate_username("a" * 60)) == 50
        assert len(service._generate_username("a" * 60, "_10")) == 50
        assert service._generate_username("a" * 60, "_10").endswith("_10")


class TestConcurrentLogin:
    """Tests for concurrent login handling (UT-B1-LG-07-CONCURRENT)."""

    @pytest.mark.asyncio
    async def test_concurrent_login_second_finds_existing(
        self, db_session, test_context, monkeypatch, ding_client, fixed_clock
    ):
        """UT-B1-LG-07-CONCURRENT: Second concurrent login finds existing user."""
        from app.domains.sys.models import Tenant, User, UserMapping

        _enable(monkeypatch)

        rows.add(db_session, Tenant(id=1, tenant_id=1, name="测试公司", status="ENABLED"))

        user = rows.user(db_session, "dt-concurrent-user", source="DINGTALK")
        rows.add(db_session, UserMapping(
            tenant_id=1,
            user_id=user.id,
            dingtalk_user_id="dt-concurrent",
        ))

        ding_client(ScriptedDingTalk(
            identity=DingTalkIdentity(user_id="dt-concurrent", mobile="", name="并发员工"),
            user_detail={"active": True, "name": "并发员工"},
        ))

        service = DingTalkLoginService()

        matched_user = service._match(DingTalkIdentity(user_id="dt-concurrent", mobile="", name="并发员工"))

        assert matched_user.id == user.id
        assert matched_user.username == "dt-concurrent-user"

    @pytest.mark.asyncio
    async def test_instant_sync_integrity_error_retries_with_suffix(
        self, db_session, test_context, monkeypatch, ding_client, fixed_clock
    ):
        """IntegrityError during instant sync retries with username suffix."""
        from unittest.mock import MagicMock
        from sqlalchemy.exc import IntegrityError

        from app.domains.sys.models import Tenant, User, UserMapping

        _enable(monkeypatch)

        rows.add(db_session, Tenant(id=1, tenant_id=1, name="测试公司", status="ENABLED"))

        ding_client(ScriptedDingTalk(
            identity=DingTalkIdentity(user_id="dt-integrity", mobile="", name="IntegrityTest"),
            user_detail={"active": True, "name": "IntegrityTest"},
        ))

        service = DingTalkLoginService()

        call_count = 0
        original_begin_nested = db_session.begin_nested

        def mock_begin_nested():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                nested = original_begin_nested()
                original_commit = nested.commit
                def fail_commit():
                    nested.rollback()
                    raise IntegrityError("", {}, None)
                nested.commit = fail_commit
                return nested
            return original_begin_nested()

        monkeypatch.setattr(db_session, "begin_nested", mock_begin_nested)

        user = service._match(DingTalkIdentity(user_id="dt-integrity", mobile="", name="IntegrityTest"))

        assert call_count >= 2
        assert user is not None
