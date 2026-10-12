# app/api/system.py - System management endpoints (FW-B07, FW-B08)
"""
System management API endpoints.

Priority endpoints for B0b:
- GET /dict-data/simple-list - Dictionary values (FP-B07-03)
- GET /dept/tree - Department tree (FP-B08-02)
- GET /user/page - User list with dept filter (FP-B08-03)
- GET /user/simple-page - Simple user list for selectors (FP-B08-08)
- GET /role/simple-list - Role list for selectors (FP-B08-08)

Also includes department CRUD, user management basics, org sync, etc.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.pagination import PageParam, PageResult
from app.core.response import CommonResult
from app.core.serialization import BaseSchema
from app.api.deps import require_permission, require_any_permission, require_login

router = APIRouter()


# ============== Dict Schemas ==============

class DictDataItem(BaseSchema):
    """Dictionary data item."""
    dict_value: str
    dict_label: str
    color_type: str = "neutral"
    sort: int = 0


class DictTypeItem(BaseSchema):
    """Dictionary type item."""
    dict_type: str
    name: str


# ============== Dept Schemas ==============

class DeptTreeNode(BaseSchema):
    """Department tree node."""
    id: str
    parent_id: Optional[str] = None
    name: str
    source: str  # DINGTALK, LOCAL, SYSTEM
    status: str  # ENABLED, DISABLED
    local_orphan: bool = False
    member_count: int = 0
    direct_member_count: int = 0
    leader_name: Optional[str] = None
    children: list["DeptTreeNode"] = []


class DeptCreateRequest(BaseSchema):
    """Create department request."""
    parent_id: str
    name: str
    sort: int = 0
    leader_user_id: Optional[str] = None


class DeptUpdateRequest(BaseSchema):
    """Update department request."""
    name: Optional[str] = None
    sort: Optional[int] = None
    leader_user_id: Optional[str] = None


class DeptMoveRequest(BaseSchema):
    """Move department request."""
    id: str
    new_parent_id: str


class DeptResponse(BaseSchema):
    """Department response."""
    id: str
    parent_id: Optional[str] = None
    name: str
    source: str
    status: str
    sort: int = 0
    leader_user_id: Optional[str] = None
    sync_override_hint: bool = False


# ============== User Schemas ==============

class UserListItem(BaseSchema):
    """User list item."""
    id: str
    username: str
    nickname: str
    mobile: Optional[str] = None  # Masked
    email: Optional[str] = None
    status: str
    main_dept_id: Optional[str] = None
    main_dept_name: Optional[str] = None
    position_label: Optional[str] = None
    last_login_time: Optional[str] = None


class UserSimpleItem(BaseSchema):
    """Simple user item for selectors."""
    id: str
    nickname: str
    main_dept_name: Optional[str] = None
    status: str


class UserCreateRequest(BaseSchema):
    """Create user request - minimal fields."""
    username: str
    nickname: str
    mobile: str
    dept_ids: list[str]
    main_dept_id: str
    password: str


# ============== Role Schemas ==============

class RoleSimpleItem(BaseSchema):
    """Simple role item for selectors."""
    id: str
    name: str
    source: str  # MANUAL, DINGTALK_AUTO


# ============== Dict Endpoints ==============

@router.get(
    "/dict-data/simple-list",
    response_model=CommonResult[list[DictDataItem]],
    summary="获取字典值列表",
)
async def get_dict_data_simple_list(
    dict_type: str = Query(..., description="字典类型"),
) -> CommonResult[list[DictDataItem]]:
    """
    Get enabled dictionary values for a type.
    
    Rules per FP-B07-03:
    - Returns enabled values only
    - Includes colorType
    - Cached in Redis (ims:dict:<type>), TTL 60s local cache
    """
    from app.services.dict import DictService
    
    service = DictService()
    items = await service.get_dict_data_simple_list(dict_type)
    return CommonResult.success(data=items)


@router.get(
    "/dict-type/list",
    response_model=CommonResult[list[DictTypeItem]],
    summary="获取字典类型列表",
    dependencies=[Depends(require_login)],
)
async def get_dict_type_list() -> CommonResult[list[DictTypeItem]]:
    """Get all dictionary types."""
    from app.services.dict import DictService
    
    service = DictService()
    items = await service.get_dict_type_list()
    return CommonResult.success(data=items)


# ============== Dept Endpoints ==============

@router.get(
    "/dept/tree",
    response_model=CommonResult[list[DeptTreeNode]],
    summary="获取部门树",
    dependencies=[Depends(require_any_permission(["ims:system:dept:query", "ims:system:user:query"]))],
)
async def get_dept_tree(
    status: Optional[str] = Query(None, description="状态筛选: ALL 返回停用部门"),
    keyword: Optional[str] = Query(None, description="部门名称关键词"),
) -> CommonResult[list[DeptTreeNode]]:
    """
    Get department tree.
    
    Rules per FP-B08-02:
    - memberCount: dedup count of active+frozen users in dept and all descendants
    - directMemberCount: users directly in this dept
    - keyword match: return matched node and ancestor path
    - Default excludes disabled depts, status=ALL includes them
    - Tree itself not filtered by data scope (org structure is public)
    - Performance: 2000 depts, 20k users -> <= 500ms
    """
    from app.services.dept import DeptService
    
    service = DeptService()
    tree = await service.get_dept_tree(
        status=status,
        keyword=keyword,
    )
    return CommonResult.success(data=tree)


@router.post(
    "/dept/create",
    response_model=CommonResult[DeptResponse],
    summary="新建部门",
    dependencies=[Depends(require_permission("ims:system:dept:create"))],
)
async def create_dept(request: DeptCreateRequest) -> CommonResult[DeptResponse]:
    """
    Create a local department.
    
    Rules per FP-B08-04:
    - source=LOCAL
    - Parent not exist -> 1500, disabled -> 1501
    - Same-parent duplicate name -> 1219
    - Under "待分配" -> 1220
    """
    from app.services.dept import DeptService
    
    service = DeptService()
    result = await service.create_dept(request)
    return CommonResult.success(data=result)


@router.put(
    "/dept/update",
    response_model=CommonResult[DeptResponse],
    summary="更新部门",
    dependencies=[Depends(require_permission("ims:system:dept:update"))],
)
async def update_dept(
    id: str = Query(..., description="部门ID"),
    request: DeptUpdateRequest = None,
) -> CommonResult[DeptResponse]:
    """
    Update department (name, leader, sort).
    
    Rules per FP-B08-05:
    - SYSTEM dept -> 1220
    - Same-parent duplicate name -> 1219
    - DINGTALK dept: success with syncOverrideHint=true
    """
    from app.services.dept import DeptService
    
    service = DeptService()
    result = await service.update_dept(id, request)
    return CommonResult.success(data=result)


@router.put(
    "/dept/move",
    response_model=CommonResult[DeptResponse],
    summary="移动部门",
    dependencies=[Depends(require_permission("ims:system:dept:update"))],
)
async def move_dept(request: DeptMoveRequest) -> CommonResult[DeptResponse]:
    """
    Move department to new parent.
    
    Rules per FP-B08-06:
    - Move to self or descendant -> 1218
    - DINGTALK to LOCAL parent -> 1220
    - SYSTEM dept cannot move or be target -> 1220
    - Same-parent duplicate name -> 1219
    - Same transaction update all descendant paths
    """
    from app.services.dept import DeptService
    
    service = DeptService()
    result = await service.move_dept(request.id, request.new_parent_id)
    return CommonResult.success(data=result)


@router.put(
    "/dept/update-status",
    response_model=CommonResult,
    summary="停用/启用部门",
    dependencies=[Depends(require_permission("ims:system:dept:update"))],
)
async def update_dept_status(
    id: str = Query(..., description="部门ID"),
    status: str = Query(..., description="状态: ENABLED/DISABLED"),
) -> CommonResult:
    """
    Enable or disable department.
    
    Rules per FP-B08-07:
    - Has enabled children -> 1502
    - SYSTEM dept -> 1220
    - DINGTALK dept: local disable allowed, next sync may re-enable
    """
    from app.services.dept import DeptService
    
    service = DeptService()
    await service.update_dept_status(id, status)
    return CommonResult.success()


@router.delete(
    "/dept/delete",
    response_model=CommonResult,
    summary="删除部门",
    dependencies=[Depends(require_permission("ims:system:dept:delete"))],
)
async def delete_dept(id: str = Query(..., description="部门ID")) -> CommonResult:
    """
    Delete department.
    
    Rules per FP-B08-07:
    - Has children or users (any status including resigned) -> 1502
    - SYSTEM dept -> 1220
    """
    from app.services.dept import DeptService
    
    service = DeptService()
    await service.delete_dept(id)
    return CommonResult.success()


# ============== User Endpoints ==============

@router.get(
    "/user/page",
    response_model=CommonResult[PageResult[UserListItem]],
    summary="用户分页列表",
    dependencies=[Depends(require_permission("ims:system:user:query"))],
)
async def get_user_page(
    dept_id: Optional[str] = Query(None, description="部门ID"),
    include_children: bool = Query(True, description="是否包含下级部门"),
    keyword: Optional[str] = Query(None, description="用户名/姓名关键词"),
    status: Optional[str] = Query(None, description="状态"),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult[PageResult[UserListItem]]:
    """
    Get paginated user list.
    
    Rules per FP-B08-03:
    - includeChildren=true: filter by path LIKE '/…/deptId/%'
    - includeChildren=false: only direct members
    - Data scope filtering applied
    """
    from app.services.user import UserService
    
    service = UserService()
    page_param = PageParam(page_no=page_no, page_size=page_size)
    result = await service.get_user_page(
        page_param=page_param,
        dept_id=dept_id,
        include_children=include_children,
        keyword=keyword,
        status=status,
    )
    return CommonResult.success(data=result)


@router.get(
    "/user/simple-page",
    response_model=CommonResult[PageResult[UserSimpleItem]],
    summary="用户选择器列表",
    dependencies=[Depends(require_login)],
)
async def get_user_simple_page(
    keyword: Optional[str] = Query(None, description="姓名关键词"),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult[PageResult[UserSimpleItem]]:
    """
    Get simple user list for selectors.
    
    LOGIN_ONLY - returns id, nickname, mainDeptName, status only.
    """
    from app.services.user import UserService
    
    service = UserService()
    page_param = PageParam(page_no=page_no, page_size=page_size)
    result = await service.get_user_simple_page(page_param, keyword)
    return CommonResult.success(data=result)


@router.post(
    "/user/create",
    response_model=CommonResult[UserListItem],
    summary="创建用户",
    dependencies=[Depends(require_permission("ims:system:user:create"))],
)
async def create_user(request: UserCreateRequest) -> CommonResult[UserListItem]:
    """
    Create a new user.
    
    Minimal fields: username, nickname, mobile, depts, mainDeptId, password.
    Full user management is in M02 module.
    """
    from app.services.user import UserService
    
    service = UserService()
    result = await service.create_user(request)
    return CommonResult.success(data=result)


# ============== Role Endpoints ==============

@router.put(
    "/dept/confirm-orphan",
    response_model=CommonResult,
    summary="确认保留待确认部门",
    dependencies=[Depends(require_permission("ims:system:dept:update"))],
)
async def confirm_orphan_dept(
    id: str = Query(..., description="部门ID"),
) -> CommonResult:
    """
    Confirm keeping a local orphan department.
    
    Rules per FP-D07-02 item 7:
    - Sets local_orphan=0, marking dept as confirmed to keep
    - Only applicable to departments with local_orphan=1
    """
    from app.services.dept import DeptService
    
    service = DeptService()
    await service.confirm_orphan_dept(id)
    return CommonResult.success()


@router.put(
    "/user/update-depts",
    response_model=CommonResult,
    summary="调整用户部门",
    dependencies=[Depends(require_permission("ims:system:user:update"))],
)
async def update_user_depts(
    id: str = Query(..., description="用户ID"),
    dept_ids: list[str] = Query(..., description="部门ID列表"),
    main_dept_id: str = Query(..., description="主部门ID"),
) -> CommonResult:
    """
    Update user's department assignments.
    
    Rules per FP-B03-02:
    - User can belong to multiple departments
    - Must have exactly one main department
    - Removing main dept requires specifying another main first
    - Removing all depts auto-assigns to "待分配" dept
    """
    from app.services.user import UserService
    
    service = UserService()
    await service.update_user_depts(id, dept_ids, main_dept_id)
    return CommonResult.success()


@router.delete(
    "/user/delete",
    response_model=CommonResult,
    summary="删除用户",
    dependencies=[Depends(require_permission("ims:system:user:delete"))],
)
async def delete_user(id: str = Query(..., description="用户ID")) -> CommonResult:
    """
    Delete user.
    
    Rules per FP-B03-01 item 3:
    - Only users who never logged in AND have no business references can be deleted
    - RESIGNED users cannot be deleted -> 1502
    """
    from app.services.user import UserService
    
    service = UserService()
    await service.delete_user(id)
    return CommonResult.success()


# ============== Org Sync Schemas ==============

class OrgSyncBatchItem(BaseSchema):
    """Org sync batch item."""
    batch_id: str
    status: str  # PENDING, RUNNING, SUCCESS, FAILED
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    added_depts: int = 0
    updated_depts: int = 0
    removed_depts: int = 0
    added_users: int = 0
    updated_users: int = 0
    removed_users: int = 0
    error_msg: Optional[str] = None


# ============== Org Sync Endpoints ==============

@router.post(
    "/org-sync/reconcile",
    response_model=CommonResult[OrgSyncBatchItem],
    summary="触发组织架构同步",
    dependencies=[Depends(require_permission("ims:system:org-sync:run"))],
)
async def trigger_org_sync_reconcile() -> CommonResult[OrgSyncBatchItem]:
    """
    Trigger organization structure reconciliation with DingTalk.
    
    Rules per FP-D07-04:
    - Compares IMS org structure with DingTalk
    - Creates sync batch record
    - Returns immediately with batch info (async execution)
    """
    from app.services.org_sync import OrgSyncService
    
    service = OrgSyncService()
    result = await service.trigger_reconcile()
    return CommonResult.success(data=result)


@router.get(
    "/org-sync/latest-batch",
    response_model=CommonResult[OrgSyncBatchItem],
    summary="获取最新同步批次",
    dependencies=[Depends(require_permission("ims:system:org-sync:query"))],
)
async def get_latest_org_sync_batch() -> CommonResult[OrgSyncBatchItem]:
    """
    Get the latest org sync batch status.
    
    Rules per FP-D07-04:
    - Returns the most recent sync batch
    - Includes counts for dept/user changes
    """
    from app.services.org_sync import OrgSyncService
    
    service = OrgSyncService()
    result = await service.get_latest_batch()
    return CommonResult.success(data=result)


# ============== Role Endpoints ==============

@router.get(
    "/role/simple-list",
    response_model=CommonResult[list[RoleSimpleItem]],
    summary="角色选择器列表",
    dependencies=[Depends(require_login)],
)
async def get_role_simple_list() -> CommonResult[list[RoleSimpleItem]]:
    """
    Get enabled roles for selectors.
    
    LOGIN_ONLY - returns id, name, source only.
    """
    from app.services.role import RoleService
    
    service = RoleService()
    items = await service.get_role_simple_list()
    return CommonResult.success(data=items)
