# app/domains/train/video.py - Video progress anti-cheat (B21 Q-D11, Q-D12)
"""
Video progress tracking with anti-cheat measures.

Per Q-D11, Q-D12, E2E-B21-27:
- Completion: watched_intervals coverage >= 95% (not simple duration sum)
- Single increment <= actual interval AND <= 20s
- Interval deduplication: merge overlapping/adjacent intervals
- Fast-forward detection: position delta > allowed increment -> no credit

P0 functions with 90% branch coverage required.
"""

from typing import Optional

MAX_SINGLE_INCREMENT = 20


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    Merge overlapping or adjacent intervals.

    Implements deduplication: watching the same segment twice counts once.

    Args:
        intervals: List of (start, end) tuples

    Returns:
        Merged list of non-overlapping intervals
    """
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged: list[tuple[int, int]] = [sorted_intervals[0]]

    for start, end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def calculate_coverage(
    intervals: list[tuple[int, int]],
    total_duration: int,
) -> float:
    """
    Calculate coverage rate after interval deduplication.

    P0 function - 90% branch coverage required.

    Args:
        intervals: List of watched (start, end) intervals
        total_duration: Total video duration in seconds

    Returns:
        Coverage rate 0.0 ~ 1.0
    """
    if total_duration <= 0:
        return 0.0

    merged = merge_intervals(intervals)
    covered = sum(end - start for start, end in merged)
    return min(covered / total_duration, 1.0)


def is_video_complete(
    intervals: list[tuple[int, int]],
    total_duration: int,
    threshold: float = 0.95,
) -> bool:
    """
    Check if video is considered complete.

    Completion criterion: coverage >= 95% (per Q-D11)

    Args:
        intervals: Watched intervals
        total_duration: Video duration in seconds
        threshold: Completion threshold (default 0.95)

    Returns:
        True if video meets completion criteria
    """
    coverage = calculate_coverage(intervals, total_duration)
    return coverage >= threshold


def validate_video_progress(
    current_pos: int,
    last_pos: int,
    interval_seconds: float,
) -> tuple[bool, int]:
    """
    Validate video progress report and calculate effective seconds.

    P0 function - 90% branch coverage required.

    Rules (per Q-D12):
    - Single increment <= actual heartbeat interval AND <= 20s
    - Fast-forward (position jump > allowed) -> 0 effective seconds
    - Backward/pause -> 0 effective seconds (valid but no credit)

    Args:
        current_pos: Current reported position in seconds
        last_pos: Last known position in seconds
        interval_seconds: Actual time since last heartbeat

    Returns:
        (is_valid, effective_seconds)
        - is_valid: True if not a fast-forward cheat
        - effective_seconds: Seconds to credit (0 if invalid)
    """
    if current_pos <= last_pos:
        return True, 0

    delta = current_pos - last_pos
    max_allowed = min(interval_seconds, MAX_SINGLE_INCREMENT)

    if delta > max_allowed:
        return False, 0

    return True, int(delta)


def update_watched_intervals(
    existing: list[tuple[int, int]],
    new_start: int,
    new_end: int,
) -> list[tuple[int, int]]:
    """
    Add a new interval and merge with existing ones.

    Args:
        existing: Current watched intervals
        new_start: New interval start
        new_end: New interval end

    Returns:
        Updated merged intervals
    """
    if new_start >= new_end:
        return existing

    intervals = existing + [(new_start, new_end)]
    return merge_intervals(intervals)


def parse_intervals_json(json_str: Optional[str]) -> list[tuple[int, int]]:
    """
    Parse intervals from JSON string.

    JSON format: [[start, end], [start, end], ...]

    Args:
        json_str: JSON string or None

    Returns:
        List of (start, end) tuples
    """
    if not json_str:
        return []

    import json
    try:
        data = json.loads(json_str)
        if not isinstance(data, list):
            return []
        return [(int(item[0]), int(item[1])) for item in data if len(item) >= 2]
    except (json.JSONDecodeError, ValueError, TypeError, IndexError):
        return []


def intervals_to_json(intervals: list[tuple[int, int]]) -> str:
    """
    Convert intervals to JSON string.

    Args:
        intervals: List of (start, end) tuples

    Returns:
        JSON string
    """
    import json
    return json.dumps([[start, end] for start, end in intervals])
