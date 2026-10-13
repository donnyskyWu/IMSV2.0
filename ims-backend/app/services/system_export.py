# app/services/system_export.py - B2 async export tasks
"""把导出结果写成可下载任务，不再返回占位 task_id。"""

import csv
import io
from typing import Any
from uuid import uuid4

from app.core.cache import Cache

EXPORT_TTL_SECONDS = 3600


def create_export_task(biz_type: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """生成导出任务并写入缓存。调用方拿到的 task_id 可回查。"""
    task_id = uuid4().hex
    buffer = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["id"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "" if row.get(key) is None else row.get(key) for key in fieldnames})
    payload = {
        "task_id": task_id,
        "biz_type": biz_type,
        "status": "SUCCESS",
        "row_count": len(rows),
        "csv": buffer.getvalue(),
    }
    Cache.set_json(f"ims:export:{task_id}", payload, ttl=EXPORT_TTL_SECONDS)
    return {
        "task_id": task_id,
        "status": "SUCCESS",
        "row_count": len(rows),
    }


def get_export_task(task_id: str) -> dict[str, Any] | None:
    """读取导出任务。不存在返回 None。"""
    data = Cache.get_json(f"ims:export:{task_id}")
    if not isinstance(data, dict):
        return None
    return data
