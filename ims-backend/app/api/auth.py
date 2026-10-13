# app/api/auth.py - Authentication endpoints (FW-D01, FW-D02, FW-D06)
"""
Authentication API endpoints.

Priority endpoints for B0b:
- POST /login - Local username/password login (FP-D01-01)
- POST /refresh-token - Token refresh (FP-D01-03)
- POST /logout - Logout (FP-D01-04)
- GET /me - Current user info, menus, permissions (FP-D06-01)

Also includes:
- GET /sso/dingtalk/redirect - DingTalk SSO redirect (FP-D02-01)
- GET /sso/dingtalk/callback - DingTalk SSO callback (FP-D02-02)
"""

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import Field

from app.core.response import CommonResult
from app.core.serialization import BaseSchema

router = APIRouter()


# ============== Schemas ==============

class LoginRequest(BaseSchema):
    """Login request."""
    username: str = Field(..., min_length=4, max_length=30)
    password: str = Field(..., min_length=8, max_length=32)
    captcha: Optional[str] = None


class LoginResponse(BaseSchema):
    """Login response."""
    access_token: str
    refresh_token: str
    expires_in: int = 7200
    pwd_reset_required: bool = False


class RefreshTokenRequest(BaseSchema):
    """Token refresh request."""
    refresh_token: str


class UserInfo(BaseSchema):
    """Current user info."""
    id: str
    username: str
    nickname: str
    avatar: Optional[str] = None
    main_dept_name: Optional[str] = None
    dept_names: list[str] = []
    position_label: Optional[str] = None
    pwd_reset_required: bool = False


class MenuItem(BaseSchema):
    """Menu tree item."""
    id: str
    parent_id: Optional[str] = None
    name: str
    type: str  # DIR, MENU
    perm_code: Optional[str] = None
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort: int = 0
    visible: bool = True
    children: list["MenuItem"] = []


class PermDetail(BaseSchema):
    """Permission detail (R/W/D)."""
    r: bool = False
    w: bool = False
    d: bool = False


class MeResponse(BaseSchema):
    """GET /me response."""
    user: UserInfo
    menus: list[MenuItem]
    perm_codes: list[str]
    perm_details: dict[str, PermDetail]
    data_scope_text: str


class ChangePasswordRequest(BaseSchema):
    """修改本人密码。长度交给服务层校验，以便返回规格文案。"""
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=1, max_length=128)


class DingTalkSSORequest(BaseSchema):
    """DingTalk SSO redirect request."""
    redirect: Optional[str] = "/"


class SetPasswordRequest(BaseSchema):
    """Set password request (PC-03)."""
    new_password: str = Field(..., min_length=1, max_length=128)


class SessionItem(BaseSchema):
    """Session item (PC-04)."""
    sid: str
    deviceName: str
    ip: str
    loginTime: Optional[str] = None
    lastActiveTime: Optional[str] = None
    current: bool = False


class SessionListResponse(BaseSchema):
    """Session list response (PC-04)."""
    list: list[SessionItem]


# ============== Endpoints ==============

@router.post("/login", response_model=CommonResult[LoginResponse], summary="账号密码登录")
async def login(request: LoginRequest) -> CommonResult[LoginResponse]:
    """
    Local username/password login.

    Rules per FP-D01-01:
    - User not exist or wrong password -> 1214 (same message)
    - 5 consecutive failures -> lock 15 minutes, return 1215
    - FROZEN/RESIGNED -> 1216 (after password check)
    - Tenant disabled/expired -> 1008
    - Success: clear count, write last_login_time/ip, create session, write login log
    - Non-existent username also counts failures (prevent enumeration)
    """
    from app.services.auth import AuthService

    auth_service = AuthService()
    result = await auth_service.login(
        username=request.username,
        password=request.password,
    )
    return CommonResult.success(data=result)


@router.post("/refresh-token", response_model=CommonResult[LoginResponse], summary="刷新令牌")
async def refresh_token(request: RefreshTokenRequest) -> CommonResult[LoginResponse]:
    """
    Refresh access token.

    Rules per FP-D01-03 / 裁定 24:
    - Valid refresh -> new access + new refresh (old refresh invalidated)
    - Rotation keeps the login-time session deadline; Redis TTL is the remainder
    - Invalid, expired, or past the absolute 7 days -> 1002 (HTTP 401)
    - Reused refresh -> 1002 and the whole session is revoked
    - 先消耗旧 refresh，再校验租户。Tenant disabled or expired -> 1008，旧 refresh 不退回
    """
    from app.services.auth import AuthService

    auth_service = AuthService()
    result = await auth_service.refresh(refresh_token=request.refresh_token)
    return CommonResult.success(data=result)


@router.post("/logout", response_model=CommonResult, summary="登出")
async def logout(request: Request) -> CommonResult:
    """
    Logout current session.

    Rules per FP-D01-04:
    - Delete current session
    - Add access token sid to blacklist (TTL = remaining time)
    """
    from app.services.auth import AuthService

    auth_service = AuthService()

    # Get token from header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        await auth_service.logout(token)

    return CommonResult.success()


@router.get("/me", response_model=CommonResult[MeResponse], summary="获取当前用户信息")
async def get_current_user_info() -> CommonResult[MeResponse]:
    # LOGIN_ONLY: authentication without a business permission code.
    """
    Get current user's info, menus, and permissions.

    Rules per FP-D06-01:
    - Menu tree = tenant package menus ∩ enabled role menus
    - Tree is nested DIR and MENU only; buttons are permCodes, not nodes
    - permCodes from all enabled roles
    - dataScopeText in Chinese (e.g., "本部门（市场一部、市场二部）")
    - PENDING_CONFIG or empty permissions -> empty menus with prompt
    """
    from app.core.context import ctx
    from app.core.errors import BizError
    from app.services.auth import AuthService

    auth_service = AuthService()
    # 未登录与其它需要登录的接口一致：HTTP 401 + 1002，而不是 200 + 1008。
    user_id = ctx.user_id
    if user_id is None or user_id <= 0:
        raise BizError(1002)
    result = await auth_service.get_current_user_info(user_id)
    return CommonResult.success(data=result)


get_current_user_info.__login_only__ = True


@router.post(
    "/password/change",
    response_model=CommonResult,
    summary="修改本人密码",
)
async def change_password(body: ChangePasswordRequest) -> CommonResult:
    """
    修改本人密码（FP-B1-PW-01）。

    原密码错误返回 1214。规则不符或与当前密码相同返回 1001。
    成功后清除须改密标记，其他会话失效，当前会话保留。
    """
    from app.core.context import ctx
    from app.core.errors import BizError
    from app.services.auth import AuthService

    current = ctx.current_or_none
    if current is None or not current.user_id:
        raise BizError(1002)
    await AuthService().change_own_password(
        user_id=current.user_id,
        old_password=body.old_password,
        new_password=body.new_password,
        keep_session_id=current.session_id,
    )
    return CommonResult.success()


change_password.__login_only__ = True


@router.post(
    "/password/set",
    response_model=CommonResult,
    summary="设置密码",
)
async def set_password(body: SetPasswordRequest) -> CommonResult:
    """
    Set password for user without password (PC-03).

    无密码用户设置密码。成功后清除须改密标记，其他会话失效，当前会话保留。
    已有密码用户调用返回 1001。
    静默忽略请求中的 roleIds、tenantId、status、deptId 等字段。
    """
    from app.core.context import ctx
    from app.core.errors import BizError
    from app.services.auth import AuthService

    current = ctx.current_or_none
    if current is None or not current.user_id:
        raise BizError(1002)
    await AuthService().set_password(
        user_id=current.user_id,
        new_password=body.new_password,
        keep_session_id=current.session_id,
    )
    return CommonResult.success()


set_password.__login_only__ = True


@router.get(
    "/session/my",
    response_model=CommonResult[SessionListResponse],
    summary="我的会话列表",
)
async def get_my_sessions() -> CommonResult[SessionListResponse]:
    """
    Get current user's session list (PC-04).

    返回当前用户的所有有效会话，包含设备名、IP、登录时间、最后活跃时间、是否当前会话。
    """
    from app.core.context import ctx
    from app.core.errors import BizError
    from app.services.auth import AuthService

    current = ctx.current_or_none
    if current is None or not current.user_id:
        raise BizError(1002)
    sessions = await AuthService().get_my_sessions(current.user_id)
    return CommonResult.success(data={"list": sessions})


get_my_sessions.__login_only__ = True


@router.delete(
    "/session/my",
    response_model=CommonResult,
    summary="下线指定会话",
)
async def delete_my_session(
    sid: str,
) -> CommonResult:
    """
    Delete one of current user's sessions (PC-04).

    下线指定会话。sid 为空返回 1001，会话不存在或属于其他用户返回 1504。
    删除当前会话等同退出登录。
    """
    from app.core.context import ctx
    from app.core.errors import BizError
    from app.services.auth import AuthService

    current = ctx.current_or_none
    if current is None or not current.user_id:
        raise BizError(1002)
    await AuthService().delete_my_session(current.user_id, sid)
    return CommonResult.success()


delete_my_session.__login_only__ = True


@router.get("/sso/dingtalk/redirect", summary="钉钉SSO跳转")
async def dingtalk_sso_redirect(redirect: str = "/"):
    """
    DingTalk SSO redirect.

    Rules per FP-D02-01:
    - Generate 32-char random state, store in Redis 5 min (with redirect)
    - redirect must be site-relative path, otherwise replace with /
    - DingTalk not configured -> 1008
    """
    from fastapi.responses import RedirectResponse

    from app.services.auth import AuthService

    auth_service = AuthService()
    redirect_url = await auth_service.get_dingtalk_redirect_url(redirect)
    return RedirectResponse(url=redirect_url)


@router.get("/sso/dingtalk/callback", summary="钉钉SSO回调")
async def dingtalk_sso_callback(auth_code: str, state: str):
    """
    DingTalk SSO callback.

    Rules per FP-D02-02:
    - state not exist/expired/used -> 1002 (GETDEL atomic)
    - Use authCode to get DingTalk userid + phone
    - Match: ims_auth_user_mapping.dingtalk_user_id -> mobile_hash
    - No match -> 1217, no token issued
    - FROZEN/RESIGNED -> 1216
    - Success: issue tokens, 302 to /sso-callback#accessToken=...&refreshToken=...&redirect=...
    """
    from fastapi.responses import RedirectResponse

    from app.services.auth import AuthService

    auth_service = AuthService()
    callback_url = await auth_service.handle_dingtalk_callback(auth_code, state)
    return RedirectResponse(url=callback_url)
