# app/core/context.py - Request context (FP-A01-04)
"""
Request context using contextvars for thread-safe access.

Context contents per FP-A01-04:
- traceId: From X-Trace-Id header or generated UUID
- userId: Current user ID (0 for system context)
- tenantId: Current tenant ID
- permCodes: User's permission codes
- dataScopes: User's data scope configuration
- deptIds: User's department IDs (per 04-B-26 multi-dept)
- ipGroupIds: User's IP group IDs
- clientIp: Client IP address

Rules:
- traceId written to response header and all logs
- Worker tasks create "system context" (userId=0, specified tenantId)
- System context cannot process HTTP requests
- White-listed routes without context -> 1008 (fail-closed, FP-C02-05)
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4


@dataclass
class DataScope:
    """Data scope configuration for a role."""
    scope_type: str  # ALL, DEPT, IP_GROUP, SELF
    role_id: int


@dataclass
class RequestContext:
    """Request context data."""
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: Optional[int] = None
    tenant_id: Optional[int] = None
    perm_codes: set[str] = field(default_factory=set)
    data_scopes: list[DataScope] = field(default_factory=list)
    dept_ids: list[int] = field(default_factory=list)
    ip_group_ids: list[int] = field(default_factory=list)
    client_ip: str = ""
    is_system: bool = False  # True for Worker system context
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.user_id is not None and self.user_id > 0
    
    @property
    def has_tenant(self) -> bool:
        """Check if tenant is set."""
        return self.tenant_id is not None and self.tenant_id > 0
    
    def has_permission(self, code: str) -> bool:
        """Check if user has a specific permission code."""
        return code in self.perm_codes
    
    def has_any_permission(self, codes: list[str]) -> bool:
        """Check if user has any of the specified permission codes."""
        return bool(self.perm_codes & set(codes))
    
    def has_all_permissions(self, codes: list[str]) -> bool:
        """Check if user has all of the specified permission codes."""
        return set(codes).issubset(self.perm_codes)
    
    def get_data_scope_types(self) -> set[str]:
        """Get all data scope types from roles."""
        return {ds.scope_type for ds in self.data_scopes}
    
    def has_all_data_scope(self) -> bool:
        """Check if user has ALL data scope."""
        return "ALL" in self.get_data_scope_types()


# Context variable for request context
_ctx_var: ContextVar[Optional[RequestContext]] = ContextVar("request_context", default=None)


class ContextAccessor:
    """Accessor for request context with lazy initialization."""
    
    @property
    def current(self) -> RequestContext:
        """Get current context, raise if not set."""
        ctx = _ctx_var.get()
        if ctx is None:
            raise RuntimeError("Request context not initialized")
        return ctx
    
    @property
    def current_or_none(self) -> Optional[RequestContext]:
        """Get current context or None."""
        return _ctx_var.get()
    
    def set(self, context: RequestContext) -> None:
        """Set the current context."""
        _ctx_var.set(context)
    
    def reset(self) -> None:
        """Reset context to None."""
        _ctx_var.set(None)
    
    @property
    def trace_id(self) -> str:
        """Get trace ID, generate if no context."""
        ctx = _ctx_var.get()
        return ctx.trace_id if ctx else str(uuid4())
    
    @property
    def user_id(self) -> Optional[int]:
        """Get user ID."""
        ctx = _ctx_var.get()
        return ctx.user_id if ctx else None
    
    @property
    def tenant_id(self) -> Optional[int]:
        """Get tenant ID."""
        ctx = _ctx_var.get()
        return ctx.tenant_id if ctx else None
    
    def require_user_id(self) -> int:
        """Get user ID, raise if not set."""
        uid = self.user_id
        if uid is None:
            from app.core.errors import BizError
            raise BizError.no_permission()
        return uid
    
    def require_tenant_id(self) -> int:
        """Get tenant ID, raise if not set."""
        tid = self.tenant_id
        if tid is None:
            from app.core.errors import BizError
            raise BizError.no_permission()
        return tid


# Global context accessor
ctx = ContextAccessor()


def create_system_context(tenant_id: int, trace_id: Optional[str] = None) -> RequestContext:
    """
    Create system context for Worker tasks.
    
    System context has userId=0 and is_system=True.
    Cannot be used to process HTTP requests.
    """
    return RequestContext(
        trace_id=trace_id or str(uuid4()),
        user_id=0,
        tenant_id=tenant_id,
        is_system=True,
    )
