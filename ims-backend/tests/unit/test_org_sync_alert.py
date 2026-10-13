# tests/unit/test_org_sync_alert.py - OrgSyncAlertService tests
"""
Unit tests for organization sync alert service.

Tests:
- Dead letter alerts (hourly merge)
- Delay alerts (hourly throttle)
- Reconcile failure P1 alerts (2 consecutive failures)
- Sync metrics calculation
"""

from datetime import datetime, timedelta

import pytest

from app.core.cache import Cache
from app.core.clock import set_clock, reset_clock
from app.services.org_sync_alert import OrgSyncAlertService
from tests.support import rows


@pytest.fixture
def service():
    """Create OrgSyncAlertService instance."""
    return OrgSyncAlertService()


@pytest.fixture
def fixed_clock():
    """Set up fixed clock for tests."""
    now = datetime(2026, 10, 13, 10, 0, 0)
    set_clock(lambda: now)
    yield now
    reset_clock()


class TestDeadLetterAlert:
    """Test dead letter alert with hourly merge."""

    @pytest.mark.asyncio
    async def test_dead_letter_alert_merges_by_hour(
        self, db_session, test_context, service, fixed_clock
    ):
        """Dead letter alerts are merged within the same hour."""
        from app.domains.sys.models import OrgSyncEvent

        event1 = OrgSyncEvent(
            tenant_id=1,
            event_id="dead-1",
            event_type="user_add_org",
            event_time=fixed_clock - timedelta(hours=1),
            received_time=fixed_clock,
            payload="{}",
            status="DEAD",
            retry_count=4,
        )
        rows.add(db_session, event1)

        await service.check_dead_letter(tenant_id=1, event_id=event1.id)

        hour_key = fixed_clock.strftime("%Y%m%d%H")
        cache_key = f"ims:alert:dead_letter:1:{hour_key}"
        assert Cache.get(cache_key) == "1"

        event2 = OrgSyncEvent(
            tenant_id=1,
            event_id="dead-2",
            event_type="user_add_org",
            event_time=fixed_clock - timedelta(hours=1),
            received_time=fixed_clock,
            payload="{}",
            status="DEAD",
            retry_count=4,
        )
        rows.add(db_session, event2)

        await service.check_dead_letter(tenant_id=1, event_id=event2.id)
        assert Cache.get(cache_key) == "2"

    @pytest.mark.asyncio
    async def test_dead_letter_alert_after_hour(
        self, db_session, test_context, service
    ):
        """Dead letter alert fires again after hour passes."""
        from app.domains.sys.models import OrgSyncEvent

        now = datetime(2026, 10, 13, 10, 0, 0)
        set_clock(lambda: now)

        event = OrgSyncEvent(
            tenant_id=1,
            event_id="dead-hourly",
            event_type="user_add_org",
            event_time=now - timedelta(hours=1),
            received_time=now,
            payload="{}",
            status="DEAD",
            retry_count=4,
        )
        rows.add(db_session, event)

        await service.check_dead_letter(tenant_id=1, event_id=event.id)

        hour_key_1 = now.strftime("%Y%m%d%H")
        assert Cache.get(f"ims:alert:dead_letter:1:{hour_key_1}") == "1"

        later = now + timedelta(hours=1, minutes=1)
        set_clock(lambda: later)

        event2 = OrgSyncEvent(
            tenant_id=1,
            event_id="dead-hourly-2",
            event_type="user_add_org",
            event_time=later - timedelta(hours=1),
            received_time=later,
            payload="{}",
            status="DEAD",
            retry_count=4,
        )
        rows.add(db_session, event2)

        await service.check_dead_letter(tenant_id=1, event_id=event2.id)

        hour_key_2 = later.strftime("%Y%m%d%H")
        assert Cache.get(f"ims:alert:dead_letter:1:{hour_key_2}") == "1"

        reset_clock()


class TestDelayAlert:
    """Test delay alert with hourly throttle."""

    @pytest.mark.asyncio
    async def test_delay_alert_fires_above_threshold(
        self, db_session, test_context, service, fixed_clock
    ):
        """Delay alert fires when delay > threshold."""
        from app.domains.sys.models import OrgSyncEvent

        event = OrgSyncEvent(
            tenant_id=1,
            event_id="delay-1",
            event_type="user_add_org",
            event_time=fixed_clock - timedelta(minutes=10),
            received_time=fixed_clock - timedelta(minutes=9),
            processed_time=fixed_clock,
            payload="{}",
            status="SUCCESS",
            delay_seconds=600,
        )
        rows.add(db_session, event)

        await service.check_delay_alert(tenant_id=1, event_id=event.id, delay_seconds=600)

        hour_key = fixed_clock.strftime("%Y%m%d%H")
        cache_key = f"ims:alert:delay:1:{hour_key}"
        assert Cache.get(cache_key) == "1"

    @pytest.mark.asyncio
    async def test_delay_alert_throttled_hourly(
        self, db_session, test_context, service, fixed_clock
    ):
        """Delay alert is throttled to once per hour."""
        from app.domains.sys.models import OrgSyncEvent

        event1 = OrgSyncEvent(
            tenant_id=1,
            event_id="delay-throttle-1",
            event_type="user_add_org",
            event_time=fixed_clock - timedelta(minutes=10),
            received_time=fixed_clock - timedelta(minutes=9),
            processed_time=fixed_clock,
            payload="{}",
            status="SUCCESS",
            delay_seconds=600,
        )
        rows.add(db_session, event1)

        await service.check_delay_alert(tenant_id=1, event_id=event1.id, delay_seconds=600)

        event2 = OrgSyncEvent(
            tenant_id=1,
            event_id="delay-throttle-2",
            event_type="user_add_org",
            event_time=fixed_clock - timedelta(minutes=10),
            received_time=fixed_clock - timedelta(minutes=9),
            processed_time=fixed_clock,
            payload="{}",
            status="SUCCESS",
            delay_seconds=700,
        )
        rows.add(db_session, event2)

        await service.check_delay_alert(tenant_id=1, event_id=event2.id, delay_seconds=700)

        hour_key = fixed_clock.strftime("%Y%m%d%H")
        cache_key = f"ims:alert:delay:1:{hour_key}"
        assert Cache.get(cache_key) == "1"

    @pytest.mark.asyncio
    async def test_delay_alert_below_threshold_not_fired(
        self, db_session, test_context, service, fixed_clock
    ):
        """Delay alert does not fire when delay < threshold."""
        from app.domains.sys.models import OrgSyncEvent

        event = OrgSyncEvent(
            tenant_id=1,
            event_id="delay-low",
            event_type="user_add_org",
            event_time=fixed_clock - timedelta(seconds=30),
            received_time=fixed_clock - timedelta(seconds=29),
            processed_time=fixed_clock,
            payload="{}",
            status="SUCCESS",
            delay_seconds=30,
        )
        rows.add(db_session, event)

        await service.check_delay_alert(tenant_id=1, event_id=event.id, delay_seconds=30)

        hour_key = fixed_clock.strftime("%Y%m%d%H")
        cache_key = f"ims:alert:delay:1:{hour_key}"
        assert Cache.get(cache_key) is None


class TestReconcileFailureAlert:
    """Test reconcile failure P1 alert on 2 consecutive failures."""

    @pytest.mark.asyncio
    async def test_p1_on_two_consecutive_failures(
        self, db_session, test_context, service, fixed_clock
    ):
        """P1 alert triggered on 2 consecutive reconcile failures."""
        from app.domains.sys.models import OrgSyncBatch as Batch

        batch1 = Batch(
            tenant_id=1,
            trigger_type="SCHEDULED",
            status="FAILED",
            started_at=fixed_clock - timedelta(hours=2),
            completed_at=fixed_clock - timedelta(hours=2, minutes=-5),
            fail_reason="Network error",
        )
        rows.add(db_session, batch1)

        batch2 = Batch(
            tenant_id=1,
            trigger_type="SCHEDULED",
            status="FAILED",
            started_at=fixed_clock - timedelta(hours=1),
            completed_at=fixed_clock - timedelta(hours=1, minutes=-5),
            fail_reason="Timeout",
        )
        rows.add(db_session, batch2)

        await service.check_reconcile_failure(tenant_id=1, batch_id=batch2.id)

    @pytest.mark.asyncio
    async def test_no_p1_on_single_failure(
        self, db_session, test_context, service, fixed_clock
    ):
        """No P1 alert on single reconcile failure."""
        from app.domains.sys.models import OrgSyncBatch as Batch

        batch = Batch(
            tenant_id=1,
            trigger_type="SCHEDULED",
            status="FAILED",
            started_at=fixed_clock - timedelta(hours=1),
            completed_at=fixed_clock - timedelta(hours=1, minutes=-5),
            fail_reason="Network error",
        )
        rows.add(db_session, batch)

        await service.check_reconcile_failure(tenant_id=1, batch_id=batch.id)

    @pytest.mark.asyncio
    async def test_no_p1_after_success(
        self, db_session, test_context, service, fixed_clock
    ):
        """No P1 alert when latest reconcile is successful."""
        from app.domains.sys.models import OrgSyncBatch as Batch

        batch1 = Batch(
            tenant_id=1,
            trigger_type="SCHEDULED",
            status="FAILED",
            started_at=fixed_clock - timedelta(hours=2),
            completed_at=fixed_clock - timedelta(hours=2, minutes=-5),
            fail_reason="Error",
        )
        rows.add(db_session, batch1)

        batch2 = Batch(
            tenant_id=1,
            trigger_type="SCHEDULED",
            status="SUCCESS",
            started_at=fixed_clock - timedelta(hours=1),
            completed_at=fixed_clock - timedelta(hours=1, minutes=-5),
        )
        rows.add(db_session, batch2)

        await service.check_reconcile_failure(tenant_id=1, batch_id=batch2.id)


class TestSyncMetrics:
    """Test sync metrics calculation."""

    @pytest.mark.asyncio
    async def test_get_sync_metrics_basic(
        self, db_session, test_context, service, fixed_clock
    ):
        """Get sync metrics returns expected structure."""
        for i in range(10):
            rows.user(db_session, f"metrics_user_{i}")

        result = await service.get_sync_metrics(tenant_id=1)

        assert "userTotal" in result
        assert "yesterdayEventCount" in result
        assert "pendingEventCount" in result
        assert "deadEventCount" in result
        assert "avgDelayMinutes" in result
        assert "p95DelayMinutes" in result
        assert "successRate24h" in result
        assert result["userTotal"] == 10

    @pytest.mark.asyncio
    async def test_get_sync_metrics_with_events(
        self, db_session, test_context, service, fixed_clock
    ):
        """Get sync metrics with events returns accurate counts."""
        from app.domains.sys.models import OrgSyncEvent

        yesterday_start = (fixed_clock - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        yesterday_mid = yesterday_start + timedelta(hours=12)

        event_pending = OrgSyncEvent(
            tenant_id=1,
            event_id="metrics-pending",
            event_type="user_add_org",
            event_time=yesterday_mid,
            received_time=yesterday_mid,
            payload="{}",
            status="PENDING",
            retry_count=0,
        )
        rows.add(db_session, event_pending)

        event_dead = OrgSyncEvent(
            tenant_id=1,
            event_id="metrics-dead",
            event_type="user_add_org",
            event_time=yesterday_mid,
            received_time=yesterday_mid,
            payload="{}",
            status="DEAD",
            retry_count=4,
        )
        rows.add(db_session, event_dead)

        event_success = OrgSyncEvent(
            tenant_id=1,
            event_id="metrics-success",
            event_type="user_add_org",
            event_time=yesterday_mid,
            received_time=yesterday_mid,
            processed_time=yesterday_mid + timedelta(seconds=30),
            payload="{}",
            status="SUCCESS",
            delay_seconds=30,
        )
        rows.add(db_session, event_success)

        result = await service.get_sync_metrics(tenant_id=1)

        assert result["pendingEventCount"] == 1
        assert result["deadEventCount"] == 1
        assert result["yesterdayEventCount"] == 3

    @pytest.mark.asyncio
    async def test_success_rate_calculation(
        self, db_session, test_context, service, fixed_clock
    ):
        """Success rate is calculated correctly."""
        from app.domains.sys.models import OrgSyncEvent

        now_minus_12h = fixed_clock - timedelta(hours=12)

        for i in range(8):
            event = OrgSyncEvent(
                tenant_id=1,
                event_id=f"rate-success-{i}",
                event_type="user_add_org",
                event_time=now_minus_12h,
                received_time=now_minus_12h,
                processed_time=now_minus_12h + timedelta(seconds=30),
                payload="{}",
                status="SUCCESS",
            )
            rows.add(db_session, event)

        for i in range(2):
            event = OrgSyncEvent(
                tenant_id=1,
                event_id=f"rate-dead-{i}",
                event_type="user_add_org",
                event_time=now_minus_12h,
                received_time=now_minus_12h,
                processed_time=now_minus_12h + timedelta(seconds=30),
                payload="{}",
                status="DEAD",
                retry_count=4,
            )
            rows.add(db_session, event)

        result = await service.get_sync_metrics(tenant_id=1)

        assert result["successRate24h"] == 0.8


class TestClockInjection:
    """Test clock injection for time-dependent logic."""

    @pytest.mark.asyncio
    async def test_set_clock_affects_cache_keys(self, db_session, test_context, service):
        """Setting clock affects cache key generation."""
        from app.domains.sys.models import OrgSyncEvent

        base_time = datetime(2026, 10, 13, 10, 0, 0)
        set_clock(lambda: base_time)

        event = OrgSyncEvent(
            tenant_id=1,
            event_id="clock-test",
            event_type="user_add_org",
            event_time=base_time - timedelta(hours=2),
            received_time=base_time - timedelta(hours=2),
            payload="{}",
            status="DEAD",
            retry_count=4,
        )
        rows.add(db_session, event)

        await service.check_dead_letter(tenant_id=1, event_id=event.id)

        hour_key_1 = base_time.strftime("%Y%m%d%H")
        assert Cache.get(f"ims:alert:dead_letter:1:{hour_key_1}") == "1"

        later = base_time + timedelta(hours=2)
        set_clock(lambda: later)

        event2 = OrgSyncEvent(
            tenant_id=1,
            event_id="clock-test-2",
            event_type="user_add_org",
            event_time=later - timedelta(hours=2),
            received_time=later - timedelta(hours=2),
            payload="{}",
            status="DEAD",
            retry_count=4,
        )
        rows.add(db_session, event2)

        await service.check_dead_letter(tenant_id=1, event_id=event2.id)

        hour_key_2 = later.strftime("%Y%m%d%H")
        assert Cache.get(f"ims:alert:dead_letter:1:{hour_key_2}") == "1"

        reset_clock()
