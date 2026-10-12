# app/core/idempotency.py - X-Client-Token idempotency (FP-C04-03)
"""Run a function once per client token and replay the first result."""

import json
import threading
from typing import Any, Callable, Optional

from app.core.context import ctx
from app.core.errors import BizError
from app.db.ids import assign_pk


class IdempotencyStore:
    """In-process lock plus one persisted row per token."""

    def __init__(self, session: Optional[Any] = None) -> None:
        self.session = session
        self._lock = threading.Lock()
        self._done: dict[str, tuple[str, Any]] = {}
        self._waiters: dict[str, threading.Event] = {}
        self.writes = 0

    def execute(self, token: Optional[str], fn: Callable[[], Any]) -> Any:
        if not token:
            raise BizError(1001)
        with self._lock:
            if token in self._done:
                return self._replay(token)
            waiter = self._waiters.get(token)
            if waiter is None:
                waiter = threading.Event()
                self._waiters[token] = waiter
                owner = True
            else:
                owner = False
        if not owner:
            waiter.wait(5)
            with self._lock:
                return self._replay(token)
        try:
            try:
                value = fn()
            except BizError as err:
                with self._lock:
                    self._done[token] = ("err", err.code)
                    self.writes += 1
                self._persist(token, "ERROR", None, err.code)
                raise
            with self._lock:
                self._done[token] = ("ok", value)
                self.writes += 1
            self._persist(token, "DONE", value, None)
            return value
        finally:
            waiter.set()
            with self._lock:
                self._waiters.pop(token, None)

    def _replay(self, token: str) -> Any:
        kind, payload = self._done[token]
        if kind == "err":
            raise BizError(payload)
        return payload

    def _persist(
        self,
        token: str,
        status: str,
        value: Any,
        error_code: Optional[int],
    ) -> None:
        if self.session is None:
            return
        from app.domains.sys.models import IdempotencyRecord

        row = IdempotencyRecord(
            tenant_id=ctx.tenant_id or 1,
            token=token,
            status=status,
            result_json=json.dumps(value) if value is not None else None,
            error_code=error_code,
        )
        assign_pk(self.session, row)
        self.session.add(row)
        self.session.flush()
