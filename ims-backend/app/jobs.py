# 定时任务登记。版本 v1.0 · 2026-10-13
"""把 @job 从 worker 进程里拆出来，避免服务和进程互相导入。"""

from typing import Any

JOBS: list[str] = []


def job(fn: Any) -> Any:
    """登记任务名。重复导入不重复登记。"""
    if fn.__name__ not in JOBS:
        JOBS.append(fn.__name__)
    return fn
