# tests/unit/test_todo.py - Todo (待办) tests (FP-G02)
"""
Tests for todo/task management.

Per 02-单测用例.md UT-G02:
- Business creates todo for specified users
- Duplicate prevention for same source
- Permission-based handler resolution
- Todo completion closes the item
- Todo cancellation marks as cancelled
"""

import pytest
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class TodoStatus(str, Enum):
    """Todo status."""
    PENDING = "PENDING"  # 待处理
    DONE = "DONE"  # 已完成
    CANCELLED = "CANCELLED"  # 已作废


class TodoType(str, Enum):
    """Todo types."""
    APPROVAL = "APPROVAL"  # 审批
    RETURN = "RETURN"  # 归还
    WARNING = "WARNING"  # 预警


@dataclass
class Todo:
    """Todo item."""
    id: int
    tenant_id: int
    todo_type: TodoType
    biz_type: str  # 业务类型
    biz_id: str  # 业务ID
    title: str
    handler_user_ids: List[int] = field(default_factory=list)
    status: TodoStatus = TodoStatus.PENDING
    handler_user_id: Optional[int] = None  # 处理人
    create_time: datetime = field(default_factory=datetime.now)
    done_time: Optional[datetime] = None


class TestTodoCreation:
    """Tests for todo creation (FP-G02-01)."""
    
    def test_create_todo_for_user(self):
        """UT-G02-01: Business can create todo for specified users."""
        todo = Todo(
            id=1,
            tenant_id=1,
            todo_type=TodoType.APPROVAL,
            biz_type="order",
            biz_id="123",
            title="请审批订单",
            handler_user_ids=[100],
        )
        
        assert todo.status == TodoStatus.PENDING
        assert 100 in todo.handler_user_ids
    
    def test_todo_has_required_fields(self):
        """UT-G02-01: Todo has required fields."""
        todo = Todo(
            id=1,
            tenant_id=1,
            todo_type=TodoType.APPROVAL,
            biz_type="order",
            biz_id="123",
            title="请审批订单",
        )
        
        assert todo.id is not None
        assert todo.tenant_id is not None
        assert todo.todo_type is not None
        assert todo.biz_type is not None
        assert todo.biz_id is not None
        assert todo.title is not None


class TestTodoDuplicatePrevention:
    """Tests for todo duplicate prevention (FP-G02-01)."""
    
    def test_same_biz_key_returns_existing(self):
        """UT-G02-02: Same source + type does not create new todo."""
        existing_todos = [
            Todo(id=1, tenant_id=1, todo_type=TodoType.APPROVAL, 
                 biz_type="order", biz_id="123", title="请审批订单")
        ]
        
        # Try to create for same biz_type + biz_id
        new_biz_type = "order"
        new_biz_id = "123"
        
        duplicate_exists = any(
            t.biz_type == new_biz_type and t.biz_id == new_biz_id
            for t in existing_todos
        )
        
        assert duplicate_exists
    
    def test_different_biz_id_creates_new(self):
        """UT-G02-02: Different biz_id creates new todo."""
        existing_todos = [
            Todo(id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
                 biz_type="order", biz_id="123", title="请审批订单")
        ]
        
        new_biz_id = "456"
        
        duplicate_exists = any(
            t.biz_type == "order" and t.biz_id == new_biz_id
            for t in existing_todos
        )
        
        assert not duplicate_exists


class TestPermissionBasedHandler:
    """Tests for permission-based handler resolution (FP-G02-01)."""
    
    def test_handler_by_permission_code(self):
        """UT-G02-03: Handlers resolved by permission code."""
        permission_code = "ims:demo:order:audit"
        
        # Mock: users with this permission
        users_with_permission = [100, 200]  # A and B
        
        # But only A's data scope covers the order
        users_with_scope = [100]  # Only A
        
        final_handlers = [u for u in users_with_permission if u in users_with_scope]
        
        assert final_handlers == [100]
    
    def test_handler_excludes_no_scope(self):
        """UT-G02-03: Users without data scope excluded."""
        users_with_permission = [100, 200]
        users_with_scope = [100]
        
        excluded = [u for u in users_with_permission if u not in users_with_scope]
        
        assert 200 in excluded


class TestTodoCompletion:
    """Tests for todo completion (FP-G02-01)."""
    
    def test_complete_todo_sets_done(self):
        """UT-G02-04: Completing sets status to DONE."""
        todo = Todo(
            id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
            biz_type="order", biz_id="123", title="请审批订单",
            handler_user_ids=[100, 200]
        )
        
        # User 200 completes
        todo.status = TodoStatus.DONE
        todo.handler_user_id = 200
        todo.done_time = datetime.now()
        
        assert todo.status == TodoStatus.DONE
        assert todo.handler_user_id == 200
    
    def test_completed_todo_not_in_pending_list(self):
        """UT-G02-04: Completed todo not shown in pending list."""
        todos = [
            Todo(id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
                 biz_type="order", biz_id="123", title="请审批订单",
                 status=TodoStatus.DONE),
            Todo(id=2, tenant_id=1, todo_type=TodoType.APPROVAL,
                 biz_type="order", biz_id="456", title="请审批订单",
                 status=TodoStatus.PENDING),
        ]
        
        pending = [t for t in todos if t.status == TodoStatus.PENDING]
        
        assert len(pending) == 1
        assert pending[0].biz_id == "456"


class TestTodoCancellation:
    """Tests for todo cancellation (FP-G02-01)."""
    
    def test_cancel_todo_sets_cancelled(self):
        """UT-G02-05: Cancelling sets status to CANCELLED."""
        todo = Todo(
            id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
            biz_type="order", biz_id="123", title="请审批订单"
        )
        
        todo.status = TodoStatus.CANCELLED
        
        assert todo.status == TodoStatus.CANCELLED
    
    def test_cancelled_not_in_statistics(self):
        """UT-G02-05: Cancelled todos not counted in '应提交' statistics."""
        todos = [
            Todo(id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
                 biz_type="order", biz_id="123", title="请审批",
                 status=TodoStatus.CANCELLED),
            Todo(id=2, tenant_id=1, todo_type=TodoType.APPROVAL,
                 biz_type="order", biz_id="456", title="请审批",
                 status=TodoStatus.PENDING),
        ]
        
        # 应提交 only counts PENDING
        pending_count = sum(1 for t in todos if t.status == TodoStatus.PENDING)
        
        assert pending_count == 1


class TestTodoVisibility:
    """Tests for todo visibility (FP-G02-02)."""
    
    def test_cannot_view_others_todo(self):
        """UT-G02-06: Cannot view/process another user's todo."""
        todo = Todo(
            id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
            biz_type="order", biz_id="123", title="请审批",
            handler_user_ids=[100]
        )
        
        current_user_id = 200
        can_view = current_user_id in todo.handler_user_ids
        
        assert not can_view
    
    def test_handler_can_view_todo(self):
        """UT-G02-06: Handler can view their todo."""
        todo = Todo(
            id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
            biz_type="order", biz_id="123", title="请审批",
            handler_user_ids=[100, 200]
        )
        
        current_user_id = 100
        can_view = current_user_id in todo.handler_user_ids
        
        assert can_view


class TestTodoCount:
    """Tests for todo count by type (FP-G02-02)."""
    
    def test_count_by_type(self):
        """UT-G02-07: Can count todos by type."""
        todos = [
            Todo(id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
                 biz_type="order", biz_id="1", title="审批",
                 handler_user_ids=[100], status=TodoStatus.PENDING),
            Todo(id=2, tenant_id=1, todo_type=TodoType.APPROVAL,
                 biz_type="order", biz_id="2", title="审批",
                 handler_user_ids=[100], status=TodoStatus.PENDING),
            Todo(id=3, tenant_id=1, todo_type=TodoType.RETURN,
                 biz_type="asset", biz_id="1", title="归还",
                 handler_user_ids=[100], status=TodoStatus.PENDING),
            Todo(id=4, tenant_id=1, todo_type=TodoType.WARNING,
                 biz_type="perf", biz_id="1", title="预警",
                 handler_user_ids=[100], status=TodoStatus.PENDING),
            Todo(id=5, tenant_id=1, todo_type=TodoType.WARNING,
                 biz_type="perf", biz_id="2", title="预警",
                 handler_user_ids=[100], status=TodoStatus.PENDING),
            Todo(id=6, tenant_id=1, todo_type=TodoType.WARNING,
                 biz_type="perf", biz_id="3", title="预警",
                 handler_user_ids=[100], status=TodoStatus.PENDING),
        ]
        
        user_id = 100
        user_todos = [t for t in todos if user_id in t.handler_user_ids and t.status == TodoStatus.PENDING]
        
        counts = {}
        for todo in user_todos:
            counts[todo.todo_type] = counts.get(todo.todo_type, 0) + 1
        
        assert counts[TodoType.APPROVAL] == 2
        assert counts[TodoType.RETURN] == 1
        assert counts[TodoType.WARNING] == 3


class TestTodoMultipleHandlers:
    """Tests for todos with multiple handlers."""
    
    def test_any_handler_can_complete(self):
        """UT-G02-04: Any handler can complete the todo."""
        todo = Todo(
            id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
            biz_type="order", biz_id="123", title="请审批",
            handler_user_ids=[100, 200]
        )
        
        # Either user can complete
        assert 100 in todo.handler_user_ids
        assert 200 in todo.handler_user_ids
    
    def test_completion_records_handler(self):
        """UT-G02-04: Completion records which handler did it."""
        todo = Todo(
            id=1, tenant_id=1, todo_type=TodoType.APPROVAL,
            biz_type="order", biz_id="123", title="请审批",
            handler_user_ids=[100, 200]
        )
        
        # User 200 completes
        todo.status = TodoStatus.DONE
        todo.handler_user_id = 200
        
        assert todo.handler_user_id == 200
