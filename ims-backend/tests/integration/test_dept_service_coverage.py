# tests/integration/test_dept_service_coverage.py
"""
Integration tests for DeptService coverage.

These tests directly exercise DeptService methods to increase coverage.
"""
import os

os.environ["IMS_ENV"] = "test"
os.environ["IMS_DB_URL"] = "sqlite:///:memory:"
os.environ["IMS_REDIS_URL"] = ""
os.environ["IMS_JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"

import asyncio

import pytest

from app.core.errors import BizError


def run_async(coro):
    """Run async function synchronously."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@pytest.fixture
def dept_service():
    """Create DeptService instance."""
    from app.services.dept import DeptService
    return DeptService()


@pytest.fixture
def dept_tree_data(db_session, test_context):
    """Create a comprehensive department tree for testing."""
    from app.domains.sys.models import Dept, User, UserDept

    root = Dept(
        id=1,
        tenant_id=1,
        parent_id=0,
        path="/1/",
        name="Root Department",
        status="ENABLED",
        source="LOCAL",
        sort=0,
    )
    db_session.add(root)

    child1 = Dept(
        id=2,
        tenant_id=1,
        parent_id=1,
        path="/1/2/",
        name="Child Department 1",
        status="ENABLED",
        source="LOCAL",
        sort=0,
    )
    db_session.add(child1)

    child2 = Dept(
        id=3,
        tenant_id=1,
        parent_id=1,
        path="/1/3/",
        name="Child Department 2",
        status="ENABLED",
        source="DINGTALK",
        sort=1,
    )
    db_session.add(child2)

    grandchild = Dept(
        id=4,
        tenant_id=1,
        parent_id=2,
        path="/1/2/4/",
        name="Grandchild Department",
        status="ENABLED",
        source="LOCAL",
        sort=0,
    )
    db_session.add(grandchild)

    system_dept = Dept(
        id=5,
        tenant_id=1,
        parent_id=1,
        path="/1/5/",
        name="待分配",
        status="ENABLED",
        source="SYSTEM",
        sort=999,
    )
    db_session.add(system_dept)

    disabled_dept = Dept(
        id=6,
        tenant_id=1,
        parent_id=1,
        path="/1/6/",
        name="Disabled Department",
        status="DISABLED",
        source="LOCAL",
        sort=2,
    )
    db_session.add(disabled_dept)

    orphan_dept = Dept(
        id=7,
        tenant_id=1,
        parent_id=1,
        path="/1/7/",
        name="Orphan Department",
        status="ENABLED",
        source="LOCAL",
        local_orphan=True,
        sort=3,
    )
    db_session.add(orphan_dept)

    leader = User(
        id=10,
        tenant_id=1,
        username="leader",
        nickname="Department Leader",
        status="ACTIVE",
        source="LOCAL",
    )
    db_session.add(leader)

    user1 = User(
        id=11,
        tenant_id=1,
        username="user1",
        nickname="User 1",
        status="ACTIVE",
        source="LOCAL",
        main_dept_id=2,
    )
    db_session.add(user1)

    user2 = User(
        id=12,
        tenant_id=1,
        username="user2",
        nickname="User 2",
        status="FROZEN",
        source="LOCAL",
        main_dept_id=4,
    )
    db_session.add(user2)

    user_dept1 = UserDept(
        id=1,
        tenant_id=1,
        user_id=11,
        dept_id=2,
        is_main=True,
        source="LOCAL",
    )
    db_session.add(user_dept1)

    user_dept2 = UserDept(
        id=2,
        tenant_id=1,
        user_id=12,
        dept_id=4,
        is_main=True,
        source="LOCAL",
    )
    db_session.add(user_dept2)

    db_session.flush()

    return {
        "root_id": 1,
        "child1_id": 2,
        "child2_id": 3,
        "grandchild_id": 4,
        "system_dept_id": 5,
        "disabled_dept_id": 6,
        "orphan_dept_id": 7,
        "leader_id": 10,
    }


class TestDeptServiceGetDeptTree:
    """Tests for DeptService.get_dept_tree."""

    def test_get_dept_tree_returns_list(self, dept_service, dept_tree_data, db_session, test_context):
        """Test get_dept_tree returns a list."""
        result = run_async(dept_service.get_dept_tree())

        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_dept_tree_has_children(self, dept_service, dept_tree_data, db_session, test_context):
        """Test tree nodes have children."""
        result = run_async(dept_service.get_dept_tree())

        root = result[0]
        assert "children" in root
        assert isinstance(root["children"], list)

    def test_get_dept_tree_includes_member_count(self, dept_service, dept_tree_data, db_session, test_context):
        """Test tree nodes have member counts."""
        result = run_async(dept_service.get_dept_tree())

        root = result[0]
        assert "member_count" in root
        assert "direct_member_count" in root

    def test_get_dept_tree_excludes_disabled_by_default(self, dept_service, dept_tree_data, db_session, test_context):
        """Test disabled depts are excluded by default."""
        result = run_async(dept_service.get_dept_tree())

        def find_disabled(nodes):
            for node in nodes:
                if node["status"] == "DISABLED":
                    return True
                if find_disabled(node.get("children", [])):
                    return True
            return False

        assert not find_disabled(result)

    def test_get_dept_tree_includes_disabled_with_status_all(self, dept_service, dept_tree_data, db_session, test_context):
        """Test disabled depts are included with status=ALL."""
        result = run_async(dept_service.get_dept_tree(status="ALL"))

        def find_disabled(nodes):
            for node in nodes:
                if node["status"] == "DISABLED":
                    return True
                if find_disabled(node.get("children", [])):
                    return True
            return False

        assert find_disabled(result)

    def test_get_dept_tree_with_keyword(self, dept_service, dept_tree_data, db_session, test_context):
        """Test tree filtering by keyword."""
        result = run_async(dept_service.get_dept_tree(keyword="Grandchild"))

        assert len(result) > 0

    def test_get_dept_tree_keyword_no_match(self, dept_service, dept_tree_data, db_session, test_context):
        """Test tree filtering with no matching keyword."""
        result = run_async(dept_service.get_dept_tree(keyword="NonExistentDept"))

        assert len(result) == 0


class TestDeptServiceCreateDept:
    """Tests for DeptService.create_dept."""

    @pytest.mark.skip(reason="SQLite autoincrement issue - needs sequence or different test setup")
    def test_create_dept_success(self, dept_service, dept_tree_data, db_session, test_context):
        """Test creating a new department."""
        class Request:
            parent_id = "1"
            name = "New Department"
            sort = 0
            leader_user_id = None

        result = run_async(dept_service.create_dept(Request()))

        assert result is not None
        assert result["name"] == "New Department"
        assert result["source"] == "LOCAL"

    @pytest.mark.skip(reason="SQLite autoincrement issue - needs sequence or different test setup")
    def test_create_dept_with_leader(self, dept_service, dept_tree_data, db_session, test_context):
        """Test creating department with leader."""
        class Request:
            parent_id = "1"
            name = "Dept With Leader"
            sort = 0
            leader_user_id = str(dept_tree_data["leader_id"])

        result = run_async(dept_service.create_dept(Request()))

        assert result["leader_user_id"] == str(dept_tree_data["leader_id"])

    def test_create_dept_parent_not_found(self, dept_service, dept_tree_data, db_session, test_context):
        """Test creating department with non-existent parent."""
        class Request:
            parent_id = "9999"
            name = "New Dept"
            sort = 0
            leader_user_id = None

        with pytest.raises(BizError) as exc_info:
            run_async(dept_service.create_dept(Request()))

        assert exc_info.value.code == 1500

    def test_create_dept_parent_disabled(self, dept_service, dept_tree_data, db_session, test_context):
        """Test creating department under disabled parent."""
        class Request:
            parent_id = str(dept_tree_data["disabled_dept_id"])
            name = "New Dept"
            sort = 0
            leader_user_id = None

        with pytest.raises(BizError) as exc_info:
            run_async(dept_service.create_dept(Request()))

        assert exc_info.value.code == 1501

    def test_create_dept_under_system_dept(self, dept_service, dept_tree_data, db_session, test_context):
        """Test creating department under SYSTEM dept fails."""
        class Request:
            parent_id = str(dept_tree_data["system_dept_id"])
            name = "New Dept"
            sort = 0
            leader_user_id = None

        with pytest.raises(BizError) as exc_info:
            run_async(dept_service.create_dept(Request()))

        assert exc_info.value.code == 1220

    def test_create_dept_duplicate_name(self, dept_service, dept_tree_data, db_session, test_context):
        """Test creating department with duplicate name under same parent."""
        class Request:
            parent_id = "1"
            name = "Child Department 1"
            sort = 0
            leader_user_id = None

        with pytest.raises(BizError) as exc_info:
            run_async(dept_service.create_dept(Request()))

        assert exc_info.value.code == 1219


class TestDeptServiceUpdateDept:
    """Tests for DeptService.update_dept."""

    def test_update_dept_name(self, dept_service, dept_tree_data, db_session, test_context):
        """Test updating department name."""
        class Request:
            name = "Updated Name"
            sort = None
            leader_user_id = None

        result = run_async(
            dept_service.update_dept(str(dept_tree_data["child1_id"]), Request())
        )

        assert result["name"] == "Updated Name"

    def test_update_dept_sort(self, dept_service, dept_tree_data, db_session, test_context):
        """Test updating department sort."""
        class Request:
            name = None
            sort = 100
            leader_user_id = None

        result = run_async(
            dept_service.update_dept(str(dept_tree_data["child1_id"]), Request())
        )

        assert result["sort"] == 100

    def test_update_dept_leader(self, dept_service, dept_tree_data, db_session, test_context):
        """Test updating department leader."""
        class Request:
            name = None
            sort = None
            leader_user_id = str(dept_tree_data["leader_id"])

        result = run_async(
            dept_service.update_dept(str(dept_tree_data["child1_id"]), Request())
        )

        assert result["leader_user_id"] == str(dept_tree_data["leader_id"])

    def test_update_dept_remove_leader(self, dept_service, dept_tree_data, db_session, test_context):
        """Test removing department leader."""
        class Request1:
            name = None
            sort = None
            leader_user_id = str(dept_tree_data["leader_id"])

        run_async(
            dept_service.update_dept(str(dept_tree_data["child1_id"]), Request1())
        )

        class Request2:
            name = None
            sort = None
            leader_user_id = ""

        result = run_async(
            dept_service.update_dept(str(dept_tree_data["child1_id"]), Request2())
        )

        assert result["leader_user_id"] is None

    def test_update_system_dept_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test updating SYSTEM department fails."""
        class Request:
            name = "New Name"
            sort = None
            leader_user_id = None

        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.update_dept(str(dept_tree_data["system_dept_id"]), Request())
            )

        assert exc_info.value.code == 1220

    def test_update_dingtalk_dept_has_hint(self, dept_service, dept_tree_data, db_session, test_context):
        """Test updating DINGTALK department has sync override hint."""
        class Request:
            name = "Updated DingTalk Dept"
            sort = None
            leader_user_id = None

        result = run_async(
            dept_service.update_dept(str(dept_tree_data["child2_id"]), Request())
        )

        assert result["sync_override_hint"] is True

    def test_update_dept_duplicate_name(self, dept_service, dept_tree_data, db_session, test_context):
        """Test updating department with duplicate name under same parent."""
        class Request:
            name = "Child Department 2"
            sort = None
            leader_user_id = None

        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.update_dept(str(dept_tree_data["child1_id"]), Request())
            )

        assert exc_info.value.code == 1219

    def test_update_nonexistent_dept(self, dept_service, dept_tree_data, db_session, test_context):
        """Test updating non-existent department."""
        class Request:
            name = "New Name"
            sort = None
            leader_user_id = None

        with pytest.raises(BizError) as exc_info:
            run_async(dept_service.update_dept("9999", Request()))

        assert exc_info.value.code == 1504


class TestDeptServiceMoveDept:
    """Tests for DeptService.move_dept."""

    def test_move_dept_success(self, dept_service, dept_tree_data, db_session, test_context):
        """Test moving department to new parent."""
        from app.domains.sys.models import Dept

        new_parent = Dept(
            id=100,
            tenant_id=1,
            parent_id=1,
            path="/1/100/",
            name="New Parent",
            status="ENABLED",
            source="LOCAL",
        )
        db_session.add(new_parent)
        db_session.flush()

        result = run_async(
            dept_service.move_dept(str(dept_tree_data["child1_id"]), "100")
        )

        assert result["parent_id"] == "100"

    def test_move_dept_to_self_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test moving department to itself fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.move_dept(
                    str(dept_tree_data["child1_id"]),
                    str(dept_tree_data["child1_id"])
                )
            )

        assert exc_info.value.code == 1218

    def test_move_dept_to_descendant_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test moving department to its descendant fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.move_dept(
                    str(dept_tree_data["child1_id"]),
                    str(dept_tree_data["grandchild_id"])
                )
            )

        assert exc_info.value.code == 1218

    def test_move_system_dept_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test moving SYSTEM department fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.move_dept(
                    str(dept_tree_data["system_dept_id"]),
                    str(dept_tree_data["child1_id"])
                )
            )

        assert exc_info.value.code == 1220

    def test_move_dept_to_system_dept_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test moving department to SYSTEM parent fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.move_dept(
                    str(dept_tree_data["child1_id"]),
                    str(dept_tree_data["system_dept_id"])
                )
            )

        assert exc_info.value.code == 1220

    def test_move_nonexistent_dept(self, dept_service, dept_tree_data, db_session, test_context):
        """Test moving non-existent department."""
        with pytest.raises(BizError) as exc_info:
            run_async(dept_service.move_dept("9999", "1"))

        assert exc_info.value.code == 1504

    def test_move_to_nonexistent_parent(self, dept_service, dept_tree_data, db_session, test_context):
        """Test moving to non-existent parent."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.move_dept(str(dept_tree_data["child1_id"]), "9999")
            )

        assert exc_info.value.code == 1500


class TestDeptServiceUpdateStatus:
    """Tests for DeptService.update_dept_status."""

    def test_disable_dept_success(self, dept_service, dept_tree_data, db_session, test_context):
        """Test disabling department without children."""
        run_async(
            dept_service.update_dept_status(str(dept_tree_data["grandchild_id"]), "DISABLED")
        )

    def test_disable_dept_with_enabled_children_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test disabling department with enabled children fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.update_dept_status(str(dept_tree_data["child1_id"]), "DISABLED")
            )

        assert exc_info.value.code == 1502

    def test_enable_dept_success(self, dept_service, dept_tree_data, db_session, test_context):
        """Test enabling disabled department."""
        run_async(
            dept_service.update_dept_status(str(dept_tree_data["disabled_dept_id"]), "ENABLED")
        )

    def test_update_status_system_dept_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test updating status of SYSTEM department fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.update_dept_status(str(dept_tree_data["system_dept_id"]), "DISABLED")
            )

        assert exc_info.value.code == 1220

    def test_update_status_invalid_value(self, dept_service, dept_tree_data, db_session, test_context):
        """Test updating status with invalid value."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.update_dept_status(str(dept_tree_data["grandchild_id"]), "INVALID")
            )

        assert exc_info.value.code == 1001


class TestDeptServiceDeleteDept:
    """Tests for DeptService.delete_dept."""

    def test_delete_dept_success(self, dept_service, dept_tree_data, db_session, test_context):
        """Test deleting department without children or users."""
        from app.domains.sys.models import Dept

        empty_dept = Dept(
            id=200,
            tenant_id=1,
            parent_id=1,
            path="/1/200/",
            name="Empty Department",
            status="ENABLED",
            source="LOCAL",
        )
        db_session.add(empty_dept)
        db_session.flush()

        run_async(dept_service.delete_dept("200"))

    def test_delete_dept_with_children_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test deleting department with children fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(dept_service.delete_dept(str(dept_tree_data["child1_id"])))

        assert exc_info.value.code == 1502

    def test_delete_dept_with_users_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test deleting department with users fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(dept_service.delete_dept(str(dept_tree_data["grandchild_id"])))

        assert exc_info.value.code == 1502

    def test_delete_system_dept_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test deleting SYSTEM department fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(dept_service.delete_dept(str(dept_tree_data["system_dept_id"])))

        assert exc_info.value.code == 1220


class TestDeptServiceConfirmOrphan:
    """Tests for DeptService.confirm_orphan_dept."""

    def test_confirm_orphan_success(self, dept_service, dept_tree_data, db_session, test_context):
        """Test confirming orphan department."""
        run_async(
            dept_service.confirm_orphan_dept(str(dept_tree_data["orphan_dept_id"]))
        )

    def test_confirm_non_orphan_fails(self, dept_service, dept_tree_data, db_session, test_context):
        """Test confirming non-orphan department fails."""
        with pytest.raises(BizError) as exc_info:
            run_async(
                dept_service.confirm_orphan_dept(str(dept_tree_data["child1_id"]))
            )

        assert exc_info.value.code == 1001
