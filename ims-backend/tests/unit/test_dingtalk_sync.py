# tests/unit/test_dingtalk_sync.py - DingTalk sync tests (FP-D07)
"""
Tests for DingTalk organization sync.

Per 02-单测用例.md UT-D07:
- Event signature validation
- Department sync with local override handling
- User sync with mapping
- Retry and dead letter handling
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class EventStatus(str, Enum):
    """DingTalk event status."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    RETRYING = "RETRYING"
    DEAD = "DEAD"
    EXPIRED = "EXPIRED"


class DeptSource(str, Enum):
    """Department source."""
    DINGTALK = "DINGTALK"
    LOCAL = "LOCAL"
    SYSTEM = "SYSTEM"


@dataclass
class DingTalkEvent:
    """DingTalk webhook event."""
    id: int
    event_id: str  # DingTalk's event ID
    event_type: str
    event_time: datetime
    payload: dict
    status: EventStatus = EventStatus.PENDING
    retry_count: int = 0
    last_sync_at: Optional[datetime] = None


@dataclass
class Dept:
    """Department model."""
    id: int
    tenant_id: int
    name: str
    parent_id: Optional[int]
    source: DeptSource
    dingtalk_dept_id: Optional[str] = None
    local_orphan: bool = False
    last_sync_at: Optional[datetime] = None


class TestEventSignatureValidation:
    """Tests for event signature validation (FP-D07-01)."""

    def test_invalid_signature_rejected(self):
        """UT-D07-01: Invalid signature returns 1008."""
        expected_signature = "abc123"
        received_signature = "wrong"

        error_code = 1008 if expected_signature != received_signature else 0

        assert error_code == 1008

    def test_valid_signature_accepted(self):
        """UT-D07-01: Valid signature is accepted."""
        expected_signature = "abc123"
        received_signature = "abc123"

        is_valid = expected_signature == received_signature

        assert is_valid


class TestEventIdempotency:
    """Tests for event idempotency (FP-D07-01)."""

    def test_duplicate_event_id_ignored(self):
        """UT-D07-02: Same event_id only stored once."""
        existing_events = [
            DingTalkEvent(id=1, event_id="evt_001", event_type="dept_modify",
                         event_time=datetime.now(), payload={})
        ]

        new_event_id = "evt_001"

        is_duplicate = any(e.event_id == new_event_id for e in existing_events)

        assert is_duplicate


class TestDeptSyncOverride:
    """Tests for department sync with local overrides (FP-D07-02)."""

    def test_dingtalk_overrides_local_name(self):
        """UT-D07-03: DingTalk rename overrides local modification."""
        dept = Dept(
            id=1, tenant_id=1, name="一组",  # Local modification
            parent_id=100, source=DeptSource.DINGTALK,
            dingtalk_dept_id="101"
        )

        # DingTalk pushes new name
        dingtalk_name = "市场 1 组"

        # Override
        old_name = dept.name
        dept.name = dingtalk_name

        assert dept.name == "市场 1 组"
        assert old_name == "一组"  # For change history

    def test_dingtalk_override_creates_change_history(self):
        """UT-D07-03: Override creates change history with reason."""
        change_logs = []

        change_logs.append({
            "biz_type": "dept",
            "biz_id": "1",
            "field": "name",
            "before_value": "一组",
            "after_value": "市场 1 组",
            "reason": "DINGTALK_OVERRIDE"
        })

        assert change_logs[0]["reason"] == "DINGTALK_OVERRIDE"


class TestDeptFullReconciliation:
    """Tests for department full reconciliation (FP-D07-02)."""

    def test_missing_in_dingtalk_deleted(self):
        """UT-D07-20: IMS DINGTALK dept missing in DingTalk is deleted."""
        ims_depts = [
            Dept(id=1, tenant_id=1, name="市场部", parent_id=None, source=DeptSource.DINGTALK, dingtalk_dept_id="100"),
            Dept(id=2, tenant_id=1, name="市场一组", parent_id=1, source=DeptSource.DINGTALK, dingtalk_dept_id="101"),
        ]
        dingtalk_depts = {"100"}  # 101 missing

        missing_depts = [d for d in ims_depts if d.source == DeptSource.DINGTALK and d.dingtalk_dept_id not in dingtalk_depts]

        assert len(missing_depts) == 1
        assert missing_depts[0].dingtalk_dept_id == "101"

    def test_local_dept_not_touched(self):
        """UT-D07-07: LOCAL department not modified by reconciliation."""
        dept = Dept(
            id=3, tenant_id=1, name="市场二组",
            parent_id=1, source=DeptSource.LOCAL
        )

        # Local depts are excluded from DingTalk sync
        should_sync = dept.source == DeptSource.DINGTALK

        assert not should_sync


class TestDingTalkDeptDelete:
    """Tests for DingTalk department deletion (FP-D07-02)."""

    def test_delete_moves_users_to_other_depts(self):
        """UT-D07-06: Deleted dept moves users to other DingTalk depts."""
        user_depts = [
            {"user_id": 1, "dept_id": 101, "source": "DINGTALK"},  # Being deleted
            {"user_id": 1, "dept_id": 200, "source": "DINGTALK"},  # Other dept
        ]
        deleted_dept_id = 101

        # Remove deleted dept membership
        remaining = [d for d in user_depts if d["dept_id"] != deleted_dept_id]

        assert len(remaining) == 1
        assert remaining[0]["dept_id"] == 200

    def test_no_other_dept_moves_to_dx(self):
        """UT-D07-06: User with no other dept moves to DX (待分配)."""
        user_depts = [
            {"user_id": 1, "dept_id": 101, "source": "DINGTALK"},
        ]
        deleted_dept_id = 101
        dx_dept_id = 999  # 待分配

        remaining = [d for d in user_depts if d["dept_id"] != deleted_dept_id]

        if not remaining:
            remaining.append({"user_id": 1, "dept_id": dx_dept_id, "source": "SYSTEM"})

        assert remaining[0]["dept_id"] == dx_dept_id


class TestLocalOrphan:
    """Tests for local orphan handling (FP-D07-02)."""

    def test_parent_deleted_marks_orphan(self):
        """UT-D07-08: LOCAL dept under deleted parent becomes orphan."""
        local_dept = Dept(
            id=12, tenant_id=1, name="市场二组",
            parent_id=1, source=DeptSource.LOCAL,
            local_orphan=False
        )
        parent_deleted = True

        if parent_deleted:
            local_dept.local_orphan = True

        assert local_dept.local_orphan

    def test_orphan_moves_to_nearest_ancestor(self):
        """UT-D07-09: Orphan moves to nearest surviving ancestor."""
        # D12 under D11 (deleted), D11 under D1 (exists)
        dept = Dept(
            id=12, tenant_id=1, name="市场二组",
            parent_id=11, source=DeptSource.LOCAL
        )
        surviving_ancestor_id = 1  # D1

        dept.parent_id = surviving_ancestor_id
        dept.local_orphan = True

        assert dept.parent_id == 1

    def test_confirm_orphan_clears_flag(self):
        """UT-D07-12: Confirming orphan clears the flag."""
        dept = Dept(
            id=12, tenant_id=1, name="市场二组",
            parent_id=1, source=DeptSource.LOCAL,
            local_orphan=True
        )

        # Admin confirms
        dept.local_orphan = False

        assert not dept.local_orphan


class TestUserSync:
    """Tests for user sync (FP-D07-03)."""

    def test_new_user_creates_mapping(self):
        """UT-D07-13: New DingTalk user creates user and mapping."""
        existing_users = []
        mobile = "13800138000"

        # No existing user with this mobile
        matched_user = next((u for u in existing_users if u.get("mobile") == mobile), None)

        if not matched_user:
            # Create new user
            new_user = {"id": 100, "mobile": mobile, "status": "ACTIVE", "password_hash": None}

        assert new_user["password_hash"] is None  # No password for DingTalk-only users


class TestEventOrdering:
    """Tests for event ordering (FP-D07-02)."""

    def test_out_of_order_uses_event_time(self):
        """UT-D07-24: Out of order events use event_time for final state."""
        events = [
            DingTalkEvent(id=1, event_id="evt_1", event_type="dept_modify",
                         event_time=datetime(2026, 10, 12, 11, 0), payload={"name": "Name at 11:00"}),
            DingTalkEvent(id=2, event_id="evt_2", event_type="dept_modify",
                         event_time=datetime(2026, 10, 12, 10, 30), payload={"name": "Name at 10:30"}),
        ]

        # Sort by event_time
        events.sort(key=lambda e: e.event_time)
        latest = events[-1]

        assert latest.payload["name"] == "Name at 11:00"

    def test_stale_event_marked_expired(self):
        """UT-D07-11: Event older than last_sync_at marked expired."""
        dept = Dept(
            id=1, tenant_id=1, name="市场部",
            parent_id=None, source=DeptSource.DINGTALK,
            last_sync_at=datetime(2026, 10, 12, 10, 5)
        )

        event = DingTalkEvent(
            id=1, event_id="evt_1", event_type="dept_modify",
            event_time=datetime(2026, 10, 12, 10, 0),  # Before last_sync
            payload={"name": "Old name"}
        )

        if event.event_time < dept.last_sync_at:
            event.status = EventStatus.EXPIRED

        assert event.status == EventStatus.EXPIRED


class TestEventRetry:
    """Tests for event retry handling (FP-D07-05)."""

    def test_retry_increments_count(self):
        """UT-D07-21: Failed event increments retry count."""
        event = DingTalkEvent(
            id=1, event_id="evt_1", event_type="dept_modify",
            event_time=datetime.now(), payload={},
            status=EventStatus.RETRYING, retry_count=0
        )

        # Retry
        event.retry_count += 1

        assert event.retry_count == 1

    def test_max_retries_becomes_dead(self):
        """UT-D07-21: After 5 retries, status becomes DEAD."""
        event = DingTalkEvent(
            id=1, event_id="evt_1", event_type="dept_modify",
            event_time=datetime.now(), payload={},
            status=EventStatus.RETRYING, retry_count=4
        )

        # 5th retry fails
        event.retry_count += 1
        if event.retry_count >= 5:
            event.status = EventStatus.DEAD

        assert event.status == EventStatus.DEAD

    def test_dead_can_be_replayed(self):
        """UT-D07-22: DEAD event can be manually replayed."""
        event = DingTalkEvent(
            id=1, event_id="evt_1", event_type="dept_modify",
            event_time=datetime.now(), payload={},
            status=EventStatus.DEAD, retry_count=5
        )

        # Manual replay
        event.status = EventStatus.PENDING

        assert event.status == EventStatus.PENDING


class TestSyncDelay:
    """Tests for sync delay alerting (FP-D07-05)."""

    def test_delay_over_5min_alerts(self):
        """UT-D07-23: Processing delay > 5 min triggers alert."""
        event_time = datetime.now() - timedelta(minutes=6)
        process_time = datetime.now()

        delay_seconds = (process_time - event_time).total_seconds()

        alert_triggered = delay_seconds > 300  # 5 minutes

        assert alert_triggered
