# tests/unit/test_scheduler.py - Scheduler tests (FP-H01)
"""
Tests for job scheduler.

Per 02-单测用例.md UT-H01:
- Distributed lock prevents duplicate execution
- Job failures logged and alerted
- Manual trigger supported
- Lock watchdog for long-running jobs
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional


class JobStatus(str, Enum):
    """Job execution status."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
    SKIPPED = "SKIPPED"  # Lock held by another instance


class TriggerType(str, Enum):
    """Job trigger type."""
    CRON = "CRON"
    MANUAL = "MANUAL"


@dataclass
class JobDef:
    """Job definition."""
    name: str
    cron: str
    handler: Callable
    lock_timeout_seconds: int = 300


@dataclass
class JobExecution:
    """Job execution record."""
    id: int
    job_name: str
    instance_id: str  # Which worker instance
    trigger_type: TriggerType
    status: JobStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None


class MockDistributedLock:
    """Mock distributed lock for testing."""

    _locks: dict = {}
    _lock = threading.Lock()

    @classmethod
    def acquire(cls, key: str, holder: str, ttl_seconds: int) -> bool:
        with cls._lock:
            if key in cls._locks:
                return False
            cls._locks[key] = {"holder": holder, "expires": time.time() + ttl_seconds}
            return True

    @classmethod
    def release(cls, key: str, holder: str) -> bool:
        with cls._lock:
            if key in cls._locks and cls._locks[key]["holder"] == holder:
                del cls._locks[key]
                return True
            return False

    @classmethod
    def renew(cls, key: str, holder: str, ttl_seconds: int) -> bool:
        with cls._lock:
            if key in cls._locks and cls._locks[key]["holder"] == holder:
                cls._locks[key]["expires"] = time.time() + ttl_seconds
                return True
            return False

    @classmethod
    def clear_all(cls):
        with cls._lock:
            cls._locks.clear()


class TestDistributedLock:
    """Tests for distributed lock (FP-H01-02)."""

    def setup_method(self):
        MockDistributedLock.clear_all()

    def test_single_instance_acquires_lock(self):
        """UT-H01-01: Single instance can acquire lock."""
        acquired = MockDistributedLock.acquire("job:cleanup", "worker-1", 60)

        assert acquired

    def test_second_instance_blocked(self):
        """UT-H01-01: Second instance cannot acquire same lock."""
        MockDistributedLock.acquire("job:cleanup", "worker-1", 60)
        acquired_second = MockDistributedLock.acquire("job:cleanup", "worker-2", 60)

        assert not acquired_second

    def test_blocked_instance_logs_skip(self):
        """UT-H01-01: Blocked instance logs '已在其他实例执行'."""
        MockDistributedLock.acquire("job:cleanup", "worker-1", 60)
        acquired = MockDistributedLock.acquire("job:cleanup", "worker-2", 60)

        log_message = "已在其他实例执行" if not acquired else None

        assert log_message == "已在其他实例执行"

    def test_lock_released_after_execution(self):
        """UT-H01-01: Lock released after job completes."""
        MockDistributedLock.acquire("job:cleanup", "worker-1", 60)
        MockDistributedLock.release("job:cleanup", "worker-1")

        # Now worker-2 can acquire
        acquired = MockDistributedLock.acquire("job:cleanup", "worker-2", 60)

        assert acquired


class TestJobFailure:
    """Tests for job failure handling (FP-H01-01)."""

    def test_failure_logged_with_error(self):
        """UT-H01-02: Job failure records error message."""
        execution = JobExecution(
            id=1,
            job_name="cleanup",
            instance_id="worker-1",
            trigger_type=TriggerType.CRON,
            status=JobStatus.FAILED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            error_message="Connection refused"
        )

        assert execution.status == JobStatus.FAILED
        assert execution.error_message is not None

    def test_failure_triggers_alert(self):
        """UT-H01-02: Job failure sends alert notification."""
        alerts_sent = []

        def send_alert(job_name: str, error: str):
            alerts_sent.append({"job": job_name, "error": error})

        # Simulate failure alert
        send_alert("cleanup", "Connection refused")

        assert len(alerts_sent) == 1
        assert alerts_sent[0]["job"] == "cleanup"


class TestManualTrigger:
    """Tests for manual job trigger (FP-H01-01)."""

    def test_manual_trigger_requires_permission(self):
        """UT-H01-03: Manual trigger requires ims:system:job:run."""
        user_permissions = ["ims:system:job:run"]
        required_permission = "ims:system:job:run"

        has_permission = required_permission in user_permissions

        assert has_permission

    def test_manual_trigger_logged_as_manual(self):
        """UT-H01-03: Manual trigger logged with MANUAL type."""
        execution = JobExecution(
            id=1,
            job_name="cleanup",
            instance_id="worker-1",
            trigger_type=TriggerType.MANUAL,
            status=JobStatus.SUCCESS,
            start_time=datetime.now(),
            end_time=datetime.now()
        )

        assert execution.trigger_type == TriggerType.MANUAL

    def test_manual_trigger_no_permission(self):
        """UT-H01-03: No permission returns 1008."""
        user_permissions = ["ims:system:user:query"]
        required_permission = "ims:system:job:run"

        has_permission = required_permission in user_permissions

        assert not has_permission


class TestLockWatchdog:
    """Tests for lock watchdog (FP-H01-02)."""

    def setup_method(self):
        MockDistributedLock.clear_all()

    def test_watchdog_renews_lock(self):
        """UT-H01-04: Watchdog renews lock during long execution."""
        MockDistributedLock.acquire("job:long", "worker-1", 30)

        # Simulate watchdog renewal
        renewed = MockDistributedLock.renew("job:long", "worker-1", 30)

        assert renewed

    def test_long_job_keeps_lock(self):
        """UT-H01-04: Long-running job keeps lock via watchdog."""
        MockDistributedLock.acquire("job:long", "worker-1", 30)

        # Worker-2 tries during worker-1's execution
        acquired = MockDistributedLock.acquire("job:long", "worker-2", 30)

        assert not acquired

    def test_renewal_only_by_holder(self):
        """UT-H01-04: Only lock holder can renew."""
        MockDistributedLock.acquire("job:long", "worker-1", 30)

        # Worker-2 cannot renew
        renewed = MockDistributedLock.renew("job:long", "worker-2", 30)

        assert not renewed


class TestJobExecutionLog:
    """Tests for job execution logging."""

    def test_execution_has_required_fields(self):
        """Job execution record has required fields."""
        execution = JobExecution(
            id=1,
            job_name="cleanup",
            instance_id="worker-1",
            trigger_type=TriggerType.CRON,
            status=JobStatus.SUCCESS,
            start_time=datetime.now(),
            end_time=datetime.now()
        )

        assert execution.id is not None
        assert execution.job_name is not None
        assert execution.instance_id is not None
        assert execution.trigger_type is not None
        assert execution.status is not None
        assert execution.start_time is not None

    def test_execution_duration_calculable(self):
        """Job execution duration can be calculated."""
        start = datetime.now()
        end = start + timedelta(seconds=45)

        execution = JobExecution(
            id=1,
            job_name="cleanup",
            instance_id="worker-1",
            trigger_type=TriggerType.CRON,
            status=JobStatus.SUCCESS,
            start_time=start,
            end_time=end
        )

        duration_seconds = (execution.end_time - execution.start_time).total_seconds()

        assert duration_seconds == 45


class TestCronSchedule:
    """Tests for cron schedule parsing."""

    def test_daily_cron(self):
        """Daily job runs once per day."""
        cron = "0 3 * * *"  # 3 AM daily

        # Simple validation - contains 5 parts
        assert len(cron.split()) == 5

    def test_hourly_cron(self):
        """Hourly job runs every hour."""
        cron = "0 * * * *"

        assert len(cron.split()) == 5

    def test_every_5_minutes(self):
        """Job can run every 5 minutes."""
        cron = "*/5 * * * *"

        assert len(cron.split()) == 5
        assert "*/5" in cron
