# tests/unit/test_clock.py - Injectable clock tests (FP-A01-01 D4)
"""
Tests for the injectable clock functionality.

Per D4 requirement: all 'now' calls go through app/core/clock.py.
"""

import pytest
from datetime import datetime, timezone

from app.core.clock import get_now, set_clock, reset_clock, BEIJING_TZ


class TestClock:
    """Tests for injectable clock (UT-A01-04-01 through UT-A01-04-03)."""
    
    def test_default_clock_returns_current_time(self):
        """UT-A01-04-01: Default clock returns approximately current time."""
        reset_clock()
        
        before = datetime.now(BEIJING_TZ)
        result = get_now()
        after = datetime.now(BEIJING_TZ)
        
        assert before <= result <= after
    
    def test_injectable_clock_returns_fixed_time(self, fixed_time):
        """UT-A01-04-02: Injectable clock returns fixed time for testing."""
        test_time = datetime(2026, 10, 12, 10, 30, 0)
        fixed_time(test_time)
        
        result = get_now()
        
        assert result == test_time
    
    def test_clock_reset_returns_to_default(self, fixed_time):
        """UT-A01-04-03: Reset returns clock to default behavior."""
        fixed_time(datetime(2026, 1, 1, 0, 0, 0))
        reset_clock()
        
        before = datetime.now(BEIJING_TZ)
        result = get_now()
        after = datetime.now(BEIJING_TZ)
        
        assert before <= result <= after
    
    def test_multiple_clock_calls_consistent(self, fixed_time):
        """Multiple calls with fixed clock return same value."""
        test_time = datetime(2026, 6, 15, 12, 0, 0)
        fixed_time(test_time)
        
        results = [get_now() for _ in range(10)]
        
        assert all(r == test_time for r in results)
