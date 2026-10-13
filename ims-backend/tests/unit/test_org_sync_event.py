# tests/unit/test_org_sync_event.py - OrgSyncEventService tests
"""
Unit tests for organization sync event processing.

Tests:
- Event reception and idempotency
- Event processing and status transitions
- Out-of-order event skipping (stale events)
- Retry and replay logic
- MAX_RETRIES -> DEAD transition
"""

from datetime import datetime, timedelta

import pytest

from app.core.clock import reset_clock, set_clock
from app.core.errors import BizError
from app.services.org_sync_event import MAX_RETRIES, OrgSyncEventService
from tests.support import rows


@pytest.fixture
def service():
    """Create OrgSyncEventService instance."""
    return OrgSyncEventService()


@pytest.fixture
def fixed_clock():
    """Set up fixed clock for tests."""
    now = datetime(2026, 10, 13, 10, 0, 0)
    set_clock(lambda: now)
    yield now
    reset_clock()


class TestEventReception:
    """Test event reception and idempotency."""

    @pytest.mark.asyncio
    async def test_receive_new_event(self, db_session, test_context, service, fixed_clock):
        """New event is stored with PENDING status."""
        result = await service.receive_event(
            tenant_id=1,
            event_id="evt-001",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload='{"test": 1}',
            biz_type="HIRE",
            subject_name="张三",
        )

        assert result["eventId"] == "evt-001"
        assert result["status"] == "PENDING"
        assert result["eventType"] == "user_add_org"
        assert result["bizType"] == "HIRE"
        assert result["subjectName"] == "张三"
        assert result["retryCount"] == 0

    @pytest.mark.asyncio
    async def test_receive_duplicate_event_is_idempotent(
        self, db_session, test_context, service, fixed_clock
    ):
        """Same event_id returns existing event without creating duplicate."""
        r1 = await service.receive_event(
            tenant_id=1,
            event_id="evt-dup",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload='{"v": 1}',
        )

        r2 = await service.receive_event(
            tenant_id=1,
            event_id="evt-dup",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload='{"v": 2}',
        )

        assert r1["id"] == r2["id"]
        assert r2["status"] == "PENDING"


class TestEventProcessing:
    """Test event processing and status transitions."""

    @pytest.mark.asyncio
    async def test_process_pending_event_success(
        self, db_session, test_context, service, fixed_clock
    ):
        """Processing a PENDING event transitions to SUCCESS."""
        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-proc-001",
            event_type="user_add_org",
            event_time=fixed_clock - timedelta(seconds=30),
            payload="{}",
            biz_type="HIRE",
        )
        event_id = int(received["id"])

        result = await service.process_event(event_id)

        assert result["status"] == "SUCCESS"
        assert result["retryCount"] == 0
        assert result["delaySeconds"] == 30

    @pytest.mark.asyncio
    async def test_process_nonexistent_event_raises_1504(
        self, db_session, test_context, service
    ):
        """Processing nonexistent event raises BizError 1504."""
        with pytest.raises(BizError) as exc:
            await service.process_event(999999)
        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_process_already_success_is_noop(
        self, db_session, test_context, service, fixed_clock
    ):
        """Processing an already SUCCESS event returns it without change."""
        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-success-noop",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        event_id = int(received["id"])
        await service.process_event(event_id)

        result = await service.process_event(event_id)

        assert result["status"] == "SUCCESS"


class TestStaleEventSkipping:
    """Test out-of-order (stale) event handling."""

    @pytest.mark.asyncio
    async def test_stale_user_event_skipped(
        self, db_session, test_context, service, fixed_clock
    ):
        """Event older than user's last_sync_time is SKIPPED."""
        from app.domains.sys.models import UserMapping

        user = rows.user(db_session, "sync_user")
        rows.add(
            db_session,
            UserMapping(
                tenant_id=1,
                user_id=user.id,
                dingtalk_user_id="dt-user-1",
                last_sync_time=fixed_clock,
            ),
        )

        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-stale-user",
            event_type="user_modify_org",
            event_time=fixed_clock - timedelta(minutes=5),
            payload="{}",
            biz_type="USER_UPDATE",
            subject_user_id=user.id,
        )
        event_id = int(received["id"])

        result = await service.process_event(event_id)

        assert result["status"] == "SKIPPED"

    @pytest.mark.asyncio
    async def test_stale_dept_event_skipped(
        self, db_session, test_context, service, fixed_clock
    ):
        """Event older than dept's last_sync_at is SKIPPED."""
        dept = rows.dept(db_session, "同步部门")
        dept.last_sync_at = fixed_clock
        db_session.flush()

        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-stale-dept",
            event_type="org_dept_modify",
            event_time=fixed_clock - timedelta(minutes=10),
            payload="{}",
            biz_type="DEPT_UPDATE",
            dept_id=dept.id,
        )
        event_id = int(received["id"])

        result = await service.process_event(event_id)

        assert result["status"] == "SKIPPED"

    @pytest.mark.asyncio
    async def test_newer_event_not_skipped(
        self, db_session, test_context, service, fixed_clock
    ):
        """Event newer than last_sync_time is processed normally."""
        from app.domains.sys.models import UserMapping

        user = rows.user(db_session, "newer_user")
        rows.add(
            db_session,
            UserMapping(
                tenant_id=1,
                user_id=user.id,
                dingtalk_user_id="dt-user-newer",
                last_sync_time=fixed_clock - timedelta(hours=1),
            ),
        )

        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-newer",
            event_type="user_modify_org",
            event_time=fixed_clock,
            payload="{}",
            biz_type="USER_UPDATE",
            subject_user_id=user.id,
        )
        event_id = int(received["id"])

        result = await service.process_event(event_id)

        assert result["status"] == "SUCCESS"


class TestRetryLogic:
    """Test retry and DEAD transition."""

    @pytest.mark.asyncio
    async def test_manual_retry_success(
        self, db_session, test_context, service, fixed_clock
    ):
        """Manual retry of RETRYING event can succeed."""
        from app.domains.sys.models import OrgSyncEvent

        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-retry-manual",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        event_id = int(received["id"])

        session = db_session
        event = session.query(OrgSyncEvent).filter(OrgSyncEvent.id == event_id).one()
        event.status = "RETRYING"
        event.retry_count = 2
        session.flush()

        result = await service.retry_event(event_id, operator_id=1)

        assert result["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_retry_pending_event_raises_1286(
        self, db_session, test_context, service, fixed_clock
    ):
        """Retry of PENDING event raises BizError 1286."""
        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-retry-pending",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        event_id = int(received["id"])

        with pytest.raises(BizError) as exc:
            await service.retry_event(event_id)
        assert exc.value.code == 1286

    @pytest.mark.asyncio
    async def test_retry_success_event_raises_1286(
        self, db_session, test_context, service, fixed_clock
    ):
        """Retry of SUCCESS event raises BizError 1286."""
        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-retry-success",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        event_id = int(received["id"])
        await service.process_event(event_id)

        with pytest.raises(BizError) as exc:
            await service.retry_event(event_id)
        assert exc.value.code == 1286

    @pytest.mark.asyncio
    async def test_retry_dead_event_can_succeed(
        self, db_session, test_context, service, fixed_clock
    ):
        """Retry of DEAD event can succeed."""
        from app.domains.sys.models import OrgSyncEvent

        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-retry-dead",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        event_id = int(received["id"])

        session = db_session
        event = session.query(OrgSyncEvent).filter(OrgSyncEvent.id == event_id).one()
        event.status = "DEAD"
        event.retry_count = MAX_RETRIES
        session.flush()

        result = await service.retry_event(event_id)

        assert result["status"] == "SUCCESS"


class TestReplayEvents:
    """Test batch replay functionality."""

    @pytest.mark.asyncio
    async def test_replay_resets_dead_retry_count(
        self, db_session, test_context, service, fixed_clock
    ):
        """Replay resets retry_count of DEAD events to 0."""
        from app.domains.sys.models import OrgSyncEvent

        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-replay-dead",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        event_id = int(received["id"])

        session = db_session
        event = session.query(OrgSyncEvent).filter(OrgSyncEvent.id == event_id).one()
        event.status = "DEAD"
        event.retry_count = MAX_RETRIES
        session.flush()

        result = await service.replay_events(
            tenant_id=1,
            start_time=fixed_clock - timedelta(hours=1),
            end_time=fixed_clock + timedelta(hours=1),
            statuses=["DEAD"],
        )

        assert result["count"] == 1

        session.refresh(event)
        assert event.status == "PENDING"
        assert event.retry_count == 0

    @pytest.mark.asyncio
    async def test_replay_timespan_limit(
        self, db_session, test_context, service, fixed_clock
    ):
        """Replay with timespan > 7 days raises BizError."""
        with pytest.raises(BizError) as exc:
            await service.replay_events(
                tenant_id=1,
                start_time=fixed_clock - timedelta(days=8),
                end_time=fixed_clock,
                statuses=["DEAD"],
            )
        assert exc.value.code == 1001
        assert "7天" in exc.value.msg

    @pytest.mark.asyncio
    async def test_replay_invalid_status_raises(
        self, db_session, test_context, service, fixed_clock
    ):
        """Replay with invalid status raises BizError."""
        with pytest.raises(BizError) as exc:
            await service.replay_events(
                tenant_id=1,
                start_time=fixed_clock - timedelta(hours=1),
                end_time=fixed_clock,
                statuses=["SUCCESS"],
            )
        assert exc.value.code == 1001

    @pytest.mark.asyncio
    async def test_replay_empty_statuses_raises(
        self, db_session, test_context, service, fixed_clock
    ):
        """Replay with empty statuses raises BizError."""
        with pytest.raises(BizError) as exc:
            await service.replay_events(
                tenant_id=1,
                start_time=fixed_clock - timedelta(hours=1),
                end_time=fixed_clock,
                statuses=[],
            )
        assert exc.value.code == 1001


class TestReplayPreview:
    """Test replay preview functionality."""

    @pytest.mark.asyncio
    async def test_preview_returns_count(
        self, db_session, test_context, service, fixed_clock
    ):
        """Preview returns count of matching events."""
        from app.domains.sys.models import OrgSyncEvent

        for i in range(3):
            received = await service.receive_event(
                tenant_id=1,
                event_id=f"evt-preview-{i}",
                event_type="user_add_org",
                event_time=fixed_clock,
                payload="{}",
            )
            session = db_session
            event = session.query(OrgSyncEvent).filter(
                OrgSyncEvent.id == int(received["id"])
            ).one()
            event.status = "DEAD"
            session.flush()

        result = await service.get_replay_preview(
            tenant_id=1,
            start_time=fixed_clock - timedelta(hours=1),
            end_time=fixed_clock + timedelta(hours=1),
            statuses=["DEAD"],
        )

        assert result["count"] == 3


class TestGetEvent:
    """Test get event detail."""

    @pytest.mark.asyncio
    async def test_get_event_with_attempts(
        self, db_session, test_context, service, fixed_clock
    ):
        """Get event includes attempts list."""
        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-get-detail",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        event_id = int(received["id"])
        await service.process_event(event_id)

        result = await service.get_event(event_id, tenant_id=1)

        assert result is not None
        assert result["eventId"] == "evt-get-detail"
        assert "attempts" in result
        assert len(result["attempts"]) == 1
        assert result["attempts"][0]["result"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_get_nonexistent_event(self, db_session, test_context, service):
        """Get nonexistent event returns None."""
        result = await service.get_event(999999, tenant_id=1)
        assert result is None


class TestGetEventsPage:
    """Test paginated event list."""

    @pytest.mark.asyncio
    async def test_get_events_page_basic(
        self, db_session, test_context, service, fixed_clock
    ):
        """Get events page returns paginated results."""
        for i in range(5):
            await service.receive_event(
                tenant_id=1,
                event_id=f"evt-page-{i}",
                event_type="user_add_org",
                event_time=fixed_clock - timedelta(minutes=i),
                payload="{}",
                subject_name=f"用户{i}",
            )

        result = await service.get_events_page(
            tenant_id=1,
            page_no=1,
            page_size=3,
        )

        assert result["total"] == 5
        assert len(result["list"]) == 3
        assert result["pageNo"] == 1
        assert result["pageSize"] == 3

    @pytest.mark.asyncio
    async def test_get_events_page_with_keyword(
        self, db_session, test_context, service, fixed_clock
    ):
        """Get events page filters by keyword."""
        await service.receive_event(
            tenant_id=1,
            event_id="evt-kw-match",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
            subject_name="张三丰",
        )
        await service.receive_event(
            tenant_id=1,
            event_id="evt-kw-nomatch",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
            subject_name="李四",
        )

        result = await service.get_events_page(
            tenant_id=1,
            keyword="三丰",
        )

        assert result["total"] == 1
        assert result["list"][0]["subjectName"] == "张三丰"

    @pytest.mark.asyncio
    async def test_get_events_page_with_status_filter(
        self, db_session, test_context, service, fixed_clock
    ):
        """Get events page filters by status."""
        from app.domains.sys.models import OrgSyncEvent

        for i, status in enumerate(["PENDING", "SUCCESS", "DEAD"]):
            received = await service.receive_event(
                tenant_id=1,
                event_id=f"evt-status-{i}",
                event_type="user_add_org",
                event_time=fixed_clock,
                payload="{}",
            )
            session = db_session
            event = session.query(OrgSyncEvent).filter(
                OrgSyncEvent.id == int(received["id"])
            ).one()
            event.status = status
            session.flush()

        result = await service.get_events_page(
            tenant_id=1,
            statuses=["DEAD"],
        )

        assert result["total"] == 1
        assert result["list"][0]["status"] == "DEAD"


class TestApplyBizEvents:
    """Drive each biz_type, including the early-return side of each check."""

    async def _receive(self, service, clock, **kwargs):
        payload = kwargs.pop("payload", "{}")
        return await service.receive_event(
            tenant_id=kwargs.pop("tenant_id", 1),
            event_id=kwargs.pop("event_id"),
            event_type=kwargs.pop("event_type", "user_modify_org"),
            event_time=kwargs.pop("event_time", clock),
            payload=payload,
            biz_type=kwargs.pop("biz_type", None),
            subject_name=kwargs.pop("subject_name", None),
        )

    @pytest.mark.asyncio
    async def test_hire_creates_and_skips(self, db_session, test_context, service, fixed_clock):
        from app.domains.sys.models import OrgSyncEvent, User, UserMapping

        created = await self._receive(
            service, fixed_clock, event_id="hire-new", biz_type="HIRE",
            payload='{"dingtalk_user_id":"dt-hire-1","name":"新同事"}',
        )
        result = await service.process_event(int(created["id"]))
        assert result["status"] == "SUCCESS"
        user = db_session.query(User).filter(User.username == "dt-hire-1").one()
        assert user.nickname == "新同事"
        assert user.source == "DINGTALK"

        holder = rows.user(db_session, "hire-holder")
        rows.add(db_session, UserMapping(
            tenant_id=1, user_id=holder.id, dingtalk_user_id="dt-hire-dup",
        ))
        dup = await self._receive(
            service, fixed_clock, event_id="hire-dup", biz_type="HIRE",
            payload='{"dingtalk_user_id":"dt-hire-dup","name":"重复"}',
        )
        assert (await service.process_event(int(dup["id"])))["status"] == "SUCCESS"
        assert db_session.query(User).filter(User.username == "dt-hire-dup").count() == 0

        via_userid = await self._receive(
            service, fixed_clock, event_id="hire-userid", biz_type="HIRE",
            payload='{"userid":"dt-hire-userid","name":"工号同事"}',
        )
        assert (await service.process_event(int(via_userid["id"])))["status"] == "SUCCESS"
        assert db_session.query(User).filter(User.username == "dt-hire-userid").count() == 1
        again = await self._receive(
            service, fixed_clock, event_id="hire-userid-again", biz_type="HIRE",
            payload='{"userid":"dt-hire-userid"}',
        )
        assert (await service.process_event(int(again["id"])))["status"] == "SUCCESS"
        assert db_session.query(User).filter(User.username == "dt-hire-userid").count() == 1

        for event_id, payload, subject in (
            ("hire-empty", "", None),
            ("hire-noid", '{"name":"无名"}', None),
            ("hire-bound", '{"dingtalk_user_id":"dt-x"}', holder.id),
        ):
            received = await self._receive(
                service, fixed_clock, event_id=event_id, biz_type="HIRE", payload=payload or "{}",
            )
            row = db_session.query(OrgSyncEvent).filter(OrgSyncEvent.id == int(received["id"])).one()
            row.payload = payload
            if subject is not None:
                row.subject_user_id = subject
            db_session.flush()
            assert (await service.process_event(row.id))["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_resign_and_user_update(self, db_session, test_context, service, fixed_clock):
        from app.domains.sys.models import OrgSyncEvent, UserMapping
        from app.services.user import USER_EVENTS

        person = rows.user(db_session, "resign-me")
        rows.add(db_session, UserMapping(
            tenant_id=1, user_id=person.id, dingtalk_user_id="dt-resign",
        ))
        USER_EVENTS.clear()
        received = await self._receive(
            service, fixed_clock, event_id="resign-1", biz_type="RESIGN",
        )
        row = db_session.get(OrgSyncEvent, int(received["id"]))
        row.subject_user_id = person.id
        db_session.flush()
        await service.process_event(row.id)
        db_session.refresh(person)
        assert person.status == "RESIGNED"
        assert any(item["user_id"] == person.id for item in USER_EVENTS)

        again = await self._receive(service, fixed_clock, event_id="resign-2", biz_type="RESIGN")
        again_row = db_session.get(OrgSyncEvent, int(again["id"]))
        again_row.subject_user_id = person.id
        db_session.flush()
        await service.process_event(again_row.id)

        missing = await self._receive(service, fixed_clock, event_id="resign-miss", biz_type="RESIGN")
        missing_row = db_session.get(OrgSyncEvent, int(missing["id"]))
        missing_row.subject_user_id = 999991
        db_session.flush()
        await service.process_event(missing_row.id)

        bare = await self._receive(service, fixed_clock, event_id="resign-bare", biz_type="RESIGN")
        await service.process_event(int(bare["id"]))

        editor = rows.user(db_session, "edit-me", email=None)
        updated = await self._receive(
            service, fixed_clock, event_id="upd-1", biz_type="USER_UPDATE",
            payload='{"name":"改名","mobile":"13800001111","email":"a@b.c","job_number":"E1"}',
        )
        upd = db_session.get(OrgSyncEvent, int(updated["id"]))
        upd.subject_user_id = editor.id
        db_session.flush()
        await service.process_event(upd.id)
        db_session.refresh(editor)
        assert editor.nickname == "改名"
        assert editor.email == "a@b.c"
        assert editor.emp_no == "E1"
        assert editor.mobile_hash

        for event_id, subject, payload in (
            ("upd-miss", 999992, "{}"),
            ("upd-empty", editor.id, ""),
            ("upd-none", None, "{}"),
        ):
            got = await self._receive(
                service, fixed_clock, event_id=event_id, biz_type="USER_UPDATE", payload=payload or "{}",
            )
            event = db_session.get(OrgSyncEvent, int(got["id"]))
            event.payload = payload
            event.subject_user_id = subject
            db_session.flush()
            await service.process_event(event.id)

    @pytest.mark.asyncio
    async def test_transfer_and_departments(self, db_session, test_context, service, fixed_clock):
        from app.domains.sys.models import Dept, OrgSyncEvent, User, UserDept

        parent = rows.dept(db_session, "父部门", ding="ding-parent", source="DINGTALK")
        child = rows.dept(db_session, "子部门", parent=parent, ding="ding-child", source="DINGTALK")
        person = rows.user(db_session, "mover")
        rows.link(db_session, person.id, parent.id, source="DINGTALK")

        moved = await self._receive(
            service, fixed_clock, event_id="xfer-1", biz_type="TRANSFER",
            payload='{"dept_dingtalk_ids":["ding-child","ding-missing"]}',
        )
        event = db_session.get(OrgSyncEvent, int(moved["id"]))
        event.subject_user_id = person.id
        db_session.flush()
        await service.process_event(event.id)
        db_session.refresh(person)
        assert person.main_dept_id == child.id
        assert db_session.query(UserDept).filter(UserDept.user_id == person.id).count() == 1

        for event_id, subject, payload in (
            ("xfer-nodept", person.id, '{"dept_dingtalk_ids":["nope"]}'),
            ("xfer-empty", person.id, '{"dept_dingtalk_ids":[]}'),
            ("xfer-nopayload", person.id, ""),
            ("xfer-miss", 999993, '{"dept_dingtalk_ids":["ding-child"]}'),
            ("xfer-nosub", None, "{}"),
        ):
            got = await self._receive(
                service, fixed_clock, event_id=event_id, biz_type="TRANSFER", payload=payload or "{}",
            )
            row = db_session.get(OrgSyncEvent, int(got["id"]))
            row.payload = payload
            row.subject_user_id = subject
            db_session.flush()
            await service.process_event(row.id)

        created = await self._receive(
            service, fixed_clock, event_id="dept-new", biz_type="DEPT_CREATE",
            payload='{"dingtalk_dept_id":"ding-new","name":"新建","parent_dingtalk_id":"ding-parent"}',
        )
        await service.process_event(int(created["id"]))
        created_dept = db_session.query(Dept).filter(Dept.dingtalk_dept_id == "ding-new").one()
        assert created_dept.parent_id == parent.id
        assert created_dept.path.endswith(f"{created_dept.id}/")

        again = await self._receive(
            service, fixed_clock, event_id="dept-again", biz_type="DEPT_CREATE",
            payload='{"dingtalk_dept_id":"ding-new","name":"新建"}',
        )
        await service.process_event(int(again["id"]))

        orphan = await self._receive(
            service, fixed_clock, event_id="dept-orphan", biz_type="DEPT_CREATE",
            payload='{"dept_id":"ding-orphan"}',
        )
        await service.process_event(int(orphan["id"]))

        for event_id, payload in (
            ("dept-nopayload", ""),
            ("dept-noid", '{"name":"缺id"}'),
        ):
            got = await self._receive(
                service, fixed_clock, event_id=event_id, biz_type="DEPT_CREATE", payload=payload or "{}",
            )
            row = db_session.get(OrgSyncEvent, int(got["id"]))
            row.payload = payload
            db_session.flush()
            await service.process_event(row.id)

        renamed = await self._receive(
            service, fixed_clock, event_id="dept-ren", biz_type="DEPT_UPDATE",
            payload='{"name":"父部门改名","parent_dingtalk_id":"ding-child"}',
        )
        ren = db_session.get(OrgSyncEvent, int(renamed["id"]))
        ren.dept_id = parent.id
        db_session.flush()
        await service.process_event(ren.id)
        db_session.refresh(parent)
        assert parent.name == "父部门改名"
        assert parent.parent_id == child.id

        by_payload = await self._receive(
            service, fixed_clock, event_id="dept-by-ding", biz_type="DEPT_UPDATE",
            payload='{"dingtalk_dept_id":"ding-orphan","name":"孤儿改名"}',
        )
        await service.process_event(int(by_payload["id"]))

        for event_id, dept_id, payload in (
            ("dept-upd-miss", 999994, '{"name":"x"}'),
            ("dept-upd-empty", parent.id, ""),
            ("dept-upd-noid", None, '{"name":"x"}'),
        ):
            got = await self._receive(
                service, fixed_clock, event_id=event_id, biz_type="DEPT_UPDATE", payload=payload or "{}",
            )
            row = db_session.get(OrgSyncEvent, int(got["id"]))
            row.payload = payload
            row.dept_id = dept_id
            db_session.flush()
            await service.process_event(row.id)

        deleted = await self._receive(
            service, fixed_clock, event_id="dept-del", biz_type="DEPT_DELETE", payload="{}",
        )
        dele = db_session.get(OrgSyncEvent, int(deleted["id"]))
        dele.dept_id = created_dept.id
        # Create stamps last_sync_at with the same clock, so an equal event_time is stale.
        dele.event_time = fixed_clock + timedelta(seconds=1)
        db_session.flush()
        await service.process_event(dele.id)
        db_session.refresh(created_dept)
        assert created_dept.deleted == created_dept.id
        assert created_dept.status == "DISABLED"

        by_ding = await self._receive(
            service, fixed_clock, event_id="dept-del-ding", biz_type="DEPT_DELETE",
            payload='{"dept_id":"ding-orphan"}',
        )
        await service.process_event(int(by_ding["id"]))
        gone = db_session.query(Dept).filter(Dept.dingtalk_dept_id == "ding-orphan").one()
        assert gone.deleted == gone.id

        for event_id, dept_id, payload in (
            ("dept-del-gone", created_dept.id, "{}"),
            ("dept-del-noid", None, '{"name":"x"}'),
        ):
            got = await self._receive(
                service, fixed_clock, event_id=event_id, biz_type="DEPT_DELETE", payload=payload,
            )
            row = db_session.get(OrgSyncEvent, int(got["id"]))
            row.dept_id = dept_id
            row.payload = payload
            db_session.flush()
            await service.process_event(row.id)

        unknown = await self._receive(
            service, fixed_clock, event_id="biz-unknown", biz_type="OTHER",
        )
        assert (await service.process_event(int(unknown["id"])))["status"] == "SUCCESS"
        assert db_session.query(User).filter(User.username == "mover").count() == 1


class TestRemainingBranches:
    """Cover the false side of checks the happy-path tests leave open."""

    @pytest.mark.asyncio
    async def test_page_filters_partial_updates_and_lookup_misses(
        self, db_session, test_context, service, fixed_clock
    ):
        from app.domains.sys.models import Dept, OrgSyncEvent, UserMapping

        bare = await service.receive_event(
            tenant_id=1,
            event_id="evt-no-time",
            event_type="user_modify_org",
            event_time=fixed_clock,
            payload="not-json",
            biz_type="HIRE",
        )
        row = db_session.get(OrgSyncEvent, int(bare["id"]))
        row.event_time = None
        db_session.flush()
        assert (await service.process_event(row.id))["status"] == "SUCCESS"

        listed = await service.receive_event(
            tenant_id=1,
            event_id="evt-list-filters",
            event_type="user_leave_org",
            event_time=fixed_clock,
            payload="[1, 2]",
            biz_type="HIRE",
            dept_id=7,
        )
        listed_row = db_session.get(OrgSyncEvent, int(listed["id"]))
        listed_row.processed_time = fixed_clock
        db_session.flush()
        await service.process_event(listed_row.id)
        page = await service.get_events_page(
            tenant_id=1,
            dept_id=7,
            event_types=["user_leave_org"],
            start_time=fixed_clock - timedelta(minutes=1),
            end_time=fixed_clock + timedelta(minutes=1),
            sort_by="processedTime",
            sort_order="asc",
        )
        assert page["total"] == 1

        with pytest.raises(BizError) as span:
            await service.get_replay_preview(
                1, fixed_clock - timedelta(days=8), fixed_clock, ["DEAD"],
            )
        assert span.value.code == 1001
        with pytest.raises(BizError):
            await service.get_replay_preview(
                1, fixed_clock - timedelta(hours=1), fixed_clock, [],
            )

        retrying = await service.receive_event(
            tenant_id=1,
            event_id="evt-replay-retrying",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        retrying_row = db_session.get(OrgSyncEvent, int(retrying["id"]))
        retrying_row.status = "RETRYING"
        retrying_row.retry_count = 2
        db_session.flush()
        replayed = await service.replay_events(
            tenant_id=1,
            start_time=fixed_clock - timedelta(hours=1),
            end_time=fixed_clock + timedelta(hours=1),
            statuses=["RETRYING"],
        )
        assert replayed["count"] == 1
        db_session.refresh(retrying_row)
        assert retrying_row.retry_count == 2
        assert retrying_row.status == "PENDING"

        editor = rows.user(db_session, "partial-edit")
        updated = await service.receive_event(
            tenant_id=1,
            event_id="upd-blank",
            event_type="user_modify_org",
            event_time=fixed_clock,
            payload="{}",
            biz_type="USER_UPDATE",
        )
        upd = db_session.get(OrgSyncEvent, int(updated["id"]))
        upd.subject_user_id = editor.id
        db_session.flush()
        await service.process_event(upd.id)

        resigned = rows.user(db_session, "already-gone", status="RESIGNED")
        resign = await service.receive_event(
            tenant_id=1,
            event_id="resign-again",
            event_type="user_leave_org",
            event_time=fixed_clock,
            payload="{}",
            biz_type="RESIGN",
        )
        resign_row = db_session.get(OrgSyncEvent, int(resign["id"]))
        resign_row.subject_user_id = resigned.id
        db_session.flush()
        await service.process_event(resign_row.id)

        parent = rows.dept(db_session, "对照父", ding="ding-keep", source="DINGTALK")
        child = rows.dept(db_session, "对照子", parent=parent, ding="ding-keep-child", source="DINGTALK")
        mover = rows.user(db_session, "mapped-mover")
        rows.add(db_session, UserMapping(
            tenant_id=1, user_id=mover.id, dingtalk_user_id="dt-mapped-mover",
        ))
        moved = await service.receive_event(
            tenant_id=1,
            event_id="xfer-mapped",
            event_type="user_modify_org",
            event_time=fixed_clock,
            payload='{"dept_dingtalk_ids":["ding-keep-child"]}',
            biz_type="TRANSFER",
        )
        moved_row = db_session.get(OrgSyncEvent, int(moved["id"]))
        moved_row.subject_user_id = mover.id
        db_session.flush()
        await service.process_event(moved_row.id)

        created = await service.receive_event(
            tenant_id=1,
            event_id="dept-no-parent",
            event_type="org_dept_create",
            event_time=fixed_clock,
            payload='{"dingtalk_dept_id":"ding-rootish","name":"无父","parent_dingtalk_id":"missing-parent"}',
            biz_type="DEPT_CREATE",
        )
        await service.process_event(int(created["id"]))
        rootish = db_session.query(Dept).filter(Dept.dingtalk_dept_id == "ding-rootish").one()
        assert rootish.parent_id == 0

        same = await service.receive_event(
            tenant_id=1,
            event_id="dept-same",
            event_type="org_dept_modify",
            event_time=fixed_clock,
            payload='{"name":"对照子","parent_dingtalk_id":"ding-keep"}',
            biz_type="DEPT_UPDATE",
        )
        same_row = db_session.get(OrgSyncEvent, int(same["id"]))
        same_row.dept_id = child.id
        db_session.flush()
        await service.process_event(same_row.id)
        db_session.refresh(child)
        assert child.name == "对照子"
        assert child.parent_id == parent.id

        for event_id, payload in (
            ("dept-upd-nobody", ""),
            ("dept-upd-unknown", '{"dingtalk_dept_id":"no-dept","name":"x"}'),
        ):
            got = await service.receive_event(
                tenant_id=1,
                event_id=event_id,
                event_type="org_dept_modify",
                event_time=fixed_clock,
                payload=payload or "{}",
                biz_type="DEPT_UPDATE",
            )
            event = db_session.get(OrgSyncEvent, int(got["id"]))
            event.payload = payload
            event.dept_id = None
            db_session.flush()
            await service.process_event(event.id)

        for event_id, payload in (
            ("dept-del-nobody", ""),
            ("dept-del-unknown", '{"dingtalk_dept_id":"no-dept"}'),
        ):
            got = await service.receive_event(
                tenant_id=1,
                event_id=event_id,
                event_type="org_dept_remove",
                event_time=fixed_clock,
                payload=payload or "{}",
                biz_type="DEPT_DELETE",
            )
            event = db_session.get(OrgSyncEvent, int(got["id"]))
            event.payload = payload
            event.dept_id = None
            db_session.flush()
            await service.process_event(event.id)

    @pytest.mark.asyncio
    async def test_process_failure_becomes_retrying_then_dead(
        self, db_session, test_context, service, fixed_clock
    ):
        from app.domains.sys.models import OrgSyncEvent

        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-boom",
            event_type="user_add_org",
            event_time=None,
            payload="{}",
        )
        event_id = int(received["id"])

        async def boom(_event):
            raise RuntimeError("boom")

        service._apply_event = boom
        with pytest.raises(RuntimeError):
            await service.process_event(event_id)
        row = db_session.get(OrgSyncEvent, event_id)
        assert row.status == "RETRYING"

        row.retry_count = MAX_RETRIES - 1
        db_session.flush()
        with pytest.raises(RuntimeError):
            await service.process_event(event_id)
        db_session.refresh(row)
        assert row.status == "DEAD"

    @pytest.mark.asyncio
    async def test_retry_missing_and_apply_failure(
        self, db_session, test_context, service, fixed_clock
    ):
        from app.domains.sys.models import OrgSyncEvent

        with pytest.raises(BizError) as missing:
            await service.retry_event(999999)
        assert missing.value.code == 1504

        received = await service.receive_event(
            tenant_id=1,
            event_id="evt-retry-blank-time",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        row = db_session.get(OrgSyncEvent, int(received["id"]))
        row.status = "RETRYING"
        row.event_time = None
        db_session.flush()
        result = await service.retry_event(row.id)
        assert result["status"] == "SUCCESS"

        failed = await service.receive_event(
            tenant_id=1,
            event_id="evt-retry-boom",
            event_type="user_add_org",
            event_time=fixed_clock,
            payload="{}",
        )
        failed_row = db_session.get(OrgSyncEvent, int(failed["id"]))
        failed_row.status = "RETRYING"
        failed_row.retry_count = MAX_RETRIES - 1
        db_session.flush()

        async def boom(_event):
            raise RuntimeError("retry-boom")

        service._apply_event = boom
        with pytest.raises(RuntimeError):
            await service.retry_event(failed_row.id)
