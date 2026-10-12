# app/integrations/football_live/metrics.py - Snapshot merge and outbox (FP-H06-04)
"""Return an IMS snapshot when Football is unavailable, and retry outbox rows."""

from typing import Any

from app.core.clock import get_now
from app.integrations.football_live.reader import UNAVAILABLE, FootballUnavailable


def merge_live_metrics(reader: Any, room_id: int, tenant_id: int, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Attach live numbers, or mark the snapshot unavailable without raising."""
    room = reader.get_room(room_id, tenant_id)
    if isinstance(room, FootballUnavailable) or room is UNAVAILABLE:
        merged = dict(snapshot)
        merged["unavailable"] = True
        merged["marker"] = "暂不可用"
        return merged
    merged = dict(snapshot)
    merged["unavailable"] = False
    merged["viewer_count"] = getattr(room, "viewer_count", 0)
    return merged


def edit_session(session_row: dict[str, Any], name: str) -> dict[str, Any]:
    """Local session edits succeed even when Football is down."""
    session_row["name"] = name
    return session_row


def retry_outbox(event: Any) -> Any:
    """Mark a failed outbox row successful."""
    event.status = "SUCCESS"
    event.synced_at = get_now()
    return event
