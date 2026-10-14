# app/core/errors.py - Error codes and business exceptions (FP-A02-02, FP-A02-03)
"""
Error code registry and business exception handling.

Rules per FP-A02-02:
- Codes registered by domain with number ranges per error code appendix §2
- Duplicate code registration -> startup failure
- Domain registering code outside its range -> startup failure
- Chinese prompts must not contain English enum codes, API paths, or dev codes
- Static check: msg containing [A-Z_]{3,} or /admin-api -> failure

Cross-domain common codes (COMMON domain):
- 1001: Parameter validation failed
- 1008: No permission
- 1500-1504: Reference errors
- 5001-5007: System errors
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

# Code ranges per error code appendix §2
CODE_RANGES: dict[str, tuple[int, int]] = {
    "COMMON": (0, 0),  # Special: 0 for success, 1001, 1008, 1500-1504, 5001-5007
    "AUTH": (1001, 1010),
    "SYS": (1211, 1290),  # 1211-1220 + extension 1281-1290
    "FLOW": (1131, 1140),
    "CONTENT": (1051, 1070),
    "COMP": (1041, 1050),
    "TRAIN": (1101, 1120),
    "LIVE": (1271, 1280),
    "SYSTEM": (5001, 5007),
}

# Allowed codes for COMMON domain
COMMON_CODES = {0, 1001, 1002, 1003, 1008, 1500, 1501, 1502, 1503, 1504, 5001, 5002, 5003, 5004, 5005, 5006, 5007}


class FrontStrategy(str, Enum):
    """Frontend handling strategy."""
    TOAST = "toast"
    RELOGIN = "relogin"
    NO_PERMISSION = "noPermission"
    SILENT = "silent"
    FIELD_ERROR = "fieldError"


@dataclass
class ErrorCodeDef:
    """Error code definition."""
    code: int
    domain: str
    msg: str
    front_strategy: FrontStrategy = FrontStrategy.TOAST

    def format_msg(self, **params: Any) -> str:
        """Format message with parameters."""
        try:
            return self.msg.format(**params)
        except KeyError:
            return self.msg


class ErrorCodeRegistry:
    """Registry for all error codes."""

    # Pattern to detect forbidden content in messages
    FORBIDDEN_PATTERN = re.compile(r"[A-Z_]{3,}|/admin-api")

    def __init__(self) -> None:
        self._codes: dict[int, ErrorCodeDef] = {}
        self._frozen = False

    def register(
        self,
        code: int,
        domain: str,
        msg: str,
        front_strategy: FrontStrategy = FrontStrategy.TOAST,
    ) -> ErrorCodeDef:
        """Register an error code."""
        if self._frozen:
            raise RuntimeError("Error code registry is frozen")

        # Check for duplicate
        if code in self._codes:
            existing = self._codes[code]
            raise ValueError(
                f"Duplicate error code {code}: already registered by {existing.domain}"
            )

        # Check domain range
        if domain == "COMMON":
            if code not in COMMON_CODES:
                raise ValueError(f"Code {code} not allowed for COMMON domain")
        elif domain in CODE_RANGES:
            min_code, max_code = CODE_RANGES[domain]
            if not (min_code <= code <= max_code):
                raise ValueError(
                    f"Code {code} outside range for {domain} domain ({min_code}-{max_code})"
                )

        # Check message content (no English codes or API paths)
        # Skip check for error code numbers themselves
        msg_check = re.sub(r'\d+', '', msg)  # Remove numbers
        if self.FORBIDDEN_PATTERN.search(msg_check):
            raise ValueError(
                f"Error message for code {code} contains forbidden content "
                f"(English codes or API paths): {msg}"
            )

        error_def = ErrorCodeDef(
            code=code,
            domain=domain,
            msg=msg,
            front_strategy=front_strategy,
        )
        self._codes[code] = error_def
        return error_def

    def get(self, code: int) -> Optional[ErrorCodeDef]:
        """Get error code definition."""
        return self._codes.get(code)

    def freeze(self) -> None:
        """Freeze registry to prevent further registration."""
        self._frozen = True

    def export_strict(self, entries: Optional[list[dict[str, Any]]] = None) -> dict[Any, dict[str, str]]:
        """Build error-codes JSON. A missing strategy fails the build."""
        if entries is None:
            entries = [
                {
                    "code": code,
                    "msg": defn.msg,
                    "strategy": defn.front_strategy.value,
                }
                for code, defn in self._codes.items()
            ]
        exported: dict[Any, dict[str, str]] = {}
        for item in entries:
            strategy = item.get("strategy")
            if not strategy:
                raise RuntimeError(f"error code {item.get('code')} missing strategy")
            exported[item["code"]] = {"msg": item["msg"], "strategy": strategy}
        return exported

    def export_json(self) -> dict[int, dict[str, str]]:
        """Export for frontend error-codes.json (FP-H03-01)."""
        return {
            code: {"msg": defn.msg, "strategy": defn.front_strategy.value}
            for code, defn in self._codes.items()
        }

    def all_codes(self) -> list[int]:
        """Get all registered codes."""
        return list(self._codes.keys())


# Global registry
error_codes = ErrorCodeRegistry()


# Register common error codes (§0.4 and error code appendix)
error_codes.register(0, "COMMON", "成功")
error_codes.register(1001, "COMMON", "参数校验失败", FrontStrategy.FIELD_ERROR)
error_codes.register(1002, "COMMON", "登录已失效，请重新登录", FrontStrategy.RELOGIN)
error_codes.register(1003, "COMMON", "您的账号已在其他设备登录，本设备已下线", FrontStrategy.RELOGIN)
error_codes.register(1006, "AUTH", "钉钉登录失败，请重新扫码", FrontStrategy.TOAST)
error_codes.register(1008, "COMMON", "暂无权限", FrontStrategy.NO_PERMISSION)
error_codes.register(1500, "COMMON", "关联的实体不存在", FrontStrategy.TOAST)
error_codes.register(1501, "COMMON", "关联的实体已停用或注销", FrontStrategy.TOAST)
error_codes.register(1502, "COMMON", "该记录已被其他数据引用，无法操作", FrontStrategy.TOAST)
error_codes.register(1503, "COMMON", "字典值不合法", FrontStrategy.FIELD_ERROR)
error_codes.register(1504, "COMMON", "资源不可用", FrontStrategy.TOAST)

# System errors (5001-5007)
error_codes.register(5001, "SYSTEM", "数据库服务异常，请稍后再试", FrontStrategy.TOAST)
error_codes.register(5002, "SYSTEM", "缓存服务异常，请稍后再试", FrontStrategy.TOAST)
error_codes.register(5003, "SYSTEM", "钉钉服务异常，请稍后再试", FrontStrategy.TOAST)
error_codes.register(5004, "SYSTEM", "图像生成服务异常，请稍后再试", FrontStrategy.TOAST)
error_codes.register(5005, "SYSTEM", "文件操作失败", FrontStrategy.TOAST)
error_codes.register(5006, "SYSTEM", "外部服务异常，请稍后再试", FrontStrategy.TOAST)
error_codes.register(5007, "SYSTEM", "系统繁忙，请稍后再试", FrontStrategy.TOAST)

# SYS domain (1211-1220, 1281-1290)
error_codes.register(1211, "SYS", "主键不可修改", FrontStrategy.TOAST)
error_codes.register(1212, "SYS", "权限码不存在", FrontStrategy.TOAST)
error_codes.register(1213, "SYS", "参数项不存在", FrontStrategy.TOAST)
error_codes.register(1214, "SYS", "用户名或密码错误", FrontStrategy.TOAST)
error_codes.register(1215, "SYS", "账号已锁定，请 {n} 分钟后再试", FrontStrategy.TOAST)
error_codes.register(1216, "SYS", "账号已冻结或已离职，无法登录", FrontStrategy.TOAST)
error_codes.register(1217, "SYS", "未找到与钉钉账号对应的用户，请联系管理员", FrontStrategy.TOAST)
error_codes.register(1218, "SYS", "部门不能移动到自身或下级部门之下", FrontStrategy.TOAST)
error_codes.register(1219, "SYS", "同一上级部门下已有同名部门", FrontStrategy.TOAST)
error_codes.register(1220, "SYS", "系统部门或钉钉部门不允许此操作", FrontStrategy.TOAST)
error_codes.register(1222, "MASTER", "公众号容量不能小于已注册数", FrontStrategy.TOAST)

# CERT domain (1032-1035)，沿用全局规范，不新增号。
error_codes.register(1032, "CERT", "已存在有效档案，如为新证请走换证流程", FrontStrategy.TOAST)
error_codes.register(1033, "CERT", "档案待审或审核状态非法", FrontStrategy.TOAST)
error_codes.register(1034, "CERT", "访问级别不足", FrontStrategy.TOAST)
error_codes.register(1035, "CERT", "高频访问拦截", FrontStrategy.TOAST)

# FLOW domain (1131-1140)
error_codes.register(1139, "FLOW", "无权撤销此流程", FrontStrategy.TOAST)

# TRAIN domain (1101-1120)
error_codes.register(1101, "TRAIN", "资料未发布或不存在", FrontStrategy.TOAST)
error_codes.register(1106, "TRAIN", "调用失败，请稍后再试", FrontStrategy.TOAST)
error_codes.register(1107, "TRAIN", "生成超时，请稍后再试", FrontStrategy.TOAST)
error_codes.register(1108, "TRAIN", "生成的题目数量为 0", FrontStrategy.TOAST)
error_codes.register(1109, "TRAIN", "服务未配置或未启用", FrontStrategy.TOAST)

# LIVE domain (1271-1280) - Football errors
error_codes.register(1271, "LIVE", "直播服务异常", FrontStrategy.TOAST)
error_codes.register(1272, "LIVE", "直播服务超时", FrontStrategy.TOAST)
error_codes.register(1273, "LIVE", "直播服务业务错误", FrontStrategy.TOAST)


class BizError(Exception):
    """Business logic exception."""

    def __init__(
        self,
        code: int,
        msg: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
        **params: Any,
    ) -> None:
        self.code = code
        self.data = dict(data or {})
        if "refs" in params:
            self.data["refs"] = params["refs"]

        # Get message from registry
        error_def = error_codes.get(code)
        if error_def:
            self.msg = msg or error_def.format_msg(**params)
            self.front_strategy = error_def.front_strategy
        else:
            self.msg = msg or "未知错误"
            self.front_strategy = FrontStrategy.TOAST

        super().__init__(self.msg)

    @classmethod
    def validation_error(cls, field_errors: list[dict[str, str]]) -> "BizError":
        """Create a validation error with field-level errors."""
        return cls(1001, data={"fieldErrors": field_errors})

    @classmethod
    def not_found(cls) -> "BizError":
        """Create a resource not found error (1504, no details exposed)."""
        return cls(1504)

    @classmethod
    def no_permission(cls, msg: Optional[str] = None) -> "BizError":
        """Create a permission denied error."""
        return cls(1008, msg=msg)

    @classmethod
    def ref_not_exist(cls, field: str) -> "BizError":
        """Create a reference not exist error."""
        return cls(1500, data={"field": field})

    @classmethod
    def ref_disabled(cls, field: str) -> "BizError":
        """Create a reference disabled error."""
        return cls(1501, data={"field": field})

    @classmethod
    def ref_in_use(cls, refs: list[dict[str, Any]]) -> "BizError":
        """Create a reference in use error."""
        return cls(1502, data={"refs": refs})


class FieldError:
    """Field-level validation error."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message}


# Convenience functions for registry access
def register_error(
    code: int,
    domain: str,
    msg: str,
    front_strategy: FrontStrategy = FrontStrategy.TOAST,
) -> ErrorCodeDef:
    """Register an error code."""
    return error_codes.register(code, domain, msg, front_strategy)


def get_error_info(code: int) -> Optional[dict[str, Any]]:
    """Get error code information as dict."""
    error_def = error_codes.get(code)
    if error_def is None:
        return None
    return {
        "code": error_def.code,
        "domain": error_def.domain,
        "msg": error_def.msg,
        "front_strategy": error_def.front_strategy.value,
    }
