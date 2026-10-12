# app/api/demo.py - Demo endpoints for testing (test env only)
"""
Demo API endpoints for B0b request layer testing.

Per FP-B08-08:
- GET /admin-api/ims/demo/error?code= - Returns specified error code
- Only registered in test environment (not in prod)
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_login
from app.core.config import get_settings
from app.core.errors import BizError, get_error_info
from app.core.response import CommonResult

router = APIRouter()
settings = get_settings()


@router.get(
    "/error",
    response_model=CommonResult,
    summary="测试错误码响应",
    dependencies=[Depends(require_login)],
)
async def demo_error(
    code: int = Query(..., description="错误码"),
) -> CommonResult:
    """
    Return specified error code for testing.

    LOGIN_ONLY - for B0b request layer example page to verify error handling.
    Only available in test environment.
    """
    error_info = get_error_info(code)
    if error_info:
        raise BizError(code=code, msg=error_info.msg)
    else:
        raise BizError(code=code, msg=f"Error code {code}")
