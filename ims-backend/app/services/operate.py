# app/services/operate.py - Operation log must not break the business call (FP-F01)
"""Run the business action even when writing the operation log fails."""

from typing import Any, Callable


def run_with_log(action: Callable[[], Any], write_log: Callable[[], None]) -> Any:
    result = action()
    try:
        write_log()
    except Exception:
        return result
    return result


def audit_sensitive_view(write_log: Callable[[], None]) -> None:
    """敏感查看日志。写失败不反向失败业务（B0a FP-F02-02）。"""
    try:
        write_log()
    except Exception:
        return None
