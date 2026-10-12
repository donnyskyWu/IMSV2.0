# tests/integration/test_role_user_service_coverage.py
"""
Integration tests for RoleService and UserService coverage.

These tests exercise service methods to increase coverage on:
- app/services/role.py
- app/services/user.py
"""
import os

# Only set defaults if not already set (CI provides MySQL/Redis)
os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")

import asyncio

import pytest

from app.core.errors import BizError


def run_async(coro):
    """Run async function synchronously."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@pytest.fixture
def role_service():
    """Create RoleService instance."""
    from app.services.role import RoleService
    return RoleService()


@pytest.fixture
def user_service():
    """Create UserService instance."""
    from app.services.user import UserService
    return UserService()


@pytest.fixture
def role_user_data(db_session, test_context):
    """Create roles, users, and menus for testing."""
    from app.domains.sys.models import Dept, Menu, Role, RoleMenu, User, UserDept, UserRole

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

    role_admin = Role(
        id=1,
        tenant_id=1,
        role_key="R_ADMIN",
        name="Administrator",
        status="ENABLED",
        source="MANUAL",
        data_scope="ALL",
        sort=0,
    )
    db_session.add(role_admin)

    role_user = Role(
        id=2,
        tenant_id=1,
        role_key="R_USER",
        name="Standard User",
        status="ENABLED",
        source="MANUAL",
        data_scope="SELF",
        sort=1,
    )
    db_session.add(role_user)

    role_disabled = Role(
        id=3,
        tenant_id=1,
        role_key="R_DISABLED",
        name="Disabled Role",
        status="DISABLED",
        source="MANUAL",
        sort=2,
    )
    db_session.add(role_disabled)

    menu1 = Menu(
        id=1,
        tenant_id=1,
        parent_id=0,
        name="System",
        type="DIR",
        perm_code="ims:system",
        status="ENABLED",
    )
    db_session.add(menu1)

    menu2 = Menu(
        id=2,
        tenant_id=1,
        parent_id=1,
        name="User Management",
        type="MENU",
        perm_code="ims:system:user",
        status="ENABLED",
    )
    db_session.add(menu2)

    role_menu1 = RoleMenu(
        id=1,
        tenant_id=1,
        role_id=1,
        menu_id=1,
    )
    db_session.add(role_menu1)

    role_menu2 = RoleMenu(
        id=2,
        tenant_id=1,
        role_id=1,
        menu_id=2,
    )
    db_session.add(role_menu2)

    user1 = User(
        id=1,
        tenant_id=1,
        username="testuser1",
        nickname="Test User 1",
        status="ACTIVE",
        source="LOCAL",
        main_dept_id=1,
    )
    db_session.add(user1)

    user2 = User(
        id=2,
        tenant_id=1,
        username="testuser2",
        nickname="Test User 2",
        status="ACTIVE",
        source="LOCAL",
        main_dept_id=2,
    )
    db_session.add(user2)

    user_neverlogin = User(
        id=3,
        tenant_id=1,
        username="neverlogin",
        nickname="Never Login User",
        status="ACTIVE",
        source="LOCAL",
        main_dept_id=1,
        last_login_time=None,
    )
    db_session.add(user_neverlogin)

    user_resigned = User(
        id=4,
        tenant_id=1,
        username="resigned",
        nickname="Resigned User",
        status="RESIGNED",
        source="LOCAL",
        main_dept_id=1,
    )
    db_session.add(user_resigned)

    user_role1 = UserRole(
        id=1,
        tenant_id=1,
        user_id=1,
        role_id=1,
        source="MANUAL",
    )
    db_session.add(user_role1)

    user_role2 = UserRole(
        id=2,
        tenant_id=1,
        user_id=1,
        role_id=2,
        source="MANUAL",
    )
    db_session.add(user_role2)

    user_dept1 = UserDept(
        id=1,
        tenant_id=1,
        user_id=1,
        dept_id=1,
        is_main=True,
        source="LOCAL",
    )
    db_session.add(user_dept1)

    user_dept2 = UserDept(
        id=2,
        tenant_id=1,
        user_id=2,
        dept_id=2,
        is_main=True,
        source="LOCAL",
    )
    db_session.add(user_dept2)

    user_dept_neverlogin = UserDept(
        id=3,
        tenant_id=1,
        user_id=3,
        dept_id=1,
        is_main=True,
        source="LOCAL",
    )
    db_session.add(user_dept_neverlogin)

    user_dept_resigned = UserDept(
        id=4,
        tenant_id=1,
        user_id=4,
        dept_id=1,
        is_main=True,
        source="LOCAL",
    )
    db_session.add(user_dept_resigned)

    db_session.flush()

    return {
        "admin_role_id": 1,
        "user_role_id": 2,
        "disabled_role_id": 3,
        "user1_id": 1,
        "user2_id": 2,
        "user_neverlogin_id": 3,
        "user_resigned_id": 4,
        "root_dept_id": 1,
        "child_dept_id": 2,
        "system_dept_id": 3,
    }


class TestRoleServiceGetRoleSimpleList:
    """Tests for RoleService.get_role_simple_list."""

    def test_get_role_simple_list_returns_enabled_only(self, role_service, role_user_data, db_session, test_context):
        """Test returns only enabled roles."""
        result = run_async(role_service.get_role_simple_list())

        assert isinstance(result, list)
        assert len(result) == 2
        for role in result:
            assert "id" in role
            assert "name" in role
            assert "source" in role


class TestRoleServiceGetRoleById:
    """Tests for RoleService.get_role_by_id."""

    def test_get_role_by_id_exists(self, role_service, role_user_data, db_session, test_context):
        """Test getting existing role."""
        result = run_async(role_service.get_role_by_id(role_user_data["admin_role_id"]))

        assert result is not None
        assert result["id"] == "1"
        assert result["role_key"] == "R_ADMIN"
        assert result["name"] == "Administrator"

    def test_get_role_by_id_not_found(self, role_service, role_user_data, db_session, test_context):
        """Test getting non-existent role."""
        result = run_async(role_service.get_role_by_id(9999))

        assert result is None


class TestRoleServiceGetUserRoles:
    """Tests for RoleService.get_user_roles."""

    def test_get_user_roles_returns_enabled(self, role_service, role_user_data, db_session, test_context):
        """Test getting enabled roles for user."""
        result = run_async(role_service.get_user_roles(role_user_data["user1_id"]))

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_user_roles_no_roles(self, role_service, role_user_data, db_session, test_context):
        """Test getting roles for user with no roles."""
        result = run_async(role_service.get_user_roles(role_user_data["user2_id"]))

        assert isinstance(result, list)
        assert len(result) == 0


class TestRoleServiceGetRolePermissionCodes:
    """Tests for RoleService.get_role_permission_codes."""

    def test_get_role_permission_codes(self, role_service, role_user_data, db_session, test_context):
        """Test getting permission codes for role."""
        result = run_async(role_service.get_role_permission_codes(role_user_data["admin_role_id"]))

        assert isinstance(result, list)
        assert len(result) == 2
        assert "ims:system" in result
        assert "ims:system:user" in result

    def test_get_role_permission_codes_no_perms(self, role_service, role_user_data, db_session, test_context):
        """Test getting permission codes for role with no menus."""
        result = run_async(role_service.get_role_permission_codes(role_user_data["user_role_id"]))

        assert isinstance(result, list)
        assert len(result) == 0


class TestRoleServiceValidateRoleExists:
    """Tests for RoleService.validate_role_exists."""

    def test_validate_role_exists_success(self, role_service, role_user_data, db_session, test_context):
        """Test validating existing role."""
        result = run_async(role_service.validate_role_exists(role_user_data["admin_role_id"]))

        assert result is True

    def test_validate_role_exists_not_found(self, role_service, role_user_data, db_session, test_context):
        """Test validating non-existent role."""
        with pytest.raises(BizError) as exc_info:
            run_async(role_service.validate_role_exists(9999))

        assert exc_info.value.code == 1500


class TestUserServiceCreateUser:
    """Tests for UserService.create_user."""

    @pytest.mark.skipif(
        "sqlite" in os.environ.get("IMS_DB_URL", "sqlite"),
        reason="SQLite autoincrement issue - run with MySQL"
    )
    def test_create_user_success(self, user_service, role_user_data, db_session, test_context):
        """Test creating a new user."""
        class Request:
            username = "newuser"
            nickname = "New User"
            mobile = "13800138001"
            dept_ids = [str(role_user_data["root_dept_id"])]
            main_dept_id = str(role_user_data["root_dept_id"])
            password = "Test1234"

        result = run_async(user_service.create_user(Request()))

        assert result is not None
        assert result["username"] == "newuser"
        assert result["nickname"] == "New User"
        assert result["status"] == "ACTIVE"

    def test_create_user_invalid_username(self, user_service, role_user_data, db_session, test_context):
        """Test creating user with invalid username."""
        class Request:
            username = "ab"
            nickname = "New User"
            mobile = "13800138001"
            dept_ids = [str(role_user_data["root_dept_id"])]
            main_dept_id = str(role_user_data["root_dept_id"])
            password = "Test1234"

        with pytest.raises(BizError) as exc_info:
            run_async(user_service.create_user(Request()))

        assert exc_info.value.code == 1001

    def test_create_user_duplicate_username(self, user_service, role_user_data, db_session, test_context):
        """Test creating user with duplicate username."""
        class Request:
            username = "testuser1"
            nickname = "New User"
            mobile = "13800138001"
            dept_ids = [str(role_user_data["root_dept_id"])]
            main_dept_id = str(role_user_data["root_dept_id"])
            password = "Test1234"

        with pytest.raises(BizError) as exc_info:
            run_async(user_service.create_user(Request()))

        assert exc_info.value.code == 1001

    def test_create_user_main_dept_not_in_list(self, user_service, role_user_data, db_session, test_context):
        """Test creating user where main dept not in dept list."""
        class Request:
            username = "newuser2"
            nickname = "New User"
            mobile = "13800138001"
            dept_ids = [str(role_user_data["root_dept_id"])]
            main_dept_id = str(role_user_data["child_dept_id"])
            password = "Test1234"

        with pytest.raises(BizError) as exc_info:
            run_async(user_service.create_user(Request()))

        assert exc_info.value.code == 1001

    def test_create_user_dept_not_found(self, user_service, role_user_data, db_session, test_context):
        """Test creating user with non-existent department."""
        class Request:
            username = "newuser3"
            nickname = "New User"
            mobile = "13800138001"
            dept_ids = ["9999"]
            main_dept_id = "9999"
            password = "Test1234"

        with pytest.raises(BizError) as exc_info:
            run_async(user_service.create_user(Request()))

        assert exc_info.value.code == 1500


class TestUserServiceUpdateUserDepts:
    """Tests for UserService.update_user_depts."""

    @pytest.mark.skipif(
        "sqlite" in os.environ.get("IMS_DB_URL", "sqlite"),
        reason="SQLite autoincrement issue - run with MySQL"
    )
    def test_update_user_depts_success(self, user_service, role_user_data, db_session, test_context):
        """Test updating user departments."""
        run_async(
            user_service.update_user_depts(
                str(role_user_data["user1_id"]),
                [str(role_user_data["root_dept_id"]), str(role_user_data["child_dept_id"])],
                str(role_user_data["child_dept_id"]),
            )
        )

    @pytest.mark.skipif(
        "sqlite" in os.environ.get("IMS_DB_URL", "sqlite"),
        reason="SQLite autoincrement issue - run with MySQL"
    )
    def test_update_user_depts_empty_assigns_system(self, user_service, role_user_data, db_session, test_context):
        """Test updating user with no depts assigns to system dept."""
        # When dept_ids is empty and main_dept_id is empty, assigns to system dept
        run_async(
            user_service.update_user_depts(
                str(role_user_data["user2_id"]),
                [],
                "",
            )
        )

    def test_update_user_depts_main_not_in_list(self, user_service, role_user_data, db_session, test_context):
        """Test updating user where main dept not in list."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                user_service.update_user_depts(
                    str(role_user_data["user1_id"]),
                    [str(role_user_data["root_dept_id"])],
                    str(role_user_data["child_dept_id"]),
                )
            )

        assert exc_info.value.code == 1001

    def test_update_user_depts_user_not_found(self, user_service, role_user_data, db_session, test_context):
        """Test updating non-existent user."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                user_service.update_user_depts(
                    "9999",
                    [str(role_user_data["root_dept_id"])],
                    str(role_user_data["root_dept_id"]),
                )
            )

        assert exc_info.value.code == 1504


class TestUserServiceDeleteUser:
    """Tests for UserService.delete_user."""

    def test_delete_user_never_logged_in(self, user_service, role_user_data, db_session, test_context):
        """Test deleting user who never logged in."""
        run_async(user_service.delete_user(str(role_user_data["user_neverlogin_id"])))

    def test_delete_user_resigned_fails(self, user_service, role_user_data, db_session, test_context):
        """Test deleting resigned user fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(user_service.delete_user(str(role_user_data["user_resigned_id"])))

        assert exc_info.value.code == 1502

    def test_delete_user_has_logged_in_fails(self, user_service, role_user_data, db_session, test_context):
        """Test deleting user who has logged in fails."""
        from datetime import datetime

        from app.domains.sys.models import User
        session = db_session

        user = session.query(User).filter(User.id == role_user_data["user2_id"]).first()
        user.last_login_time = datetime.now()
        session.flush()

        with pytest.raises(BizError) as exc_info:
            run_async(user_service.delete_user(str(role_user_data["user2_id"])))

        assert exc_info.value.code == 1502

    def test_delete_user_not_found(self, user_service, role_user_data, db_session, test_context):
        """Test deleting non-existent user."""
        with pytest.raises(BizError) as exc_info:
            run_async(user_service.delete_user("9999"))

        assert exc_info.value.code == 1504
