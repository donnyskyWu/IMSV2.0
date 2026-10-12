# app/core - Configuration, context, response, error codes, pagination, serialization, security
"""
Core framework components shared across all domains.
"""

from app.core.clock import get_now, reset_clock, set_clock
from app.core.config import get_settings, settings
from app.core.context import RequestContext, ctx
from app.core.errors import BizError, error_codes
from app.core.pagination import PageParam, PageResult
from app.core.response import CommonResult

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
