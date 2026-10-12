# app/db/session.py - Database session management (FP-C01-01)
"""
Database session and engine management.

Rules per FP-C01-01:
- One IMS main database session per HTTP request
- Service methods use @transactional for transaction boundaries
- Nested calls reuse outer transaction
- Any exception -> full rollback
- Route layer must not call commit directly (static check)
- Football read-only session is independent (FP-H06-01)
"""

from contextvars import ContextVar
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Main IMS database engine
engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None

# Football read-only engine (FP-H06-01)
football_engine: Optional[Engine] = None
FootballSession: Optional[sessionmaker] = None

# Context variable for request-scoped session
_db_session: ContextVar[Optional[Session]] = ContextVar("db_session", default=None)


def init_db() -> None:
    """Initialize database engines and session factories."""
    global engine, SessionLocal, football_engine, FootballSession

    # Main IMS database
    if settings.db.url:
        engine = create_engine(
            settings.db.url,
            pool_size=settings.db.pool_size,
            pool_recycle=settings.db.pool_recycle,
            echo=settings.db.echo,
        )
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )

    # Football read-only database (if configured)
    if settings.football_live.enabled and settings.football_live.url:
        football_engine = create_engine(
            settings.football_live.url,
            pool_size=5,
            pool_recycle=settings.db.pool_recycle,
            echo=settings.db.echo,
        )
        FootballSession = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=football_engine,
        )

        # Add read-only interceptor for Football connection
        @event.listens_for(football_engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            """Ensure only SELECT statements on Football connection."""
            stmt_upper = statement.strip().upper()
            if not stmt_upper.startswith("SELECT") and not stmt_upper.startswith("SHOW"):
                raise RuntimeError(
                    "Football connection is read-only. "
                    f"Attempted to execute: {statement[:100]}"
                )


def get_db_session() -> Session:
    """
    Get the current request-scoped database session.

    This should be used within request context where a session
    has already been created.
    """
    session = _db_session.get()
    if session is None:
        raise RuntimeError("No database session in context")
    return session


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes to get database session.

    Creates a new session for each request and handles cleanup.
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")

    session = SessionLocal()
    token = _db_session.set(session)
    try:
        yield session
    finally:
        _db_session.reset(token)
        session.close()


def get_football_session() -> Generator[Session, None, None]:
    """
    Get a Football read-only database session.

    This is a separate session that does not participate in
    IMS transactions.
    """
    if FootballSession is None:
        raise RuntimeError("Football database not configured or disabled")

    session = FootballSession()
    try:
        yield session
    finally:
        session.close()


class DatabaseHealth:
    """Database health check utilities."""

    @staticmethod
    def check_ims() -> bool:
        """Check IMS database connectivity."""
        if engine is None:
            return False
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    @staticmethod
    def check_football() -> tuple[bool, str]:
        """
        Check Football database connectivity.

        Returns:
            (is_up, status): status is UP/DOWN/DISABLED
        """
        if not settings.football_live.enabled:
            return True, "DISABLED"
        if football_engine is None:
            return False, "DOWN"
        try:
            with football_engine.connect() as conn:
                conn.execute("SELECT 1")
            return True, "UP"
        except Exception:
            return False, "DOWN"
