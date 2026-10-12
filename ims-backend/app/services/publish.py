# app/services/publish.py - Publish-time visibility snapshot (FP-C02-04)
"""Visibility uses the department set captured when the object was published."""

from typing import Any


def publish(record: Any, creator_dept_ids: list[int]) -> None:
    record.publish_dept_ids = ",".join(str(item) for item in creator_dept_ids)


def can_view(record: Any, viewer_dept_ids: list[int]) -> bool:
    raw = record.publish_dept_ids or ""
    allowed = {int(part) for part in raw.split(",") if part}
    return any(dept_id in allowed for dept_id in viewer_dept_ids)
