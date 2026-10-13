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

from datetime import datetime, timedelta
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

    userTotal: int
    yesterdayEventCount: int
    pendingEventCount: int
    deadEventCount: int
    avgDelayMinutes: float
    p95DelayMinutes: float
    successRate24h: float
    dingtalkUnavailable: bool
    reconcileFailedTwice: bool


class DiffSummaryResponse(BaseSchema):
    """Diff summary response."""

    overrideCount: int
    pendingAssignCount: int
    localOrphanCount: int
    sameNameCount: int
    unboundCount: int


class EventListItem(BaseSchema):
    """Event list item."""

    id: str
    eventType: Optional[str] = None
    eventId: str
    subjectName: Optional[str] = None
    empNo: Optional[str] = None
    beforeDeptNames: Optional[str] = None
    afterDeptNames: Optional[str] = None
    status: str
    retryCount: int
    eventTime: Optional[str] = None
    processedTime: Optional[str] = None


class EventDetailResponse(BaseSchema):
    """Event detail response."""

    id: str
    eventId: str
    eventType: Optional[str] = None
    bizType: Optional[str] = None
    subjectUserId: Optional[str] = None
    subjectName: Optional[str] = None
    deptId: Optional[str] = None
    beforeDeptNames: Optional[str] = None
    afterDeptNames: Optional[str] = None
    status: str
    retryCount: int
    lastError: Optional[str] = None
    eventTime: Optional[str] = None
    receivedTime: Optional[str] = None
    processedTime: Optional[str] = None
    delaySeconds: Optional[int] = None
    payload: Optional[str] = None
    attempts: list = []


class ReplayPreviewResponse(BaseSchema):
    """Replay preview response."""

    count: int


class ReplayRequest(BaseSchema):
    """Replay request."""

    startTime: str
    endTime: str
    statuses: list[str]


class ReconcileBatchItem(BaseSchema):
    """Reconcile batch item."""

    id: str
    triggerType: Optional[str] = None
    status: str
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    diffCount: int = 0
    fixedCount: int = 0
    failReason: Optional[str] = None


class ReconcileResponse(BaseSchema):
    """Reconcile response."""

    batchId: str
    status: str


class UserDetailResponse(BaseSchema):
    """User detail for org sync view."""

    id: str
    nickname: str
    empNo: Optional[str] = None
    username: str
    status: str
    mainDeptName: Optional[str] = None
    deptNames: list[str] = []
    positionLabel: Optional[str] = None
    dingtalkBound: bool
    lastSyncTime: Optional[str] = None
    source: str
    roles: list = []
    dataScopeText: Optional[str] = None
    menuCount: int = 0
    recentEvents: list = []


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
    from app.domains.sys.models import ChangeLog, Dept, User, UserMapping

    from app.db.session import get_db_session

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
            Dept.local_orphan == True,
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
    deptId: Optional[str] = Query(None),
    eventTypes: Optional[str] = Query(None),
    statuses: Optional[str] = Query(None),
    startTime: Optional[str] = Query(None),
    endTime: Optional[str] = Query(None),
    sortBy: str = Query("eventTime"),
    sortOrder: str = Query("desc"),
    pageNo: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
) -> CommonResult:
    """Get paginated event list."""
    from app.core.clock import parse_datetime
    from app.services.org_sync_event import OrgSyncEventService

    tenant_id = ctx.tenant_id

    start = None
    end = None

    if startTime:
        start = parse_datetime(startTime)
    else:
        start = get_now() - timedelta(days=7)

    if endTime:
        end = parse_datetime(endTime)
    else:
        end = get_now()

    if (end - start).days > 90:
        raise BizError(1001, msg="时间范围不能超过90天")

    event_type_list = eventTypes.split(",") if eventTypes else None
    status_list = statuses.split(",") if statuses else None
    dept_id_int = int(deptId) if deptId else None

    service = OrgSyncEventService()
    result = await service.get_events_page(
        tenant_id=tenant_id,
        page_no=pageNo,
        page_size=pageSize,
        keyword=keyword,
        dept_id=dept_id_int,
        event_types=event_type_list,
        statuses=status_list,
        start_time=start,
        end_time=end,
        sort_by=sortBy,
        sort_order=sortOrder,
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
    startTime: str = Query(...),
    endTime: str = Query(...),
    statuses: str = Query(...),
) -> CommonResult[ReplayPreviewResponse]:
    """Preview replay count."""
    from app.core.clock import parse_datetime
    from app.services.org_sync_event import OrgSyncEventService

    tenant_id = ctx.tenant_id

    start = parse_datetime(startTime)
    end = parse_datetime(endTime)
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
    startTime: Optional[str] = Query(None),
    endTime: Optional[str] = Query(None),
    triggerTypes: Optional[str] = Query(None),
    statuses: Optional[str] = Query(None),
    pageNo: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
) -> CommonResult:
    """Get paginated reconcile batch list."""
    from app.domains.sys.models import OrgSyncBatch

    from app.db.session import get_db_session

    session = get_db_session()
    tenant_id = ctx.tenant_id

    query = session.query(OrgSyncBatch).filter(
        OrgSyncBatch.tenant_id == tenant_id,
        OrgSyncBatch.deleted == 0,
    )

    if statuses:
        status_list = statuses.split(",")
        query = query.filter(OrgSyncBatch.status.in_(status_list))

    if triggerTypes:
        trigger_list = triggerTypes.split(",")
        query = query.filter(OrgSyncBatch.trigger_type.in_(trigger_list))

    total = query.count()
    offset = (pageNo - 1) * pageSize
    batches = query.order_by(OrgSyncBatch.id.desc()).offset(offset).limit(pageSize).all()

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
            "pageNo": pageNo,
            "pageSize": pageSize,
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
    from app.domains.sys.models import OrgSyncBatch

    from app.db.session import get_db_session

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
    pageNo: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
) -> CommonResult:
    """Get reconcile batch items."""
    from app.domains.sys.models import OrgSyncBatchItem

    from app.db.session import get_db_session

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
    offset = (pageNo - 1) * pageSize
    items = query.order_by(OrgSyncBatchItem.id).offset(offset).limit(pageSize).all()

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
            "pageNo": pageNo,
            "pageSize": pageSize,
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
    from app.domains.sys.models import (
        Dept,
        Menu,
        OrgSyncEvent,
        Role,
        RoleMenu,
        User,
        UserDept,
        UserMapping,
        UserRole,
    )

    from app.db.session import get_db_session

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
