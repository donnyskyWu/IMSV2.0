# app/domains/train/models.py - Training domain models (B21)
"""
Training management models.

8 tables per 00-工作包.md §0.5:
- ims_train_material_cate: 资料分类
- ims_train_material: 培训资料
- ims_train_material_version: 资料版本快照
- ims_train_task: 学习任务
- ims_train_task_record: 学习记录
- ims_train_study_log: 学习日志/心跳
- ims_train_stat_daily: 每日汇总
- ims_train_dept_alert: 部门低完成率推送记录

Soft delete rule: deleted = id (not 1)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase


class TrainMaterialCate(AuditBase):
    """
    Training material category (FP-B21-MT-01/02).

    Table: ims_train_material_cate

    Rules:
    - Top-level nodes link to position via position_code
    - parent_id=0 for position nodes
    - Unique: (tenant_id, parent_id, cate_name, deleted)
    """

    __tablename__ = "ims_train_material_cate"

    parent_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="父分类ID，岗位节点为0"
    )
    position_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="顶层节点关联的岗位字典码"
    )
    cate_name: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="类别名称"
    )
    sort: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "parent_id", "cate_name", "deleted",
            name="uk_train_cate"
        ),
        Index("idx_train_cate_parent", "parent_id"),
        Index("idx_train_cate_position", "position_code"),
    )


class TrainMaterial(AuditBase):
    """
    Training material (FP-B21-MT-03~10).

    Table: ims_train_material

    Rules:
    - material_no format: MT+YYYYMMDD+seq
    - material_type: DOC/VIDEO/LINK
    - status: DRAFT/PUBLISHED/OFFLINE
    - convert_status: PENDING/DONE/FAILED (for DOC only)
    - link_url only http:// or https://
    """

    __tablename__ = "ims_train_material"

    material_no: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="编号 MT+日期+流水"
    )
    title: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="标题≤128"
    )
    cate_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属类别"
    )
    material_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="DOC/VIDEO/LINK"
    )
    file_key: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True, comment="文件服务键"
    )
    link_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="外链，仅http(s)"
    )
    position_codes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="关联岗位码JSON数组"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="版本号"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT", comment="DRAFT/PUBLISHED/OFFLINE"
    )
    convert_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="文档转换状态 PENDING/DONE/FAILED"
    )
    page_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="文档页数"
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="视频时长秒"
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="发布时间"
    )
    uploader_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="上传人"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "material_no", "deleted",
            name="uk_train_mat_no"
        ),
        Index("idx_train_mat_cate", "cate_id"),
        Index("idx_train_mat_status", "status"),
    )


class TrainMaterialVersion(AuditBase):
    """
    Material version snapshot (FP-B21-MT-06/07).

    Table: ims_train_material_version

    Rules:
    - Explicit tenant_id column
    - Unique: (tenant_id, material_id, version, deleted)
    - Soft delete then re-insert for version replacement
    """

    __tablename__ = "ims_train_material_version"

    material_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="资料ID"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="版本号"
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="快照标题"
    )
    file_key: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True, comment="快照文件"
    )
    pdf_key: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True, comment="转换后PDF"
    )
    link_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="外链"
    )
    page_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="页数"
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="视频时长秒"
    )
    editor_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="编辑人"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="版本创建时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "material_id", "version", "deleted",
            name="uk_mat_version"
        ),
        Index("idx_mat_version_material", "material_id"),
    )


class TrainTask(AuditBase):
    """
    Learning task (FP-B21-TK-01~11).

    Table: ims_train_task

    Rules:
    - task_no format: TT+YYYYMMDD+seq
    - assign_scope: BY_USER/BY_POSITION
    - confirm_type: DURATION/QUIZ
    - status: IN_PROGRESS/FINISHED
    - source: MANUAL/ONBOARDING
    - deleted_at written together with soft_delete
    """

    __tablename__ = "ims_train_task"

    task_no: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="编号 TT+日期+流水"
    )
    task_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="任务名称"
    )
    material_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="资料ID数组JSON"
    )
    assign_scope: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="BY_USER/BY_POSITION"
    )
    deadline: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="截止时间"
    )
    confirm_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="DURATION/QUIZ"
    )
    required_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="要求学时分钟"
    )
    quiz: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="问卷题目JSON"
    )
    pass_score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="及格分1-100"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="IN_PROGRESS", comment="IN_PROGRESS/FINISHED"
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MANUAL", comment="MANUAL/ONBOARDING"
    )
    source_position_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="入职自动指派来源岗位"
    )
    client_token: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="幂等令牌"
    )
    creator_dept_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="创建人部门(数据范围)"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="删除时间(soft_delete同写)"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "task_no", "deleted",
            name="uk_train_task_no"
        ),
        UniqueConstraint(
            "tenant_id", "client_token", "deleted",
            name="uk_train_task_token"
        ),
        Index("idx_train_task_status", "status"),
        Index("idx_train_task_creator_dept", "creator_dept_id"),
    )


class TrainTaskRecord(AuditBase):
    """
    Learning record (FP-B21-TK-08, FP-B21-ST-*).

    Table: ims_train_task_record

    Rules:
    - Unique: (tenant_id, task_id, user_id, deleted)
    - Soft delete then re-insert for assignment replacement
    - user_dept_id for data scope filtering
    """

    __tablename__ = "ims_train_task_record"

    task_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="任务ID"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="被指派学员"
    )
    progress: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="总进度0-100"
    )
    material_progress: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="单资料进度JSON {materialId: percent}"
    )
    effective_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="有效学时秒"
    )
    confirm_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="NOT_CONFIRMED",
        comment="NOT_CONFIRMED/CONFIRMED"
    )
    confirm_score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="问卷得分"
    )
    quiz_draft: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="暂存答案JSON"
    )
    attempt_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="作答次数"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="开始学习时间"
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="完成确认时间"
    )
    is_overdue: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否逾期完成"
    )
    todo_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="待办ID"
    )
    remind_due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="截止前提醒时间(幂等)"
    )
    remind_overdue_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="逾期提醒时间(幂等)"
    )
    user_dept_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="学员主部门(数据范围)"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "task_id", "user_id", "deleted",
            name="uk_train_record"
        ),
        Index("idx_train_record_task", "task_id"),
        Index("idx_train_record_user", "user_id"),
        Index("idx_train_record_user_dept", "user_dept_id"),
        Index("idx_train_record_confirm", "confirm_status"),
    )


class TrainStudyLog(AuditBase):
    """
    Study log / heartbeat (FP-B21-ST-03~05).

    Table: ims_train_study_log

    Rules:
    - Explicit tenant_id column
    - Unique: (tenant_id, record_id, material_id, stat_date, deleted)
    - watched_intervals: JSON array [[start, end], ...]
    """

    __tablename__ = "ims_train_study_log"

    record_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="学习记录ID"
    )
    material_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="资料ID"
    )
    stat_date: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="学习日期YYYY-MM-DD"
    )
    effective_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当日有效秒"
    )
    watched_intervals: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="视频已观看区间JSON [[0,30],[45,60]]"
    )
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="最后心跳"
    )
    last_position: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="视频位置秒/文档页码"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "record_id", "material_id", "stat_date", "deleted",
            name="uk_study_log"
        ),
        Index("idx_study_log_record", "record_id"),
        Index("idx_study_log_material", "material_id"),
    )


class TrainStatDaily(AuditBase):
    """
    Daily statistics summary (FP-B21-SS-02/06).

    Table: ims_train_stat_daily

    Rules:
    - Unique: (tenant_id, stat_date, dept_id)
    - Upsert pattern for daily job
    """

    __tablename__ = "ims_train_stat_daily"

    stat_date: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="统计日期YYYY-MM-DD"
    )
    dept_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="部门"
    )
    assigned_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="应完成人次"
    )
    finished_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已完成人次"
    )
    overdue_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="逾期人次"
    )
    total_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="总时长分钟"
    )
    finish_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True, comment="完成率"
    )
    avg_duration_minutes: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True, comment="人均时长"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "stat_date", "dept_id",
            name="uk_train_stat"
        ),
        Index("idx_train_stat_date", "stat_date"),
        Index("idx_train_stat_dept", "dept_id"),
    )


class TrainDeptAlert(AuditBase):
    """
    Low completion rate alert record (FP-B21-SS-06).

    Table: ims_train_dept_alert

    Rules:
    - Unique: (tenant_id, dept_id, week_start)
    - Prevents duplicate weekly alerts
    """

    __tablename__ = "ims_train_dept_alert"

    dept_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="部门"
    )
    week_start: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="周起始日YYYY-MM-DD"
    )
    notified_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="推送时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "dept_id", "week_start",
            name="uk_dept_alert"
        ),
        Index("idx_dept_alert_week", "week_start"),
    )
