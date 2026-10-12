# app/integrations/base.py - Adapter base (FP-H04-01)
"""
Base adapter class with timeout, retry, circuit breaker.

Per FP-H04-01:
- Unified timeout (default 10s, configurable)
- Retry (idempotent read ops only, max 2 times)
- Circuit breaker (5 failures in 1 min -> breaker for 30s)
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Generic, Optional, TypeVar

from app.core.clock import get_now

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        failure_window_seconds: int = 60,
        recovery_seconds: int = 30,
    ):
        self.failure_threshold = failure_threshold
        self.failure_window = timedelta(seconds=failure_window_seconds)
        self.recovery_timeout = timedelta(seconds=recovery_seconds)
        self.failures: list[datetime] = []
        self.open_until: Optional[datetime] = None

    def record_failure(self) -> None:
        """Record a failure."""
        now = get_now()
        self.failures.append(now)

        # Clean old failures
        cutoff = now - self.failure_window
        self.failures = [f for f in self.failures if f > cutoff]

        # Check if threshold exceeded
        if len(self.failures) >= self.failure_threshold:
            self.open_until = now + self.recovery_timeout
            logger.warning(f"Circuit breaker opened until {self.open_until}")

    def record_success(self) -> None:
        """Record a success, reset failures."""
        self.failures = []
        self.open_until = None

    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.open_until is None:
            return False

        if get_now() > self.open_until:
            self.open_until = None
            return False

        return True


class BaseAdapter(ABC, Generic[T]):
    """
    Base adapter for external systems.

    Subclasses implement:
    - _call_real(): Actual API call
    - _call_mock(): Mock response
    """

    def __init__(
        self,
        mode: str = "mock",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
    ):
        self.mode = mode
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.breaker = CircuitBreaker()

    @property
    @abstractmethod
    def system_name(self) -> str:
        """System name for logging."""
        pass

    @property
    @abstractmethod
    def error_code_timeout(self) -> int:
        """Error code for timeout (e.g., 5003 for DingTalk)."""
        pass

    @abstractmethod
    async def _call_real(self, *args, **kwargs) -> T:
        """Make real API call."""
        pass

    @abstractmethod
    async def _call_mock(self, *args, **kwargs) -> T:
        """Return mock response."""
        pass

    async def call(self, *args, idempotent: bool = False, **kwargs) -> T:
        """
        Execute adapter call with retry and circuit breaker.

        Args:
            idempotent: If True, allow retries on failure

        Returns:
            Response from adapter

        Raises:
            BizError with appropriate error code on failure
        """
        from app.core.errors import BizError

        # Check circuit breaker
        if self.breaker.is_open():
            logger.warning(f"{self.system_name} circuit breaker is open")
            raise BizError(self.error_code_timeout, msg=f"{self.system_name}服务暂时不可用")

        # Use mock in mock mode
        if self.mode == "mock":
            return await self._call_mock(*args, **kwargs)

        # Real call with retry
        attempts = 1 if not idempotent else (self.max_retries + 1)

        for attempt in range(attempts):
            try:
                result = await self._call_real(*args, **kwargs)
                self.breaker.record_success()
                return result
            except Exception as e:
                self.breaker.record_failure()
                logger.warning(
                    f"{self.system_name} call failed (attempt {attempt + 1}): {e}"
                )

        # All retries failed
        raise BizError(self.error_code_timeout, msg=f"{self.system_name}调用失败")
