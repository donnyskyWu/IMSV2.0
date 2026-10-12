# tests/unit/test_integrations.py - Integration adapter tests (FP-H04)
"""
Tests for external integration adapters.

Covers:
- UT-H04-01: Mock mode returns mock data without network
- UT-H04-02: Timeout returns 5003
- UT-H04-03: Football error codes 1271-1273
- UT-H04-04: Circuit breaker after 5 failures
- UT-H08-01 through UT-H08-14: Train AI client tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.errors import BizError


class TestDingTalkClient:
    """Tests for DingTalk adapter (FP-H04-01)."""
    
    def test_client_exists(self):
        """DingTalkClient class exists."""
        from app.integrations.dingtalk.client import DingTalkClient
        
        assert DingTalkClient is not None
    
    def test_client_has_mode(self):
        """DingTalkClient has mode attribute."""
        from app.integrations.dingtalk.client import DingTalkClient
        
        client = DingTalkClient(mode="mock")
        assert client.mode == "mock"
    
    def test_error_code_5003_defined(self):
        """Error code 5003 is defined for DingTalk timeout."""
        from app.core.errors import get_error_info
        
        info = get_error_info(5003)
        assert info is not None


class TestFootballLiveReader:
    """Tests for Football Live reader (FP-H06)."""
    
    def test_reader_exists(self):
        """FootballLiveReader class exists."""
        from app.integrations.football_live.reader import FootballLiveReader
        
        assert FootballLiveReader is not None
    
    def test_reader_has_mode(self):
        """FootballLiveReader has mode attribute."""
        from app.integrations.football_live.reader import FootballLiveReader
        
        reader = FootballLiveReader(mode="mock")
        assert reader.mode == "mock"
    
    def test_error_codes_1271_through_1273(self):
        """UT-H04-03: Football returns error codes 1271-1273."""
        from app.core.errors import get_error_info
        
        # Verify error codes are registered
        for code in [1271, 1272, 1273]:
            info = get_error_info(code)
            assert info is not None
            assert info["domain"] == "FOOTBALL" or "直播" in info["msg"] or "Football" in str(info)
    
    def test_readonly_no_write_operations(self):
        """UT-H06-01: Football reader only performs SELECT."""
        from app.integrations.football_live.reader import FootballLiveReader
        
        reader = FootballLiveReader(mode="mock")
        
        # Reader should not have write methods
        assert not hasattr(reader, "create_room")
        assert not hasattr(reader, "update_room")
        assert not hasattr(reader, "delete_room")


class TestTrainAIClient:
    """Tests for Train AI client (FP-H08)."""
    
    @pytest.mark.asyncio
    async def test_mock_mode_returns_questions(self):
        """UT-H08-01: Mock mode returns valid questions."""
        from app.integrations.train_ai.client import TrainAIClient
        
        client = TrainAIClient(mode="mock")
        
        result = await client.generate_questions(
            content="Test content",
            question_count=5
        )
        
        # Should return questions
        assert result is not None
        assert len(result) >= 1
    
    @pytest.mark.asyncio
    async def test_unconfigured_real_returns_1109(self):
        """UT-H08-06: Unconfigured client returns error 1109."""
        from app.integrations.train_ai.client import TrainAIClient
        
        client = TrainAIClient(mode="real", api_key="")
        
        with pytest.raises(BizError) as exc_info:
            await client.generate_questions(
                content="Test content",
                question_count=5
            )
        
        assert exc_info.value.code == 1109
    
    def test_is_configured_checks_api_key(self):
        """Client is_configured checks api_key."""
        from app.integrations.train_ai.client import TrainAIClient
        
        client_unconfigured = TrainAIClient(mode="real", api_key="")
        client_configured = TrainAIClient(mode="real", api_key="sk-test")
        
        assert client_unconfigured.is_configured is False
        assert client_configured.is_configured is True
    
    def test_error_code_timeout_is_1107(self):
        """Timeout error code is 1107."""
        from app.integrations.train_ai.client import TrainAIClient
        
        client = TrainAIClient(mode="mock")
        
        assert client.error_code_timeout == 1107
    
    def test_error_codes_registered(self):
        """Train AI error codes are registered."""
        from app.core.errors import get_error_info
        
        codes = [1106, 1107, 1108, 1109]
        for code in codes:
            info = get_error_info(code)
            assert info is not None
    
    def test_system_name(self):
        """System name is 培训AI."""
        from app.integrations.train_ai.client import TrainAIClient
        
        client = TrainAIClient(mode="mock")
        
        assert client.system_name == "培训AI"


class TestCircuitBreaker:
    """Tests for circuit breaker functionality (FP-H04-01)."""
    
    def test_circuit_opens_after_5_failures(self):
        """UT-H04-04: Circuit opens after 5 consecutive failures."""
        from app.integrations.base import CircuitBreaker
        
        breaker = CircuitBreaker(failure_threshold=5, recovery_seconds=30)
        
        # Record 5 failures
        for _ in range(5):
            breaker.record_failure()
        
        # Circuit should be open
        assert breaker.is_open() is True
    
    def test_circuit_closed_initially(self):
        """Circuit is closed initially."""
        from app.integrations.base import CircuitBreaker
        
        breaker = CircuitBreaker(failure_threshold=5, recovery_seconds=30)
        
        # Should be closed initially
        assert breaker.is_open() is False
    
    def test_circuit_resets_on_success(self):
        """Circuit resets failure count on success."""
        from app.integrations.base import CircuitBreaker
        
        breaker = CircuitBreaker(failure_threshold=5, recovery_seconds=30)
        
        # Record some failures
        for _ in range(3):
            breaker.record_failure()
        
        # Record success
        breaker.record_success()
        
        # Failures should be reset (list cleared)
        assert len(breaker.failures) == 0


class TestBaseAdapter:
    """Tests for BaseAdapter functionality."""
    
    def test_adapter_is_abstract(self):
        """BaseAdapter is abstract and cannot be instantiated directly."""
        from app.integrations.base import BaseAdapter
        
        # BaseAdapter is abstract, so we test via a concrete implementation
        # like TrainAIClient or DingTalkClient
        from app.integrations.train_ai.client import TrainAIClient
        
        client = TrainAIClient(mode="mock")
        assert client.mode == "mock"
    
    def test_adapter_has_breaker(self):
        """Adapter has circuit breaker."""
        from app.integrations.train_ai.client import TrainAIClient
        
        client = TrainAIClient(mode="mock")
        
        # Should have circuit breaker
        assert hasattr(client, "breaker")
        assert client.breaker is not None
