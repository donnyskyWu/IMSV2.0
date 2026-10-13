# tests/unit/test_train_video.py - Video progress anti-cheat tests (B21)
"""
Unit tests for video progress tracking with anti-cheat measures.

Per Q-D11, Q-D12, E2E-B21-27:
- Single increment <= actual interval AND <= 20s
- Interval deduplication
- Coverage >= 95% for completion
"""

import pytest

from app.domains.train.video import (
    calculate_coverage,
    intervals_to_json,
    is_video_complete,
    merge_intervals,
    parse_intervals_json,
    update_watched_intervals,
    validate_video_progress,
)


class TestMergeIntervals:
    """Tests for interval merging (deduplication)."""

    def test_empty_intervals(self):
        """UT-B21-VIDEO-04: Empty list returns empty."""
        assert merge_intervals([]) == []

    def test_single_interval(self):
        """Single interval unchanged."""
        assert merge_intervals([(0, 30)]) == [(0, 30)]

    def test_non_overlapping(self):
        """Non-overlapping intervals preserved."""
        result = merge_intervals([(0, 30), (60, 90)])
        assert result == [(0, 30), (60, 90)]

    def test_overlapping_merge(self):
        """UT-B21-VIDEO-04: Overlapping intervals merged."""
        result = merge_intervals([(0, 30), (20, 50)])
        assert result == [(0, 50)]

    def test_adjacent_merge(self):
        """Adjacent intervals merged."""
        result = merge_intervals([(0, 30), (30, 60)])
        assert result == [(0, 60)]

    def test_unsorted_input(self):
        """Unsorted intervals handled correctly."""
        result = merge_intervals([(60, 90), (0, 30)])
        assert result == [(0, 30), (60, 90)]

    def test_duplicate_region(self):
        """UT-B21-VIDEO-04: Repeated watching same segment only counts once."""
        result = merge_intervals([(0, 30), (0, 30), (0, 30)])
        assert result == [(0, 30)]

    def test_contained_interval(self):
        """Contained interval absorbed."""
        result = merge_intervals([(0, 60), (10, 30)])
        assert result == [(0, 60)]


class TestCalculateCoverage:
    """Tests for coverage calculation."""

    def test_empty_intervals(self):
        """Zero coverage for empty intervals."""
        assert calculate_coverage([], 100) == 0.0

    def test_zero_duration(self):
        """Zero coverage for zero duration."""
        assert calculate_coverage([(0, 30)], 0) == 0.0

    def test_full_coverage(self):
        """Full coverage returns 1.0."""
        assert calculate_coverage([(0, 100)], 100) == 1.0

    def test_partial_coverage(self):
        """Partial coverage calculated correctly."""
        result = calculate_coverage([(0, 50)], 100)
        assert result == 0.5

    def test_coverage_with_gaps(self):
        """Coverage with gaps calculated correctly."""
        result = calculate_coverage([(0, 30), (60, 90)], 100)
        assert result == 0.6

    def test_overlapping_intervals(self):
        """Overlapping intervals deduplicated before calculation."""
        result = calculate_coverage([(0, 50), (40, 90)], 100)
        assert result == 0.9

    def test_coverage_capped_at_one(self):
        """Coverage capped at 1.0."""
        result = calculate_coverage([(0, 150)], 100)
        assert result == 1.0


class TestIsVideoComplete:
    """Tests for video completion check."""

    def test_complete_at_95_percent(self):
        """UT-B21-VIDEO-05: Complete at exactly 95%."""
        assert is_video_complete([(0, 95)], 100) is True

    def test_incomplete_below_95_percent(self):
        """UT-B21-VIDEO-06: Incomplete below 95%."""
        assert is_video_complete([(0, 94)], 100) is False

    def test_complete_above_95_percent(self):
        """Complete above 95%."""
        assert is_video_complete([(0, 100)], 100) is True

    def test_custom_threshold(self):
        """Custom threshold works."""
        assert is_video_complete([(0, 80)], 100, threshold=0.8) is True
        assert is_video_complete([(0, 79)], 100, threshold=0.8) is False


class TestValidateVideoProgress:
    """Tests for progress validation (anti-cheat)."""

    def test_normal_progress(self):
        """UT-B21-VIDEO-01: Normal progress accepted."""
        is_valid, seconds = validate_video_progress(
            current_pos=30,
            last_pos=15,
            interval_seconds=15.0,
        )
        assert is_valid is True
        assert seconds == 15

    def test_fast_forward_detected(self):
        """UT-B21-VIDEO-02: Fast forward detected."""
        is_valid, seconds = validate_video_progress(
            current_pos=100,
            last_pos=15,
            interval_seconds=15.0,
        )
        assert is_valid is False
        assert seconds == 0

    def test_max_20_seconds_per_heartbeat(self):
        """UT-B21-VIDEO-03: Max 20s even with longer interval."""
        is_valid, seconds = validate_video_progress(
            current_pos=30,
            last_pos=0,
            interval_seconds=30.0,
        )
        assert is_valid is False
        assert seconds == 0

    def test_backward_no_credit(self):
        """UT-B21-VIDEO-07: Backward movement valid but no credit."""
        is_valid, seconds = validate_video_progress(
            current_pos=10,
            last_pos=30,
            interval_seconds=15.0,
        )
        assert is_valid is True
        assert seconds == 0

    def test_pause_no_credit(self):
        """Pause (same position) valid but no credit."""
        is_valid, seconds = validate_video_progress(
            current_pos=30,
            last_pos=30,
            interval_seconds=15.0,
        )
        assert is_valid is True
        assert seconds == 0

    def test_exact_interval_match(self):
        """Exact interval match is valid."""
        is_valid, seconds = validate_video_progress(
            current_pos=35,
            last_pos=20,
            interval_seconds=15.0,
        )
        assert is_valid is True
        assert seconds == 15

    def test_slightly_over_interval(self):
        """Slightly over interval is fast forward."""
        is_valid, seconds = validate_video_progress(
            current_pos=36,
            last_pos=20,
            interval_seconds=15.0,
        )
        assert is_valid is False
        assert seconds == 0


class TestUpdateWatchedIntervals:
    """Tests for interval updates."""

    def test_add_to_empty(self):
        """Add interval to empty list."""
        result = update_watched_intervals([], 0, 30)
        assert result == [(0, 30)]

    def test_add_non_overlapping(self):
        """Add non-overlapping interval."""
        result = update_watched_intervals([(0, 30)], 60, 90)
        assert result == [(0, 30), (60, 90)]

    def test_add_overlapping(self):
        """Add overlapping interval merges."""
        result = update_watched_intervals([(0, 30)], 20, 50)
        assert result == [(0, 50)]

    def test_invalid_interval_ignored(self):
        """Invalid interval (start >= end) ignored."""
        result = update_watched_intervals([(0, 30)], 50, 50)
        assert result == [(0, 30)]

        result = update_watched_intervals([(0, 30)], 60, 40)
        assert result == [(0, 30)]


class TestIntervalsJson:
    """Tests for JSON serialization."""

    def test_parse_empty(self):
        """Parse empty/null returns empty list."""
        assert parse_intervals_json(None) == []
        assert parse_intervals_json("") == []

    def test_parse_valid(self):
        """Parse valid JSON."""
        result = parse_intervals_json("[[0, 30], [60, 90]]")
        assert result == [(0, 30), (60, 90)]

    def test_parse_invalid(self):
        """Parse invalid JSON returns empty."""
        assert parse_intervals_json("invalid") == []
        assert parse_intervals_json("[invalid]") == []

    def test_serialize(self):
        """Serialize intervals to JSON."""
        result = intervals_to_json([(0, 30), (60, 90)])
        assert result == "[[0, 30], [60, 90]]"
