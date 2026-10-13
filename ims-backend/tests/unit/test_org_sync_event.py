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
