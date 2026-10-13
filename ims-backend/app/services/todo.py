# app/services/todo.py - 待办服务（B3 新建，P0）
"""
待办服务实现。

功能：
- create: 创建待办（幂等，钉钉推送，24h 去重）
- complete: 完成待办
- cancel: 作废待办（由源模块调用）
- close_for_user: 本人关闭（只写 assignee.closed=1）
- get_my_page: 我的待办分页
- get_my_count: 我的待办计数
- get_my_detail: 我的待办详情
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.cache import Cache
from app.core.clock import get_now
from app.core.context import ctx
from app.core.errors import BizError
from app.db.ids import assign_pk
from app.domains.sys.models import TodoAssignee, TodoItem

logger = logging.getLogger(__name__)

TODO_DEDUP_TTL = 86400  # 24 hours


class TodoType:
    """待办类型码值（dict_todo_type）。"""
    APPROVAL = "APPROVAL"  # 审批
    RETURN = "RETURN"      # 归还
    REVIEW = "REVIEW"      # 审核
    CONFIRM = "CONFIRM"    # 确认
    WARNING = "WARNING"    # 预警
    ALERT = "ALERT"        # 告警
    STUDY = "STUDY"        # 学习

    # 审批/审核类不能由用户直接关闭
    CANNOT_CLOSE = {APPROVAL, REVIEW}


class TodoStatus:
    """待办状态。"""
    PENDING = "PENDING"      # 待处理
    DONE = "DONE"            # 已完成
    CANCELLED = "CANCELLED"  # 已作废
    CLOSED = "CLOSED"        # 已关闭（保留，本批不写入）


def create(
    session: Session,
    *,
    todo_type: str,
    source_module: str,
    source_type: str,
    source_id: int,
    title: str,
    route: Optional[str] = None,
    assignee_user_ids: list[int],
    due_time: Optional[datetime] = None,
    content: Optional[str] = None,
) -> TodoItem:
    """
    创建待办。

    - 幂等：同 source_type + source_id + type 返回已有待办
    - 同时写 ims_sys_todo + ims_sys_todo_assignee
    - 双写 assignee_user_id（第一个处理人）
    - 创建时钉钉推送（24 小时去重）
    """
    tenant_id = ctx.tenant_id

    # 幂等检查
    existing = session.query(TodoItem).filter(
        TodoItem.tenant_id == tenant_id,
        TodoItem.source_type == source_type,
        TodoItem.source_id == source_id,
        TodoItem.type == todo_type,
        TodoItem.deleted == 0,
    ).first()
    if existing:
        return existing

    # 创建待办
    todo = TodoItem(
        tenant_id=tenant_id,
        type=todo_type,
        source_module=source_module,
        source_type=source_type,
        source_id=source_id,
        title=title,
        route=route,
        content=content,
        due_time=due_time,
        status=TodoStatus.PENDING,
        assignee_user_id=assignee_user_ids[0] if assignee_user_ids else None,
    )
    assign_pk(session, todo)
    session.add(todo)
    session.flush()

    # 创建处理人关联
    for user_id in assignee_user_ids:
        assignee = TodoAssignee(
            tenant_id=tenant_id,
            todo_id=todo.id,
            user_id=user_id,
            closed=0,
        )
        assign_pk(session, assignee)
        session.add(assignee)

    # 钉钉推送（24 小时去重）
    _push_dingtalk_notification(todo, assignee_user_ids)

    return todo


def complete(
    session: Session,
    *,
    source_type: str,
    source_id: int,
    by_user: int,
) -> Optional[TodoItem]:
    """
    完成待办。

    设 status=DONE, done_by, done_time。
    """
    tenant_id = ctx.tenant_id

    todo = session.query(TodoItem).filter(
        TodoItem.tenant_id == tenant_id,
        TodoItem.source_type == source_type,
        TodoItem.source_id == source_id,
        TodoItem.status == TodoStatus.PENDING,
        TodoItem.deleted == 0,
    ).first()

    if not todo:
        return None

    todo.status = TodoStatus.DONE
    todo.done_by = by_user
    todo.done_time = get_now()

    return todo


def cancel(
    session: Session,
    *,
    source_type: str,
    source_id: int,
    reason: Optional[str] = None,
) -> Optional[TodoItem]:
    """
    作废待办（由源模块调用）。

    设 status=CANCELLED。
    """
    tenant_id = ctx.tenant_id

    todo = session.query(TodoItem).filter(
        TodoItem.tenant_id == tenant_id,
        TodoItem.source_type == source_type,
        TodoItem.source_id == source_id,
        TodoItem.status == TodoStatus.PENDING,
        TodoItem.deleted == 0,
    ).first()

    if not todo:
        return None

    todo.status = TodoStatus.CANCELLED
    if reason:
        todo.content = f"{todo.content or ''}\n作废原因：{reason}".strip()

    return todo


def close_for_user(
    session: Session,
    *,
    todo_id: int,
    user_id: int,
) -> None:
    """
    本人关闭待办。

    只写 assignee.closed=1，不写 status=CLOSED。
    审批/审核类 → 1001"该待办需在来源单据中处理"
    非 PENDING → 1001"待办已处理或已关闭"
    """
    tenant_id = ctx.tenant_id

    # 查询待办
    todo = session.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.tenant_id == tenant_id,
        TodoItem.deleted == 0,
    ).first()

    if not todo:
        raise BizError(1504, "待办不存在或无权访问")

    # 查询处理人关联
    assignee = session.query(TodoAssignee).filter(
        TodoAssignee.todo_id == todo_id,
        TodoAssignee.user_id == user_id,
        TodoAssignee.tenant_id == tenant_id,
        TodoAssignee.deleted == 0,
    ).first()

    if not assignee:
        raise BizError(1504, "待办不存在或无权访问")

    # 审批/审核类不能关闭
    if todo.type in TodoType.CANNOT_CLOSE:
        raise BizError(1001, "该待办需在来源单据中处理")

    # 非 PENDING 不能关闭
    if todo.status != TodoStatus.PENDING:
        raise BizError(1001, "待办已处理或已关闭")

    # 已关闭的再关闭
    if assignee.closed:
        raise BizError(1001, "待办已处理或已关闭")

    # 关闭
    assignee.closed = 1
    assignee.closed_time = get_now()


def get_my_page(
    session: Session,
    *,
    user_id: int,
    todo_type: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page_no: int = 1,
    page_size: int = 20,
) -> dict:
    """
    我的待办分页。

    JOIN assignee 过滤 user_id 且 closed=0。
    CANCELLED 在任何状态下都不出现。
    "已处理"只含 DONE，按处理时间倒序。
    """
    tenant_id = ctx.tenant_id

    # 基础查询
    query = session.query(TodoItem).join(
        TodoAssignee,
        and_(
            TodoAssignee.todo_id == TodoItem.id,
            TodoAssignee.user_id == user_id,
            TodoAssignee.closed == 0,
            TodoAssignee.deleted == 0,
        )
    ).filter(
        TodoItem.tenant_id == tenant_id,
        TodoItem.deleted == 0,
        TodoItem.status != TodoStatus.CANCELLED,  # 已作废不出现
    )

    # 类型筛选（STUDY 只在"全部"里显示）
    if todo_type:
        query = query.filter(TodoItem.type == todo_type)

    # 状态筛选
    if status == "PENDING":
        query = query.filter(TodoItem.status == TodoStatus.PENDING)
    elif status == "DONE":
        query = query.filter(TodoItem.status == TodoStatus.DONE)
    elif status == "OVERDUE":
        # 已过期 = PENDING 且 due_time < now
        now = get_now()
        query = query.filter(
            TodoItem.status == TodoStatus.PENDING,
            TodoItem.due_time.isnot(None),
            TodoItem.due_time < now,
        )

    # 关键字搜索
    if keyword:
        query = query.filter(
            or_(
                TodoItem.title.contains(keyword),
                TodoItem.content.contains(keyword),
            )
        )

    # 计数
    total = query.count()

    # 排序：PENDING 按 due_time ASC NULLS LAST；DONE 按 done_time DESC
    if status == "DONE":
        query = query.order_by(TodoItem.done_time.desc())
    else:
        # PENDING 按逾期优先（有截止且已过期置顶），然后按截止时间升序
        query = query.order_by(
            TodoItem.due_time.is_(None),  # NULL 排最后
            TodoItem.due_time.asc(),
            TodoItem.create_time.desc(),
        )

    # 分页
    offset = (page_no - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return {
        "total": total,
        "pageNo": page_no,
        "pageSize": page_size,
        "list": [_todo_to_dict(item) for item in items],
    }


def get_my_count(
    session: Session,
    *,
    user_id: int,
) -> dict:
    """
    我的待办计数。

    返回 {total, byType: {APPROVAL: n, ...}, overdue: n}。
    只计 PENDING 且未关闭。
    """
    tenant_id = ctx.tenant_id
    now = get_now()

    # 基础查询
    base_query = session.query(TodoItem).join(
        TodoAssignee,
        and_(
            TodoAssignee.todo_id == TodoItem.id,
            TodoAssignee.user_id == user_id,
            TodoAssignee.closed == 0,
            TodoAssignee.deleted == 0,
        )
    ).filter(
        TodoItem.tenant_id == tenant_id,
        TodoItem.deleted == 0,
        TodoItem.status == TodoStatus.PENDING,
    )

    # 总数
    total = base_query.count()

    # 按类型分组（STUDY 也计入，但只在"全部"里显示）
    type_counts = session.query(
        TodoItem.type,
        func.count(TodoItem.id),
    ).join(
        TodoAssignee,
        and_(
            TodoAssignee.todo_id == TodoItem.id,
            TodoAssignee.user_id == user_id,
            TodoAssignee.closed == 0,
            TodoAssignee.deleted == 0,
        )
    ).filter(
        TodoItem.tenant_id == tenant_id,
        TodoItem.deleted == 0,
        TodoItem.status == TodoStatus.PENDING,
    ).group_by(TodoItem.type).all()

    by_type = {t: c for t, c in type_counts if t}

    # 逾期数
    overdue = base_query.filter(
        TodoItem.due_time.isnot(None),
        TodoItem.due_time < now,
    ).count()

    return {
        "total": total,
        "byType": by_type,
        "overdue": overdue,
    }


def get_my_detail(
    session: Session,
    *,
    todo_id: int,
    user_id: int,
) -> dict:
    """
    我的待办详情。

    他人/不存在 → 1504。
    """
    tenant_id = ctx.tenant_id

    # 查询待办
    todo = session.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.tenant_id == tenant_id,
        TodoItem.deleted == 0,
    ).first()

    if not todo:
        raise BizError(1504, "待办不存在或无权访问")

    # 查询处理人关联
    assignee = session.query(TodoAssignee).filter(
        TodoAssignee.todo_id == todo_id,
        TodoAssignee.user_id == user_id,
        TodoAssignee.tenant_id == tenant_id,
        TodoAssignee.deleted == 0,
    ).first()

    if not assignee:
        raise BizError(1504, "待办不存在或无权访问")

    return _todo_to_dict(todo, include_done_by_name=True, session=session)


def _todo_to_dict(
    todo: TodoItem,
    include_done_by_name: bool = False,
    session: Optional[Session] = None,
) -> dict:
    """将 TodoItem 转为字典。"""
    now = get_now()
    is_overdue = (
        todo.status == TodoStatus.PENDING
        and todo.due_time is not None
        and todo.due_time < now
    )
    overdue_days = 0
    if is_overdue and todo.due_time:
        overdue_days = (now - todo.due_time).days

    result = {
        "id": str(todo.id),
        "type": todo.type,
        "title": todo.title,
        "content": todo.content,
        "sourceModule": todo.source_module,
        "sourceType": todo.source_type,
        "sourceId": str(todo.source_id) if todo.source_id else None,
        "route": todo.route,
        "status": todo.status,
        "dueTime": todo.due_time.isoformat() if todo.due_time else None,
        "isOverdue": is_overdue,
        "overdueDays": overdue_days,
        "createTime": todo.create_time.isoformat() if todo.create_time else None,
        "doneTime": todo.done_time.isoformat() if todo.done_time else None,
        "doneBy": str(todo.done_by) if todo.done_by else None,
    }

    # 处理人姓名（详情页需要）
    if include_done_by_name and todo.done_by and session:
        from app.domains.sys.models import User
        user = session.query(User).filter(User.id == todo.done_by).first()
        result["doneByName"] = user.nickname if user else None

    return result


def _push_dingtalk_notification(todo: TodoItem, user_ids: list[int]) -> None:
    """钉钉推送（24 小时去重）。"""
    for user_id in user_ids:
        dedup_key = f"todo:{todo.source_type}:{todo.source_id}:{user_id}"
        if Cache.get(dedup_key):
            logger.debug(f"钉钉推送去重跳过: {dedup_key}")
            continue

        # TODO: 实际调用钉钉推送 API
        logger.info(f"钉钉推送待办: user={user_id}, title={todo.title}")

        # 设置去重标记
        Cache.set(dedup_key, "1", TODO_DEDUP_TTL)
