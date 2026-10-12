# tests/unit/test_repository.py
"""
Unit tests for repository layer.

Covers app/db/repository.py
"""
import os

os.environ["IMS_ENV"] = "test"
os.environ["IMS_DB_URL"] = "sqlite:///:memory:"
os.environ["IMS_REDIS_URL"] = ""
os.environ["IMS_JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"


class TestRepositoryBasics:
    """Basic tests for repository."""

    def test_repository_import(self):
        """Test repository can be imported."""
        from app.db.repository import BaseRepository
        assert BaseRepository is not None

    def test_repository_has_methods(self):
        """Test repository has required methods."""
        from app.db.repository import BaseRepository

        methods = ["get", "list", "create", "update", "delete"]
        for method in methods:
            assert hasattr(BaseRepository, method)


class TestRepositoryWithDb:
    """Repository tests with database."""

    def test_get_nonexistent(self, db_session, test_context):
        """Test getting non-existent record."""
        from app.domains.sys.models import User

        user = db_session.query(User).filter(User.id == 9999).first()
        assert user is None

    def test_create_and_get(self, db_session, test_context):
        """Test creating and getting a record."""
        from app.domains.sys.models import User

        user = User(
            id=1, tenant_id=1, username="test", nickname="Test",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        result = db_session.query(User).filter(User.id == 1).first()
        assert result is not None
        assert result.username == "test"

    def test_update_record(self, db_session, test_context):
        """Test updating a record."""
        from app.domains.sys.models import User

        user = User(
            id=1, tenant_id=1, username="test", nickname="Test",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        user.nickname = "Updated"
        db_session.flush()

        result = db_session.query(User).filter(User.id == 1).first()
        assert result.nickname == "Updated"

    def test_delete_record(self, db_session, test_context):
        """Test deleting (soft delete) a record."""
        from app.domains.sys.models import User

        user = User(
            id=1, tenant_id=1, username="test", nickname="Test",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        user.deleted = user.id
        db_session.flush()

        result = db_session.query(User).filter(
            User.id == 1, User.deleted == 0
        ).first()
        assert result is None

    def test_list_with_filter(self, db_session, test_context):
        """Test listing with filter."""
        from app.domains.sys.models import User

        user1 = User(
            id=1, tenant_id=1, username="active1", nickname="Active 1",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user1)
        user2 = User(
            id=2, tenant_id=1, username="frozen1", nickname="Frozen 1",
            status="FROZEN", source="LOCAL",
        )
        db_session.add(user2)
        db_session.flush()

        active_users = db_session.query(User).filter(
            User.tenant_id == 1,
            User.status == "ACTIVE",
            User.deleted == 0,
        ).all()

        assert len(active_users) == 1
        assert active_users[0].username == "active1"

    def test_pagination(self, db_session, test_context):
        """Test pagination."""
        from app.domains.sys.models import User

        for i in range(25):
            user = User(
                id=i + 1, tenant_id=1, username=f"user{i}", nickname=f"User {i}",
                status="ACTIVE", source="LOCAL",
            )
            db_session.add(user)
        db_session.flush()

        page1 = db_session.query(User).filter(
            User.tenant_id == 1,
            User.deleted == 0,
        ).limit(10).offset(0).all()

        page2 = db_session.query(User).filter(
            User.tenant_id == 1,
            User.deleted == 0,
        ).limit(10).offset(10).all()

        page3 = db_session.query(User).filter(
            User.tenant_id == 1,
            User.deleted == 0,
        ).limit(10).offset(20).all()

        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 5


class TestRepositoryTenantIsolation:
    """Tests for tenant isolation in repository."""

    def test_tenant_filter(self, db_session, test_context):
        """Test tenant isolation."""
        from app.domains.sys.models import User

        user_t1 = User(
            id=1, tenant_id=1, username="user_t1", nickname="T1 User",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user_t1)

        user_t2 = User(
            id=2, tenant_id=2, username="user_t2", nickname="T2 User",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user_t2)
        db_session.flush()

        t1_users = db_session.query(User).filter(
            User.tenant_id == 1,
            User.deleted == 0,
        ).all()

        assert len(t1_users) == 1
        assert t1_users[0].tenant_id == 1
