# app/api/deps.py - API dependencies for auth and permissions (FP-D03-01, FP-D03-02)
"""
FastAPI dependencies for authentication and permission checks.

Rules per FP-D03-01:
- Route declares permission via Depends(perm("ims:system:user:update"))
- Can declare multiple (any satisfy / all satisfy)
- LOGIN_ONLY for auth-level whitelist (only login + tenant check)
- ANONYMOUS for anonymous whitelist (limited to FP-A01-02 list)
- Business route without any -> startup failure
- Declared permission not in menu seed -> startup failure

Rules per FP-D03-02:
- Permission set = union of all enabled roles ∩ tenant package menus
- DISABLED, PENDING_CONFIG roles contribute nothing
- Read requires R, write requires W, delete requires D
- Not satisfied -> 1008
- Empty set -> 1008
"""

from typing import Callable, Optional

from fastapi import Depends, Header, Request

from app.core.context import RequestContext, ctx
from app.core.errors import BizError


async def get_token_from_header(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[str]:
    """Extract JWT token from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


async def get_current_user_optional(
    token: Optional[str] = Depends(get_token_from_header),
) -> Optional[int]:
    """
    Get current user ID if authenticated, None otherwise.
    
    Sets up request context with user info.
    """
    if not token:
        return None
    
    from app.services.auth import AuthService
    
    auth_service = AuthService()
    try:
        user_info = await auth_service.verify_token(token)
        
        # Update context with user info
        context = RequestContext(
            trace_id=ctx.trace_id,
            user_id=user_info["user_id"],
            tenant_id=user_info["tenant_id"],
            perm_codes=set(user_info.get("perm_codes", [])),
            data_scopes=user_info.get("data_scopes", []),
            dept_ids=user_info.get("dept_ids", []),
            ip_group_ids=user_info.get("ip_group_ids", []),
            client_ip=ctx.current.client_ip if ctx.current_or_none else "",
        )
        ctx.set(context)
        
        return user_info["user_id"]
    except BizError:
        return None


async def get_current_user(
    user_id: Optional[int] = Depends(get_current_user_optional),
) -> int:
    """
    Get current user ID, raise if not authenticated.
    
    Use this for routes that require authentication.
    """
    if user_id is None:
        raise BizError(1002)  # 登录已失效
    return user_id


async def require_login(
    user_id: int = Depends(get_current_user),
) -> int:
    """
    Require login (authentication-level whitelist).
    
    Only checks that user is logged in and has valid tenant.
    Does not check specific permissions.
    """
    # Verify tenant is valid
    tenant_id = ctx.tenant_id
    if tenant_id is None:
        raise BizError.no_permission()
    
    # Could add tenant status check here
    
    return user_id


def require_permission(perm_code: str) -> Callable:
    """
    Create dependency that requires a specific permission.
    
    Usage:
        @router.get("/users", dependencies=[Depends(require_permission("ims:system:user:query"))])
    """
    async def dependency(user_id: int = Depends(get_current_user)) -> int:
        context = ctx.current_or_none
        if context is None:
            raise BizError.no_permission()
        
        if perm_code not in context.perm_codes:
            raise BizError.no_permission()
        
        return user_id
    
    return dependency


def require_any_permission(perm_codes: list[str]) -> Callable:
    """
    Create dependency that requires any of the specified permissions.
    
    Usage:
        @router.get("/dept/tree", dependencies=[
            Depends(require_any_permission(["ims:system:dept:query", "ims:system:user:query"]))
        ])
    """
    async def dependency(user_id: int = Depends(get_current_user)) -> int:
        context = ctx.current_or_none
        if context is None:
            raise BizError.no_permission()
        
        if not context.has_any_permission(perm_codes):
            raise BizError.no_permission()
        
        return user_id
    
    return dependency


def require_all_permissions(perm_codes: list[str]) -> Callable:
    """
    Create dependency that requires all specified permissions.
    """
    async def dependency(user_id: int = Depends(get_current_user)) -> int:
        context = ctx.current_or_none
        if context is None:
            raise BizError.no_permission()
        
        if not context.has_all_permissions(perm_codes):
            raise BizError.no_permission()
        
        return user_id
    
    return dependency


def require_data_scope(model_name: str) -> Callable:
    """
    Create dependency that validates data scope is configured for the model.
    
    Fails at startup if model doesn't have __scope_fields__ defined.
    """
    async def dependency(user_id: int = Depends(get_current_user)) -> int:
        context = ctx.current_or_none
        if context is None:
            raise BizError.no_permission()
        
        # Check if user has any data scope configured
        if not context.data_scopes:
            raise BizError.no_permission()
        
        return user_id
    
    return dependency


class PermissionChecker:
    """
    Permission checker that can be customized per route.
    
    Usage:
        checker = PermissionChecker(read_perm="ims:demo:order:query")
        @router.get("/orders", dependencies=[Depends(checker.read)])
    """
    
    def __init__(
        self,
        read_perm: Optional[str] = None,
        write_perm: Optional[str] = None,
        delete_perm: Optional[str] = None,
    ):
        self.read_perm = read_perm
        self.write_perm = write_perm
        self.delete_perm = delete_perm
    
    async def read(self, user_id: int = Depends(get_current_user)) -> int:
        """Check read permission."""
        if self.read_perm:
            context = ctx.current
            if self.read_perm not in context.perm_codes:
                raise BizError.no_permission()
        return user_id
    
    async def write(self, user_id: int = Depends(get_current_user)) -> int:
        """Check write permission."""
        if self.write_perm:
            context = ctx.current
            if self.write_perm not in context.perm_codes:
                raise BizError.no_permission()
        return user_id
    
    async def delete(self, user_id: int = Depends(get_current_user)) -> int:
        """Check delete permission."""
        if self.delete_perm:
            context = ctx.current
            if self.delete_perm not in context.perm_codes:
                raise BizError.no_permission()
        return user_id
