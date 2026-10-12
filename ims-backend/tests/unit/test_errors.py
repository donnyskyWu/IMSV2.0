# tests/unit/test_errors.py - Error code tests (FP-A02-02)
"""
Tests for error code registry and business errors.

Per FP-A02-02:
- Error codes registered by domain with number ranges
- Same code duplicate registration -> startup failure
- Cross-domain codes allowed for COMMON domain
"""


from app.core.errors import COMMON_CODES, BizError, get_error_info


class TestErrorRegistry:
    """Tests for error code registration."""

    def test_common_codes_registered(self):
        """UT-A02-02-01: Common codes are pre-registered."""
        assert 1001 in COMMON_CODES
        assert 1008 in COMMON_CODES
        assert 1504 in COMMON_CODES
        assert 5001 in COMMON_CODES
        assert 5007 in COMMON_CODES

    def test_auth_codes_registered(self):
        """UT-A02-02-02: Auth/SYS domain codes registered (1214-1217 are SYS range)."""
        info = get_error_info(1214)
        assert info is not None
        assert info["domain"] == "SYS"  # 1214 is in SYS range per spec
        assert "用户名或密码错误" in info["msg"]

        info = get_error_info(1215)
        assert info is not None
        assert "锁定" in info["msg"]

    def test_sys_codes_registered(self):
        """UT-A02-02-03: System domain codes registered."""
        for code in [1218, 1219, 1220]:
            info = get_error_info(code)
            assert info is not None
            assert info["domain"] == "SYS"


class TestBizError:
    """Tests for BizError exception."""

    def test_create_with_registered_code(self):
        """UT-A02-02-04: Create BizError with registered code."""
        error = BizError(1001)

        assert error.code == 1001
        assert "参数" in error.msg

    def test_create_with_custom_message(self):
        """UT-A02-02-05: Create BizError with custom message override."""
        error = BizError(1001, msg="自定义消息")

        assert error.code == 1001
        assert error.msg == "自定义消息"

    def test_create_with_template_params(self):
        """UT-A02-02-06: Create BizError with template parameters."""
        error = BizError(1215, n=15)

        assert error.code == 1215
        assert "15" in error.msg

    def test_create_with_data(self):
        """UT-A02-02-07: Create BizError with additional data."""
        error = BizError(1502, data={"refs": [{"entity": "用户", "count": 5}]})

        assert error.code == 1502
        assert error.data["refs"][0]["entity"] == "用户"

    def test_no_permission_shortcut(self):
        """UT-A02-02-08: no_permission() returns 1008."""
        error = BizError.no_permission()

        assert error.code == 1008
        assert "权限" in error.msg or "暂无权限" in error.msg

    def test_not_found_shortcut(self):
        """UT-A02-02-09: not_found() returns 1504."""
        error = BizError.not_found()

        assert error.code == 1504
        assert "资源" in error.msg or "不可用" in error.msg

    def test_error_string_representation(self):
        """UT-A02-02-10: Error has useful string representation."""
        error = BizError(1001, msg="测试错误")

        error_str = str(error)
        # str() calls __str__ which returns self.msg
        assert "测试错误" in error_str
        # Also verify code is stored correctly
        assert error.code == 1001
