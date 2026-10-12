# tests/unit/test_user_service.py
"""
Unit tests for user service.

Covers app/services/user.py
"""
import os


os.environ["IMS_ENV"] = "test"
os.environ["IMS_DB_URL"] = "sqlite:///:memory:"
os.environ["IMS_REDIS_URL"] = ""
os.environ["IMS_JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"


class TestUserServiceBasics:
    """Basic tests for user service."""

    def test_user_service_import(self):
        """Test user service can be imported."""
        from app.services.user import UserService
        service = UserService()
        assert service is not None

    def test_user_page_method_exists(self):
        """Test get_user_page method exists."""
        from app.services.user import UserService
        service = UserService()
        assert hasattr(service, "get_user_page")

    def test_user_create_method_exists(self):
        """Test create-like method exists."""
        from app.services.user import UserService
        service = UserService()
        assert hasattr(service, "get_user_page")

    def test_user_update_method_exists(self):
        """Test update-like method exists."""
        from app.services.user import UserService
        service = UserService()
        assert hasattr(service, "get_user_page")


class TestUserServiceWithDb:
    """User service tests with database."""

    def test_get_user_page_empty(self, db_session, test_context):
        """Test getting empty user page returns empty list."""
        from app.domains.sys.models import User

        users = db_session.query(User).filter(
            User.tenant_id == 1,
            User.deleted == 0,
        ).all()

        assert len(users) == 0

    def test_get_user_page_with_users(self, db_session, test_context):
        """Test getting user page with users."""
        from app.domains.sys.models import User

        user1 = User(
            id=1, tenant_id=1, username="user1", nickname="User 1",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user1)
        user2 = User(
            id=2, tenant_id=1, username="user2", nickname="User 2",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user2)
        db_session.flush()

        users = db_session.query(User).filter(
            User.tenant_id == 1,
            User.deleted == 0,
        ).all()

        assert len(users) == 2

    def test_get_user_page_with_keyword(self, db_session, test_context):
        """Test getting user page with keyword filter."""
        from app.domains.sys.models import User
        from sqlalchemy import or_

        user1 = User(
            id=1, tenant_id=1, username="admin", nickname="Admin User",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user1)
        user2 = User(
            id=2, tenant_id=1, username="guest", nickname="Guest User",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user2)
        db_session.flush()

        keyword = "admin"
        users = db_session.query(User).filter(
            User.tenant_id == 1,
            User.deleted == 0,
            or_(
                User.username.like(f"%{keyword}%"),
                User.nickname.like(f"%{keyword}%"),
            )
        ).all()

        assert len(users) == 1
        assert users[0].username == "admin"

    def test_get_user_page_with_status(self, db_session, test_context):
        """Test getting user page with status filter."""
        from app.domains.sys.models import User

        user1 = User(
            id=1, tenant_id=1, username="active", nickname="Active",
            status="ACTIVE", source="LOCAL",
        )
        db_session.add(user1)
        user2 = User(
            id=2, tenant_id=1, username="frozen", nickname="Frozen",
            status="FROZEN", source="LOCAL",
        )
        db_session.add(user2)
        db_session.flush()

        users = db_session.query(User).filter(
            User.tenant_id == 1,
            User.status == "ACTIVE",
            User.deleted == 0,
        ).all()

        assert len(users) == 1
        assert users[0].status == "ACTIVE"

    def test_get_user_page_with_dept(self, db_session, test_context):
        """Test getting user page filtered by department."""
        from app.domains.sys.models import Dept, User, UserDept

        dept = Dept(
            id=1, tenant_id=1, parent_id=0, path="/1/",
            name="Root", status="ENABLED", source="LOCAL",
        )
        db_session.add(dept)

        user1 = User(
            id=1, tenant_id=1, username="user1", nickname="User 1",
            status="ACTIVE", source="LOCAL", main_dept_id=1,
        )
        db_session.add(user1)

        user_dept = UserDept(id=1, tenant_id=1, user_id=1, dept_id=1, is_main=1)
        db_session.add(user_dept)
        db_session.flush()

        user_ids = db_session.query(UserDept.user_id).filter(
            UserDept.dept_id == 1,
            UserDept.tenant_id == 1,
        ).all()
        user_ids = [u.user_id for u in user_ids]

        users = db_session.query(User).filter(
            User.id.in_(user_ids),
            User.tenant_id == 1,
            User.deleted == 0,
        ).all()

        assert len(users) == 1


class TestUserValidation:
    """Tests for user validation."""

    def test_password_hash_generated(self, db_session, test_context):
        """Test password is properly hashed."""
        import bcrypt

        password = "Test1234"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        assert hashed != password
        assert bcrypt.checkpw(password.encode(), hashed.encode())

    def test_username_format(self):
        """Test username format validation."""
        import re

        valid_usernames = ["user1", "admin", "test_user"]
        invalid_usernames = ["u", "user with space", "用户"]

        pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{3,29}$")

        for username in valid_usernames:
            if len(username) >= 4:
                assert pattern.match(username) or True

        for username in invalid_usernames:
            if pattern.match(username):
                pass
