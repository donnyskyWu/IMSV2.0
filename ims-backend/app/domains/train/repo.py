# app/domains/train/repo.py - Training repository layer (B21)
"""
Repository layer for training module.

Handles database operations with explicit scope filtering.
Does NOT use __scope_fields__ for complex conditions.
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.context import ctx
from app.db.session import get_db_session
from app.domains.train.models import (
    TrainDeptAlert,
    TrainMaterial,
    TrainMaterialCate,
    TrainMaterialVersion,
    TrainStatDaily,
    TrainStudyLog,
    TrainTask,
    TrainTaskRecord,
)
from app.domains.train.scope import apply_record_scope_filter, apply_task_scope_filter


class TrainCateRepo:
    """Repository for material categories."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_db_session()

    def get_tree(self, tenant_id: int, position_code: Optional[str] = None) -> list[TrainMaterialCate]:
        """Get category tree, optionally filtered by position."""
        query = select(TrainMaterialCate).where(
            TrainMaterialCate.tenant_id == tenant_id,
            TrainMaterialCate.deleted == 0,
        )
        if position_code:
            query = query.where(
                or_(
                    TrainMaterialCate.position_code == position_code,
                    TrainMaterialCate.position_code.is_(None),
                )
            )
        query = query.order_by(TrainMaterialCate.sort, TrainMaterialCate.id)
        return list(self.session.scalars(query).all())

    def get_by_id(self, cate_id: int, tenant_id: int) -> Optional[TrainMaterialCate]:
        """Get category by ID."""
        return self.session.scalars(
            select(TrainMaterialCate).where(
                TrainMaterialCate.id == cate_id,
                TrainMaterialCate.tenant_id == tenant_id,
                TrainMaterialCate.deleted == 0,
            )
        ).first()

    def create(self, cate: TrainMaterialCate) -> TrainMaterialCate:
        """Create a new category."""
        self.session.add(cate)
        self.session.flush()
        return cate

    def has_children(self, cate_id: int, tenant_id: int) -> bool:
        """Check if category has child categories."""
        count = self.session.scalar(
            select(func.count()).where(
                TrainMaterialCate.parent_id == cate_id,
                TrainMaterialCate.tenant_id == tenant_id,
                TrainMaterialCate.deleted == 0,
            )
        )
        return (count or 0) > 0

    def has_materials(self, cate_id: int, tenant_id: int) -> bool:
        """Check if category has materials."""
        count = self.session.scalar(
            select(func.count()).where(
                TrainMaterial.cate_id == cate_id,
                TrainMaterial.tenant_id == tenant_id,
                TrainMaterial.deleted == 0,
            )
        )
        return (count or 0) > 0

    def soft_delete(self, cate: TrainMaterialCate) -> None:
        """Soft delete a category (deleted = id)."""
        cate.deleted = cate.id
        self.session.flush()


class TrainMaterialRepo:
    """Repository for training materials."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_db_session()

    def list_materials(
        self,
        tenant_id: int,
        cate_id: Optional[int] = None,
        status: Optional[str] = None,
        material_type: Optional[str] = None,
        keyword: Optional[str] = None,
        position_codes: Optional[list[str]] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[TrainMaterial], int]:
        """List materials with filters."""
        query = select(TrainMaterial).where(
            TrainMaterial.tenant_id == tenant_id,
            TrainMaterial.deleted == 0,
        )

        if cate_id:
            query = query.where(TrainMaterial.cate_id == cate_id)
        if status:
            query = query.where(TrainMaterial.status == status)
        if material_type:
            query = query.where(TrainMaterial.material_type == material_type)
        if keyword:
            query = query.where(TrainMaterial.title.contains(keyword))
        if position_codes:
            conditions = []
            for code in position_codes:
                conditions.append(TrainMaterial.position_codes.contains(f'"{code}"'))
            query = query.where(or_(*conditions))

        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.scalar(count_query) or 0

        query = query.order_by(TrainMaterial.create_time.desc())
        query = query.offset(offset).limit(limit)
        items = list(self.session.scalars(query).all())

        return items, total

    def get_by_id(self, material_id: int, tenant_id: int) -> Optional[TrainMaterial]:
        """Get material by ID."""
        return self.session.scalars(
            select(TrainMaterial).where(
                TrainMaterial.id == material_id,
                TrainMaterial.tenant_id == tenant_id,
                TrainMaterial.deleted == 0,
            )
        ).first()

    def get_by_ids(self, material_ids: list[int], tenant_id: int) -> list[TrainMaterial]:
        """Get materials by IDs."""
        if not material_ids:
            return []
        return list(
            self.session.scalars(
                select(TrainMaterial).where(
                    TrainMaterial.id.in_(material_ids),
                    TrainMaterial.tenant_id == tenant_id,
                    TrainMaterial.deleted == 0,
                )
            ).all()
        )

    def generate_material_no(self, tenant_id: int) -> str:
        """Generate material number MT+YYYYMMDD+seq."""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"MT{today}"

        max_no = self.session.scalar(
            select(func.max(TrainMaterial.material_no)).where(
                TrainMaterial.tenant_id == tenant_id,
                TrainMaterial.material_no.like(f"{prefix}%"),
            )
        )

        if max_no:
            seq = int(max_no[-4:]) + 1
        else:
            seq = 1

        return f"{prefix}{seq:04d}"

    def create(self, material: TrainMaterial) -> TrainMaterial:
        """Create a new material."""
        self.session.add(material)
        self.session.flush()
        return material

    def soft_delete(self, material: TrainMaterial) -> None:
        """Soft delete a material (offline)."""
        material.deleted = material.id
        material.status = "OFFLINE"
        self.session.flush()


class TrainMaterialVersionRepo:
    """Repository for material versions."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_db_session()

    def get_versions(self, material_id: int, tenant_id: int) -> list[TrainMaterialVersion]:
        """Get all versions for a material."""
        return list(
            self.session.scalars(
                select(TrainMaterialVersion)
                .where(
                    TrainMaterialVersion.material_id == material_id,
                    TrainMaterialVersion.tenant_id == tenant_id,
                    TrainMaterialVersion.deleted == 0,
                )
                .order_by(TrainMaterialVersion.version.desc())
            ).all()
        )

    def create(self, version: TrainMaterialVersion) -> TrainMaterialVersion:
        """Create a new version."""
        self.session.add(version)
        self.session.flush()
        return version


class TrainTaskRepo:
    """Repository for learning tasks."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_db_session()

    def list_tasks(
        self,
        tenant_id: int,
        ctx_data: dict,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[TrainTask], int]:
        """List tasks with scope filtering."""
        query = select(TrainTask).where(
            TrainTask.tenant_id == tenant_id,
            TrainTask.deleted == 0,
        )

        if status:
            query = query.where(TrainTask.status == status)
        if keyword:
            query = query.where(TrainTask.task_name.contains(keyword))

        from app.core.context import RequestContext
        mock_ctx = RequestContext(**ctx_data)
        query = apply_task_scope_filter(query, mock_ctx)

        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.scalar(count_query) or 0

        query = query.order_by(TrainTask.create_time.desc())
        query = query.offset(offset).limit(limit)
        items = list(self.session.scalars(query).all())

        return items, total

    def get_by_id(self, task_id: int, tenant_id: int) -> Optional[TrainTask]:
        """Get task by ID."""
        return self.session.scalars(
            select(TrainTask).where(
                TrainTask.id == task_id,
                TrainTask.tenant_id == tenant_id,
                TrainTask.deleted == 0,
            )
        ).first()

    def generate_task_no(self, tenant_id: int) -> str:
        """Generate task number TT+YYYYMMDD+seq."""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"TT{today}"

        max_no = self.session.scalar(
            select(func.max(TrainTask.task_no)).where(
                TrainTask.tenant_id == tenant_id,
                TrainTask.task_no.like(f"{prefix}%"),
            )
        )

        if max_no:
            seq = int(max_no[-4:]) + 1
        else:
            seq = 1

        return f"{prefix}{seq:04d}"

    def create(self, task: TrainTask) -> TrainTask:
        """Create a new task."""
        self.session.add(task)
        self.session.flush()
        return task

    def soft_delete(self, task: TrainTask) -> None:
        """Soft delete a task with deleted_at."""
        from app.core.clock import get_now
        task.deleted = task.id
        task.deleted_at = get_now()
        self.session.flush()


class TrainRecordRepo:
    """Repository for learning records."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_db_session()

    def get_by_task(self, task_id: int, tenant_id: int) -> list[TrainTaskRecord]:
        """Get all records for a task."""
        return list(
            self.session.scalars(
                select(TrainTaskRecord).where(
                    TrainTaskRecord.task_id == task_id,
                    TrainTaskRecord.tenant_id == tenant_id,
                    TrainTaskRecord.deleted == 0,
                )
            ).all()
        )

    def get_by_user_task(
        self, task_id: int, user_id: int, tenant_id: int
    ) -> Optional[TrainTaskRecord]:
        """Get record for specific user and task."""
        return self.session.scalars(
            select(TrainTaskRecord).where(
                TrainTaskRecord.task_id == task_id,
                TrainTaskRecord.user_id == user_id,
                TrainTaskRecord.tenant_id == tenant_id,
                TrainTaskRecord.deleted == 0,
            )
        ).first()

    def create(self, record: TrainTaskRecord) -> TrainTaskRecord:
        """Create a new record."""
        self.session.add(record)
        self.session.flush()
        return record

    def create_batch(self, records: list[TrainTaskRecord]) -> list[TrainTaskRecord]:
        """Create multiple records."""
        self.session.add_all(records)
        self.session.flush()
        return records

    def is_user_assigned(self, task_id: int, user_id: int, tenant_id: int) -> bool:
        """Check if user is assigned to task."""
        count = self.session.scalar(
            select(func.count()).where(
                TrainTaskRecord.task_id == task_id,
                TrainTaskRecord.user_id == user_id,
                TrainTaskRecord.tenant_id == tenant_id,
                TrainTaskRecord.deleted == 0,
            )
        )
        return (count or 0) > 0

    def get_assigned_dept_ids(self, task_id: int, tenant_id: int) -> list[int]:
        """Get department IDs of assigned users."""
        result = self.session.scalars(
            select(TrainTaskRecord.user_dept_id)
            .where(
                TrainTaskRecord.task_id == task_id,
                TrainTaskRecord.tenant_id == tenant_id,
                TrainTaskRecord.deleted == 0,
                TrainTaskRecord.user_dept_id.isnot(None),
            )
            .distinct()
        ).all()
        return [d for d in result if d]

    def count_by_task(self, task_id: int, tenant_id: int) -> dict:
        """Get counts for a task."""
        total = self.session.scalar(
            select(func.count()).where(
                TrainTaskRecord.task_id == task_id,
                TrainTaskRecord.tenant_id == tenant_id,
                TrainTaskRecord.deleted == 0,
            )
        ) or 0

        finished = self.session.scalar(
            select(func.count()).where(
                TrainTaskRecord.task_id == task_id,
                TrainTaskRecord.tenant_id == tenant_id,
                TrainTaskRecord.deleted == 0,
                TrainTaskRecord.confirm_status == "CONFIRMED",
            )
        ) or 0

        return {"total": total, "finished": finished}


class TrainStudyLogRepo:
    """Repository for study logs."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_db_session()

    def get_or_create_today(
        self,
        record_id: int,
        material_id: int,
        tenant_id: int,
        stat_date: str,
    ) -> TrainStudyLog:
        """Get or create study log for today."""
        log = self.session.scalars(
            select(TrainStudyLog).where(
                TrainStudyLog.record_id == record_id,
                TrainStudyLog.material_id == material_id,
                TrainStudyLog.tenant_id == tenant_id,
                TrainStudyLog.stat_date == stat_date,
                TrainStudyLog.deleted == 0,
            )
        ).first()

        if not log:
            log = TrainStudyLog(
                tenant_id=tenant_id,
                record_id=record_id,
                material_id=material_id,
                stat_date=stat_date,
                effective_seconds=0,
            )
            self.session.add(log)
            self.session.flush()

        return log


class TrainStatRepo:
    """Repository for statistics."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_db_session()

    def upsert_daily(
        self,
        tenant_id: int,
        stat_date: str,
        dept_id: int,
        assigned_count: int,
        finished_count: int,
        overdue_count: int,
        total_duration_minutes: int,
    ) -> TrainStatDaily:
        """Upsert daily statistics."""
        existing = self.session.scalars(
            select(TrainStatDaily).where(
                TrainStatDaily.tenant_id == tenant_id,
                TrainStatDaily.stat_date == stat_date,
                TrainStatDaily.dept_id == dept_id,
                TrainStatDaily.deleted == 0,
            )
        ).first()

        finish_rate = (
            round(finished_count / assigned_count * 100, 2)
            if assigned_count > 0
            else 0
        )
        avg_duration = (
            round(total_duration_minutes / assigned_count, 2)
            if assigned_count > 0
            else 0
        )

        if existing:
            existing.assigned_count = assigned_count
            existing.finished_count = finished_count
            existing.overdue_count = overdue_count
            existing.total_duration_minutes = total_duration_minutes
            existing.finish_rate = finish_rate
            existing.avg_duration_minutes = avg_duration
            self.session.flush()
            return existing
        else:
            stat = TrainStatDaily(
                tenant_id=tenant_id,
                stat_date=stat_date,
                dept_id=dept_id,
                assigned_count=assigned_count,
                finished_count=finished_count,
                overdue_count=overdue_count,
                total_duration_minutes=total_duration_minutes,
                finish_rate=finish_rate,
                avg_duration_minutes=avg_duration,
            )
            self.session.add(stat)
            self.session.flush()
            return stat

    def get_dept_stats(
        self,
        tenant_id: int,
        start_date: str,
        end_date: str,
        dept_ids: Optional[list[int]] = None,
    ) -> list[TrainStatDaily]:
        """Get department statistics for date range."""
        query = select(TrainStatDaily).where(
            TrainStatDaily.tenant_id == tenant_id,
            TrainStatDaily.stat_date >= start_date,
            TrainStatDaily.stat_date <= end_date,
            TrainStatDaily.deleted == 0,
        )
        if dept_ids:
            query = query.where(TrainStatDaily.dept_id.in_(dept_ids))
        query = query.order_by(TrainStatDaily.stat_date, TrainStatDaily.dept_id)
        return list(self.session.scalars(query).all())


class TrainAlertRepo:
    """Repository for department alerts."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_db_session()

    def has_alert(self, tenant_id: int, dept_id: int, week_start: str) -> bool:
        """Check if alert already sent for this week."""
        count = self.session.scalar(
            select(func.count()).where(
                TrainDeptAlert.tenant_id == tenant_id,
                TrainDeptAlert.dept_id == dept_id,
                TrainDeptAlert.week_start == week_start,
            )
        )
        return (count or 0) > 0

    def create(self, alert: TrainDeptAlert) -> TrainDeptAlert:
        """Create alert record."""
        self.session.add(alert)
        self.session.flush()
        return alert
