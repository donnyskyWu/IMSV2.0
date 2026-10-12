# app/core/response.py - Unified response format (FP-A02-01)
"""
Unified response format: {code, msg, data}

Rules per FP-A02-01:
- Success: code=0, msg="成功"
- Route functions return data objects directly, framework wraps them
- Route handlers must NOT manually write {code:...} (static check)
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class CommonResult(BaseModel, Generic[T]):
    """
    Unified API response format.

    All API responses follow this structure:
    - code: 0 for success, non-zero for errors
    - msg: Human-readable message in Chinese
    - data: Response payload (can be any type)
    """

    code: int = Field(default=0, description="Response code, 0 = success")
    msg: str = Field(default="成功", description="Response message")
    data: Optional[T] = Field(default=None, description="Response data")

    model_config = {"json_schema_extra": {"examples": [{"code": 0, "msg": "成功", "data": {}}]}}

    @classmethod
    def success(cls, data: Optional[T] = None, msg: str = "成功") -> "CommonResult[T]":
        """Create a success response."""
        return cls(code=0, msg=msg, data=data)

    @classmethod
    def error(cls, code: int, msg: str, data: Optional[T] = None) -> "CommonResult[T]":
        """Create an error response."""
        return cls(code=code, msg=msg, data=data)

    @classmethod
    def from_exception(cls, exc: Any) -> "CommonResult[Any]":
        """Create response from BizError."""
        from app.core.errors import BizError
        if isinstance(exc, BizError):
            return cls(code=exc.code, msg=exc.msg, data=exc.data or None)
        return cls(code=5007, msg="系统繁忙，请稍后再试")


class EmptyData(BaseModel):
    """Empty data model for responses with no payload."""
    pass


# Type aliases for common response types
SuccessResult = CommonResult[EmptyData]


def ok(data: Any = None, msg: str = "成功") -> CommonResult[Any]:
    """Shorthand for success response."""
    return CommonResult.success(data=data, msg=msg)


def fail(code: int, msg: str, data: Any = None) -> CommonResult[Any]:
    """Shorthand for error response."""
    return CommonResult.error(code=code, msg=msg, data=data)
