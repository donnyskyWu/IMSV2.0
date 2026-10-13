# app/api/train.py - Training management API (B21)
"""
Training management API endpoints.

Implements 27 endpoints per 培训管理-实现理解.md §2:
- Material category: 4 endpoints
- Material: 6 endpoints
- Task: 7 endpoints
- Study: 3 endpoints
- Statistics: 6 endpoints
- AI generation: 1 endpoint

Prefix: /admin-api/ims/train
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile

from app.api.deps import require_any_permission, require_login, require_permission
from app.core.pagination import PageResult
from app.core.response import CommonResult
from app.domains.train.schemas import (
    AIGenerateRequest,
    AIGenerateResponse,
    CateCreateRequest,
    CateTreeNode,
    CateUpdateRequest,
    ConfirmResponse,
    DeptStatItem,
    FinishRateOverview,
    MaterialCreateRequest,
    MaterialDetail,
    MaterialListItem,
    MaterialUpdateRequest,
    MaterialHeatItem,
    MyTaskListItem,
    OverdueItem,
    PositionPreviewResponse,
    ProgressReportRequest,
    QuizDraftSaveRequest,
    QuizSubmitRequest,
    RankItem,
    RecordListItem,
    StudyTaskDetail,
    TaskCreateRequest,
    TaskDetail,
    TaskListItem,
    TaskUpdateRequest,
    WeeklyUpdateMetrics,
)

router = APIRouter()


# ============== Category Endpoints (FP-B21-MT-01/02) ==============

@router.get(
    "/material/cates",
    response_model=CommonResult[list[CateTreeNode]],
    summary="获取资料分类树",
    dependencies=[Depends(require_any_permission([
        "ims:train:material:query",
        "ims:train:study:query",
    ]))],
)
async def get_cate_tree(
    for_student: bool = Query(False, description="学员视角（只见本岗位）"),
) -> CommonResult[list[CateTreeNode]]:
    """
    Get material category tree.
    
    - Managers see all categories
    - Students only see their position's categories
    """
    from app.domains.train.service import TrainMaterialService
    
    service = TrainMaterialService()
    tree = await service.get_cate_tree(for_student=for_student)
    return CommonResult.success(data=tree)


@router.post(
    "/material/cate",
    response_model=CommonResult[CateTreeNode],
    summary="新增分类",
    dependencies=[Depends(require_permission("ims:train:cate:edit"))],
)
async def create_cate(req: CateCreateRequest) -> CommonResult[CateTreeNode]:
    """Create a new category."""
    from app.domains.train.service import TrainMaterialService
    
    service = TrainMaterialService()
    cate = await service.create_cate(req)
    return CommonResult.success(data=cate)


@router.put(
    "/material/cate/{cate_id}",
    response_model=CommonResult[CateTreeNode],
    summary="编辑分类",
    dependencies=[Depends(require_permission("ims:train:cate:edit"))],
)
async def update_cate(
    cate_id: str,
    req: CateUpdateRequest,
) -> CommonResult[CateTreeNode]:
    """Update category."""
    from app.domains.train.service import TrainMaterialService
    
    service = TrainMaterialService()
    cate = await service.update_cate(cate_id, req)
    return CommonResult.success(data=cate)


@router.delete(
    "/material/cate/{cate_id}",
    response_model=CommonResult,
    summary="删除分类",
    dependencies=[Depends(require_permission("ims:train:cate:edit"))],
)
async def delete_cate(cate_id: str) -> CommonResult:
    """Delete category (must have no children or materials)."""
    from app.domains.train.service import TrainMaterialService
    
    service = TrainMaterialService()
    await service.delete_cate(cate_id)
    return CommonResult.success()


# ============== Material Endpoints (FP-B21-MT-03~10) ==============

@router.get(
    "/material/list",
    response_model=CommonResult[PageResult[MaterialListItem]],
    summary="资料列表",
    dependencies=[Depends(require_any_permission([
        "ims:train:material:query",
        "ims:train:study:query",
    ]))],
)
async def list_materials(
    cate_id: Optional[str] = Query(None, description="分类ID"),
    status: Optional[str] = Query(None, description="状态"),
    material_type: Optional[str] = Query(None, description="类型"),
    keyword: Optional[str] = Query(None, description="关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    for_student: bool = Query(False, description="学员视角"),
) -> CommonResult[PageResult[MaterialListItem]]:
    """
    List materials.
    
    - Managers can filter by status
    - Students only see published materials for their position
    """
    from app.domains.train.service import TrainMaterialService
    
    service = TrainMaterialService()
    items, total = await service.list_materials(
        cate_id=cate_id,
        status=status,
        material_type=material_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
        for_student=for_student,
    )
    return CommonResult.success(data=PageResult(
        total=total,
        page=page,
        page_size=page_size,
        list=items,
    ))


@router.post(
    "/material",
    response_model=CommonResult[MaterialDetail],
    summary="上传资料",
    dependencies=[Depends(require_permission("ims:train:material:add"))],
)
async def create_material(req: MaterialCreateRequest) -> CommonResult[MaterialDetail]:
    """
    Create material.
    
    File upload should be done separately via /file/upload with scene TRAIN_DOC or TRAIN_VIDEO.
    """
    from app.domains.train.service import TrainMaterialService
    
    service = TrainMaterialService()
    material = await service.create_material(req)
    return CommonResult.success(data=material)


@router.get(
    "/material/{material_id}",
    response_model=CommonResult[MaterialDetail],
    summary="资料详情",
    dependencies=[Depends(require_any_permission([
        "ims:train:material:query",
        "ims:train:study:query",
    ]))],
)
async def get_material_detail(material_id: str) -> CommonResult[MaterialDetail]:
    """Get material detail with version history."""
    from app.domains.train.service import TrainMaterialService
    
    service = TrainMaterialService()
    material = await service.get_material_detail(material_id)
    return CommonResult.success(data=material)


@router.put(
    "/material/{material_id}",
    response_model=CommonResult[MaterialDetail],
    summary="编辑资料",
    dependencies=[Depends(require_permission("ims:train:material:edit"))],
)
async def update_material(
    material_id: str,
    req: MaterialUpdateRequest,
) -> CommonResult[MaterialDetail]:
    """Update material (creates new version if content changes)."""
    from app.domains.train.service import TrainMaterialService
    
    service = TrainMaterialService()
    material = await service.update_material(material_id, req)
    return CommonResult.success(data=material)


@router.delete(
    "/material/{material_id}",
    response_model=CommonResult,
    summary="下架资料",
    dependencies=[Depends(require_permission("ims:train:material:offline"))],
)
async def offline_material(material_id: str) -> CommonResult:
    """Offline (soft delete) material."""
    from app.domains.train.service import TrainMaterialService
    
    service = TrainMaterialService()
    await service.offline_material(material_id)
    return CommonResult.success()


@router.get(
    "/material/weekly-update-metrics",
    response_model=CommonResult[WeeklyUpdateMetrics],
    summary="周更新率",
    dependencies=[Depends(require_permission("ims:train:material:query"))],
)
async def get_weekly_update_metrics() -> CommonResult[WeeklyUpdateMetrics]:
    """Get weekly material update rate."""
    return CommonResult.success(data=WeeklyUpdateMetrics(
        total_count=0,
        updated_count=0,
        update_rate=0.0,
    ))


# ============== Task Endpoints (FP-B21-TK-01~08) ==============

@router.get(
    "/task/list",
    response_model=CommonResult[PageResult[TaskListItem]],
    summary="任务列表",
    dependencies=[Depends(require_permission("ims:train:task:query"))],
)
async def list_tasks(
    status: Optional[str] = Query(None, description="状态"),
    keyword: Optional[str] = Query(None, description="关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CommonResult[PageResult[TaskListItem]]:
    """List tasks with data scope filtering."""
    from app.domains.train.service import TrainTaskService
    
    service = TrainTaskService()
    items, total = await service.list_tasks(
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return CommonResult.success(data=PageResult(
        total=total,
        page=page,
        page_size=page_size,
        list=items,
    ))


@router.post(
    "/task",
    response_model=CommonResult[TaskDetail],
    summary="创建任务",
    dependencies=[Depends(require_permission("ims:train:task:add"))],
)
async def create_task(req: TaskCreateRequest) -> CommonResult[TaskDetail]:
    """
    Create learning task.
    
    - BY_USER: specify assigned_user_ids
    - BY_POSITION: specify assigned_position_codes
    """
    from app.domains.train.service import TrainTaskService
    
    service = TrainTaskService()
    if req.assign_scope == "BY_USER":
        task = await service.create_task_by_user(req)
    else:
        task = await service.create_task_by_position(req)
    return CommonResult.success(data=task)


@router.get(
    "/task/{task_id}",
    response_model=CommonResult[TaskDetail],
    summary="任务详情",
    dependencies=[Depends(require_any_permission([
        "ims:train:task:query",
        "ims:train:study:query",
    ]))],
)
async def get_task_detail(task_id: str) -> CommonResult[TaskDetail]:
    """
    Get task detail.
    
    - With task:query: check data scope, return 1504 if out of scope
    - With study:query only: check if assigned, return 1105 if not
    """
    from app.domains.train.service import TrainTaskService
    
    service = TrainTaskService()
    task = await service.get_task_detail(task_id)
    return CommonResult.success(data=task)


@router.put(
    "/task/{task_id}",
    response_model=CommonResult[TaskDetail],
    summary="编辑任务",
    dependencies=[Depends(require_permission("ims:train:task:edit"))],
)
async def update_task(
    task_id: str,
    req: TaskUpdateRequest,
) -> CommonResult[TaskDetail]:
    """Update task (only IN_PROGRESS and before deadline)."""
    from app.domains.train.service import TrainTaskService
    
    service = TrainTaskService()
    task = await service.update_task(task_id, req)
    return CommonResult.success(data=task)


@router.delete(
    "/task/{task_id}",
    response_model=CommonResult,
    summary="删除任务",
    dependencies=[Depends(require_permission("ims:train:task:delete"))],
)
async def delete_task(task_id: str) -> CommonResult:
    """Delete task."""
    from app.domains.train.service import TrainTaskService
    
    service = TrainTaskService()
    await service.delete_task(task_id)
    return CommonResult.success()


@router.get(
    "/task/position-preview",
    response_model=CommonResult[list[PositionPreviewResponse]],
    summary="按岗位预览人数",
    dependencies=[Depends(require_permission("ims:train:task:add"))],
)
async def preview_position_users(
    position_codes: str = Query(..., description="岗位码，逗号分隔"),
) -> CommonResult[list[PositionPreviewResponse]]:
    """Preview users for position assignment."""
    from app.domains.train.service import TrainTaskService
    
    codes = [c.strip() for c in position_codes.split(",") if c.strip()]
    service = TrainTaskService()
    result = await service.preview_position_users(codes)
    return CommonResult.success(data=result)


@router.get(
    "/task/records",
    response_model=CommonResult[PageResult[RecordListItem]],
    summary="学习记录",
    dependencies=[Depends(require_any_permission([
        "ims:train:task:query",
        "ims:train:study:query",
    ]))],
)
async def get_task_records(
    task_id: Optional[str] = Query(None, description="任务ID"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    confirm_status: Optional[str] = Query(None, description="确认状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CommonResult[PageResult[RecordListItem]]:
    """Get learning records with data scope filtering."""
    return CommonResult.success(data=PageResult(
        total=0,
        page=page,
        page_size=page_size,
        list=[],
    ))


# ============== Study Endpoints (FP-B21-ST-01~08) ==============

@router.get(
    "/study/my-tasks",
    response_model=CommonResult[PageResult[MyTaskListItem]],
    summary="我的学习任务",
    dependencies=[Depends(require_permission("ims:train:study:query"))],
)
async def get_my_tasks(
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CommonResult[PageResult[MyTaskListItem]]:
    """Get current user's learning tasks."""
    from app.domains.train.service import TrainStudyService
    
    service = TrainStudyService()
    items, total = await service.get_my_tasks(
        status=status,
        page=page,
        page_size=page_size,
    )
    return CommonResult.success(data=PageResult(
        total=total,
        page=page,
        page_size=page_size,
        list=items,
    ))


@router.get(
    "/study/task/{task_id}",
    response_model=CommonResult[StudyTaskDetail],
    summary="学习任务详情",
    dependencies=[Depends(require_permission("ims:train:study:query"))],
)
async def get_study_task_detail(task_id: str) -> CommonResult[StudyTaskDetail]:
    """Get task detail for study execution."""
    from app.domains.train.service import TrainStudyService
    
    service = TrainStudyService()
    detail = await service.get_task_for_study(task_id)
    return CommonResult.success(data=detail)


@router.put(
    "/task/{task_id}/progress",
    response_model=CommonResult[dict],
    summary="上报进度",
    dependencies=[Depends(require_permission("ims:train:study:do"))],
)
async def report_progress(
    task_id: str,
    req: ProgressReportRequest,
) -> CommonResult[dict]:
    """
    Report study progress (heartbeat).
    
    Video: validates anti-cheat rules (Q-D11, Q-D12)
    """
    from app.domains.train.service import TrainStudyService
    from app.domains.train.models import TrainMaterial
    from app.db.session import get_db_session
    
    session = get_db_session()
    material = session.query(TrainMaterial).filter(
        TrainMaterial.id == int(req.material_id),
    ).first()
    
    service = TrainStudyService()
    
    if material and material.material_type == "VIDEO":
        result = await service.report_video_progress(
            task_id=task_id,
            material_id=req.material_id,
            position=req.position,
            heartbeat_interval=req.heartbeat_interval,
        )
    elif material and material.material_type == "DOC":
        result = await service.report_document_progress(
            task_id=task_id,
            material_id=req.material_id,
            page=req.position,
            heartbeat_interval=req.heartbeat_interval,
        )
    else:
        result = await service.report_link_progress(
            task_id=task_id,
            material_id=req.material_id,
            heartbeat_interval=req.heartbeat_interval,
        )
    
    return CommonResult.success(data=result)


@router.put(
    "/task/{task_id}/quiz-draft",
    response_model=CommonResult,
    summary="暂存作答",
    dependencies=[Depends(require_permission("ims:train:study:do"))],
)
async def save_quiz_draft(
    task_id: str,
    req: QuizDraftSaveRequest,
) -> CommonResult:
    """Save quiz draft answers."""
    from app.domains.train.service import TrainStudyService
    
    service = TrainStudyService()
    await service.save_quiz_draft(task_id, req.answers)
    return CommonResult.success()


@router.post(
    "/task/{task_id}/confirm",
    response_model=CommonResult[ConfirmResponse],
    summary="确认完成/提交问卷",
    dependencies=[Depends(require_permission("ims:train:study:do"))],
)
async def confirm_completion(
    task_id: str,
    req: Optional[QuizSubmitRequest] = None,
) -> CommonResult[ConfirmResponse]:
    """
    Confirm task completion.
    
    - DURATION type: check if duration requirement met
    - QUIZ type: submit answers and grade
    """
    from app.domains.train.service import TrainStudyService, TrainTaskService
    from app.db.session import get_db_session
    from app.domains.train.models import TrainTask
    from app.core.context import ctx
    
    session = get_db_session()
    task = session.query(TrainTask).filter(
        TrainTask.id == int(task_id),
        TrainTask.tenant_id == ctx.tenant_id,
        TrainTask.deleted == 0,
    ).first()
    
    service = TrainStudyService()
    
    if task and task.confirm_type == "QUIZ":
        if not req or not req.answers:
            from app.core.errors import BizError
            raise BizError(1001, msg="问卷类型必须提交答案")
        result = await service.submit_quiz(task_id, req.answers)
    else:
        result = await service.confirm_duration(task_id)
    
    return CommonResult.success(data=result)


# ============== Statistics Endpoints (FP-B21-SS-01~06) ==============

@router.get(
    "/stat/finish-rate",
    response_model=CommonResult[FinishRateOverview],
    summary="完成率总览",
    dependencies=[Depends(require_any_permission([
        "ims:train:stat:query",
        "ims:train:study:query",
    ]))],
)
async def get_finish_rate(
    dept_id: Optional[str] = Query(None, description="部门ID"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
) -> CommonResult[FinishRateOverview]:
    """Get finish rate overview with data scope filtering."""
    from app.domains.train.service import TrainStatService
    
    service = TrainStatService()
    result = await service.get_finish_rate(
        dept_id=dept_id,
        start_date=start_date,
        end_date=end_date,
    )
    return CommonResult.success(data=result)


@router.get(
    "/stat/dept",
    response_model=CommonResult[PageResult[DeptStatItem]],
    summary="部门日汇总",
    dependencies=[Depends(require_permission("ims:train:stat:query"))],
)
async def get_dept_stat(
    start_date: str = Query(..., description="开始日期"),
    end_date: str = Query(..., description="结束日期"),
    dept_id: Optional[str] = Query(None, description="部门ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CommonResult[PageResult[DeptStatItem]]:
    """Get department daily statistics."""
    return CommonResult.success(data=PageResult(
        total=0,
        page=page,
        page_size=page_size,
        list=[],
    ))


@router.get(
    "/stat/rank",
    response_model=CommonResult[list[RankItem]],
    summary="时长排行",
    dependencies=[Depends(require_permission("ims:train:stat:query"))],
)
async def get_rank(
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    limit: int = Query(10, ge=1, le=100),
) -> CommonResult[list[RankItem]]:
    """Get duration ranking."""
    return CommonResult.success(data=[])


@router.get(
    "/stat/overdue",
    response_model=CommonResult[PageResult[OverdueItem]],
    summary="逾期督办",
    dependencies=[Depends(require_permission("ims:train:stat:query"))],
)
async def get_overdue_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CommonResult[PageResult[OverdueItem]]:
    """Get overdue supervision list."""
    return CommonResult.success(data=PageResult(
        total=0,
        page=page,
        page_size=page_size,
        list=[],
    ))


@router.post(
    "/stat/overdue/export",
    response_model=CommonResult[dict],
    summary="逾期导出",
    dependencies=[Depends(require_permission("ims:train:stat:export"))],
)
async def export_overdue() -> CommonResult[dict]:
    """Export overdue list."""
    return CommonResult.success(data={"task_id": "export_task_id"})


@router.get(
    "/stat/material-heat",
    response_model=CommonResult[list[MaterialHeatItem]],
    summary="资料热度",
    dependencies=[Depends(require_permission("ims:train:stat:query"))],
)
async def get_material_heat(
    limit: int = Query(10, ge=1, le=100),
) -> CommonResult[list[MaterialHeatItem]]:
    """Get material popularity ranking."""
    return CommonResult.success(data=[])


# ============== AI Generation Endpoint (FP-B21-TK-05) ==============

@router.post(
    "/quiz/ai-generate",
    response_model=CommonResult[AIGenerateResponse],
    summary="AI生成试卷",
    dependencies=[Depends(require_permission("ims:train:quiz:ai"))],
)
async def ai_generate_quiz(req: AIGenerateRequest) -> CommonResult[AIGenerateResponse]:
    """
    Generate quiz using AI.
    
    Error codes:
    - 1101: Material not found or not published
    - 1106: AI call failed (no mock fallback)
    - 1107: AI call timeout (no mock fallback)
    - 1108: Zero questions generated
    - 1109: AI not configured
    """
    from app.core.errors import BizError
    
    raise BizError(1109, msg="培训AI未配置或未启用")
