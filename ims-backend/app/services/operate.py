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
