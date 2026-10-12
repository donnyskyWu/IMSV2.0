# app/core - Configuration, context, response, error codes, pagination, serialization, security
"""
Core framework components shared across all domains.
"""

from app.core.clock import get_now, set_clock, reset_clock
from app.core.config import settings, get_settings
from app.core.context import ctx, RequestContext
from app.core.errors import BizError, error_codes
from app.core.response import CommonResult
from app.core.pagination import PageParam, PageResult

__all__ = [
    "get_now",
    "set_clock",
    "reset_clock",
    "settings",
    "get_settings",
    "ctx",
    "RequestContext",
    "BizError",
    "error_codes",
    "CommonResult",
    "PageParam",
    "PageResult",
]
