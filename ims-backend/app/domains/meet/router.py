# app/domains/meet/router.py - Meeting API endpoints (B18-M18)
"""
Meeting management API endpoints.

9 endpoints:
1. POST /minutes - 登记会议/录入纪要
2. GET /minutes/list - 纪要列表
3. GET /minutes/{id} - 纪要详情
4. PUT /minutes/{id} - 编辑纪要
5. PUT /minutes/{id}/archive - 归档
6. POST /minutes/{id}/appendix - 附录说明
7. DELETE /minutes/{id} - 删除
8. PUT /minutes/action-item/{itemId} - 行动项回填
9. GET /minutes/archive-rate - 留痕率统计
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    require_any_permission,
    require_login,
    require_permission,
)
from app.core.context import ctx
from app.core.pagination import PageParam
from app.core.response import CommonResult
from app.domains.meet.schemas import (
    ActionItemCloseReq,
    ActionItemVO,
    AppendixCreateReq,
    ArchiveRateResp,
    MeetingCreateResp,
    MeetingMinutesCreateReq,
    MeetingMinutesUpdateReq,
    MeetingMinutesVO,
)
from app.domains.meet.service import MeetingService

router = APIRouter()

PERM_QUERY = "ims:meet:minutes:query"
PERM_QUERY_SELF = "ims:meet:minutes:query-self"
PERM_ADD = "ims:meet:minutes:add"
PERM_EDIT = "ims:meet:minutes:edit"
PERM_ARCHIVE = "ims:meet:minutes:archive"
PERM_DELETE = "ims:meet:minutes:delete"
PERM_APPENDIX = "ims:meet:minutes:appendix"
PERM_SUPERVISE = "ims:meet:minutes:supervise"


async def _is_recorder(minutes_id: int) -> bool:
    """检查当前用户是否是指定纪要的记录人。"""
    from app.db.session import get_db_session
    from app.domains.meet.models import MeetingMinutes

    session = get_db_session()
    minutes = session.query(MeetingMinutes).filter(
        MeetingMinutes.id == minutes_id,
        MeetingMinutes.tenant_id == ctx.tenant_id,
        MeetingMinutes.deleted == 0,
    ).first()

    if not minutes:
        return False

    return minutes.recorder_user_id == ctx.user_id


@router.post(
    "/minutes",
    response_model=CommonResult[MeetingCreateResp],
    summary="登记会议/录入纪要",
    dependencies=[Depends(require_permission(PERM_ADD))],
)
async def create_minutes(request: MeetingMinutesCreateReq) -> CommonResult[MeetingCreateResp]:
    """
    登记会议或录入纪要 (MN-02, MN-03).

    - 正文为空 → REGISTERED
    - 正文非空 → MINUTES_RECORDED
    - 会后 > 24h → warnings 带 1116
    """

    service = MeetingService()
    result = await service.create_minutes(request)

    return CommonResult.success(data=MeetingCreateResp(
        data=result["data"],
        warnings=result["warnings"],
    ))


@router.get(
    "/minutes/list",
    response_model=CommonResult,
    summary="纪要列表",
    dependencies=[Depends(require_any_permission([PERM_QUERY, PERM_QUERY_SELF]))],
)
async def list_minutes(
    page_no: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    title: Optional[str] = None,
    meeting_date_start: Optional[datetime] = None,
    meeting_date_end: Optional[datetime] = None,
    status: Optional[str] = None,
) -> CommonResult:
    """
    纪要列表 (MN-01).

    按数据范围过滤。
    """

    service = MeetingService()
    result = await service.list_minutes(
        page_param=PageParam(page_no=page_no, page_size=page_size),
        title=title,
        meeting_date_start=meeting_date_start,
        meeting_date_end=meeting_date_end,
        status=status,
    )

    return CommonResult.success(data=result.model_dump())


@router.get(
    "/minutes/archive-rate",
    response_model=CommonResult[ArchiveRateResp],
    summary="留痕率统计",
    dependencies=[Depends(require_permission(PERM_SUPERVISE))],
)
async def get_archive_rate(
    date_range_start: Optional[datetime] = None,
    date_range_end: Optional[datetime] = None,
) -> CommonResult[ArchiveRateResp]:
    """
    留痕率统计 (ST-01).

    按数据范围过滤。
    """
    service = MeetingService()
    result = await service.get_archive_rate(
        date_range_start=date_range_start,
        date_range_end=date_range_end,
    )

    return CommonResult.success(data=result)


@router.get(
    "/minutes/{minutes_id}",
    response_model=CommonResult[MeetingMinutesVO],
    summary="纪要详情",
    dependencies=[Depends(require_any_permission([PERM_QUERY, PERM_QUERY_SELF]))],
)
async def get_minutes(minutes_id: int) -> CommonResult[MeetingMinutesVO]:
    """
    纪要详情 (MN-08).

    按数据范围过滤。
    """
    service = MeetingService()
    result = await service.get_minutes(minutes_id)

    return CommonResult.success(data=result)


@router.put(
    "/minutes/{minutes_id}",
    response_model=CommonResult[MeetingCreateResp],
    summary="编辑纪要",
    dependencies=[Depends(require_login)],
)
async def update_minutes(minutes_id: int, request: MeetingMinutesUpdateReq) -> CommonResult[MeetingCreateResp]:
    """
    编辑纪要 (MN-03, MN-04).

    - 记录人可编辑，无需 edit 权限
    - 非记录人需要 edit 权限
    - 已归档不可编辑 → 1117
    """
    is_recorder = await _is_recorder(minutes_id)
    if not is_recorder:
        from app.core.errors import BizError

        context = ctx.current_or_none
        if context is None or PERM_EDIT not in (context.perm_codes or set()):
            raise BizError.no_permission()

    service = MeetingService()
    result = await service.update_minutes(minutes_id, request)

    return CommonResult.success(data=MeetingCreateResp(
        data=result["data"],
        warnings=result["warnings"],
    ))


@router.put(
    "/minutes/{minutes_id}/archive",
    response_model=CommonResult[MeetingCreateResp],
    summary="归档",
    dependencies=[Depends(require_login)],
)
async def archive_minutes(minutes_id: int) -> CommonResult[MeetingCreateResp]:
    """
    归档纪要 (MN-05).

    - 记录人可归档，无需 archive 权限
    - 非记录人需要 archive 权限
    - REGISTERED 不可归档 → 1001
    - 已归档不可重复归档 → 1117
    """
    is_recorder = await _is_recorder(minutes_id)
    if not is_recorder:
        from app.core.errors import BizError

        context = ctx.current_or_none
        if context is None or PERM_ARCHIVE not in (context.perm_codes or set()):
            raise BizError.no_permission()

    service = MeetingService()
    result = await service.archive_minutes(minutes_id)

    return CommonResult.success(data=MeetingCreateResp(
        data=result["data"],
        warnings=result["warnings"],
    ))


@router.post(
    "/minutes/{minutes_id}/appendix",
    response_model=CommonResult[MeetingMinutesVO],
    summary="附录说明",
    dependencies=[Depends(require_login)],
)
async def add_appendix(minutes_id: int, request: AppendixCreateReq) -> CommonResult[MeetingMinutesVO]:
    """
    附录说明 (MN-06).

    - 记录人可添加，无需 appendix 权限
    - 非记录人需要 appendix 权限
    - 仅已归档可追加
    """
    is_recorder = await _is_recorder(minutes_id)
    if not is_recorder:
        from app.core.errors import BizError

        context = ctx.current_or_none
        if context is None or PERM_APPENDIX not in (context.perm_codes or set()):
            raise BizError.no_permission()

    service = MeetingService()
    result = await service.add_appendix(minutes_id, request)

    return CommonResult.success(data=result)


@router.delete(
    "/minutes/{minutes_id}",
    response_model=CommonResult,
    summary="删除纪要",
    dependencies=[Depends(require_permission(PERM_DELETE))],
)
async def delete_minutes(minutes_id: int) -> CommonResult:
    """
    删除纪要 (MN-07).

    - 需要 delete 权限
    - 已归档不可删除 → 1117
    """
    service = MeetingService()
    await service.delete_minutes(minutes_id)

    return CommonResult.success()


@router.put(
    "/minutes/action-item/{item_id}",
    response_model=CommonResult[ActionItemVO],
    summary="行动项回填",
    dependencies=[Depends(require_login)],
)
async def close_action_item(item_id: int, request: ActionItemCloseReq) -> CommonResult[ActionItemVO]:
    """
    行动项回填 (AI-02).

    - LOGIN_ONLY + 责任人校验
    - 非责任人 → 1118
    - 已闭环 → 1001
    """
    service = MeetingService()
    result = await service.close_action_item(item_id, request)

    return CommonResult.success(data=result)
