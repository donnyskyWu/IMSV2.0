# tests/unit/test_db_session.py
"""
Unit tests for database session management.

Covers app/db/session.py
"""
import os

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")

import pytest


class TestDatabaseSessionImports:
    """Tests for database session imports."""

    def test_init_db_import(self):
        """Test init_db can be imported."""
        from app.db.session import init_db
        assert callable(init_db)

    def test_get_db_session_import(self):
        """Test get_db_session can be imported."""
        from app.db.session import get_db_session
        assert callable(get_db_session)

    def test_get_db_import(self):
        """Test get_db dependency can be imported."""
        from app.db.session import get_db
        assert callable(get_db)

    def test_database_health_import(self):
        """Test DatabaseHealth can be imported."""
        from app.db.session import DatabaseHealth
        assert DatabaseHealth is not None


class TestDatabaseHealth:
    """Tests for database health checks."""

    def test_check_ims_method_exists(self):
        """Test check_ims method exists."""
        from app.db.session import DatabaseHealth
        assert hasattr(DatabaseHealth, "check_ims")

    def test_check_football_method_exists(self):
        """Test check_football method exists."""
        from app.db.session import DatabaseHealth
        assert hasattr(DatabaseHealth, "check_football")

    def test_check_ims_returns_bool(self):
        """Test check_ims returns boolean."""
        from app.db.session import DatabaseHealth, init_db
        init_db()
        result = DatabaseHealth.check_ims()
        # 裸字符串 SELECT 在 SQLAlchemy 2 会抛错并被吞掉，结果变成 False。
        assert result is True

    def test_check_football_returns_tuple(self):
        """Test check_football returns (bool, str) tuple."""
        from app.db.session import DatabaseHealth, init_db
        init_db()
        result = DatabaseHealth.check_football()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_check_football_status_values(self):
        """Test check_football status is UP, DOWN, or DISABLED."""
        from app.db.session import DatabaseHealth, init_db
        init_db()
        is_up, status = DatabaseHealth.check_football()
        assert status in ("UP", "DOWN", "DISABLED")


class TestGetDbSession:
    """Tests for get_db_session function."""

    def test_get_db_session_no_context_raises(self):
        """Test get_db_session raises when no session in context."""
        from app.db.session import _db_session, get_db_session

        # Reset context
        _db_session.set(None)

        with pytest.raises(RuntimeError, match="No database session"):
            get_db_session()


class TestGetDb:
    """Tests for get_db dependency."""

    async def test_get_db_generator(self):
        """get_db 是异步生成器，这样 ContextVar 才能留在请求任务里。"""
        from app.db.session import get_db, init_db

        init_db()
        gen = get_db()
        assert hasattr(gen, "__anext__")
        await gen.aclose()

    async def test_get_db_yields_session(self):
        """Test get_db yields a Session object."""
        from sqlalchemy.orm import Session

        from app.db.session import get_db, init_db

        init_db()
        gen = get_db()
        session = await anext(gen)
        assert isinstance(session, Session)
        await gen.aclose()

    async def test_get_db_session_available_during_request(self):
        """Test get_db_session works during request context."""
        from sqlalchemy.orm import Session

        from app.db.session import get_db, get_db_session, init_db

        init_db()
        gen = get_db()
        request_session = await anext(gen)

        # Now get_db_session should work
        ctx_session = get_db_session()
        assert ctx_session is request_session
        assert isinstance(ctx_session, Session)
        await gen.aclose()


class TestInitDb:
    """Tests for init_db function."""

    def test_init_db_creates_engine(self):
        """Test init_db creates database engine."""
        from app.db.session import init_db

        init_db()
        from app.db.session import engine as updated_engine
        assert updated_engine is not None

    def test_init_db_creates_session_local(self):
        """Test init_db creates SessionLocal factory."""
        from app.db.session import init_db

        init_db()
        from app.db.session import SessionLocal
        assert SessionLocal is not None


class TestUseDbSession:
    """请求会话的提交、回滚，以及借用已有会话。"""

    def test_borrowed_session_is_not_closed(self, db_session):
        """夹具已经绑过会话时，请求边界不能把它关掉。"""
        from app.db.session import use_db_session
        from app.domains.sys.models import Tenant

        with use_db_session() as session:
            assert session is db_session
        assert db_session.query(Tenant).count() >= 0

    def test_commit_persists_and_rollback_discards(self, db_engine):
        """新建会话成功则提交，异常则回滚。"""
        from sqlalchemy.orm import sessionmaker

        import app.db.session as sess
        from app.domains.sys.models import Tenant

        token = sess._db_session.set(None)
        previous_local = sess.SessionLocal
        previous_engine = sess.engine
        sess.engine = db_engine
        sess.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        try:
            with sess.use_db_session() as session:
                session.add(Tenant(tenant_id=1, name="提交探针", status="ENABLED"))

            with sess.use_db_session() as session:
                saved = session.query(Tenant).filter(Tenant.name == "提交探针").one()
                assert saved.id is not None
                session.delete(saved)

            with pytest.raises(RuntimeError, match="boom"):
                with sess.use_db_session() as session:
                    session.add(Tenant(tenant_id=1, name="回滚探针", status="ENABLED"))
                    session.flush()
                    raise RuntimeError("boom")

            with sess.use_db_session() as session:
                assert session.query(Tenant).filter(Tenant.name == "回滚探针").first() is None
                assert session.query(Tenant).filter(Tenant.name == "提交探针").first() is None
        finally:
            sess.SessionLocal = previous_local
            sess.engine = previous_engine
            sess._db_session.reset(token)
