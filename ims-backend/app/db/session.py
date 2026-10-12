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

from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db import ids as _ids  # noqa: F401  # registers the SQLite primary-key listener

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


@contextmanager
def use_db_session() -> Generator[Session, None, None]:
    """Bind one session into the request context.

    已有会话（单测夹具、嵌套调用）只借用，不提交也不关闭。
    否则新建会话：成功提交、异常回滚、无论成败都关闭。
    未真正开始事务时不提交，避免空提交去连已经宕掉的库。
    """
    existing = _db_session.get()
    if existing is not None:
        yield existing
        return

    if SessionLocal is None:
        raise RuntimeError("Database not initialized")

    session = SessionLocal()
    token = _db_session.set(session)
    try:
        yield session
        # 只在有事务或待写入对象时提交。空会话 commit() 会 autobegin 去连库，
        # 库宕掉时会把 /health 的 503 变成 500。
        pending = bool(session.new or session.dirty or session.deleted)
        if session.in_transaction() or pending:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        _db_session.reset(token)
        session.close()


async def get_db() -> AsyncGenerator[Optional[Session], None]:
    """FastAPI 依赖：在请求任务内绑定会话。

    必须是异步生成器。同步依赖跑在线程池里，写进 ContextVar 的会话
    路由和后续依赖都看不见。
    库还没初始化时交出 None，让 /health 仍能报告 db DOWN。
    """
    if SessionLocal is None and _db_session.get() is None:
        yield None
        return

    with use_db_session() as session:
        yield session


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
                # SQLAlchemy 2 拒绝裸字符串，必须 text()，否则 /health 的 db 永远是 DOWN。
                conn.execute(text("SELECT 1"))
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
                conn.execute(text("SELECT 1"))
            return True, "UP"
        except Exception:
            return False, "DOWN"
