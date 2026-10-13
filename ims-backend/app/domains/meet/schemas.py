# app/domains/meet/schemas.py - Meeting domain schemas (B18-M18)
"""
Meeting domain request/response schemas.

All schemas use camelCase for API compatibility per global conventions.
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from app.core.serialization import BaseSchema


class AttendeesSchema(BaseSchema):
    """参会人结构。"""
    internal: list[int] = Field(default_factory=list, description="内部参会人 userId 列表")
    external: list[str] = Field(default_factory=list, description="外部参会人姓名列表")

    @field_validator("external")
    @classmethod
    def validate_external_names(cls, v: list[str]) -> list[str]:
        for name in v:
            if len(name) > 32:
                raise ValueError("外部参会人姓名不能超过 32 字")
        return v


class DecisionCreateSchema(BaseSchema):
    """创建决议事项。"""
    content: str = Field(..., max_length=512, description="决议内容")


class ActionItemCreateSchema(BaseSchema):
    """创建行动项。"""
    description: str = Field(..., max_length=256, description="行动项描述")
    assignee_user_id: int = Field(..., description="责任人 userId")
    due_date: date = Field(..., description="截止日期")


class MeetingMinutesCreateReq(BaseSchema):
    """创建会议纪要请求。"""
    title: str = Field(..., max_length=128, description="会议主题")
    meeting_date: datetime = Field(..., description="会议时间")
    meeting_room: Optional[str] = Field(None, max_length=64, description="会议室")
    recorder_user_id: Optional[int] = Field(None, description="记录人，默认当前用户")
    attendees: AttendeesSchema = Field(..., description="参会人")
    summary: Optional[str] = Field(None, max_length=20000, description="纪要正文（富文本）")
    decisions: list[DecisionCreateSchema] = Field(default_factory=list, description="决议事项")
    action_items: list[ActionItemCreateSchema] = Field(default_factory=list, description="行动项")
    client_token: str = Field(..., max_length=64, description="幂等键")

    @field_validator("attendees")
    @classmethod
    def validate_attendees(cls, v: AttendeesSchema) -> AttendeesSchema:
        if not v.internal and not v.external:
            raise ValueError("参会人不能为空")
        return v


class MeetingMinutesUpdateReq(BaseSchema):
    """编辑会议纪要请求。"""
    title: str = Field(..., max_length=128, description="会议主题")
    meeting_date: datetime = Field(..., description="会议时间")
    meeting_room: Optional[str] = Field(None, max_length=64, description="会议室")
    recorder_user_id: Optional[int] = Field(None, description="记录人")
    attendees: AttendeesSchema = Field(..., description="参会人")
    summary: Optional[str] = Field(None, max_length=20000, description="纪要正文（富文本）")
    decisions: list[DecisionCreateSchema] = Field(default_factory=list, description="决议事项")
    action_items: list[ActionItemCreateSchema] = Field(default_factory=list, description="行动项")
    base_version: int = Field(..., description="乐观锁版本号")


class AppendixCreateReq(BaseSchema):
    """创建附录请求。"""
    content: str = Field(..., min_length=1, max_length=1024, description="附录内容")


class ActionItemCloseReq(BaseSchema):
    """行动项回填请求。"""
    close_remark: str = Field(..., min_length=1, max_length=512, description="闭环说明")
    evidence_url: Optional[str] = Field(None, max_length=512, description="证据链接")


class DecisionVO(BaseSchema):
    """决议事项 VO。"""
    id: str
    seq: int
    content: str


class ActionItemVO(BaseSchema):
    """行动项 VO。"""
    id: str
    description: str
    assignee_user_id: str
    assignee_name: Optional[str] = None
    due_date: date
    status: str
    close_remark: Optional[str] = None
    evidence_url: Optional[str] = None
    closed_at: Optional[datetime] = None
    overdue_days: Optional[int] = None


class AppendixVO(BaseSchema):
    """附录 VO。"""
    id: str
    content: str
    creator_name: Optional[str] = None
    create_time: datetime


class MeetingMinutesVO(BaseSchema):
    """会议纪要 VO。"""
    id: str
    code: str
    title: str
    meeting_date: datetime
    meeting_room: Optional[str] = None
    dept_id: str
    dept_name: Optional[str] = None
    recorder_user_id: str
    recorder_name: Optional[str] = None
    attendees: AttendeesSchema
    attendee_names: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    status: str
    archived_at: Optional[datetime] = None
    archived_by: Optional[str] = None
    archived_by_name: Optional[str] = None
    create_time: datetime
    update_time: Optional[datetime] = None
    version: int

    decisions: list[DecisionVO] = Field(default_factory=list)
    action_items: list[ActionItemVO] = Field(default_factory=list)
    appendices: list[AppendixVO] = Field(default_factory=list)

    action_item_count: int = 0
    action_item_closed_count: int = 0


class MeetingMinutesListVO(BaseSchema):
    """会议纪要列表项 VO（不含子表详情）。"""
    id: str
    code: str
    title: str
    meeting_date: datetime
    recorder_user_id: str
    recorder_name: Optional[str] = None
    attendee_names: list[str] = Field(default_factory=list)
    status: str
    archived_at: Optional[datetime] = None
    action_item_count: int = 0
    action_item_closed_count: int = 0


class ArchiveRateResp(BaseSchema):
    """留痕率统计响应。"""
    total_meetings: int = Field(..., description="分母：会议时间已过的会议数")
    archived_count: int = Field(..., description="分子：已归档数")
    archive_rate: float = Field(..., description="留痕率（百分比）")
    unarchived_list: list["UnarchivedMinutesVO"] = Field(default_factory=list)


class UnarchivedMinutesVO(BaseSchema):
    """未归档会议 VO。"""
    minutes_no: str
    meeting_title: str
    meeting_date: datetime
    recorder_name: str
    hours_since_meeting: float


class MeetingMinutesListQuery(BaseSchema):
    """纪要列表查询参数。"""
    page_no: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    title: Optional[str] = None
    meeting_date_start: Optional[datetime] = None
    meeting_date_end: Optional[datetime] = None
    status: Optional[str] = None


class ArchiveRateQuery(BaseSchema):
    """留痕率查询参数。"""
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class MeetingCreateResp(BaseSchema):
    """创建会议响应（含 warnings）。"""
    data: MeetingMinutesVO
    warnings: list[int] = Field(default_factory=list)
