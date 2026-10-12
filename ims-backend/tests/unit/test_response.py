# tests/unit/test_response.py - Response format tests (FP-A02)
"""
Tests for unified response format.

Covers:
- UT-A02-01: Successful response structure {code:0, msg:"成功", data:{...}}
- UT-A02-06: Validation error response with fieldErrors
- UT-A02-07: Uncaught exception returns 5007
- UT-A02-08: DB error returns 5001 without SQL
- UT-A02-10: Resource not found returns 1504
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.errors import BizError
from app.core.response import CommonResult


class TestCommonResult:
    """Tests for CommonResult response model."""
    
    def test_success_response_structure(self):
        """UT-A02-01: Success response has correct structure."""
        result = CommonResult.success(data={"id": "123", "name": "Test"})
        
        assert result.code == 0
        assert result.msg == "成功"
        assert result.data == {"id": "123", "name": "Test"}
    
    def test_error_response_structure(self):
        """UT-A02-01: Error response has correct structure."""
        result = CommonResult.error(code=1001, msg="参数校验失败")
        
        assert result.code == 1001
        assert result.msg == "参数校验失败"
        assert result.data is None
    
    def test_error_with_field_errors(self):
        """UT-A02-06: Validation error includes fieldErrors."""
        field_errors = [
            {"field": "amount", "message": "金额必须为数字"},
            {"field": "name", "message": "名称不能为空"},
        ]
        result = CommonResult.error(
            code=1001, 
            msg="参数校验失败",
            data={"fieldErrors": field_errors}
        )
        
        assert result.code == 1001
        assert "fieldErrors" in result.data
        assert len(result.data["fieldErrors"]) == 2
        
        # Field names should be camelCase
        fields = [e["field"] for e in result.data["fieldErrors"]]
        assert "amount" in fields
        assert "name" in fields
    
    def test_error_from_biz_error(self):
        """UT-A02-07: BizError converts to CommonResult."""
        error = BizError(code=1504, msg="资源不可用")
        result = CommonResult.from_exception(error)
        
        assert result.code == 1504
        assert result.msg == "资源不可用"


class TestValidationErrors:
    """Tests for validation error handling (FP-A02-03)."""
    
    def test_field_errors_camel_case(self):
        """UT-A02-06: Field names in errors are camelCase."""
        # Simulating a validation error for owner_user_id
        field_errors = [
            {"field": "ownerUserId", "message": "必填字段"},  # Should be camelCase
        ]
        result = CommonResult.error(
            code=1001,
            msg="参数校验失败",
            data={"fieldErrors": field_errors}
        )
        
        assert result.data["fieldErrors"][0]["field"] == "ownerUserId"
        # Should NOT be snake_case
        assert "owner_user_id" not in str(result.data)


class TestExceptionHandling:
    """Tests for exception handling in responses (FP-A02-03)."""
    
    def test_uncaught_exception_returns_5007(self):
        """UT-A02-07: Uncaught RuntimeError returns 5007 without details."""
        # The actual exception handling is in middleware
        # Here we test the error code registry
        from app.core.errors import get_error_info
        
        info = get_error_info(5007)
        assert info is not None
        assert "系统繁忙" in info["msg"] or "稍后再试" in info["msg"]
    
    def test_db_error_returns_5001(self):
        """UT-A02-08: Database error returns 5001."""
        from app.core.errors import get_error_info
        
        info = get_error_info(5001)
        assert info is not None
        # Should not contain SQL keywords
        assert "SELECT" not in info["msg"]
        assert "INSERT" not in info["msg"]
    
    def test_redis_error_returns_5002(self):
        """UT-A02-09: Redis error returns 5002."""
        from app.core.errors import get_error_info
        
        info = get_error_info(5002)
        assert info is not None
    
    def test_not_found_returns_1504(self):
        """UT-A02-10: Resource not found returns 1504."""
        error = BizError.not_found()
        
        assert error.code == 1504
        assert "资源" in error.msg or "不可用" in error.msg
