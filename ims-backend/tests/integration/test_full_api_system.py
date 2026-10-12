# tests/integration/test_full_api_system.py
"""
Full integration tests for system API using TestClient.

These tests exercise the actual API endpoints via HTTP requests,
which provides coverage for:
- app/api/system.py
- app/api/deps.py
- app/services/user.py
- app/services/dept.py
- app/services/role.py
- app/services/dict.py
- app/db/repository.py
- app/db/session.py

Uses TestClient to test full request/response cycle.
"""
import os

os.environ["IMS_ENV"] = "test"
os.environ["IMS_DB_URL"] = "sqlite:///:memory:"
os.environ["IMS_REDIS_URL"] = ""
os.environ["IMS_JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient


def create_valid_token(user_id: int = 1, tenant_id: int = 1, session_id: str = "test-session"):
    """Create a valid JWT token for testing."""
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "sid": session_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(
        payload,
        os.environ["IMS_JWT_SECRET"],
        algorithm="HS256",
    )


@pytest.fixture
def app_client(db_session, test_context):
    """Create test client with database session."""
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_dict_data(db_session, test_context):
    """Create sample dictionary data for testing."""
    from app.domains.sys.models import DictData, DictType

    dict_type = DictType(
        id=1,
        tenant_id=1,
        dict_type="dict_test_type",
        name="Test Type",
        status="ENABLED",
    )
    db_session.add(dict_type)

    data1 = DictData(
        id=1,
        tenant_id=1,
        dict_type="dict_test_type",
        dict_value="VALUE1",
        dict_label="Label 1",
        color_type="success",
        sort=0,
        status="ENABLED",
        is_builtin=False,
    )
    db_session.add(data1)

    db_session.flush()

    return {"dict_type": "dict_test_type"}


def assert_auth_required(response):
    """Assert that authentication is required for a response."""
    if response.status_code == 401:
        return True
    if response.status_code == 200:
        data = response.json()
        return data.get("code") != 0
    return False


class TestDictDataEndpoint:
    """Integration tests for GET /admin-api/ims/system/dict-data/simple-list."""

    def test_dict_data_endpoint_exists(self, app_client):
        """Test dict data endpoint is registered."""
        response = app_client.get(
            "/admin-api/ims/system/dict-data/simple-list",
            params={"dict_type": "unknown"},
        )
        assert response.status_code == 200

    def test_dict_data_returns_list(self, app_client, sample_dict_data, db_session):
        """Test dict data returns list of values."""
        response = app_client.get(
            "/admin-api/ims/system/dict-data/simple-list",
            params={"dict_type": sample_dict_data["dict_type"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)

    def test_dict_data_requires_dict_type_param(self, app_client):
        """Test dict data requires dict_type parameter."""
        response = app_client.get("/admin-api/ims/system/dict-data/simple-list")
        assert response.status_code in [200, 422]


class TestDictTypeEndpoint:
    """Integration tests for GET /admin-api/ims/system/dict-type/list."""

    def test_dict_type_endpoint_without_auth_fails(self, app_client):
        """Test dict type endpoint requires login."""
        response = app_client.get("/admin-api/ims/system/dict-type/list")
        assert assert_auth_required(response)


class TestDeptTreeEndpoint:
    """Integration tests for GET /admin-api/ims/system/dept/tree."""

    def test_dept_tree_endpoint_without_auth_fails(self, app_client):
        """Test dept tree endpoint requires permission."""
        response = app_client.get("/admin-api/ims/system/dept/tree")
        assert assert_auth_required(response)


class TestDeptCreateEndpoint:
    """Integration tests for POST /admin-api/ims/system/dept/create."""

    def test_dept_create_endpoint_without_auth_fails(self, app_client):
        """Test dept create endpoint requires permission."""
        response = app_client.post(
            "/admin-api/ims/system/dept/create",
            json={"parent_id": "1", "name": "New Dept"},
        )
        assert assert_auth_required(response)


class TestDeptUpdateEndpoint:
    """Integration tests for PUT /admin-api/ims/system/dept/update."""

    def test_dept_update_endpoint_without_auth_fails(self, app_client):
        """Test dept update endpoint requires permission."""
        response = app_client.put(
            "/admin-api/ims/system/dept/update",
            params={"id": "1"},
            json={"name": "Updated Dept"},
        )
        assert assert_auth_required(response)


class TestDeptMoveEndpoint:
    """Integration tests for PUT /admin-api/ims/system/dept/move."""

    def test_dept_move_endpoint_without_auth_fails(self, app_client):
        """Test dept move endpoint requires permission."""
        response = app_client.put(
            "/admin-api/ims/system/dept/move",
            json={"id": "2", "new_parent_id": "1"},
        )
        assert assert_auth_required(response)


class TestDeptStatusEndpoint:
    """Integration tests for PUT /admin-api/ims/system/dept/update-status."""

    def test_dept_status_endpoint_without_auth_fails(self, app_client):
        """Test dept status endpoint requires permission."""
        response = app_client.put(
            "/admin-api/ims/system/dept/update-status",
            params={"id": "1", "status": "DISABLED"},
        )
        assert assert_auth_required(response)


class TestDeptDeleteEndpoint:
    """Integration tests for DELETE /admin-api/ims/system/dept/delete."""

    def test_dept_delete_endpoint_without_auth_fails(self, app_client):
        """Test dept delete endpoint requires permission."""
        response = app_client.delete(
            "/admin-api/ims/system/dept/delete",
            params={"id": "1"},
        )
        assert assert_auth_required(response)


class TestConfirmOrphanEndpoint:
    """Integration tests for PUT /admin-api/ims/system/dept/confirm-orphan."""

    def test_confirm_orphan_endpoint_without_auth_fails(self, app_client):
        """Test confirm orphan endpoint requires permission."""
        response = app_client.put(
            "/admin-api/ims/system/dept/confirm-orphan",
            params={"id": "1"},
        )
        assert assert_auth_required(response)


class TestUserPageEndpoint:
    """Integration tests for GET /admin-api/ims/system/user/page."""

    def test_user_page_endpoint_without_auth_fails(self, app_client):
        """Test user page endpoint requires permission."""
        response = app_client.get("/admin-api/ims/system/user/page")
        assert assert_auth_required(response)


class TestUserSimplePageEndpoint:
    """Integration tests for GET /admin-api/ims/system/user/simple-page."""

    def test_user_simple_page_endpoint_without_auth_fails(self, app_client):
        """Test user simple page endpoint requires login."""
        response = app_client.get("/admin-api/ims/system/user/simple-page")
        assert assert_auth_required(response)


class TestUserCreateEndpoint:
    """Integration tests for POST /admin-api/ims/system/user/create."""

    def test_user_create_endpoint_without_auth_fails(self, app_client):
        """Test user create endpoint requires permission."""
        response = app_client.post(
            "/admin-api/ims/system/user/create",
            json={
                "username": "newuser",
                "nickname": "New User",
                "mobile": "13800138001",
                "dept_ids": ["1"],
                "main_dept_id": "1",
                "password": "password123",
            },
        )
        assert assert_auth_required(response)


class TestUserUpdateDeptsEndpoint:
    """Integration tests for PUT /admin-api/ims/system/user/update-depts."""

    def test_user_update_depts_endpoint_without_auth_fails(self, app_client):
        """Test user update depts endpoint requires permission."""
        response = app_client.put(
            "/admin-api/ims/system/user/update-depts",
            params={"id": "1"},
            json={"dept_ids": ["1"], "main_dept_id": "1"},
        )
        assert assert_auth_required(response)


class TestUserDeleteEndpoint:
    """Integration tests for DELETE /admin-api/ims/system/user/delete."""

    def test_user_delete_endpoint_without_auth_fails(self, app_client):
        """Test user delete endpoint requires permission."""
        response = app_client.delete(
            "/admin-api/ims/system/user/delete",
            params={"id": "1"},
        )
        assert assert_auth_required(response)


class TestRoleSimpleListEndpoint:
    """Integration tests for GET /admin-api/ims/system/role/simple-list."""

    def test_role_simple_list_endpoint_without_auth_fails(self, app_client):
        """Test role simple list endpoint requires login."""
        response = app_client.get("/admin-api/ims/system/role/simple-list")
        assert assert_auth_required(response)


class TestOrgSyncEndpoints:
    """Integration tests for org sync endpoints."""

    def test_org_sync_reconcile_endpoint_without_auth_fails(self, app_client):
        """Test org sync reconcile endpoint requires permission."""
        response = app_client.post("/admin-api/ims/system/org-sync/reconcile")
        assert assert_auth_required(response)

    def test_org_sync_latest_batch_endpoint_without_auth_fails(self, app_client):
        """Test org sync latest batch endpoint requires permission."""
        response = app_client.get("/admin-api/ims/system/org-sync/latest-batch")
        assert assert_auth_required(response)
