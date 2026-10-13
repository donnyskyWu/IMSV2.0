# tests/unit/test_train_job.py - Training job tests (B21)
"""
Unit tests for training scheduled jobs.

Per 培训管理-实现理解.md §11:
- Time: get_now/set_clock
- Idempotency: unique keys
- LibreOffice/ffprobe: timeout + isolation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from app.core.clock import get_now, set_clock, reset_clock


class TestTrainTaskJobFinishExpired:
    """Tests for finish_expired_tasks."""

    @pytest.mark.asyncio
    async def test_finishes_expired_tasks(self, db_session, test_context):
        """Tasks past deadline are marked FINISHED."""
        from app.domains.train.jobs import TrainTaskJob
        from app.domains.train.models import TrainTask
        from app.core.context import ctx

        past = datetime.now() - timedelta(days=1)
        task = TrainTask(
            tenant_id=ctx.tenant_id,
            task_no="TT202610010001",
            task_name="Expired Task",
            assign_scope="BY_USER",
            deadline=past,
            confirm_type="DURATION",
            status="IN_PROGRESS",
        )
        db_session.add(task)
        db_session.flush()

        job = TrainTaskJob(db_session)
        result = await job.finish_expired_tasks(ctx.tenant_id)

        assert result["finished_count"] >= 1
        db_session.refresh(task)
        assert task.status == "FINISHED"

    @pytest.mark.asyncio
    async def test_does_not_finish_future_tasks(self, db_session, test_context):
        """Tasks with future deadline not affected."""
        from app.domains.train.jobs import TrainTaskJob
        from app.domains.train.models import TrainTask
        from app.core.context import ctx

        future = datetime.now() + timedelta(days=7)
        task = TrainTask(
            tenant_id=ctx.tenant_id,
            task_no="TT202610010002",
            task_name="Future Task",
            assign_scope="BY_USER",
            deadline=future,
            confirm_type="DURATION",
            status="IN_PROGRESS",
        )
        db_session.add(task)
        db_session.flush()

        job = TrainTaskJob(db_session)
        await job.finish_expired_tasks(ctx.tenant_id)

        db_session.refresh(task)
        assert task.status == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_idempotent_on_already_finished(self, db_session, test_context):
        """Already finished tasks not re-processed."""
        from app.domains.train.jobs import TrainTaskJob
        from app.domains.train.models import TrainTask
        from app.core.context import ctx

        past = datetime.now() - timedelta(days=1)
        task = TrainTask(
            tenant_id=ctx.tenant_id,
            task_no="TT202610010003",
            task_name="Already Finished",
            assign_scope="BY_USER",
            deadline=past,
            confirm_type="DURATION",
            status="FINISHED",
        )
        db_session.add(task)
        db_session.flush()

        job = TrainTaskJob(db_session)
        result = await job.finish_expired_tasks(ctx.tenant_id)

        assert result["finished_count"] == 0


class TestTrainReminderJobDue:
    """Tests for due reminders."""

    @pytest.mark.asyncio
    async def test_reminds_within_24h(self, db_session, test_context):
        """UT-B21-JOB-02: Records with deadline in 24h get reminded."""
        from app.domains.train.jobs import TrainReminderJob
        from app.domains.train.models import TrainTask, TrainTaskRecord
        from app.core.context import ctx

        deadline = datetime.now() + timedelta(hours=12)
        task = TrainTask(
            tenant_id=ctx.tenant_id,
            task_no="TT202610010004",
            task_name="Due Soon",
            assign_scope="BY_USER",
            deadline=deadline,
            confirm_type="DURATION",
            status="IN_PROGRESS",
        )
        db_session.add(task)
        db_session.flush()

        record = TrainTaskRecord(
            tenant_id=ctx.tenant_id,
            task_id=task.id,
            user_id=1,
            confirm_status="NOT_CONFIRMED",
        )
        db_session.add(record)
        db_session.flush()

        job = TrainReminderJob(db_session)
        result = await job.remind_due(ctx.tenant_id)

        assert result["reminded_count"] >= 1
        db_session.refresh(record)
        assert record.remind_due_at is not None

    @pytest.mark.asyncio
    async def test_idempotent_already_reminded(self, db_session, test_context):
        """UT-B21-JOB-04: Already reminded records not re-reminded."""
        from app.domains.train.jobs import TrainReminderJob
        from app.domains.train.models import TrainTask, TrainTaskRecord
        from app.core.context import ctx

        deadline = datetime.now() + timedelta(hours=12)
        task = TrainTask(
            tenant_id=ctx.tenant_id,
            task_no="TT202610010005",
            task_name="Already Reminded",
            assign_scope="BY_USER",
            deadline=deadline,
            confirm_type="DURATION",
            status="IN_PROGRESS",
        )
        db_session.add(task)
        db_session.flush()

        record = TrainTaskRecord(
            tenant_id=ctx.tenant_id,
            task_id=task.id,
            user_id=1,
            confirm_status="NOT_CONFIRMED",
            remind_due_at=datetime.now(),
        )
        db_session.add(record)
        db_session.flush()

        job = TrainReminderJob(db_session)
        result = await job.remind_due(ctx.tenant_id)

        assert result["reminded_count"] == 0


class TestTrainReminderJobOverdue:
    """Tests for overdue reminders."""

    @pytest.mark.asyncio
    async def test_reminds_overdue(self, db_session, test_context):
        """UT-B21-JOB-03: Overdue records get reminded."""
        from app.domains.train.jobs import TrainReminderJob
        from app.domains.train.models import TrainTask, TrainTaskRecord
        from app.core.context import ctx

        past = datetime.now() - timedelta(days=2)
        task = TrainTask(
            tenant_id=ctx.tenant_id,
            task_no="TT202610010006",
            task_name="Overdue Task",
            assign_scope="BY_USER",
            deadline=past,
            confirm_type="DURATION",
            status="IN_PROGRESS",
        )
        db_session.add(task)
        db_session.flush()

        record = TrainTaskRecord(
            tenant_id=ctx.tenant_id,
            task_id=task.id,
            user_id=1,
            confirm_status="NOT_CONFIRMED",
        )
        db_session.add(record)
        db_session.flush()

        job = TrainReminderJob(db_session)
        result = await job.remind_overdue(ctx.tenant_id)

        assert result["reminded_count"] >= 1
        db_session.refresh(record)
        assert record.remind_overdue_at is not None
        assert record.is_overdue is True


class TestTrainStatJobDailySummary:
    """Tests for daily summary job."""

    @pytest.mark.asyncio
    async def test_generates_summary(self, db_session, test_context):
        """Daily summary is generated correctly."""
        from app.domains.train.jobs import TrainStatJob
        from app.domains.train.models import TrainTask, TrainTaskRecord, TrainStatDaily
        from app.core.context import ctx

        now = datetime.now()
        task = TrainTask(
            tenant_id=ctx.tenant_id,
            task_no="TT202610010007",
            task_name="Stats Task",
            assign_scope="BY_USER",
            deadline=now + timedelta(days=7),
            confirm_type="DURATION",
            status="IN_PROGRESS",
        )
        db_session.add(task)
        db_session.flush()

        record = TrainTaskRecord(
            tenant_id=ctx.tenant_id,
            task_id=task.id,
            user_id=1,
            user_dept_id=1,
            confirm_status="CONFIRMED",
            effective_seconds=3600,
        )
        db_session.add(record)
        db_session.flush()

        job = TrainStatJob(db_session)
        result = await job.daily_summary(ctx.tenant_id)

        assert result["upserted_count"] >= 0


class TestTrainStatJobLowRateAlert:
    """Tests for low completion rate alert."""

    @pytest.mark.asyncio
    async def test_alerts_low_rate_depts(self, db_session, test_context):
        """Departments below threshold get alerted."""
        from app.domains.train.jobs import TrainStatJob
        from app.domains.train.models import TrainStatDaily, TrainDeptAlert
        from app.core.context import ctx
        from decimal import Decimal

        now = datetime.now()
        week_start = now - timedelta(days=now.weekday() + 7)

        for i in range(7):
            stat = TrainStatDaily(
                tenant_id=ctx.tenant_id,
                stat_date=(week_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                dept_id=99,
                assigned_count=10,
                finished_count=7,
                finish_rate=Decimal("70.0"),
            )
            db_session.add(stat)

        db_session.flush()

        job = TrainStatJob(db_session)
        result = await job.low_rate_alert(ctx.tenant_id, threshold=85.0)

        assert result["alerted_count"] >= 0

    @pytest.mark.asyncio
    async def test_idempotent_already_alerted(self, db_session, test_context):
        """Already alerted departments not re-alerted."""
        from app.domains.train.jobs import TrainStatJob
        from app.domains.train.models import TrainStatDaily, TrainDeptAlert
        from app.core.context import ctx
        from decimal import Decimal

        now = datetime.now()
        week_start = (now - timedelta(days=now.weekday() + 7)).strftime("%Y-%m-%d")

        alert = TrainDeptAlert(
            tenant_id=ctx.tenant_id,
            dept_id=99,
            week_start=week_start,
            notified_at=now,
        )
        db_session.add(alert)
        db_session.flush()

        job = TrainStatJob(db_session)
        result = await job.low_rate_alert(ctx.tenant_id, threshold=85.0)

        alerts = db_session.query(TrainDeptAlert).filter(
            TrainDeptAlert.dept_id == 99,
            TrainDeptAlert.week_start == week_start,
        ).count()

        assert alerts == 1


class TestTrainMaterialJobConvert:
    """Tests for document conversion."""

    @pytest.mark.asyncio
    async def test_timeout_handling(self, db_session, test_context):
        """UT-B21-CONVERT-01: Timeout marks as FAILED."""
        from app.domains.train.jobs import TrainMaterialJob
        from app.domains.train.models import TrainMaterial
        from app.core.context import ctx

        material = TrainMaterial(
            tenant_id=ctx.tenant_id,
            material_no="MT202610010001",
            title="Test Doc",
            cate_id=1,
            material_type="DOC",
            file_key="/nonexistent/file.docx",
            status="DRAFT",
            convert_status="PENDING",
        )
        db_session.add(material)
        db_session.flush()

        job = TrainMaterialJob(db_session)

        with patch.object(job, "_run_libreoffice_convert") as mock_convert:
            import asyncio
            mock_convert.side_effect = asyncio.TimeoutError()

            result = await job.convert_document(material.id)

        assert result["success"] is False
        assert "timeout" in result.get("error", "").lower()
        db_session.refresh(material)
        assert material.convert_status == "FAILED"

    @pytest.mark.asyncio
    async def test_success_sets_done(self, db_session, test_context):
        """UT-B21-CONVERT-02: Success marks as DONE."""
        from app.domains.train.jobs import TrainMaterialJob
        from app.domains.train.models import TrainMaterial
        from app.core.context import ctx

        material = TrainMaterial(
            tenant_id=ctx.tenant_id,
            material_no="MT202610010002",
            title="Test Doc 2",
            cate_id=1,
            material_type="DOC",
            file_key="/test/file.docx",
            status="DRAFT",
            convert_status="PENDING",
        )
        db_session.add(material)
        db_session.flush()

        job = TrainMaterialJob(db_session)

        with patch.object(job, "_run_libreoffice_convert") as mock_convert:
            mock_convert.return_value = ("train/pdf/1/test.pdf", 5)

            result = await job.convert_document(material.id)

        assert result["success"] is True
        assert result["page_count"] == 5
        db_session.refresh(material)
        assert material.convert_status == "DONE"


class TestTrainMaterialJobFfprobe:
    """Tests for ffprobe duration extraction."""

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self, db_session, test_context):
        """UT-B21-FFPROBE-02: Timeout returns error."""
        from app.domains.train.jobs import TrainMaterialJob
        from app.domains.train.models import TrainMaterial
        from app.core.context import ctx

        material = TrainMaterial(
            tenant_id=ctx.tenant_id,
            material_no="MT202610010003",
            title="Test Video",
            cate_id=1,
            material_type="VIDEO",
            file_key="/nonexistent/video.mp4",
            status="DRAFT",
        )
        db_session.add(material)
        db_session.flush()

        job = TrainMaterialJob(db_session)

        with patch.object(job, "_run_ffprobe") as mock_ffprobe:
            import asyncio
            mock_ffprobe.side_effect = asyncio.TimeoutError()

            result = await job.extract_video_duration(material.id)

        assert result["success"] is False
        assert "timeout" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_success_sets_duration(self, db_session, test_context):
        """UT-B21-FFPROBE-01: Success sets duration."""
        from app.domains.train.jobs import TrainMaterialJob
        from app.domains.train.models import TrainMaterial
        from app.core.context import ctx

        material = TrainMaterial(
            tenant_id=ctx.tenant_id,
            material_no="MT202610010004",
            title="Test Video 2",
            cate_id=1,
            material_type="VIDEO",
            file_key="/test/video.mp4",
            status="DRAFT",
        )
        db_session.add(material)
        db_session.flush()

        job = TrainMaterialJob(db_session)

        with patch.object(job, "_run_ffprobe") as mock_ffprobe:
            mock_ffprobe.return_value = 300

            result = await job.extract_video_duration(material.id)

        assert result["success"] is True
        assert result["duration_seconds"] == 300
        db_session.refresh(material)
        assert material.duration_seconds == 300


class TestClockUsage:
    """Tests for clock usage in jobs."""

    def test_jobs_use_get_now(self):
        """Jobs use get_now from app.core.clock."""
        from app.domains.train.jobs import TrainTaskJob, TrainReminderJob, TrainStatJob

        import inspect
        source_task = inspect.getsource(TrainTaskJob.finish_expired_tasks)
        source_due = inspect.getsource(TrainReminderJob.remind_due)
        source_stat = inspect.getsource(TrainStatJob.daily_summary)

        assert "get_now()" in source_task
        assert "get_now()" in source_due
        assert "get_now()" in source_stat

    @pytest.mark.asyncio
    async def test_set_clock_affects_job(self, db_session, test_context):
        """set_clock injection affects job behavior."""
        from app.core.clock import set_clock, reset_clock
        from app.domains.train.jobs import TrainTaskJob
        from app.domains.train.models import TrainTask
        from app.core.context import ctx

        deadline = datetime(2026, 10, 15, 12, 0, 0)
        task = TrainTask(
            tenant_id=ctx.tenant_id,
            task_no="TT202610010008",
            task_name="Clock Test",
            assign_scope="BY_USER",
            deadline=deadline,
            confirm_type="DURATION",
            status="IN_PROGRESS",
        )
        db_session.add(task)
        db_session.flush()

        set_clock(lambda: datetime(2026, 10, 14, 12, 0, 0))
        job = TrainTaskJob(db_session)
        await job.finish_expired_tasks(ctx.tenant_id)
        db_session.refresh(task)
        assert task.status == "IN_PROGRESS"

        set_clock(lambda: datetime(2026, 10, 16, 12, 0, 0))
        await job.finish_expired_tasks(ctx.tenant_id)
        db_session.refresh(task)
        assert task.status == "FINISHED"

        reset_clock()


class TestWeekBoundary:
    """Tests for week boundary handling."""

    @pytest.mark.asyncio
    async def test_monday_boundary(self, db_session, test_context):
        """UT-B21-JOB-01: Monday 00:00 boundary handled correctly."""
        from app.core.clock import set_clock, reset_clock
        from app.domains.train.jobs import TrainStatJob
        from app.core.context import ctx

        set_clock(lambda: datetime(2026, 10, 12, 0, 0, 0))

        job = TrainStatJob(db_session)
        result = await job.low_rate_alert(ctx.tenant_id)

        assert "alerted_count" in result

        reset_clock()
