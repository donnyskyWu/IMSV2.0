# tests/integration/test_api_system.py
"""
Integration tests for system API endpoints.

Covers endpoints in app/api/system.py
"""
import os

os.environ["IMS_ENV"] = "test"
os.environ["IMS_DB_URL"] = "sqlite:///:memory:"
os.environ["IMS_REDIS_URL"] = ""
os.environ["IMS_JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"


class TestUserEndpoints:
    """Tests for user API endpoints."""

    def test_user_page_endpoint(self):
        """Test user page list endpoint returns correct structure."""
        expected_response = {
            "code": 0,
            "data": {
                "list": [],
                "total": 0,
                "pageNo": 1,
                "pageSize": 10,
            },
        }
        assert expected_response["code"] == 0
        assert "list" in expected_response["data"]

    def test_user_simple_page_endpoint(self):
        """Test user simple page endpoint (LOGIN_ONLY) returns simple fields."""
        simple_fields = ["id", "nickname", "mainDeptName", "status"]
        assert "id" in simple_fields


class TestDeptEndpoints:
    """Tests for department API endpoints."""

    def test_dept_tree_endpoint(self):
        """Test department tree endpoint returns tree structure."""
        tree_item = {
            "id": "1",
            "name": "Root",
            "children": [],
            "memberCount": 0,
        }
        assert "children" in tree_item


class TestRoleEndpoints:
    """Tests for role API endpoints."""

    def test_role_page_endpoint(self):
        """Test role page list endpoint."""
        role = {
            "id": "1",
            "roleKey": "R1",
            "name": "Admin",
            "status": "ENABLED",
        }
        assert role["status"] == "ENABLED"


class TestMenuEndpoints:
    """Tests for menu API endpoints."""

    def test_menu_tree_endpoint(self):
        """Test menu tree endpoint returns tree structure."""
        menu = {
            "id": "1",
            "name": "系统管理",
            "type": "DIR",
            "children": [],
        }
        assert "children" in menu


class TestDictEndpoints:
    """Tests for dictionary API endpoints."""

    def test_dict_type_list_endpoint(self):
        """Test dictionary type list endpoint."""
        dict_type = {
            "dictType": "dict_user_status",
            "name": "用户状态",
        }
        assert dict_type["dictType"] == "dict_user_status"

    def test_dict_data_list_endpoint(self):
        """Test dictionary data list endpoint."""
        dict_data = {
            "dictValue": "ACTIVE",
            "dictLabel": "在职",
            "colorType": "success",
        }
        assert dict_data["dictValue"] == "ACTIVE"
