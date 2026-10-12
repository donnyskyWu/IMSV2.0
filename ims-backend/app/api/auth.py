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


class DingTalkSSORequest(BaseSchema):
    """DingTalk SSO redirect request."""
    redirect: Optional[str] = "/"


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

    Rules per FP-D01-03:
    - Valid refresh -> new access + new refresh (old refresh invalidated)
    - Invalid/expired/reused refresh -> 1002 (HTTP 401)
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
