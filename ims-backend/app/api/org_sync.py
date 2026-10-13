# app/api/org_sync.py - Organization sync API (FP-B1-ORG-01~11)
"""
Organization sync API endpoints.

Implements:
- Sync metrics and alerts
- Sync diff queries
- Event queries and retry
- Reconcile batch queries
- Export
- User detail (org sync view)
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_permission
from app.core.clock import get_now
from app.core.context import ctx
from app.core.errors import BizError
from app.core.response import CommonResult
from app.core.serialization import BaseSchema

router = APIRouter(prefix="/org", tags=["Organization Sync"])


class SyncMetricsResponse(BaseSchema):
    """Sync metrics response."""

    user_total: int
    yesterday_event_count: int
    pending_event_count: int
    dead_event_count: int
    avg_delay_minutes: float
    p95_delay_minutes: float
    success_rate_24h: float
    dingtalk_unavailable: bool
    reconcile_failed_twice: bool


class DiffSummaryResponse(BaseSchema):
    """Diff summary response."""

    override_count: int
    pending_assign_count: int
    local_orphan_count: int
    same_name_count: int
    unbound_count: int


class EventListItem(BaseSchema):
    """Event list item."""

    id: str
    event_type: Optional[str] = None
    event_id: str
    subject_name: Optional[str] = None
    emp_no: Optional[str] = None
    before_dept_names: Optional[str] = None
    after_dept_names: Optional[str] = None
    status: str
    retry_count: int
    event_time: Optional[str] = None
    processed_time: Optional[str] = None


class EventDetailResponse(BaseSchema):
    """Event detail response."""

    id: str
    event_id: str
    event_type: Optional[str] = None
    biz_type: Optional[str] = None
    subject_user_id: Optional[str] = None
    subject_name: Optional[str] = None
    dept_id: Optional[str] = None
    before_dept_names: Optional[str] = None
    after_dept_names: Optional[str] = None
    status: str
    retry_count: int
    last_error: Optional[str] = None
    event_time: Optional[str] = None
    received_time: Optional[str] = None
    processed_time: Optional[str] = None
    delay_seconds: Optional[int] = None
    payload: Optional[str] = None
    attempts: list = []


class ReplayPreviewResponse(BaseSchema):
    """Replay preview response."""

    count: int


class ReplayRequest(BaseSchema):
    """Replay request."""

    start_time: str
    end_time: str
    statuses: list[str]


class ReconcileBatchItem(BaseSchema):
    """Reconcile batch item."""

    id: str
    trigger_type: Optional[str] = None
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    diff_count: int = 0
    fixed_count: int = 0
    fail_reason: Optional[str] = None


class ReconcileResponse(BaseSchema):
    """Reconcile response."""

    batch_id: str
    status: str


class UserDetailResponse(BaseSchema):
    """User detail for org sync view."""

    id: str
    nickname: str
    emp_no: Optional[str] = None
    username: str
    status: str
    main_dept_name: Optional[str] = None
    dept_names: list[str] = []
    position_label: Optional[str] = None
    dingtalk_bound: bool
    last_sync_time: Optional[str] = None
    source: str
    roles: list = []
    data_scope_text: Optional[str] = None
    menu_count: int = 0
    recent_events: list = []


@router.get(
    "/sync-metrics",
    response_model=CommonResult[SyncMetricsResponse],
    summary="获取同步概览",
    dependencies=[Depends(require_permission("ims:system:org-sync:query"))],
)
async def get_sync_metrics() -> CommonResult[SyncMetricsResponse]:
    """Get sync metrics for dashboard."""
    from app.services.org_sync_alert import OrgSyncAlertService

    tenant_id = ctx.tenant_id
    service = OrgSyncAlertService()
    metrics = await service.get_sync_metrics(tenant_id)
    return CommonResult.success(data=metrics)


@router.get(
    "/diffs/summary",
    response_model=CommonResult[DiffSummaryResponse],
    summary="获取同步差异汇总",
    dependencies=[Depends(require_permission("ims:system:org-sync:query"))],
)
async def get_diff_summary() -> CommonResult[DiffSummaryResponse]:
    """Get diff summary counts."""
    from app.db.session import get_db_session
    from app.domains.sys.models import ChangeLog, Dept, User, UserMapping

    session = get_db_session()
    tenant_id = ctx.tenant_id

    override_count = (
        session.query(ChangeLog)
        .filter(
            ChangeLog.tenant_id == tenant_id,
            ChangeLog.reason == "DINGTALK_OVERRIDE",
            ChangeLog.deleted == 0,
        )
        .count()
    )

    pending_assign = (
        session.query(Dept)
        .filter(
            Dept.tenant_id == tenant_id,
            Dept.source == "SYSTEM",
            Dept.name == "待分配",
            Dept.deleted == 0,
        )
        .first()
    )

    pending_assign_count = 0
    if pending_assign:
        from app.domains.sys.models import UserDept

        pending_assign_count = (
            session.query(UserDept)
            .filter(
                UserDept.tenant_id == tenant_id,
                UserDept.dept_id == pending_assign.id,
            )
            .count()
        )

    local_orphan_count = (
        session.query(Dept)
        .filter(
            Dept.tenant_id == tenant_id,
            Dept.local_orphan.is_(True),
            Dept.deleted == 0,
        )
        .count()
    )

    same_name_count = 0

    unbound_count = (
        session.query(User)
        .outerjoin(UserMapping, User.id == UserMapping.user_id)
        .filter(
            User.tenant_id == tenant_id,
            User.status == "ACTIVE",
            User.deleted == 0,
            UserMapping.id.is_(None),
        )
        .count()
    )

    return CommonResult.success(
        data={
            "overrideCount": override_count,
            "pendingAssignCount": pending_assign_count,
            "localOrphanCount": local_orphan_count,
            "sameNameCount": same_name_count,
            "unboundCount": unbound_count,
        }
    )


@router.get(
    "/events",
    response_model=CommonResult,
    summary="获取同步事件列表",
    dependencies=[Depends(require_permission("ims:system:org-sync:query"))],
)
async def get_events(
    keyword: Optional[str] = Query(None, max_length=50),
    dept_id: Optional[str] = Query(None, alias="deptId"),
    event_types: Optional[str] = Query(None, alias="eventTypes"),
    statuses: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None, alias="startTime"),
    end_time: Optional[str] = Query(None, alias="endTime"),
    sort_by: str = Query("eventTime", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult:
    """Get paginated event list."""
    from app.core.clock import parse_datetime
    from app.services.org_sync_event import OrgSyncEventService

    tenant_id = ctx.tenant_id

    start = parse_datetime(start_time) if start_time else get_now() - timedelta(days=7)
    end = parse_datetime(end_time) if end_time else get_now()

    if (end - start).days > 90:
        raise BizError(1001, msg="时间范围不能超过90天")

    event_type_list = event_types.split(",") if event_types else None
    status_list = statuses.split(",") if statuses else None
    dept_id_int = int(dept_id) if dept_id else None

    service = OrgSyncEventService()
    result = await service.get_events_page(
        tenant_id=tenant_id,
        page_no=page_no,
        page_size=page_size,
        keyword=keyword,
        dept_id=dept_id_int,
        event_types=event_type_list,
        statuses=status_list,
        start_time=start,
        end_time=end,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return CommonResult.success(data=result)


@router.get(
    "/events/{id}",
    response_model=CommonResult[EventDetailResponse],
    summary="获取事件详情",
    dependencies=[Depends(require_permission("ims:system:org-sync:query"))],
)
async def get_event_detail(id: str) -> CommonResult[EventDetailResponse]:
    """Get event detail by ID."""
    from app.services.org_sync_event import OrgSyncEventService

    tenant_id = ctx.tenant_id
    service = OrgSyncEventService()
    event = await service.get_event(int(id), tenant_id)

    if event is None:
        raise BizError(1504)

    return CommonResult.success(data=event)


@router.post(
    "/events/{id}/retry",
    response_model=CommonResult,
    summary="重试单条事件",
    dependencies=[Depends(require_permission("ims:system:org-sync:run"))],
)
async def retry_event(id: str) -> CommonResult:
    """Retry a single event."""
    from app.services.org_sync_event import OrgSyncEventService

    user_id = ctx.user_id
    service = OrgSyncEventService()
    await service.retry_event(int(id), operator_id=user_id)

    return CommonResult.success()


@router.get(
    "/events/replay-preview",
    response_model=CommonResult[ReplayPreviewResponse],
    summary="重放预览",
    dependencies=[Depends(require_permission("ims:system:org-sync:run"))],
)
async def get_replay_preview(
    start_time: str = Query(..., alias="startTime"),
    end_time: str = Query(..., alias="endTime"),
    statuses: str = Query(...),
) -> CommonResult[ReplayPreviewResponse]:
    """Preview replay count."""
    from app.core.clock import parse_datetime
    from app.services.org_sync_event import OrgSyncEventService

    tenant_id = ctx.tenant_id

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)
    status_list = statuses.split(",")

    service = OrgSyncEventService()
    result = await service.get_replay_preview(
        tenant_id=tenant_id,
        start_time=start,
        end_time=end,
        statuses=status_list,
    )

    return CommonResult.success(data=result)


@router.post(
    "/events/replay",
    response_model=CommonResult,
    summary="批量重放失败事件",
    dependencies=[Depends(require_permission("ims:system:org-sync:run"))],
)
async def replay_events(request: ReplayRequest) -> CommonResult:
    """Batch replay failed events."""
    from app.core.clock import parse_datetime
    from app.services.org_sync_event import OrgSyncEventService

    tenant_id = ctx.tenant_id
    user_id = ctx.user_id

    start = parse_datetime(request.startTime)
    end = parse_datetime(request.endTime)

    service = OrgSyncEventService()
    result = await service.replay_events(
        tenant_id=tenant_id,
        start_time=start,
        end_time=end,
        statuses=request.statuses,
        operator_id=user_id,
    )

    return CommonResult.success(data=result)


@router.get(
    "/reconcile-batches",
    response_model=CommonResult,
    summary="获取对账批次列表",
    dependencies=[Depends(require_permission("ims:system:org-sync:query"))],
)
async def get_reconcile_batches(
    start_time: Optional[str] = Query(None, alias="startTime"),
    end_time: Optional[str] = Query(None, alias="endTime"),
    trigger_types: Optional[str] = Query(None, alias="triggerTypes"),
    statuses: Optional[str] = Query(None),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult:
    """Get paginated reconcile batch list."""
    from app.db.session import get_db_session
    from app.domains.sys.models import OrgSyncBatch

    session = get_db_session()
    tenant_id = ctx.tenant_id

    query = session.query(OrgSyncBatch).filter(
        OrgSyncBatch.tenant_id == tenant_id,
        OrgSyncBatch.deleted == 0,
    )

    if statuses:
        status_list = statuses.split(",")
        query = query.filter(OrgSyncBatch.status.in_(status_list))

    if trigger_types:
        trigger_list = trigger_types.split(",")
        query = query.filter(OrgSyncBatch.trigger_type.in_(trigger_list))

    total = query.count()
    offset = (page_no - 1) * page_size
    batches = query.order_by(OrgSyncBatch.id.desc()).offset(offset).limit(page_size).all()

    items = [
        {
            "id": str(b.id),
            "triggerType": b.trigger_type,
            "status": b.status,
            "startedAt": b.started_at.isoformat() + "+08:00" if b.started_at else None,
            "completedAt": b.completed_at.isoformat() + "+08:00" if b.completed_at else None,
            "diffCount": b.diff_count,
            "fixedCount": b.fixed_count,
            "failReason": b.fail_reason,
        }
        for b in batches
    ]

    return CommonResult.success(
        data={
            "total": total,
            "list": items,
            "pageNo": page_no,
            "pageSize": page_size,
        }
    )


@router.get(
    "/reconcile-batches/{id}",
    response_model=CommonResult,
    summary="获取对账批次详情",
    dependencies=[Depends(require_permission("ims:system:org-sync:query"))],
)
async def get_reconcile_batch_detail(id: str) -> CommonResult:
    """Get reconcile batch detail."""
    from app.db.session import get_db_session
    from app.domains.sys.models import OrgSyncBatch

    session = get_db_session()
    tenant_id = ctx.tenant_id

    batch = session.query(OrgSyncBatch).filter(
        OrgSyncBatch.id == int(id),
        OrgSyncBatch.tenant_id == tenant_id,
        OrgSyncBatch.deleted == 0,
    ).first()

    if batch is None:
        raise BizError(1504)

    return CommonResult.success(
        data={
            "id": str(batch.id),
            "triggerType": batch.trigger_type,
            "operatorId": str(batch.operator_id) if batch.operator_id else None,
            "status": batch.status,
            "startedAt": batch.started_at.isoformat() + "+08:00" if batch.started_at else None,
            "completedAt": batch.completed_at.isoformat() + "+08:00" if batch.completed_at else None,
            "addedDepts": batch.added_depts,
            "updatedDepts": batch.updated_depts,
            "removedDepts": batch.removed_depts,
            "addedUsers": batch.added_users,
            "updatedUsers": batch.updated_users,
            "removedUsers": batch.removed_users,
            "diffCount": batch.diff_count,
            "fixedCount": batch.fixed_count,
            "errorMsg": batch.error_msg,
            "failReason": batch.fail_reason,
        }
    )


@router.get(
    "/reconcile-batches/{id}/items",
    response_model=CommonResult,
    summary="获取对账明细列表",
    dependencies=[Depends(require_permission("ims:system:org-sync:query"))],
)
async def get_reconcile_batch_items(
    id: str,
    result: Optional[str] = Query(None),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult:
    """Get reconcile batch items."""
    from app.db.session import get_db_session
    from app.domains.sys.models import OrgSyncBatchItem

    session = get_db_session()
    tenant_id = ctx.tenant_id

    query = session.query(OrgSyncBatchItem).filter(
        OrgSyncBatchItem.batch_id == int(id),
        OrgSyncBatchItem.tenant_id == tenant_id,
        OrgSyncBatchItem.deleted == 0,
    )

    if result:
        query = query.filter(OrgSyncBatchItem.result == result)

    total = query.count()
    offset = (page_no - 1) * page_size
    items = query.order_by(OrgSyncBatchItem.id).offset(offset).limit(page_size).all()

    return CommonResult.success(
        data={
            "total": total,
            "list": [
                {
                    "id": str(item.id),
                    "objectType": item.object_type,
                    "objectId": item.object_id,
                    "objectName": item.object_name,
                    "deptId": str(item.dept_id) if item.dept_id else None,
                    "action": item.action,
                    "beforeValue": item.before_value,
                    "afterValue": item.after_value,
                    "result": item.result,
                    "errorMsg": item.error_msg,
                }
                for item in items
            ],
            "pageNo": page_no,
            "pageSize": page_size,
        }
    )


@router.get(
    "/users/{id}",
    response_model=CommonResult[UserDetailResponse],
    summary="获取人员详情",
    dependencies=[Depends(require_permission("ims:system:org-sync:query"))],
)
async def get_user_detail(id: str) -> CommonResult[UserDetailResponse]:
    """Get user detail for org sync view."""
    from app.db.session import get_db_session
    from app.domains.sys.models import (
        Dept,
        OrgSyncEvent,
        Role,
        RoleMenu,
        User,
        UserDept,
        UserMapping,
        UserRole,
    )

    session = get_db_session()
    tenant_id = ctx.tenant_id

    user = session.query(User).filter(
        User.id == int(id),
        User.tenant_id == tenant_id,
        User.deleted == 0,
    ).first()

    if user is None:
        raise BizError(1504)

    mapping = session.query(UserMapping).filter(
        UserMapping.user_id == user.id,
        UserMapping.deleted == 0,
    ).first()

    user_depts = session.query(UserDept).filter(
        UserDept.user_id == user.id,
        UserDept.tenant_id == tenant_id,
    ).all()

    dept_ids = [ud.dept_id for ud in user_depts]
    depts = session.query(Dept).filter(Dept.id.in_(dept_ids)).all() if dept_ids else []
    dept_map = {d.id: d.name for d in depts}

    main_dept_name = None
    if user.main_dept_id:
        main_dept = session.query(Dept).filter(Dept.id == user.main_dept_id).first()
        if main_dept:
            main_dept_name = main_dept.name

    dept_names = [dept_map.get(ud.dept_id, "") for ud in user_depts if ud.dept_id in dept_map]

    user_roles = session.query(UserRole).join(
        Role, Role.id == UserRole.role_id
    ).filter(
        UserRole.user_id == user.id,
        Role.deleted == 0,
    ).all()

    role_ids = [ur.role_id for ur in user_roles]
    roles = session.query(Role).filter(Role.id.in_(role_ids)).all() if role_ids else []
    role_map = {r.id: r for r in roles}

    role_list = []
    for ur in user_roles:
        role = role_map.get(ur.role_id)
        if role:
            role_list.append({
                "id": str(role.id),
                "name": role.name,
                "source": ur.source,
                "status": role.status,
                "revokeAt": ur.revoke_at.isoformat() + "+08:00" if ur.revoke_at else None,
            })

    menu_count = 0
    if role_ids:
        menu_count = session.query(RoleMenu).filter(
            RoleMenu.role_id.in_(role_ids)
        ).distinct(RoleMenu.menu_id).count()

    recent_events = session.query(OrgSyncEvent).filter(
        OrgSyncEvent.subject_user_id == user.id,
        OrgSyncEvent.deleted == 0,
    ).order_by(OrgSyncEvent.event_time.desc()).limit(10).all()

    return CommonResult.success(
        data={
            "id": str(user.id),
            "nickname": user.nickname,
            "empNo": user.emp_no,
            "username": user.username,
            "status": user.status,
            "mainDeptName": main_dept_name,
            "deptNames": dept_names,
            "positionLabel": user.position_code,
            "dingtalkBound": mapping is not None,
            "lastSyncTime": mapping.last_sync_time.isoformat() + "+08:00" if mapping and mapping.last_sync_time else None,
            "source": user.source,
            "roles": role_list,
            "dataScopeText": None,
            "menuCount": menu_count,
            "recentEvents": [
                {
                    "id": str(e.id),
                    "eventType": e.event_type,
                    "eventTime": e.event_time.isoformat() + "+08:00" if e.event_time else None,
                    "status": e.status,
                }
                for e in recent_events
            ],
        }
    )


@router.post(
    "/events/export",
    response_model=CommonResult,
    summary="导出同步事件",
    dependencies=[Depends(require_permission("ims:system:org-sync:export"))],
)
async def export_events() -> CommonResult:
    """Export sync events (async via B0a export mechanism)."""
    return CommonResult.success(data={"message": "Export task created"})
