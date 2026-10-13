# app/domains/train/schemas.py - Training domain schemas (B21)
"""
Pydantic request/response schemas for training module.

Follows project conventions:
- camelCase output via BaseSchema
- String IDs for frontend compatibility
- Error codes per 00-工作包.md Q-D27
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from app.core.serialization import BaseSchema

# ============== Category Schemas ==============

class CateTreeNode(BaseSchema):
    """Category tree node."""
    id: str
    parent_id: Optional[str] = None
    position_code: Optional[str] = None
    cate_name: str
    sort: int = 0
    children: list["CateTreeNode"] = []


class CateCreateRequest(BaseSchema):
    """Create category request."""
    parent_id: str
    cate_name: str = Field(..., min_length=1, max_length=64)
    sort: int = Field(default=0, ge=0)


class CateUpdateRequest(BaseSchema):
    """Update category request."""
    cate_name: Optional[str] = Field(None, min_length=1, max_length=64)
    sort: Optional[int] = Field(None, ge=0)


# ============== Material Schemas ==============

class MaterialListItem(BaseSchema):
    """Material list item."""
    id: str
    material_no: str
    title: str
    cate_id: str
    cate_name: Optional[str] = None
    material_type: str
    status: str
    convert_status: Optional[str] = None
    version: int
    page_count: Optional[int] = None
    duration_seconds: Optional[int] = None
    position_labels: list[str] = []
    published_at: Optional[str] = None
    create_time: Optional[str] = None


class MaterialDetail(BaseSchema):
    """Material detail response."""
    id: str
    material_no: str
    title: str
    cate_id: str
    cate_name: Optional[str] = None
    material_type: str
    file_key: Optional[str] = None
    link_url: Optional[str] = None
    position_codes: list[str] = []
    position_labels: list[str] = []
    version: int
    status: str
    convert_status: Optional[str] = None
    page_count: Optional[int] = None
    duration_seconds: Optional[int] = None
    pdf_key: Optional[str] = None
    published_at: Optional[str] = None
    uploader_name: Optional[str] = None
    create_time: Optional[str] = None
    versions: list["MaterialVersionItem"] = []


class MaterialVersionItem(BaseSchema):
    """Material version history item."""
    version: int
    title: Optional[str] = None
    file_key: Optional[str] = None
    pdf_key: Optional[str] = None
    link_url: Optional[str] = None
    page_count: Optional[int] = None
    duration_seconds: Optional[int] = None
    editor_name: Optional[str] = None
    created_at: str


class MaterialCreateRequest(BaseSchema):
    """Create material request."""
    title: str = Field(..., min_length=1, max_length=128)
    cate_id: str
    material_type: str = Field(..., pattern="^(DOC|VIDEO|LINK)$")
    file_key: Optional[str] = None
    link_url: Optional[str] = None
    position_codes: list[str] = []
    status: str = Field(default="DRAFT", pattern="^(DRAFT|PUBLISHED)$")


class MaterialUpdateRequest(BaseSchema):
    """Update material request."""
    title: Optional[str] = Field(None, min_length=1, max_length=128)
    cate_id: Optional[str] = None
    file_key: Optional[str] = None
    link_url: Optional[str] = None
    position_codes: Optional[list[str]] = None
    status: Optional[str] = Field(None, pattern="^(DRAFT|PUBLISHED|OFFLINE)$")


class WeeklyUpdateMetrics(BaseSchema):
    """Weekly update rate metrics."""
    total_count: int
    updated_count: int
    update_rate: float


# ============== Task Schemas ==============

class TaskListItem(BaseSchema):
    """Task list item."""
    id: str
    task_no: str
    task_name: str
    assign_scope: str
    confirm_type: str
    deadline: str
    status: str
    source: str
    assigned_count: int = 0
    finished_count: int = 0
    progress_rate: float = 0.0
    creator_name: Optional[str] = None
    create_time: Optional[str] = None


class TaskDetail(BaseSchema):
    """Task detail response."""
    id: str
    task_no: str
    task_name: str
    material_ids: list[str] = []
    materials: list["TaskMaterialItem"] = []
    assign_scope: str
    deadline: str
    confirm_type: str
    required_minutes: int = 0
    quiz: Optional[list["QuizQuestion"]] = None
    pass_score: Optional[int] = None
    status: str
    source: str
    assigned_users: list["TaskAssignedUser"] = []
    creator_name: Optional[str] = None
    create_time: Optional[str] = None


class TaskMaterialItem(BaseSchema):
    """Task material info."""
    id: str
    title: str
    material_type: str
    duration_seconds: Optional[int] = None
    page_count: Optional[int] = None


class TaskAssignedUser(BaseSchema):
    """Task assigned user info."""
    user_id: str
    nickname: str
    dept_name: Optional[str] = None
    progress: int = 0
    confirm_status: str


class QuizQuestion(BaseSchema):
    """Quiz question structure (Q-D8)."""
    type: str = Field(..., pattern="^(SINGLE|TRUE_FALSE)$")
    question: str
    options: Optional[list[str]] = None
    answer_index: Optional[int] = None
    answer_boolean: Optional[bool] = None


class TaskCreateRequest(BaseSchema):
    """Create task request."""
    task_name: str = Field(..., min_length=1, max_length=128)
    material_ids: list[str] = Field(..., min_length=1)
    assign_scope: str = Field(..., pattern="^(BY_USER|BY_POSITION)$")
    assigned_user_ids: Optional[list[str]] = None
    assigned_position_codes: Optional[list[str]] = None
    deadline: str
    confirm_type: str = Field(..., pattern="^(DURATION|QUIZ)$")
    required_minutes: Optional[int] = Field(None, ge=1)
    quiz: Optional[list[QuizQuestion]] = None
    pass_score: Optional[int] = Field(None, ge=1, le=100)
    client_token: Optional[str] = Field(None, max_length=64)

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError("Invalid datetime format") from e
        return v


class TaskUpdateRequest(BaseSchema):
    """Update task request (only IN_PROGRESS and before deadline)."""
    task_name: Optional[str] = Field(None, min_length=1, max_length=128)
    material_ids: Optional[list[str]] = None
    assigned_user_ids: Optional[list[str]] = None
    assigned_position_codes: Optional[list[str]] = None
    deadline: Optional[str] = None
    required_minutes: Optional[int] = Field(None, ge=1)
    quiz: Optional[list[QuizQuestion]] = None
    pass_score: Optional[int] = Field(None, ge=1, le=100)


class PositionPreviewResponse(BaseSchema):
    """Position users preview response."""
    position_code: str
    position_label: str
    user_count: int
    users: list["PositionPreviewUser"] = []


class PositionPreviewUser(BaseSchema):
    """Position preview user."""
    user_id: str
    nickname: str
    dept_name: Optional[str] = None


# ============== Record Schemas ==============

class RecordListItem(BaseSchema):
    """Learning record list item."""
    id: str
    task_id: str
    task_name: str
    user_id: str
    user_nickname: str
    user_dept_name: Optional[str] = None
    progress: int
    effective_minutes: int
    confirm_status: str
    confirm_score: Optional[int] = None
    is_overdue: bool
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


# ============== Study Schemas ==============

class MyTaskListItem(BaseSchema):
    """My task list item for study center."""
    id: str
    task_no: str
    task_name: str
    confirm_type: str
    deadline: str
    status: str
    progress: int
    confirm_status: str
    is_overdue: bool
    material_count: int


class StudyTaskDetail(BaseSchema):
    """Task detail for study execution."""
    id: str
    task_no: str
    task_name: str
    materials: list["StudyMaterialItem"]
    confirm_type: str
    required_minutes: int
    pass_score: Optional[int] = None
    deadline: str
    progress: int
    effective_minutes: int
    confirm_status: str
    quiz_draft: Optional[list[Any]] = None
    attempt_count: int = 0


class StudyMaterialItem(BaseSchema):
    """Material item for study."""
    id: str
    title: str
    material_type: str
    file_key: Optional[str] = None
    pdf_key: Optional[str] = None
    link_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    page_count: Optional[int] = None
    progress: int = 0
    last_position: Optional[int] = None


class ProgressReportRequest(BaseSchema):
    """Report progress request (heartbeat)."""
    material_id: str
    position: int = Field(..., ge=0)
    heartbeat_interval: float = Field(default=15.0, ge=1.0, le=60.0)


class QuizDraftSaveRequest(BaseSchema):
    """Save quiz draft request."""
    answers: list[Any]


class QuizSubmitRequest(BaseSchema):
    """Submit quiz request."""
    answers: list[Any]


class ConfirmResponse(BaseSchema):
    """Confirm completion response."""
    success: bool
    message: str
    score: Optional[int] = None
    passed: Optional[bool] = None


# ============== Statistics Schemas ==============

class FinishRateOverview(BaseSchema):
    """Finish rate overview."""
    total_assigned: int
    total_finished: int
    total_overdue: int
    finish_rate: float
    overdue_rate: float


class DeptStatItem(BaseSchema):
    """Department statistics item."""
    dept_id: str
    dept_name: str
    stat_date: str
    assigned_count: int
    finished_count: int
    overdue_count: int
    finish_rate: float
    avg_duration_minutes: float


class RankItem(BaseSchema):
    """Duration rank item."""
    rank: int
    user_id: str
    nickname: str
    dept_name: Optional[str] = None
    total_minutes: int


class OverdueItem(BaseSchema):
    """Overdue supervision item."""
    user_id: str
    nickname: str
    dept_name: Optional[str] = None
    task_id: str
    task_name: str
    deadline: str
    overdue_days: int


class MaterialHeatItem(BaseSchema):
    """Material heat item."""
    material_id: str
    title: str
    view_count: int
    completion_count: int
    avg_duration_minutes: float


# ============== AI Generation Schemas ==============

class AIGenerateRequest(BaseSchema):
    """AI quiz generation request."""
    material_ids: list[str] = Field(..., min_length=1)
    question_count: int = Field(default=10, ge=1, le=50)
    difficulty: str = Field(default="MEDIUM", pattern="^(EASY|MEDIUM|HARD)$")


class AIGenerateResponse(BaseSchema):
    """AI quiz generation response."""
    questions: list[QuizQuestion]
    material_titles: list[str]
