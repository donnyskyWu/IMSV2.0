# app/domains/meet/models.py - Meeting domain models (B18-M18)
"""
Meeting domain models.

Implements:
- MeetingMinutes: 会议纪要主表
- MeetingDecision: 决议事项子表
- MeetingActionItem: 行动项子表
- MeetingAppendix: 附录说明子表
- MeetingClientToken: 幂等键存储
"""

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase, Base


class MeetingMinutes(AuditBase):
    """
    会议纪要主表 (MN-01~MN-08).

    Table: ims_meeting_minutes

    Rules:
    - 编号格式: MM + yyyyMMdd + 3 位流水（>999 时扩展为 4 位）
    - 状态: REGISTERED → MINUTES_RECORDED → ARCHIVED（终态）
    - 已归档不可修改/删除，仅可追加附录
    - 数据范围: dept_id OR 本人相关（recorder/attendees/action item assignee）
    """

    __tablename__ = "ims_meeting_minutes"
    __versioned__ = True

    code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="编号 MM+yyyyMMdd+3位流水"
    )
    title: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="会议主题"
    )
    meeting_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="会议时间"
    )
    meeting_room: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="会议室"
    )
    dept_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="记录人主部门（数据范围判定用）"
    )
    recorder_user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="记录人"
    )
    attendees: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="{internal: [userId], external: [name]}"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="纪要正文（富文本白名单净化后存储）"
    )
    import_from_ai_minutes: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="预留：是否从钉钉 AI 听记导入"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="REGISTERED/MINUTES_RECORDED/ARCHIVED"
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="归档时间"
    )
    archived_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="归档人"
    )
    remind_24h_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="已发送 24h 提醒时间（幂等用）"
    )
    remind_48h_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="已发送 48h 提醒时间（幂等用）"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="乐观锁版本号"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", "deleted", name="uk_minutes_code"),
        Index("idx_minutes_tenant_date", "tenant_id", "meeting_date"),
        Index("idx_minutes_status", "tenant_id", "status"),
        Index("idx_minutes_dept", "tenant_id", "dept_id"),
    )


class MeetingDecision(AuditBase):
    """
    决议事项子表.

    Table: ims_meeting_decision

    Rules:
    - 同一纪要内 seq 唯一
    - 内容 HTML 转义存储
    """

    __tablename__ = "ims_meeting_decision"

    minutes_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="关联纪要"
    )
    seq: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="序号"
    )
    content: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="决议内容（HTML 转义存储）"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "minutes_id", "seq", "deleted", name="uk_decision_seq"),
        Index("idx_decision_tenant", "tenant_id"),
    )


class MeetingActionItem(AuditBase):
    """
    行动项子表 (AI-01~AI-03).

    Table: ims_meeting_action_item

    Rules:
    - 责任人必须为本租户启用内部用户
    - 状态: OPEN → OVERDUE（定时任务标记）→ CLOSED（回填后）
    - 逾期满 1 天推送责任人，满 3 天升级推送 supervise 用户
    - 已闭环行动项不可修改
    """

    __tablename__ = "ims_meeting_action_item"

    minutes_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="关联纪要"
    )
    description: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="行动项描述"
    )
    assignee_user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="责任人"
    )
    due_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="截止日期"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", comment="OPEN/OVERDUE/CLOSED"
    )
    close_remark: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="闭环说明"
    )
    evidence_url: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="证据链接（仅 http/https）"
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="闭环时间"
    )
    todo_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="关联待办 ID"
    )
    notified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="逾期 1 天推送时间（幂等用）"
    )
    escalated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="逾期 3 天升级时间（幂等用）"
    )

    __table_args__ = (
        Index("idx_action_due", "due_date", "status"),
        Index("idx_action_tenant", "tenant_id"),
    )


class MeetingAppendix(AuditBase):
    """
    附录说明子表.

    Table: ims_meeting_appendix

    Rules:
    - 仅已归档纪要可追加
    - 内容 HTML 转义存储
    """

    __tablename__ = "ims_meeting_appendix"

    minutes_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="关联纪要"
    )
    content: Mapped[str] = mapped_column(
        String(1024), nullable=False, comment="附录内容（HTML 转义存储）"
    )

    __table_args__ = (
        Index("idx_appendix_tenant", "tenant_id"),
    )


class MeetingClientToken(Base):
    """
    幂等键存储.

    Table: ims_meeting_client_token

    Rules:
    - 24 小时 TTL
    - 存在时返回已有结果，不重复创建
    """

    __tablename__ = "ims_meeting_client_token"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    client_token: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="幂等键"
    )
    result_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="创建结果 ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="创建时间"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="过期时间（24h）"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "client_token", name="uk_client_token"),
        Index("idx_client_token_expires", "expires_at"),
    )
