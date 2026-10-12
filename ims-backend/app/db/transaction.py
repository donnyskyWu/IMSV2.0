# app/db/transaction.py - Transaction management (FP-C01-01)
"""
Transaction decorator for service layer methods.

Rules per FP-C01-01:
- Service methods use @transactional for transaction boundaries
- Nested calls reuse outer transaction
- Any exception -> full rollback
- Route layer must not call commit directly
"""

import functools
from typing import Any, Callable, ParamSpec, TypeVar

from sqlalchemy.orm import Session

from app.db.session import get_db_session

P = ParamSpec("P")
R = TypeVar("R")


def transactional(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to wrap a function in a database transaction.
    
    - Creates a new transaction if none exists
    - Reuses existing transaction if already in one (nested calls)
    - Commits on success, rolls back on exception
    
    Usage:
        @transactional
        def create_user(self, data: UserCreate) -> User:
            ...
    """
    
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        session: Session = get_db_session()
        
        # Check if we're already in a transaction
        in_transaction = session.in_transaction()
        
        try:
            result = func(*args, **kwargs)
            
            # Only commit if we started the transaction
            if not in_transaction:
                session.commit()
            
            return result
        except Exception:
            # Always rollback on exception
            session.rollback()
            raise
    
    return wrapper


class TransactionContext:
    """
    Context manager for explicit transaction control.
    
    Usage:
        with TransactionContext() as tx:
            # do stuff
            tx.commit()
    """
    
    def __init__(self) -> None:
        self._session: Session | None = None
        self._started_transaction = False
    
    def __enter__(self) -> "TransactionContext":
        self._session = get_db_session()
        self._started_transaction = not self._session.in_transaction()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._session is None:
            return
        
        if exc_type is not None:
            self._session.rollback()
        elif self._started_transaction:
            # Auto-rollback if not explicitly committed
            self._session.rollback()
    
    def commit(self) -> None:
        """Explicitly commit the transaction."""
        if self._session and self._started_transaction:
            self._session.commit()
    
    def rollback(self) -> None:
        """Explicitly rollback the transaction."""
        if self._session:
            self._session.rollback()
    
    def flush(self) -> None:
        """Flush pending changes without committing."""
        if self._session:
            self._session.flush()
