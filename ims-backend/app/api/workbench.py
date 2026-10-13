# ruff: noqa: B008
# app/api/workbench.py - 工作台 API 路由（B3 新建）
"""
工作台相关接口：
- GET /auth/workbench/dashboard - 工作台仪表盘
- GET /todo/my/page - 我的待办分页
- GET /todo/my/count - 我的待办计数
- GET /todo/my/get - 我的待办详情
- PUT /todo/my/close - 关闭待办
- GET /message/my/page - 我的消息分页
- GET /message/my/unread-count - 未读消息数
- GET /message/my/get - 消息详情
- POST /message/my/read - 标记已读
- POST /message/my/read-all - 全部已读
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_login
from app.core.response import CommonResult
from app.core.serialization import BaseSchema
from app.db.session import get_db
from app.services import message as message_service
from app.services import todo as todo_service
from app.services import workbench as workbench_service

# ============== Routers ==============

workbench_auth_router = APIRouter()
todo_router = APIRouter(dependencies=[Depends(require_login)])
message_router = APIRouter(dependencies=[Depends(require_login)])


# ============== Schemas ==============

class DashboardResponse(BaseSchema):
    """工作台仪表盘响应。"""
    todo_count: int
    todo_by_type: dict
    todo_overdue: int
    unread_message_count: int
    my_account_count: Optional[int] = None
    my_asset_count: Optional[int] = None
    my_approval_count: Optional[int] = None
    my_attendance_count: Optional[int] = None


class TodoItem(BaseSchema):
    """待办项。"""
    id: str
    type: Optional[str] = None
    title: str
    content: Optional[str] = None
    source_module: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    route: Optional[str] = None
    status: str
    due_time: Optional[str] = None
    is_overdue: bool = False
    overdue_days: int = 0
    create_time: Optional[str] = None
    done_time: Optional[str] = None
    done_by: Optional[str] = None
    done_by_name: Optional[str] = None


class TodoPageResponse(BaseSchema):
    """待办分页响应。"""
    total: int
    page_no: int
    page_size: int
    list: list[TodoItem]


class TodoCountResponse(BaseSchema):
    """待办计数响应。"""
    total: int
    by_type: dict
    overdue: int


class CloseRequest(BaseSchema):
    """关闭待办请求。"""
    id: int


class MessageItem(BaseSchema):
    """消息项。"""
    id: str
    title: str
    body: str
    event_type: Optional[str] = None
    source_module: Optional[str] = None
    route: Optional[str] = None
    ref_type: Optional[str] = None
    ref_id: Optional[str] = None
    read_status: str
    read_time: Optional[str] = None
    create_time: Optional[str] = None


class MessagePageResponse(BaseSchema):
    """消息分页响应。"""
    total: int
    page_no: int
    page_size: int
    list: list[MessageItem]


class MarkReadRequest(BaseSchema):
    """标记已读请求。"""
    ids: list[int]


class MarkReadResponse(BaseSchema):
    """标记已读响应。"""
    updated: int


# ============== Dashboard Endpoints ==============

@workbench_auth_router.get(
    "/workbench/dashboard",
    response_model=CommonResult[DashboardResponse],
    summary="获取工作台仪表盘数据",
    dependencies=[Depends(require_login)],
)
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult[DashboardResponse]:
    """获取工作台仪表盘数据。"""
    data = workbench_service.get_dashboard(db, user_id=current_user)
    return CommonResult(data=DashboardResponse(**data))


# ============== Todo Endpoints ==============

@todo_router.get(
    "/my/page",
    response_model=CommonResult[TodoPageResponse],
    summary="我的待办分页",
)
async def get_my_todos(
    type: Optional[str] = Query(None, description="待办类型"),
    status: Optional[str] = Query(None, description="状态"),
    keyword: Optional[str] = Query(None, description="关键字"),
    page_no: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult[TodoPageResponse]:
    """我的待办分页。"""
    data = todo_service.get_my_page(
        db,
        user_id=current_user,
        todo_type=type,
        status=status,
        keyword=keyword,
        page_no=page_no,
        page_size=page_size,
    )
    return CommonResult(data=TodoPageResponse(**data))


@todo_router.get(
    "/my/count",
    response_model=CommonResult[TodoCountResponse],
    summary="我的待办计数",
)
async def get_my_todo_count(
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult[TodoCountResponse]:
    """我的待办计数。"""
    data = todo_service.get_my_count(db, user_id=current_user)
    return CommonResult(data=TodoCountResponse(**data))


@todo_router.get(
    "/my/get",
    response_model=CommonResult[TodoItem],
    summary="我的待办详情",
)
async def get_my_todo_detail(
    id: int = Query(..., description="待办 ID"),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult[TodoItem]:
    """我的待办详情。"""
    data = todo_service.get_my_detail(db, todo_id=id, user_id=current_user)
    return CommonResult(data=TodoItem(**data))


@todo_router.put(
    "/my/close",
    response_model=CommonResult,
    summary="关闭待办",
)
async def close_my_todo(
    request: CloseRequest,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult:
    """关闭待办。"""
    todo_service.close_for_user(db, todo_id=request.id, user_id=current_user)
    return CommonResult(msg="操作成功")


# ============== Message Endpoints ==============

@message_router.get(
    "/my/page",
    response_model=CommonResult[MessagePageResponse],
    summary="我的消息分页",
)
async def get_my_messages(
    read_status: Optional[str] = Query(None, description="已读状态"),
    keyword: Optional[str] = Query(None, description="关键字"),
    page_no: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult[MessagePageResponse]:
    """我的消息分页。"""
    data = message_service.get_my_page(
        db,
        user_id=current_user,
        read_status=read_status,
        keyword=keyword,
        page_no=page_no,
        page_size=page_size,
    )
    return CommonResult(data=MessagePageResponse(**data))


@message_router.get(
    "/my/unread-count",
    response_model=CommonResult[int],
    summary="未读消息数",
)
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult[int]:
    """未读消息数。"""
    count = message_service.get_unread_count(db, user_id=current_user)
    return CommonResult(data=count)


@message_router.get(
    "/my/get",
    response_model=CommonResult[MessageItem],
    summary="消息详情",
)
async def get_my_message_detail(
    id: int = Query(..., description="消息 ID"),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult[MessageItem]:
    """消息详情。"""
    data = message_service.get_my_detail(db, message_id=id, user_id=current_user)
    return CommonResult(data=MessageItem(**data))


@message_router.post(
    "/my/read",
    response_model=CommonResult[MarkReadResponse],
    summary="标记已读",
)
async def mark_messages_read(
    request: MarkReadRequest,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult[MarkReadResponse]:
    """标记已读。"""
    data = message_service.mark_read(db, user_id=current_user, ids=request.ids)
    return CommonResult(data=MarkReadResponse(**data))


@message_router.post(
    "/my/read-all",
    response_model=CommonResult[MarkReadResponse],
    summary="全部已读",
)
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
) -> CommonResult[MarkReadResponse]:
    """全部已读。"""
    data = message_service.mark_all_read(db, user_id=current_user)
    return CommonResult(data=MarkReadResponse(**data))
