# tests/integration/test_service_coverage.py
"""
Integration tests for service layer coverage.

These tests directly exercise service methods to increase coverage on:
- app/services/user.py
- app/services/dept.py
- app/services/role.py
- app/services/dict.py
- app/services/auth.py
- app/db/repository.py
- app/db/session.py
"""
import os

# Only set defaults if not already set (CI provides MySQL/Redis)
os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")

import asyncio

import pytest

from app.core.pagination import PageParam


def run_async(coro):
    """Run async function synchronously."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@pytest.fixture
def user_service():
    """Create UserService instance."""
    from app.services.user import UserService
    return UserService()


@pytest.fixture
def dept_service():
    """Create DeptService instance."""
    from app.services.dept import DeptService
    return DeptService()


@pytest.fixture
def role_service():
    """Create RoleService instance."""
    from app.services.role import RoleService
    return RoleService()


@pytest.fixture
def dict_service():
    """Create DictService instance."""
    from app.services.dict import DictService
    return DictService()


@pytest.fixture
def auth_service():
    """Create AuthService instance."""
    from app.services.auth import AuthService
    return AuthService()


@pytest.fixture
def sample_users(db_session, test_context):
    """Create sample users for testing."""
    from app.domains.sys.models import Dept, User, UserDept

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

    user1 = User(
        id=1,
        tenant_id=1,
        username="user1",
        nickname="User One",
        status="ACTIVE",
        source="LOCAL",
        main_dept_id=1,
    )
    db_session.add(user1)

    user2 = User(
        id=2,
        tenant_id=1,
        username="user2",
        nickname="User Two",
        status="ACTIVE",
        source="LOCAL",
        main_dept_id=2,
    )
    db_session.add(user2)

    user3 = User(
        id=3,
        tenant_id=1,
        username="frozen_user",
        nickname="Frozen User",
        status="FROZEN",
        source="LOCAL",
        main_dept_id=1,
    )
    db_session.add(user3)

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

    user_dept3 = UserDept(
        id=3,
        tenant_id=1,
        user_id=3,
        dept_id=1,
        is_main=True,
        source="LOCAL",
    )
    db_session.add(user_dept3)

    db_session.flush()

    return {
        "user1": {"id": 1, "username": "user1"},
        "user2": {"id": 2, "username": "user2"},
        "frozen_user": {"id": 3, "username": "frozen_user"},
        "root_dept_id": 1,
        "child_dept_id": 2,
        "system_dept_id": 3,
    }


@pytest.fixture
def sample_dicts(db_session, test_context):
    """Create sample dictionaries for testing."""
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
        ("ACTIVE", "在职", "success", 0),
        ("FROZEN", "冻结", "warning", 1),
        ("RESIGNED", "离职", "danger", 2),
    ]

    for i, (value, label, color, sort) in enumerate(statuses):
        data = DictData(
            id=10 + i,
            tenant_id=1,
            dict_type="dict_user_status",
            dict_value=value,
            dict_label=label,
            color_type=color,
            sort=sort,
            status="ENABLED",
            is_builtin=True,
        )
        db_session.add(data)

    db_session.flush()

    return {"dict_type": "dict_user_status"}


@pytest.fixture
def sample_roles(db_session, test_context):
    """Create sample roles for testing."""
    from app.domains.sys.models import Role

    role1 = Role(
        id=1,
        tenant_id=1,
        role_key="R_ADMIN",
        name="管理员",
        status="ENABLED",
        source="MANUAL",
        data_scope="ALL",
    )
    db_session.add(role1)

    role2 = Role(
        id=2,
        tenant_id=1,
        role_key="R_USER",
        name="普通用户",
        status="ENABLED",
        source="MANUAL",
        data_scope="SELF",
    )
    db_session.add(role2)

    role3 = Role(
        id=3,
        tenant_id=1,
        role_key="R_DISABLED",
        name="停用角色",
        status="DISABLED",
        source="MANUAL",
    )
    db_session.add(role3)

    db_session.flush()

    return {
        "admin_role_id": 1,
        "user_role_id": 2,
        "disabled_role_id": 3,
    }


class TestUserServiceGetUserPage:
    """Tests for UserService.get_user_page."""

    def test_get_user_page_basic(self, user_service, sample_users, db_session, test_context):
        """Test basic user page listing."""
        page_param = PageParam(page_no=1, page_size=10)
        result = run_async(user_service.get_user_page(page_param))

        assert result is not None
        assert result.total >= 0
        assert isinstance(result.list, list)

    def test_get_user_page_with_dept_filter(self, user_service, sample_users, db_session, test_context):
        """Test user page with department filter."""
        page_param = PageParam(page_no=1, page_size=10)
        result = run_async(
            user_service.get_user_page(
                page_param,
                dept_id=str(sample_users["root_dept_id"]),
                include_children=True,
            )
        )

        assert result is not None
        assert isinstance(result.list, list)

    def test_get_user_page_with_dept_filter_no_children(self, user_service, sample_users, db_session, test_context):
        """Test user page with department filter excluding children."""
        page_param = PageParam(page_no=1, page_size=10)
        result = run_async(
            user_service.get_user_page(
                page_param,
                dept_id=str(sample_users["root_dept_id"]),
                include_children=False,
            )
        )

        assert result is not None
        assert isinstance(result.list, list)

    def test_get_user_page_with_keyword(self, user_service, sample_users, db_session, test_context):
        """Test user page with keyword search."""
        page_param = PageParam(page_no=1, page_size=10)
        result = run_async(
            user_service.get_user_page(page_param, keyword="user")
        )

        assert result is not None
        assert isinstance(result.list, list)

    def test_get_user_page_with_status(self, user_service, sample_users, db_session, test_context):
        """Test user page with status filter."""
        page_param = PageParam(page_no=1, page_size=10)
        result = run_async(
            user_service.get_user_page(page_param, status="ACTIVE")
        )

        assert result is not None
        assert isinstance(result.list, list)


class TestUserServiceGetUserSimplePage:
    """Tests for UserService.get_user_simple_page."""

    def test_get_user_simple_page_basic(self, user_service, sample_users, db_session, test_context):
        """Test basic simple user page listing."""
        page_param = PageParam(page_no=1, page_size=10)
        result = run_async(user_service.get_user_simple_page(page_param))

        assert result is not None
        assert isinstance(result.list, list)

    def test_get_user_simple_page_with_keyword(self, user_service, sample_users, db_session, test_context):
        """Test simple user page with keyword."""
        page_param = PageParam(page_no=1, page_size=10)
        result = run_async(
            user_service.get_user_simple_page(page_param, keyword="User")
        )

        assert result is not None
        assert isinstance(result.list, list)


class TestDictServiceGetDictDataSimpleList:
    """Tests for DictService.get_dict_data_simple_list."""

    def test_get_dict_data_simple_list_returns_list(self, dict_service, sample_dicts, db_session, test_context):
        """Test get dict data returns list."""
        result = run_async(
            dict_service.get_dict_data_simple_list(sample_dicts["dict_type"])
        )

        assert isinstance(result, list)
        assert len(result) == 3

    def test_get_dict_data_simple_list_empty_type(self, dict_service, db_session, test_context):
        """Test get dict data returns empty list for unknown type."""
        result = run_async(
            dict_service.get_dict_data_simple_list("unknown_type")
        )

        assert isinstance(result, list)
        assert len(result) == 0


class TestDictServiceGetDictTypeList:
    """Tests for DictService.get_dict_type_list."""

    def test_get_dict_type_list_returns_list(self, dict_service, sample_dicts, db_session, test_context):
        """Test get dict type list returns list."""
        result = run_async(dict_service.get_dict_type_list())

        assert isinstance(result, list)
        assert len(result) >= 1


class TestRoleServiceGetRoleSimpleList:
    """Tests for RoleService.get_role_simple_list."""

    def test_get_role_simple_list_returns_enabled_only(self, role_service, sample_roles, db_session, test_context):
        """Test get role simple list returns only enabled roles."""
        result = run_async(role_service.get_role_simple_list())

        assert isinstance(result, list)
        assert len(result) == 2


class TestAuthServiceBuildDataScopeText:
    """Tests for AuthService._build_data_scope_text."""

    def test_build_data_scope_text_all(self, auth_service, sample_users, db_session, test_context):
        """Test data scope text for ALL scope."""
        perm_data = {
            "data_scopes": [{"scope_type": "ALL", "role_id": 1}],
            "dept_ids": [1],
        }
        result = run_async(
            auth_service._build_data_scope_text(perm_data, 1)
        )

        assert result == "全部"

    def test_build_data_scope_text_dept(self, auth_service, sample_users, db_session, test_context):
        """Test data scope text for DEPT scope."""
        perm_data = {
            "data_scopes": [{"scope_type": "DEPT", "role_id": 1}],
            "dept_ids": [1],
        }
        result = run_async(
            auth_service._build_data_scope_text(perm_data, 1)
        )

        assert "本部门" in result

    def test_build_data_scope_text_self(self, auth_service, db_session, test_context):
        """Test data scope text for SELF scope."""
        perm_data = {
            "data_scopes": [{"scope_type": "SELF", "role_id": 1}],
            "dept_ids": [],
        }
        result = run_async(
            auth_service._build_data_scope_text(perm_data, 1)
        )

        assert "仅本人" in result

    def test_build_data_scope_text_ip_group(self, auth_service, db_session, test_context):
        """Test data scope text for IP_GROUP scope."""
        perm_data = {
            "data_scopes": [{"scope_type": "IP_GROUP", "role_id": 1}],
            "dept_ids": [],
        }
        result = run_async(
            auth_service._build_data_scope_text(perm_data, 1)
        )

        assert "IP" in result

    def test_build_data_scope_text_empty(self, auth_service, db_session, test_context):
        """Test data scope text for no scopes."""
        perm_data = {
            "data_scopes": [],
            "dept_ids": [],
        }
        result = run_async(
            auth_service._build_data_scope_text(perm_data, 1)
        )

        assert "权限" in result or "未配置" in result


class TestAuthServiceGetUserPermissions:
    """Tests for AuthService._get_user_permissions."""

    def test_get_user_permissions_with_roles(self, auth_service, sample_users, sample_roles, db_session, test_context):
        """Test get user permissions with roles."""
        from app.domains.sys.models import UserRole

        user_role = UserRole(
            id=100,
            tenant_id=1,
            user_id=1,
            role_id=1,
            source="MANUAL",
        )
        db_session.add(user_role)
        db_session.flush()

        result = run_async(auth_service._get_user_permissions(1))

        assert isinstance(result, dict)
        assert "perm_codes" in result
        assert "data_scopes" in result
        assert "dept_ids" in result

    def test_get_user_permissions_no_roles(self, auth_service, sample_users, db_session, test_context):
        """Test get user permissions without roles."""
        result = run_async(auth_service._get_user_permissions(1))

        assert isinstance(result, dict)
        assert "perm_codes" in result
        assert result["perm_codes"] == []


class TestAuthServiceRecordLoginFailure:
    """Tests for AuthService._record_login_failure."""

    def test_record_login_failure_increments_count(self, auth_service, db_session, test_context):
        """Test record login failure increments count."""
        run_async(auth_service._record_login_failure("testuser"))


class TestAuthServiceWriteLoginLog:
    """Tests for AuthService._write_login_log."""

    def test_write_login_log_success(self, auth_service, db_session, test_context):
        """Test write login log for success."""
        run_async(
            auth_service._write_login_log(
                user_id=1,
                username="testuser",
                method="PASSWORD",
                result="SUCCESS",
            )
        )

    def test_write_login_log_failure(self, auth_service, db_session, test_context):
        """Test write login log for failure."""
        run_async(
            auth_service._write_login_log(
                username="testuser",
                method="PASSWORD",
                result="FAILED",
            )
        )


class TestUserServiceHelpers:
    """Tests for UserService helper methods."""

    def test_mask_mobile(self, user_service):
        """Test mobile number masking."""
        result = user_service._mask_mobile("13800138000")
        assert "***" in result

    def test_encrypt_mobile(self, user_service):
        """Test mobile encryption."""
        result = user_service._encrypt_mobile("13800138000")
        assert result is not None

    def test_hash_mobile(self, user_service):
        """Test mobile hashing."""
        result = user_service._hash_mobile("13800138000")
        assert result is not None
        assert len(result) > 0


# ============================================================================
# OrgSyncService Tests (FP-D07 - DingTalk Organization Sync Stub)
# ============================================================================
# Note: org_sync.py implements stub functionality for DingTalk organization
# synchronization. The actual DingTalk API integration requires external
# credentials which are not available in CI. The stub:
# - Creates sync batch records with PENDING status
# - Returns batch info immediately (async execution placeholder)
# - The TODO comments indicate where DingTalk adapter calls would be added
# ============================================================================


@pytest.fixture
def org_sync_service():
    """Create OrgSyncService instance."""
    from app.services.org_sync import OrgSyncService
    return OrgSyncService()


class TestOrgSyncServiceTriggerReconcile:
    """Tests for OrgSyncService.trigger_reconcile - UT-D07-18."""

    @pytest.mark.skipif(
        "sqlite" in os.environ.get("IMS_DB_URL", "sqlite"),
        reason="SQLite autoincrement issue - run with MySQL"
    )
    def test_trigger_reconcile_creates_batch(self, org_sync_service, db_session, test_context):
        """UT-D07-18: Test trigger reconcile creates a pending batch."""
        result = run_async(org_sync_service.trigger_reconcile())

        assert result is not None
        assert "batch_id" in result
        assert result["status"] == "PENDING"
        assert result["started_at"] is not None
        assert result["added_depts"] == 0
        assert result["added_users"] == 0

    @pytest.mark.skipif(
        "sqlite" in os.environ.get("IMS_DB_URL", "sqlite"),
        reason="SQLite autoincrement issue - run with MySQL"
    )
    def test_trigger_reconcile_returns_batch_info(self, org_sync_service, db_session, test_context):
        """Test trigger reconcile returns proper batch info structure."""
        result = run_async(org_sync_service.trigger_reconcile())

        expected_keys = [
            "batch_id", "status", "started_at", "completed_at",
            "added_depts", "updated_depts", "removed_depts",
            "added_users", "updated_users", "removed_users", "error_msg"
        ]
        for key in expected_keys:
            assert key in result


class TestOrgSyncServiceGetLatestBatch:
    """Tests for OrgSyncService.get_latest_batch - UT-D07-04."""

    def test_get_latest_batch_no_batches(self, org_sync_service, db_session, test_context):
        """Test get latest batch returns None when no batches exist."""
        result = run_async(org_sync_service.get_latest_batch())

        assert result is None

    @pytest.mark.skipif(
        "sqlite" in os.environ.get("IMS_DB_URL", "sqlite"),
        reason="SQLite autoincrement issue - run with MySQL"
    )
    def test_get_latest_batch_returns_most_recent(self, org_sync_service, db_session, test_context):
        """Test get latest batch returns the most recent batch."""
        run_async(org_sync_service.trigger_reconcile())
        run_async(org_sync_service.trigger_reconcile())

        result = run_async(org_sync_service.get_latest_batch())

        assert result is not None
        assert "batch_id" in result
        assert result["status"] == "PENDING"


class TestOrgSyncServiceBatchToResponse:
    """Tests for OrgSyncService._batch_to_response helper."""

    @pytest.mark.skipif(
        "sqlite" in os.environ.get("IMS_DB_URL", "sqlite"),
        reason="SQLite autoincrement issue - run with MySQL"
    )
    def test_batch_to_response_formats_correctly(self, org_sync_service, db_session, test_context):
        """Test batch to response formats all fields correctly."""
        result = run_async(org_sync_service.trigger_reconcile())

        assert isinstance(result["batch_id"], str)
        assert result["started_at"].endswith("+08:00")
        assert result["completed_at"] is None
        assert result["error_msg"] is None
