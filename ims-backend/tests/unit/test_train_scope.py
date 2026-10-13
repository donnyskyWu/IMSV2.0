# tests/unit/test_train_scope.py - Data scope filter tests (B21)
"""
Unit tests for training data scope filtering.

Per TK-01:
- DEPT = creator_dept_id IN dept_ids OR EXISTS(assigned user in dept_ids)
- SELF = creator == user_id OR user is assigned

P0 functions with 90% branch coverage required.
"""

import pytest
from unittest.mock import MagicMock

from app.core.context import DataScope
from app.domains.train.scope import (
    check_task_in_scope,
    get_stat_visible_depts,
    get_tenant_perm_key,
    get_user_perm_key,
)


def make_mock_ctx(
    user_id: int = 1,
    tenant_id: int = 1,
    dept_ids: list = None,
    data_scope: str = "ALL",
) -> MagicMock:
    """Create a mock RequestContext."""
    mock = MagicMock()
    mock.user_id = user_id
    mock.tenant_id = tenant_id
    mock.dept_ids = dept_ids or [1]
    mock.data_scopes = [{"scope_type": data_scope, "role_id": 1}]
    return mock


def make_mock_task(
    creator: int = 1,
    creator_dept_id: int = 1,
) -> MagicMock:
    """Create a mock TrainTask."""
    mock = MagicMock()
    mock.creator = creator
    mock.creator_dept_id = creator_dept_id
    return mock


class TestCheckTaskInScope:
    """Tests for task scope checking."""

    def test_all_scope_always_visible(self):
        """UT-B21-SCOPE-01: ALL scope sees everything."""
        ctx = make_mock_ctx(data_scope="ALL")
        task = make_mock_task(creator=999, creator_dept_id=999)
        
        assert check_task_in_scope(ctx, task, []) is True

    def test_dept_scope_creator_in_dept(self):
        """UT-B21-SCOPE-02: DEPT scope - creator in user's dept."""
        ctx = make_mock_ctx(dept_ids=[1, 2], data_scope="DEPT")
        task = make_mock_task(creator=999, creator_dept_id=1)
        
        assert check_task_in_scope(ctx, task, []) is True

    def test_dept_scope_assigned_in_dept(self):
        """UT-B21-SCOPE-03: DEPT scope - assigned user in user's dept."""
        ctx = make_mock_ctx(dept_ids=[1, 2], data_scope="DEPT")
        task = make_mock_task(creator=999, creator_dept_id=999)
        
        assert check_task_in_scope(ctx, task, [2]) is True

    def test_dept_scope_no_match(self):
        """UT-B21-SCOPE-04: DEPT scope - no dept match."""
        ctx = make_mock_ctx(dept_ids=[1, 2], data_scope="DEPT")
        task = make_mock_task(creator=999, creator_dept_id=999)
        
        assert check_task_in_scope(ctx, task, [3, 4]) is False

    def test_self_scope_creator(self):
        """UT-B21-SCOPE-05: SELF scope - user is creator."""
        ctx = make_mock_ctx(user_id=1, data_scope="SELF")
        task = make_mock_task(creator=1, creator_dept_id=999)
        
        assert check_task_in_scope(ctx, task, []) is True

    def test_self_scope_not_creator_not_assigned(self):
        """UT-B21-SCOPE-07: SELF scope - not creator, not assigned."""
        ctx = make_mock_ctx(user_id=1, data_scope="SELF")
        task = make_mock_task(creator=999, creator_dept_id=999)
        
        assert check_task_in_scope(ctx, task, []) is False


class TestGetStatVisibleDepts:
    """Tests for statistics scope filtering."""

    def test_all_no_dept_id(self):
        """UT-B21-SCOPE-08: ALL without deptId returns None (all depts)."""
        ctx = make_mock_ctx(data_scope="ALL")
        
        depts, is_self = get_stat_visible_depts(ctx, None)
        
        assert depts is None
        assert is_self is False

    def test_all_with_dept_id(self):
        """UT-B21-SCOPE-09: ALL with deptId returns that dept."""
        ctx = make_mock_ctx(data_scope="ALL")
        
        depts, is_self = get_stat_visible_depts(ctx, 5)
        
        assert depts == [5]
        assert is_self is False

    def test_dept_no_dept_id(self):
        """UT-B21-SCOPE-10: DEPT without deptId returns user's depts."""
        ctx = make_mock_ctx(dept_ids=[1, 2, 3], data_scope="DEPT")
        
        depts, is_self = get_stat_visible_depts(ctx, None)
        
        assert set(depts) == {1, 2, 3}
        assert is_self is False

    def test_dept_with_own_dept_id(self):
        """UT-B21-SCOPE-11: DEPT with own deptId returns that dept."""
        ctx = make_mock_ctx(dept_ids=[1, 2, 3], data_scope="DEPT")
        
        depts, is_self = get_stat_visible_depts(ctx, 2)
        
        assert depts == [2]
        assert is_self is False

    def test_dept_with_other_dept_id(self):
        """UT-B21-SCOPE-12: DEPT with other deptId returns empty (E2E-B21-38)."""
        ctx = make_mock_ctx(dept_ids=[1, 2, 3], data_scope="DEPT")
        
        depts, is_self = get_stat_visible_depts(ctx, 999)
        
        assert depts == []
        assert is_self is False

    def test_self_scope(self):
        """UT-B21-SCOPE-13: SELF returns is_self=True."""
        ctx = make_mock_ctx(data_scope="SELF")
        
        depts, is_self = get_stat_visible_depts(ctx, 5)
        
        assert depts is None
        assert is_self is True

    def test_dept_empty_dept_ids(self):
        """DEPT with empty dept_ids returns empty."""
        ctx = make_mock_ctx(dept_ids=[], data_scope="DEPT")
        
        depts, is_self = get_stat_visible_depts(ctx, None)
        
        assert depts == []
        assert is_self is False


class TestPermVersionKeys:
    """Tests for permission version key format."""

    def test_user_perm_key_format(self):
        """UT-B21-SESSION-03: User perm key format correct."""
        assert get_user_perm_key(123) == "ims:perm_ver:u:123"
        assert get_user_perm_key(1) == "ims:perm_ver:u:1"

    def test_tenant_perm_key_format(self):
        """Tenant perm key format correct."""
        assert get_tenant_perm_key(1) == "ims:perm_ver:t:1"
        assert get_tenant_perm_key(456) == "ims:perm_ver:t:456"
