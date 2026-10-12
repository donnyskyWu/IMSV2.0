# app/core/clock.py - Injectable clock for testability (D4: no datetime.now() directly)
"""
Clock abstraction for time operations.

All code must call get_now() instead of datetime.now() directly.
Tests can inject a fake clock via set_clock() for deterministic time testing.

Per work package D4: 取当前时间一律调用 app/core 的时钟函数，禁止直接调 datetime.now()
"""

from datetime import datetime, timezone, timedelta
from typing import Callable, Optional
from zoneinfo import ZoneInfo

BEIJING_TZ = ZoneInfo("Asia/Shanghai")
_clock: Optional[Callable[[], datetime]] = None


def _default_clock() -> datetime:
    """Return current time in Beijing timezone."""
    return datetime.now(BEIJING_TZ)


def get_now() -> datetime:
    """
    Get current time using the configured clock.
    
    Returns Beijing timezone datetime by default.
    Tests can override via set_clock().
    """
    if _clock is not None:
        return _clock()
    return _default_clock()


def set_clock(clock_fn: Callable[[], datetime]) -> None:
    """
    Set a custom clock function for testing.
    
    Example:
        def fake_clock():
            return datetime(2026, 10, 12, 10, 0, 0, tzinfo=BEIJING_TZ)
        set_clock(fake_clock)
    """
    global _clock
    _clock = clock_fn


def reset_clock() -> None:
    """Reset to default system clock."""
    global _clock
    _clock = None


def get_today() -> datetime:
    """Get today's date at midnight in Beijing timezone."""
    now = get_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def format_datetime(dt: datetime) -> str:
    """Format datetime as ISO 8601 with Beijing timezone offset."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BEIJING_TZ)
    return dt.isoformat()


def parse_datetime(s: str) -> datetime:
    """Parse ISO 8601 datetime string, converting to Beijing time."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BEIJING_TZ)
    else:
        dt = dt.astimezone(BEIJING_TZ)
    return dt
