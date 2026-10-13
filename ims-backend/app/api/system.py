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

from app.api.deps import require_any_permission, require_login, require_permission
from app.core.pagination import PageParam, PageResult
from app.core.response import CommonResult
from app.core.serialization import BaseSchema

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
    id: str,
    dept_ids: list[str],
    main_dept_id: str,
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


# ============== B2 System Management Endpoints ==============

# ---------- User Management (U-05 to U-16) ----------

class UserDetailResponse(BaseSchema):
    """User detail response."""
    id: str
    username: str
    nickname: str
    mobile: Optional[str] = None
    email: Optional[str] = None
    status: str
    main_dept_id: Optional[str] = None
    main_dept_name: Optional[str] = None
    dept_ids: list[str] = []
    dept_names: list[str] = []
    role_ids: list[str] = []
    role_names: list[str] = []
    position_code: Optional[str] = None
    emp_no: Optional[str] = None
    source: str
    pwd_reset_required: bool = False
    last_login_time: Optional[str] = None


class UserUpdateRequest(BaseSchema):
    """Update user request."""
    nickname: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    emp_no: Optional[str] = None


class UserRolesUpdateRequest(BaseSchema):
    """Update user roles request."""
    role_ids: list[str]


@router.get(
    "/user/get",
    response_model=CommonResult[UserDetailResponse],
    summary="获取用户详情",
    dependencies=[Depends(require_permission("ims:system:user:query"))],
)
async def get_user_detail(
    id: str = Query(..., description="用户ID"),
) -> CommonResult[UserDetailResponse]:
    """Get user detail by ID (U-06)."""
    from app.services.system_user import SystemUserService

    service = SystemUserService()
    result = await service.get_user_detail(id)
    return CommonResult.success(data=result)


@router.put(
    "/user/update",
    response_model=CommonResult[UserDetailResponse],
    summary="更新用户信息",
    dependencies=[Depends(require_permission("ims:system:user:update"))],
)
async def update_user(
    id: str = Query(..., description="用户ID"),
    request: UserUpdateRequest = None,
) -> CommonResult[UserDetailResponse]:
    """Update user basic info (U-06)."""
    from app.services.system_user import SystemUserService

    service = SystemUserService()
    result = await service.update_user(id, request)
    return CommonResult.success(data=result)


@router.put(
    "/user/update-roles",
    response_model=CommonResult,
    summary="更新用户角色",
    dependencies=[Depends(require_permission("ims:system:user:update"))],
)
async def update_user_roles(
    id: str = Query(..., description="用户ID"),
    request: UserRolesUpdateRequest = None,
) -> CommonResult:
    """Update user's role assignments (U-08)."""
    from app.services.system_user import SystemUserService

    service = SystemUserService()
    await service.update_user_roles(id, request.role_ids)
    return CommonResult.success()


@router.put(
    "/user/update-status",
    response_model=CommonResult,
    summary="更新用户状态",
    dependencies=[Depends(require_permission("ims:system:user:update"))],
)
async def update_user_status(
    id: str = Query(..., description="用户ID"),
    status: str = Query(..., description="状态: ACTIVE/FROZEN"),
) -> CommonResult:
    """Update user status - freeze or reactivate (U-09)."""
    from app.services.system_user import SystemUserService

    service = SystemUserService()
    await service.update_user_status(id, status)
    return CommonResult.success()


@router.put(
    "/user/resign",
    response_model=CommonResult,
    summary="设为离职",
    dependencies=[Depends(require_permission("ims:system:user:update"))],
)
async def resign_user(
    id: str = Query(..., description="用户ID"),
) -> CommonResult:
    """Mark user as resigned (U-10)."""
    from app.services.system_user import SystemUserService

    service = SystemUserService()
    await service.resign_user(id)
    return CommonResult.success()


class ResetPasswordResponse(BaseSchema):
    """Reset password response."""
    new_password: str


@router.put(
    "/user/reset-password",
    response_model=CommonResult[ResetPasswordResponse],
    summary="重置用户密码",
    dependencies=[Depends(require_permission("ims:system:user:update"))],
)
async def reset_user_password(
    id: str = Query(..., description="用户ID"),
) -> CommonResult[ResetPasswordResponse]:
    """Reset user password to a random value (U-11)."""
    from app.services.system_user import SystemUserService

    service = SystemUserService()
    result = await service.reset_password(id)
    return CommonResult.success(data=result)


@router.put(
    "/user/unlock",
    response_model=CommonResult,
    summary="解锁用户",
    dependencies=[Depends(require_permission("ims:system:user:update"))],
)
async def unlock_user(
    id: str = Query(..., description="用户ID"),
) -> CommonResult:
    """Unlock a locked user account (U-12)."""
    from app.services.system_user import SystemUserService

    service = SystemUserService()
    await service.unlock_user(id)
    return CommonResult.success()


@router.put(
    "/user/kick",
    response_model=CommonResult,
    summary="强制下线",
    dependencies=[Depends(require_permission("ims:system:user:update"))],
)
async def kick_user(
    id: str = Query(..., description="用户ID"),
) -> CommonResult:
    """Kick user's all sessions offline (U-13)."""
    from app.services.system_user import SystemUserService

    service = SystemUserService()
    await service.kick_user(id)
    return CommonResult.success()


@router.post(
    "/user/export",
    response_model=CommonResult,
    summary="导出用户",
    dependencies=[Depends(require_permission("ims:system:user:export"))],
)
async def export_users() -> CommonResult:
    """Create user export task (U-15)."""
    from app.services.system_user import SystemUserService

    service = SystemUserService()
    result = await service.export_users()
    return CommonResult.success(data=result)


# ---------- Role Management (R-01 to R-12) ----------

class RoleListItem(BaseSchema):
    """Role list item."""
    id: str
    role_key: str
    name: str
    source: str
    status: str
    data_scope: Optional[str] = None
    position_code: Optional[str] = None
    is_standard: bool = False
    sort: int = 0
    remark: Optional[str] = None
    member_count: int = 0


class RoleDetailResponse(BaseSchema):
    """Role detail response."""
    id: str
    role_key: str
    name: str
    source: str
    status: str
    data_scope: Optional[str] = None
    position_code: Optional[str] = None
    is_standard: bool = False
    sort: int = 0
    remark: Optional[str] = None
    menu_ids: list[str] = []
    member_count: int = 0


class RoleCreateRequest(BaseSchema):
    """Create role request."""
    role_key: str
    name: str
    data_scope: Optional[str] = None
    sort: int = 0
    remark: Optional[str] = None


class RoleUpdateRequest(BaseSchema):
    """Update role request."""
    name: Optional[str] = None
    sort: Optional[int] = None
    remark: Optional[str] = None


class RoleMenusUpdateRequest(BaseSchema):
    """Update role menus request."""
    menu_ids: list[str]


class RolePermDetailRequest(BaseSchema):
    """Update role permission detail request."""
    perm_code: str
    r: bool = True
    w: bool = False
    d: bool = False


class RoleMembersRequest(BaseSchema):
    """Add/remove role members request."""
    user_ids: list[str]


@router.get(
    "/role/page",
    response_model=CommonResult[PageResult[RoleListItem]],
    summary="角色分页列表",
    dependencies=[Depends(require_permission("ims:system:role:query"))],
)
async def get_role_page(
    keyword: Optional[str] = Query(None, description="角色名称关键词"),
    status: Optional[str] = Query(None, description="状态"),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult[PageResult[RoleListItem]]:
    """Get paginated role list (R-01)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    page_param = PageParam(page_no=page_no, page_size=page_size)
    result = await service.get_role_page(page_param, keyword, status)
    return CommonResult.success(data=result)


@router.post(
    "/role",
    response_model=CommonResult[RoleDetailResponse],
    summary="创建角色",
    dependencies=[Depends(require_permission("ims:system:role:create"))],
)
async def create_role(request: RoleCreateRequest) -> CommonResult[RoleDetailResponse]:
    """Create a new role (R-02)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    result = await service.create_role(request)
    return CommonResult.success(data=result)


@router.get(
    "/role/get",
    response_model=CommonResult[RoleDetailResponse],
    summary="获取角色详情",
    dependencies=[Depends(require_permission("ims:system:role:query"))],
)
async def get_role_detail(
    id: str = Query(..., description="角色ID"),
) -> CommonResult[RoleDetailResponse]:
    """Get role detail (R-03)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    result = await service.get_role_detail(id)
    return CommonResult.success(data=result)


@router.put(
    "/role/update",
    response_model=CommonResult[RoleDetailResponse],
    summary="更新角色",
    dependencies=[Depends(require_permission("ims:system:role:update"))],
)
async def update_role(
    id: str = Query(..., description="角色ID"),
    request: RoleUpdateRequest = None,
) -> CommonResult[RoleDetailResponse]:
    """Update role basic info (R-03)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    result = await service.update_role(id, request)
    return CommonResult.success(data=result)


@router.put(
    "/role/update-status",
    response_model=CommonResult,
    summary="更新角色状态",
    dependencies=[Depends(require_permission("ims:system:role:update"))],
)
async def update_role_status(
    id: str = Query(..., description="角色ID"),
    status: str = Query(..., description="状态: ENABLED/DISABLED"),
) -> CommonResult:
    """Update role status (R-03)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    await service.update_role_status(id, status)
    return CommonResult.success()


@router.put(
    "/role/{id}/menus",
    response_model=CommonResult,
    summary="配置角色菜单",
    dependencies=[Depends(require_permission("ims:system:role:update"))],
)
async def update_role_menus(
    id: str,
    request: RoleMenusUpdateRequest,
) -> CommonResult:
    """Update role menu assignments (R-04)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    await service.update_role_menus(id, request.menu_ids)
    return CommonResult.success()


@router.put(
    "/role/{id}/perm-detail",
    response_model=CommonResult,
    summary="配置角色功能点权限",
    dependencies=[Depends(require_permission("ims:system:role:update"))],
)
async def update_role_perm_detail(
    id: str,
    request: RolePermDetailRequest,
) -> CommonResult:
    """Update role permission detail R/W/D (R-04)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    result = await service.update_role_perm_detail(id, request.perm_code, request.r, request.w, request.d)
    return CommonResult.success(data=result)


@router.put(
    "/role/{id}/data-scope",
    response_model=CommonResult,
    summary="配置角色数据范围",
    dependencies=[Depends(require_permission("ims:system:role:update"))],
)
async def update_role_data_scope(
    id: str,
    data_scope: str = Query(..., description="数据范围: ALL/DEPT/SELF"),
) -> CommonResult:
    """Update role data scope (R-05)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    await service.update_role_data_scope(id, data_scope)
    return CommonResult.success()


@router.put(
    "/role/{id}/dingtalk-position",
    response_model=CommonResult,
    summary="绑定钉钉岗位",
    dependencies=[Depends(require_permission("ims:system:role:update"))],
)
async def update_role_dingtalk_position(
    id: str,
    position_code: str = Query(None, description="岗位编码"),
) -> CommonResult:
    """Update role DingTalk position binding (R-06)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    await service.update_role_dingtalk_position(id, position_code)
    return CommonResult.success()


@router.get(
    "/role/{id}/members",
    response_model=CommonResult[PageResult[UserSimpleItem]],
    summary="获取角色成员",
    dependencies=[Depends(require_permission("ims:system:role:query"))],
)
async def get_role_members(
    id: str,
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult[PageResult[UserSimpleItem]]:
    """Get role members (R-09)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    page_param = PageParam(page_no=page_no, page_size=page_size)
    result = await service.get_role_members(id, page_param)
    return CommonResult.success(data=result)


@router.post(
    "/role/{id}/members",
    response_model=CommonResult,
    summary="添加角色成员",
    dependencies=[Depends(require_permission("ims:system:role:update"))],
)
async def add_role_members(
    id: str,
    request: RoleMembersRequest,
) -> CommonResult:
    """Add members to role (R-09)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    await service.add_role_members(id, request.user_ids)
    return CommonResult.success()


@router.delete(
    "/role/{id}/members",
    response_model=CommonResult,
    summary="移除角色成员",
    dependencies=[Depends(require_permission("ims:system:role:update"))],
)
async def remove_role_members(
    id: str,
    request: RoleMembersRequest,
) -> CommonResult:
    """Remove members from role (R-09)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    await service.remove_role_members(id, request.user_ids)
    return CommonResult.success()


@router.delete(
    "/role/delete",
    response_model=CommonResult,
    summary="删除角色",
    dependencies=[Depends(require_permission("ims:system:role:delete"))],
)
async def delete_role(
    id: str = Query(..., description="角色ID"),
) -> CommonResult:
    """Delete role (R-10)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    await service.delete_role(id)
    return CommonResult.success()


@router.post(
    "/role/export",
    response_model=CommonResult,
    summary="导出角色",
    dependencies=[Depends(require_permission("ims:system:role:export"))],
)
async def export_roles() -> CommonResult:
    """Create role export task (R-12)."""
    from app.services.system_role import SystemRoleService

    service = SystemRoleService()
    result = await service.export_roles()
    return CommonResult.success(data=result)


# ---------- Menu Management (M-01 to M-04) ----------

class MenuTreeNode(BaseSchema):
    """Menu tree node."""
    id: str
    parent_id: Optional[str] = None
    type: str
    name: str
    perm_code: Optional[str] = None
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort: int = 0
    visible: bool = True
    status: str
    children: list["MenuTreeNode"] = []


class MenuCreateRequest(BaseSchema):
    """Create menu request."""
    parent_id: Optional[str] = None
    type: str
    name: str
    perm_code: Optional[str] = None
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort: int = 0
    visible: bool = True


class MenuUpdateRequest(BaseSchema):
    """Update menu request."""
    name: Optional[str] = None
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort: Optional[int] = None
    visible: Optional[bool] = None


@router.get(
    "/menu/tree",
    response_model=CommonResult[list[MenuTreeNode]],
    summary="获取菜单树",
    dependencies=[Depends(require_permission("ims:system:menu:query"))],
)
async def get_menu_tree(
    keyword: Optional[str] = Query(None, description="菜单名称关键词"),
) -> CommonResult[list[MenuTreeNode]]:
    """Get full menu tree (M-01). Platform tenant only."""
    from app.services.system_menu import SystemMenuService

    service = SystemMenuService()
    result = await service.get_menu_tree(keyword)
    return CommonResult.success(data=result)


@router.post(
    "/menu/create",
    response_model=CommonResult,
    summary="创建菜单",
    dependencies=[Depends(require_permission("ims:system:menu:create"))],
)
async def create_menu(request: MenuCreateRequest) -> CommonResult:
    """Create a new menu (M-02). Platform tenant only."""
    from app.services.system_menu import SystemMenuService

    service = SystemMenuService()
    result = await service.create_menu(request)
    return CommonResult.success(data=result)


@router.put(
    "/menu/update",
    response_model=CommonResult,
    summary="更新菜单",
    dependencies=[Depends(require_permission("ims:system:menu:update"))],
)
async def update_menu(
    id: str = Query(..., description="菜单ID"),
    request: MenuUpdateRequest = None,
) -> CommonResult:
    """Update menu (M-02). Platform tenant only."""
    from app.services.system_menu import SystemMenuService

    service = SystemMenuService()
    result = await service.update_menu(id, request)
    return CommonResult.success(data=result)


@router.delete(
    "/menu/delete",
    response_model=CommonResult,
    summary="删除菜单",
    dependencies=[Depends(require_permission("ims:system:menu:delete"))],
)
async def delete_menu(
    id: str = Query(..., description="菜单ID"),
) -> CommonResult:
    """Delete menu (M-04). Platform tenant only."""
    from app.services.system_menu import SystemMenuService

    service = SystemMenuService()
    await service.delete_menu(id)
    return CommonResult.success()


# ---------- Log Management (L-01 to L-04) ----------

class OperateLogListItem(BaseSchema):
    """Operation log list item."""
    id: str
    module: str
    operation: str
    operator_name: Optional[str] = None
    result: str
    ip: Optional[str] = None
    duration_ms: Optional[int] = None
    create_time: Optional[str] = None


class OperateLogDetailResponse(BaseSchema):
    """Operation log detail response."""
    id: str
    module: str
    operation: str
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    operator_name: Optional[str] = None
    result: str
    error_code: Optional[int] = None
    ip: Optional[str] = None
    duration_ms: Optional[int] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    request_params: Optional[str] = None
    create_time: Optional[str] = None


class LoginLogListItem(BaseSchema):
    """Login log list item."""
    id: str
    username: str
    user_id: Optional[str] = None
    login_method: str
    result: str
    ip: Optional[str] = None
    device: Optional[str] = None
    create_time: Optional[str] = None


@router.get(
    "/operate-log/page",
    response_model=CommonResult[PageResult[OperateLogListItem]],
    summary="操作日志分页列表",
    dependencies=[Depends(require_permission("ims:system:log:query"))],
)
async def get_operate_log_page(
    module: Optional[str] = Query(None, description="模块"),
    operation: Optional[str] = Query(None, description="操作"),
    operator_name: Optional[str] = Query(None, description="操作人"),
    start_time: Optional[str] = Query(None, description="开始时间"),
    end_time: Optional[str] = Query(None, description="结束时间"),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult[PageResult[OperateLogListItem]]:
    """Get paginated operation log list (L-01)."""
    from app.services.system_log import SystemLogService

    service = SystemLogService()
    page_param = PageParam(page_no=page_no, page_size=page_size)
    result = await service.get_operate_log_page(page_param, module, operation, operator_name, start_time, end_time)
    return CommonResult.success(data=result)


@router.get(
    "/operate-log/get",
    response_model=CommonResult[OperateLogDetailResponse],
    summary="获取操作日志详情",
    dependencies=[Depends(require_permission("ims:system:log:query"))],
)
async def get_operate_log_detail(
    id: str = Query(..., description="日志ID"),
) -> CommonResult[OperateLogDetailResponse]:
    """Get operation log detail (L-02)."""
    from app.services.system_log import SystemLogService

    service = SystemLogService()
    result = await service.get_operate_log_detail(id)
    return CommonResult.success(data=result)


@router.get(
    "/login-log/page",
    response_model=CommonResult[PageResult[LoginLogListItem]],
    summary="登录日志分页列表",
    dependencies=[Depends(require_permission("ims:system:log:query"))],
)
async def get_login_log_page(
    username: Optional[str] = Query(None, description="用户名"),
    result: Optional[str] = Query(None, description="结果"),
    start_time: Optional[str] = Query(None, description="开始时间"),
    end_time: Optional[str] = Query(None, description="结束时间"),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult[PageResult[LoginLogListItem]]:
    """Get paginated login log list (L-03)."""
    from app.services.system_log import SystemLogService

    service = SystemLogService()
    page_param = PageParam(page_no=page_no, page_size=page_size)
    log_result = await service.get_login_log_page(page_param, username, result, start_time, end_time)
    return CommonResult.success(data=log_result)


@router.post(
    "/operate-log/export",
    response_model=CommonResult,
    summary="导出操作日志",
    dependencies=[Depends(require_permission("ims:system:log:export"))],
)
async def export_operate_logs() -> CommonResult:
    """Create operation log export task (L-04)."""
    from app.services.system_log import SystemLogService

    service = SystemLogService()
    result = await service.export_operate_logs()
    return CommonResult.success(data=result)


@router.post(
    "/login-log/export",
    response_model=CommonResult,
    summary="导出登录日志",
    dependencies=[Depends(require_permission("ims:system:log:export"))],
)
async def export_login_logs() -> CommonResult:
    """Create login log export task (L-04)."""
    from app.services.system_log import SystemLogService

    service = SystemLogService()
    result = await service.export_login_logs()
    return CommonResult.success(data=result)


# ---------- Parameter Management (P-01 to P-03) ----------

class ParamListItem(BaseSchema):
    """Parameter list item."""
    id: str
    param_key: str
    name: str
    group: str
    value_type: str
    value: Optional[str] = None
    default_value: Optional[str] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    options: Optional[str] = None
    is_builtin: bool = True
    remark: Optional[str] = None


@router.get(
    "/param/list",
    response_model=CommonResult[list[ParamListItem]],
    summary="获取参数列表",
    dependencies=[Depends(require_permission("ims:system:param:query"))],
)
async def get_param_list(
    group: Optional[str] = Query(None, description="参数分组"),
) -> CommonResult[list[ParamListItem]]:
    """Get parameter list (P-01)."""
    from app.services.system_param import SystemParamService

    service = SystemParamService()
    result = await service.get_param_list(group)
    return CommonResult.success(data=result)


@router.put(
    "/param/update",
    response_model=CommonResult,
    summary="更新参数",
    dependencies=[Depends(require_permission("ims:system:param:update"))],
)
async def update_param(
    param_key: str = Query(..., description="参数键"),
    value: str = Query(..., description="参数值"),
) -> CommonResult:
    """Update parameter value (P-02)."""
    from app.services.system_param import SystemParamService

    service = SystemParamService()
    result = await service.update_param(param_key, value)
    return CommonResult.success(data=result)


# ---------- Calendar Management (Q4) ----------

class CalendarDayItem(BaseSchema):
    """Calendar day item."""
    id: str
    day: str
    kind: str


@router.get(
    "/calendar/list",
    response_model=CommonResult[list[CalendarDayItem]],
    summary="获取工作日历",
    dependencies=[Depends(require_permission("ims:system:calendar:query"))],
)
async def get_calendar_list(
    year: int = Query(..., description="年份"),
    month: Optional[int] = Query(None, description="月份"),
) -> CommonResult[list[CalendarDayItem]]:
    """Get calendar list (Q4)."""
    from app.services.system_calendar import SystemCalendarService

    service = SystemCalendarService()
    result = await service.get_calendar_list(year, month)
    return CommonResult.success(data=result)


@router.put(
    "/calendar/update",
    response_model=CommonResult,
    summary="更新工作日历",
    dependencies=[Depends(require_permission("ims:system:calendar:update"))],
)
async def update_calendar(
    day: str = Query(..., description="日期 YYYY-MM-DD"),
    kind: str = Query(..., description="类型: HOLIDAY/WORKDAY/NORMAL"),
) -> CommonResult:
    """Update calendar day (Q4)."""
    from app.services.system_calendar import SystemCalendarService

    service = SystemCalendarService()
    result = await service.update_calendar(day, kind)
    return CommonResult.success(data=result)


# ---------- Notification Management (N-01 to N-02) ----------

class NotifyRecordListItem(BaseSchema):
    """Notification record list item."""
    id: str
    event_type: str
    status: str
    synced_at: Optional[str] = None
    create_time: Optional[str] = None


@router.get(
    "/notify-record/page",
    response_model=CommonResult[PageResult[NotifyRecordListItem]],
    summary="通知记录分页列表",
    dependencies=[Depends(require_permission("ims:system:notify:query"))],
)
async def get_notify_record_page(
    status: Optional[str] = Query(None, description="状态"),
    event_type: Optional[str] = Query(None, description="事件类型"),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult[PageResult[NotifyRecordListItem]]:
    """Get paginated notification record list (N-01)."""
    from app.services.system_notify import SystemNotifyService

    service = SystemNotifyService()
    page_param = PageParam(page_no=page_no, page_size=page_size)
    result = await service.get_notify_record_page(page_param, status, event_type)
    return CommonResult.success(data=result)


@router.post(
    "/notify-record/resend",
    response_model=CommonResult,
    summary="重发通知",
    dependencies=[Depends(require_permission("ims:system:notify:update"))],
)
async def resend_notification(
    id: str = Query(..., description="记录ID"),
) -> CommonResult:
    """Resend a failed notification (N-02)."""
    from app.services.system_notify import SystemNotifyService

    service = SystemNotifyService()
    result = await service.resend_notification(id)
    return CommonResult.success(data=result)


# ---------- Tenant Management (T-01 to T-04) ----------

class TenantListItem(BaseSchema):
    """Tenant list item."""
    id: str
    name: str
    package_id: Optional[str] = None
    status: str
    expire_time: Optional[str] = None


class TenantCreateRequest(BaseSchema):
    """Create tenant request."""
    name: str
    package_id: Optional[str] = None
    admin_username: str
    expire_time: Optional[str] = None


class TenantUpdateRequest(BaseSchema):
    """Update tenant request."""
    name: Optional[str] = None
    package_id: Optional[str] = None
    status: Optional[str] = None
    expire_time: Optional[str] = None


class TenantCreateResponse(BaseSchema):
    """Create tenant response."""
    tenant_id: str
    admin_password: str


class PackageSimpleItem(BaseSchema):
    """Simple package item."""
    id: str
    name: str


class PackageListItem(BaseSchema):
    """Package list item."""
    id: str
    name: str
    status: str
    menu_count: int = 0


class PackageCreateRequest(BaseSchema):
    """Create package request."""
    name: str


class PackageUpdateRequest(BaseSchema):
    """Update package request."""
    name: Optional[str] = None
    menu_ids: Optional[list[str]] = None


@router.get(
    "/tenant/page",
    response_model=CommonResult[PageResult[TenantListItem]],
    summary="租户分页列表",
    dependencies=[Depends(require_permission("ims:system:tenant:query"))],
)
async def get_tenant_page(
    keyword: Optional[str] = Query(None, description="租户名称关键词"),
    status: Optional[str] = Query(None, description="状态"),
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
) -> CommonResult[PageResult[TenantListItem]]:
    """Get paginated tenant list (T-01). Platform-only."""
    from app.services.system_tenant import SystemTenantService

    service = SystemTenantService()
    page_param = PageParam(page_no=page_no, page_size=page_size)
    result = await service.get_tenant_page(page_param, keyword, status)
    return CommonResult.success(data=result)


@router.post(
    "/tenant/create",
    response_model=CommonResult[TenantCreateResponse],
    summary="创建租户",
    dependencies=[Depends(require_permission("ims:system:tenant:create"))],
)
async def create_tenant(request: TenantCreateRequest) -> CommonResult[TenantCreateResponse]:
    """Create a new tenant (T-02). Platform-only."""
    from app.services.system_tenant import SystemTenantService

    service = SystemTenantService()
    result = await service.create_tenant(request)
    return CommonResult.success(data=result)


@router.put(
    "/tenant/{id}",
    response_model=CommonResult,
    summary="更新租户",
    dependencies=[Depends(require_permission("ims:system:tenant:update"))],
)
async def update_tenant(
    id: str,
    request: TenantUpdateRequest,
) -> CommonResult:
    """Update tenant (T-03). Platform-only."""
    from app.services.system_tenant import SystemTenantService

    service = SystemTenantService()
    result = await service.update_tenant(id, request)
    return CommonResult.success(data=result)


@router.get(
    "/tenant-package/simple-list",
    response_model=CommonResult[list[PackageSimpleItem]],
    summary="套餐选择器列表",
    dependencies=[Depends(require_permission("ims:system:tenant:query"))],
)
async def get_package_simple_list() -> CommonResult[list[PackageSimpleItem]]:
    """Get simple package list for selectors (T-03)."""
    from app.services.system_tenant import SystemTenantService

    service = SystemTenantService()
    result = await service.get_package_simple_list()
    return CommonResult.success(data=result)


@router.get(
    "/tenant-package/list",
    response_model=CommonResult[list[PackageListItem]],
    summary="套餐列表",
    dependencies=[Depends(require_permission("ims:system:tenant:query"))],
)
async def get_package_list() -> CommonResult[list[PackageListItem]]:
    """Get full package list (T-04). Platform-only."""
    from app.services.system_tenant import SystemTenantService

    service = SystemTenantService()
    result = await service.get_package_list()
    return CommonResult.success(data=result)


@router.post(
    "/tenant-package/create",
    response_model=CommonResult,
    summary="创建套餐",
    dependencies=[Depends(require_permission("ims:system:tenant:create"))],
)
async def create_package(request: PackageCreateRequest) -> CommonResult:
    """Create a new package (T-04). Platform-only."""
    from app.services.system_tenant import SystemTenantService

    service = SystemTenantService()
    result = await service.create_package(request)
    return CommonResult.success(data=result)


@router.put(
    "/tenant-package/update",
    response_model=CommonResult,
    summary="更新套餐",
    dependencies=[Depends(require_permission("ims:system:tenant:update"))],
)
async def update_package(
    id: str = Query(..., description="套餐ID"),
    request: PackageUpdateRequest = None,
) -> CommonResult:
    """Update package (T-04). Platform-only."""
    from app.services.system_tenant import SystemTenantService

    service = SystemTenantService()
    result = await service.update_package(id, request)
    return CommonResult.success(data=result)
