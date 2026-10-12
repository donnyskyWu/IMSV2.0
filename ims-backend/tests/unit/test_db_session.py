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

    def test_idle_session_skips_commit(self, db_engine):
        """没读也没写时不提交，避免空提交去连已经宕掉的库。"""
        from sqlalchemy.orm import Session, sessionmaker

        import app.db.session as sess

        commits: list[int] = []

        class TrackingSession(Session):
            def commit(self):  # type: ignore[override]
                commits.append(1)
                return super().commit()

        token = sess._db_session.set(None)
        previous_local = sess.SessionLocal
        previous_engine = sess.engine
        sess.engine = db_engine
        sess.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=db_engine, class_=TrackingSession,
        )
        try:
            with sess.use_db_session():
                pass
            assert commits == []
        finally:
            sess.SessionLocal = previous_local
            sess.engine = previous_engine
            sess._db_session.reset(token)

    def test_pending_commits_when_transaction_flag_is_false(self, db_engine):
        """待写入对象在事务标记为假时仍然提交。"""
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
                session.add(Tenant(tenant_id=1, name="待提交探针", status="ENABLED"))
                session.in_transaction = lambda: False  # type: ignore[method-assign]

            with sess.use_db_session() as session:
                saved = session.query(Tenant).filter(Tenant.name == "待提交探针").one()
                assert saved.status == "ENABLED"
                session.delete(saved)
        finally:
            sess.SessionLocal = previous_local
            sess.engine = previous_engine
            sess._db_session.reset(token)

    def test_new_session_requires_factory(self):
        """没有工厂、也没有可借用的会话时，直接失败。"""
        import app.db.session as sess

        token = sess._db_session.set(None)
        previous = sess.SessionLocal
        sess.SessionLocal = None
        try:
            with pytest.raises(RuntimeError, match="Database not initialized"):
                with sess.use_db_session():
                    pass
        finally:
            sess.SessionLocal = previous
            sess._db_session.reset(token)


class TestSessionP0Branches:
    """补 FP-C01-01 里原先没走到的分支，供 P0 分支门禁使用。

    足球只读拦截、未初始化、健康检查成功/失败都要有明确结果断言。
    SQLAlchemy 2 拒绝裸字符串，check_* 里的 ``return True`` 用接受探测语句的连接替身走到。
    """

    def test_init_skips_engines_and_reports_disabled(self, monkeypatch):
        """库地址为空且足球未启用：不建引擎，健康检查分别是 False 和 DISABLED。"""
        import app.db.session as session_mod

        self._snapshot(monkeypatch, session_mod)
        monkeypatch.setattr(session_mod.settings.db, "url", "")
        monkeypatch.setattr(session_mod.settings.football_live, "url", "")
        monkeypatch.setattr(session_mod.settings.football_live, "enabled", False)
        monkeypatch.setattr(session_mod, "engine", None)
        monkeypatch.setattr(session_mod, "SessionLocal", None)
        monkeypatch.setattr(session_mod, "football_engine", None)

        session_mod.init_db()

        assert session_mod.engine is None
        assert session_mod.SessionLocal is None
        assert session_mod.football_engine is None
        assert session_mod.DatabaseHealth.check_ims() is False
        assert session_mod.DatabaseHealth.check_football() == (True, "DISABLED")

    def test_football_enabled_without_engine_is_down(self, monkeypatch):
        """足球开关开着但引擎没建出来，探活是 DOWN，而不是 DISABLED。"""
        import app.db.session as session_mod

        self._snapshot(monkeypatch, session_mod)
        monkeypatch.setattr(session_mod.settings.football_live, "enabled", True)
        monkeypatch.setattr(session_mod, "football_engine", None)

        assert session_mod.DatabaseHealth.check_football() == (False, "DOWN")

    async def test_get_db_yields_none_when_uninitialized(self, monkeypatch):
        """库还没初始化且没有借用会话时，依赖交出 None，让 /health 仍能报 DOWN。"""
        import app.db.session as session_mod

        self._snapshot(monkeypatch, session_mod)
        monkeypatch.setattr(session_mod, "SessionLocal", None)
        session_mod._db_session.set(None)

        gen = session_mod.get_db()
        assert await anext(gen) is None
        await gen.aclose()

    async def test_get_db_borrows_existing_without_factory(self, monkeypatch, db_session):
        """已有会话时，即使工厂是空的也只借用，不新建。"""
        import app.db.session as session_mod

        self._snapshot(monkeypatch, session_mod)
        monkeypatch.setattr(session_mod, "SessionLocal", None)
        session_mod._db_session.set(db_session)

        gen = session_mod.get_db()
        borrowed = await anext(gen)
        assert borrowed is db_session
        await gen.aclose()
        assert db_session.is_active

    def test_football_session_requires_factory(self, monkeypatch):
        """没配置足球库时，不能借出会话。"""
        import app.db.session as session_mod

        self._snapshot(monkeypatch, session_mod)
        monkeypatch.setattr(session_mod, "FootballSession", None)

        with pytest.raises(RuntimeError, match="Football database not configured"):
            next(session_mod.get_football_session())

    def test_football_readonly_interceptor_and_session(self, monkeypatch):
        """SELECT / SHOW 放行，其他语句在执行前被只读拦截拒绝。"""
        from sqlalchemy.exc import OperationalError

        import app.db.session as session_mod

        self._snapshot(monkeypatch, session_mod)
        monkeypatch.setattr(session_mod.settings.football_live, "enabled", True)
        monkeypatch.setattr(session_mod.settings.football_live, "url", "sqlite://")

        before_engine = session_mod.football_engine
        session_mod.init_db()
        created = session_mod.football_engine
        assert created is not None
        assert created is not before_engine
        try:
            conn = created.connect()
            try:
                conn.exec_driver_sql("  select 1")
                # SHOW 不是 SELECT，拦截器仍应放行；sqlite 自己不认识这条语法。
                with pytest.raises(OperationalError):
                    conn.exec_driver_sql("SHOW TABLES")
                with pytest.raises(RuntimeError, match="read-only"):
                    conn.exec_driver_sql("DELETE FROM live_room")
            finally:
                conn.close()

            assert session_mod.DatabaseHealth.check_football() == (True, "UP")
            assert session_mod.DatabaseHealth.check_ims() is True

            gen = session_mod.get_football_session()
            football_session = next(gen)
            try:
                assert football_session.bind is created
            finally:
                gen.close()
        finally:
            created.dispose()

    def test_health_probe_success_and_query_failure(self, monkeypatch):
        """探测语句成功则为 UP / True，抛错则为 DOWN / False。"""
        import app.db.session as session_mod

        class _Conn:
            def __init__(self, fail: bool) -> None:
                self.fail = fail
                self.statements: list[object] = []

            def __enter__(self) -> "_Conn":
                return self

            def __exit__(self, *_args: object) -> bool:
                return False

            def execute(self, statement: object) -> int:
                self.statements.append(statement)
                if self.fail:
                    raise RuntimeError("db down")
                return 1

        class _Engine:
            def __init__(self, fail: bool) -> None:
                self.conn = _Conn(fail)

            def connect(self) -> _Conn:
                return self.conn

        self._snapshot(monkeypatch, session_mod)
        monkeypatch.setattr(session_mod.settings.football_live, "enabled", True)

        ims_up = _Engine(False)
        monkeypatch.setattr(session_mod, "engine", ims_up)
        assert session_mod.DatabaseHealth.check_ims() is True
        assert "SELECT 1" in str(ims_up.conn.statements[0])

        ims_down = _Engine(True)
        monkeypatch.setattr(session_mod, "engine", ims_down)
        assert session_mod.DatabaseHealth.check_ims() is False
        assert "SELECT 1" in str(ims_down.conn.statements[0])

        football_up = _Engine(False)
        monkeypatch.setattr(session_mod, "football_engine", football_up)
        assert session_mod.DatabaseHealth.check_football() == (True, "UP")
        assert "SELECT 1" in str(football_up.conn.statements[0])

        football_down = _Engine(True)
        monkeypatch.setattr(session_mod, "football_engine", football_down)
        assert session_mod.DatabaseHealth.check_football() == (False, "DOWN")

    @staticmethod
    def _snapshot(monkeypatch: pytest.MonkeyPatch, session_mod: object) -> None:
        """记住 init_db 会改写的全局量，用例结束时还原，避免污染其他用例。"""
        for name in ("engine", "SessionLocal", "football_engine", "FootballSession"):
            monkeypatch.setattr(session_mod, name, getattr(session_mod, name))
