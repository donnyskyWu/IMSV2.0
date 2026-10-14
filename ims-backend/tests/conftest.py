# tests/conftest.py - Pytest fixtures for IMS v2
"""
Test fixtures and configuration.

Rules:
- Tests require MySQL 8 (via IMS_DB_URL env var)
- Tests require Redis (via IMS_REDIS_URL env var)
- Injectable clock for time-dependent tests (D4)
- All external integrations use Mock mode
"""

import contextlib
import os
from datetime import datetime
from typing import Generator

import pytest

# Set test environment BEFORE importing app modules
os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")
os.environ.setdefault("IMS_JWT_ACCESS_TOKEN_TTL", "7200")
os.environ.setdefault("IMS_JWT_REFRESH_TOKEN_TTL", "604800")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.clock import reset_clock, set_clock
from app.core.context import RequestContext, ctx
from app.db.base import Base


def _is_sqlite(url: str) -> bool:
    """True when tests fall back to an in-memory SQLite database."""
    return url.startswith("sqlite")


@pytest.fixture(scope="function")
def db_engine():
    """Create database engine for tests.

    CI sets MySQL. Several test modules overwrite IMS_DB_URL with
    sqlite:///:memory: at import time. In-memory SQLite needs one shared
    connection (StaticPool) and check_same_thread=False, because TestClient
    runs the app on another thread.
    """
    db_url = os.environ.get("IMS_DB_URL")
    redis_url = os.environ.get("IMS_REDIS_URL")
    if not db_url:
        pytest.exit("IMS_DB_URL environment variable is required", returncode=1)
    if not redis_url:
        pytest.exit("IMS_REDIS_URL environment variable is required", returncode=1)

    if _is_sqlite(db_url):
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
        )

    # Import all models to ensure they're registered with Base
    from app.domains.sys import models  # noqa: F401

    # Drop and recreate all tables for clean state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
    )

    session = testing_session_local()

    # Set up session in context
    from app.db.session import _db_session
    token = _db_session.set(session)

    try:
        yield session
    finally:
        _db_session.reset(token)
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def _isolate_clock_and_cache():
    """Drop fake time and cached permissions so one test cannot affect the next."""
    yield
    from app.core import cache as cache_mod
    from app.core.clock import reset_clock

    reset_clock()
    cache_mod._memory_cache.clear()
    client = cache_mod._redis_client
    if client is not None:
        with contextlib.suppress(Exception):
            client.flushdb()


@pytest.fixture
def test_context():
    """Set up test request context."""
    context = RequestContext(
        trace_id="test-trace-id",
        user_id=1,
        tenant_id=1,
        perm_codes={"ims:system:user:query", "ims:system:dept:query"},
        dept_ids=[1, 2],
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


@pytest.fixture
def admin_context():
    """Set up admin request context with all permissions."""
    context = RequestContext(
        trace_id="admin-trace-id",
        user_id=1,
        tenant_id=1,
        perm_codes={
            "ims:system:user:query",
            "ims:system:user:create",
            "ims:system:user:update",
            "ims:system:user:delete",
            "ims:system:dept:query",
            "ims:system:dept:create",
            "ims:system:dept:update",
            "ims:system:dept:delete",
            "ims:system:role:query",
            "ims:system:role:update",
        },
        data_scopes=[{"scope_type": "ALL", "role_id": 1}],
        dept_ids=[1],
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


@pytest.fixture
def fixed_time():
    """
    Fixture to set a fixed time for tests.

    Usage:
        def test_with_fixed_time(fixed_time):
            fixed_time(datetime(2026, 10, 12, 10, 0, 0))
            assert get_now() == datetime(2026, 10, 12, 10, 0, 0)
    """
    def _set_time(dt: datetime):
        set_clock(lambda: dt)

    yield _set_time

    # Reset clock after test
    reset_clock()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    """Create test client with database session."""
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(client, admin_context) -> TestClient:
    """Test client with authentication context set up."""
    return client


# Test data fixtures

@pytest.fixture
def sample_user(db_session, test_context) -> dict:
    """Create a sample user for testing."""
    from app.domains.sys.models import User

    user = User(
        id=1,
        tenant_id=1,
        username="testuser",
        nickname="Test User",
        status="ACTIVE",
        source="LOCAL",
    )
    db_session.add(user)
    db_session.flush()

    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
    }


@pytest.fixture
def sample_dept(db_session, test_context) -> dict:
    """Create a sample department for testing."""
    from app.domains.sys.models import Dept

    root_dept = Dept(
        id=1,
        tenant_id=1,
        parent_id=0,
        path="/1/",
        name="Root Department",
        status="ENABLED",
        source="LOCAL",
    )
    db_session.add(root_dept)

    child_dept = Dept(
        id=2,
        tenant_id=1,
        parent_id=1,
        path="/1/2/",
        name="Child Department",
        status="ENABLED",
        source="LOCAL",
    )
    db_session.add(child_dept)

    system_dept = Dept(
        id=3,
        tenant_id=1,
        parent_id=1,
        path="/1/3/",
        name="待分配",
        status="ENABLED",
        source="SYSTEM",
    )
    db_session.add(system_dept)

    db_session.flush()

    return {
        "root": {"id": 1, "name": "Root Department"},
        "child": {"id": 2, "name": "Child Department"},
        "system": {"id": 3, "name": "待分配"},
    }


@pytest.fixture
def sample_dict(db_session, test_context) -> dict:
    """Create sample dictionary data for testing."""
    from app.domains.sys.models import DictData, DictType

    dict_type = DictType(
        id=1,
        tenant_id=1,
        dict_type="dict_user_status",
        name="用户状态",
        status="ENABLED",
    )
    db_session.add(dict_type)

    statuses = [
        ("ACTIVE", "在职", "success"),
        ("FROZEN", "冻结", "warning"),
        ("RESIGNED", "离职", "danger"),
    ]

    for i, (value, label, color) in enumerate(statuses):
        data = DictData(
            id=100 + i,
            tenant_id=1,
            dict_type="dict_user_status",
            dict_value=value,
            dict_label=label,
            color_type=color,
            sort=i,
            status="ENABLED",
            is_builtin=True,
        )
        db_session.add(data)

    db_session.flush()

    return {
        "type": "dict_user_status",
        "values": ["ACTIVE", "FROZEN", "RESIGNED"],
    }
