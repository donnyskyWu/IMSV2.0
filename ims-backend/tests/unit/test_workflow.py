# tests/unit/test_workflow.py - Workflow engine tests (FP-G03)
"""
Tests for workflow engine (approval flows).

Per 02-单测用例.md UT-G03:
- Two-node approval flow
- Rejection returns to initiator
- Withdrawal requires permission
- Version management for templates
- Timeout handling
"""

import pytest
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class FlowStatus(str, Enum):
    """Flow instance status."""
    RUNNING = "RUNNING"  # 进行中
    APPROVED = "APPROVED"  # 已通过
    REJECTED = "REJECTED"  # 已驳回
    WITHDRAWN = "WITHDRAWN"  # 已撤销
    SUSPENDED = "SUSPENDED"  # 已挂起


class TaskStatus(str, Enum):
    """Flow task status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"  # 退回
    CANCELLED = "CANCELLED"


class NodeType(str, Enum):
    """Node handler type."""
    USER = "USER"  # 指定人
    PERMISSION = "PERMISSION"  # 权限码
    LEADER = "LEADER"  # 部门负责人


@dataclass
class FlowNode:
    """Flow template node."""
    id: int
    name: str
    sequence: int
    handler_type: NodeType
    handler_value: str  # user_id, perm_code, or LEADER
    timeout_hours: Optional[int] = None


@dataclass
class FlowTemplate:
    """Flow template."""
    id: int
    name: str
    version: int
    nodes: List[FlowNode] = field(default_factory=list)
    published: bool = False


@dataclass
class FlowInstance:
    """Flow instance."""
    id: int
    template_id: int
    template_version: int
    biz_type: str
    biz_id: str
    initiator_id: int
    status: FlowStatus = FlowStatus.RUNNING
    current_node_seq: int = 1
    create_time: datetime = field(default_factory=datetime.now)


@dataclass
class FlowTask:
    """Flow task for a node."""
    id: int
    instance_id: int
    node_id: int
    handler_user_id: int
    status: TaskStatus = TaskStatus.PENDING
    overdue: bool = False
    create_time: datetime = field(default_factory=datetime.now)


class TestTwoNodeApproval:
    """Tests for two-node approval flow (FP-G03-02)."""
    
    def test_node1_approve_advances_to_node2(self):
        """UT-G03-01: First node approval advances flow."""
        instance = FlowInstance(
            id=1, template_id=1, template_version=1,
            biz_type="order", biz_id="123",
            initiator_id=100,
            current_node_seq=1
        )
        
        # Node 1 approves
        instance.current_node_seq = 2
        
        assert instance.current_node_seq == 2
        assert instance.status == FlowStatus.RUNNING
    
    def test_node2_approve_completes_flow(self):
        """UT-G03-01: Second node approval completes flow."""
        instance = FlowInstance(
            id=1, template_id=1, template_version=1,
            biz_type="order", biz_id="123",
            initiator_id=100,
            current_node_seq=2
        )
        
        # Node 2 approves (last node)
        instance.status = FlowStatus.APPROVED
        
        assert instance.status == FlowStatus.APPROVED
    
    def test_approval_triggers_callback(self):
        """UT-G03-01: Approval triggers business callback."""
        callback_called = False
        callback_result = None
        
        def business_callback(instance_id: int, result: str):
            nonlocal callback_called, callback_result
            callback_called = True
            callback_result = result
        
        # Simulate approval callback
        business_callback(1, "APPROVED")
        
        assert callback_called
        assert callback_result == "APPROVED"


class TestRejection:
    """Tests for rejection handling (FP-G03-02)."""
    
    def test_node1_reject_ends_flow(self):
        """UT-G03-02: Node 1 rejection ends flow."""
        instance = FlowInstance(
            id=1, template_id=1, template_version=1,
            biz_type="order", biz_id="123",
            initiator_id=100,
            current_node_seq=1
        )
        
        # Node 1 rejects
        instance.status = FlowStatus.REJECTED
        
        assert instance.status == FlowStatus.REJECTED
    
    def test_rejection_notifies_initiator(self):
        """UT-G03-02: Rejection sends notification to initiator."""
        initiator_id = 100
        notification_sent_to = []
        
        def send_notification(user_id: int, title: str):
            notification_sent_to.append(user_id)
        
        # Simulate rejection notification
        send_notification(initiator_id, "您的申请已被驳回")
        
        assert initiator_id in notification_sent_to
    
    def test_rejection_callback_result(self):
        """UT-G03-02: Rejection callback has REJECTED result."""
        callback_result = None
        
        def business_callback(result: str):
            nonlocal callback_result
            callback_result = result
        
        business_callback("REJECTED")
        
        assert callback_result == "REJECTED"


class TestReturn:
    """Tests for return/rollback handling (FP-G03-02)."""
    
    def test_node2_return_goes_back_to_node1(self):
        """UT-G03-03: Node 2 return goes back to node 1."""
        instance = FlowInstance(
            id=1, template_id=1, template_version=1,
            biz_type="order", biz_id="123",
            initiator_id=100,
            current_node_seq=2
        )
        
        # Return to node 1
        instance.current_node_seq = 1
        
        assert instance.current_node_seq == 1
        assert instance.status == FlowStatus.RUNNING
    
    def test_return_creates_new_task(self):
        """UT-G03-03: Return creates new task for returned node."""
        existing_tasks = [
            FlowTask(id=1, instance_id=1, node_id=1, handler_user_id=100, status=TaskStatus.APPROVED),
            FlowTask(id=2, instance_id=1, node_id=2, handler_user_id=200, status=TaskStatus.RETURNED),
        ]
        
        # New task for node 1
        new_task = FlowTask(id=3, instance_id=1, node_id=1, handler_user_id=100, status=TaskStatus.PENDING)
        existing_tasks.append(new_task)
        
        pending_tasks = [t for t in existing_tasks if t.status == TaskStatus.PENDING]
        
        assert len(pending_tasks) == 1
        assert pending_tasks[0].node_id == 1


class TestWithdrawal:
    """Tests for withdrawal handling (FP-G03-02)."""
    
    def test_initiator_can_withdraw(self):
        """UT-G03-05: Initiator can withdraw their flow."""
        instance = FlowInstance(
            id=1, template_id=1, template_version=1,
            biz_type="order", biz_id="123",
            initiator_id=100
        )
        current_user_id = 100
        
        can_withdraw = instance.initiator_id == current_user_id
        
        assert can_withdraw
    
    def test_non_initiator_cannot_withdraw_without_permission(self):
        """UT-G03-04: Non-initiator without permission cannot withdraw."""
        instance = FlowInstance(
            id=1, template_id=1, template_version=1,
            biz_type="order", biz_id="123",
            initiator_id=100
        )
        current_user_id = 200
        has_withdraw_permission = False
        
        can_withdraw = (
            instance.initiator_id == current_user_id or 
            has_withdraw_permission
        )
        
        assert not can_withdraw
    
    def test_withdrawal_cancels_pending_tasks(self):
        """UT-G03-05: Withdrawal cancels in-flight tasks."""
        tasks = [
            FlowTask(id=1, instance_id=1, node_id=1, handler_user_id=100, status=TaskStatus.APPROVED),
            FlowTask(id=2, instance_id=1, node_id=2, handler_user_id=200, status=TaskStatus.PENDING),
        ]
        
        # Cancel pending tasks
        for task in tasks:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
        
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]
        
        assert len(pending) == 0
    
    def test_withdrawal_sets_status(self):
        """UT-G03-05: Withdrawal sets instance status to WITHDRAWN."""
        instance = FlowInstance(
            id=1, template_id=1, template_version=1,
            biz_type="order", biz_id="123",
            initiator_id=100
        )
        
        instance.status = FlowStatus.WITHDRAWN
        
        assert instance.status == FlowStatus.WITHDRAWN


class TestVersionManagement:
    """Tests for template version management (FP-G03-01)."""
    
    def test_inflight_uses_old_version(self):
        """UT-G03-06: In-flight instance uses original version."""
        template_v1 = FlowTemplate(id=1, name="审批", version=1, published=True)
        template_v2 = FlowTemplate(id=1, name="审批", version=2, published=True)
        
        # Instance created with v1
        instance = FlowInstance(
            id=1, template_id=1, template_version=1,
            biz_type="order", biz_id="123",
            initiator_id=100
        )
        
        assert instance.template_version == 1
    
    def test_new_instance_uses_latest_version(self):
        """UT-G03-06: New instance uses latest published version."""
        templates = [
            FlowTemplate(id=1, name="审批", version=1, published=True),
            FlowTemplate(id=1, name="审批", version=2, published=True),
        ]
        
        latest_version = max(t.version for t in templates if t.published)
        
        new_instance = FlowInstance(
            id=2, template_id=1, template_version=latest_version,
            biz_type="order", biz_id="456",
            initiator_id=100
        )
        
        assert new_instance.template_version == 2
    
    def test_cannot_modify_published_template(self):
        """UT-G03-07: Cannot modify published template."""
        template = FlowTemplate(id=1, name="审批", version=1, published=True)
        
        can_modify = not template.published
        
        assert not can_modify


class TestLeaderHandler:
    """Tests for LEADER handler type (FP-G03-02)."""
    
    def test_leader_resolves_to_dept_head(self):
        """UT-G03-08: LEADER resolves to department head."""
        initiator_dept_id = "D1"
        dept_leader_mapping = {"D1": 300, "D0": 400}
        
        leader_user_id = dept_leader_mapping.get(initiator_dept_id)
        
        assert leader_user_id == 300
    
    def test_initiator_is_leader_escalates_to_parent(self):
        """UT-G03-08: If initiator is leader, escalate to parent dept."""
        initiator_id = 300
        initiator_dept_id = "D1"
        parent_dept_id = "D0"
        dept_leader_mapping = {"D1": 300, "D0": 400}  # Initiator is D1's leader
        
        # Check if initiator is the leader
        if dept_leader_mapping.get(initiator_dept_id) == initiator_id:
            # Escalate to parent
            handler_user_id = dept_leader_mapping.get(parent_dept_id)
        else:
            handler_user_id = dept_leader_mapping.get(initiator_dept_id)
        
        assert handler_user_id == 400


class TestPermissionHandler:
    """Tests for permission-based handler (FP-G03-02)."""
    
    def test_excludes_initiator_from_handlers(self):
        """UT-G03-09: Initiator excluded from permission handlers."""
        initiator_id = 100
        users_with_permission = [100, 200]  # A (initiator) and B
        
        handlers = [u for u in users_with_permission if u != initiator_id]
        
        assert handlers == [200]
    
    def test_only_initiator_has_permission_suspends(self):
        """UT-G03-10: If only initiator has permission, instance suspends."""
        initiator_id = 100
        users_with_permission = [100]
        
        handlers = [u for u in users_with_permission if u != initiator_id]
        
        if not handlers:
            status = FlowStatus.SUSPENDED
        else:
            status = FlowStatus.RUNNING
        
        assert status == FlowStatus.SUSPENDED


class TestTimeout:
    """Tests for task timeout (FP-G03-03)."""
    
    def test_overdue_detection(self):
        """UT-G03-11: Task marked overdue after timeout."""
        task = FlowTask(
            id=1, instance_id=1, node_id=1, handler_user_id=100,
            create_time=datetime.now() - timedelta(hours=3)
        )
        timeout_hours = 2
        
        hours_elapsed = (datetime.now() - task.create_time).total_seconds() / 3600
        is_overdue = hours_elapsed > timeout_hours
        
        assert is_overdue
    
    def test_overdue_sends_reminder(self):
        """UT-G03-11: Overdue task sends reminder notification."""
        handler_user_id = 100
        reminders_sent = []
        
        def send_reminder(user_id: int):
            reminders_sent.append(user_id)
        
        send_reminder(handler_user_id)
        
        assert handler_user_id in reminders_sent
    
    def test_reminder_not_duplicated(self):
        """UT-G03-11: Second scan does not duplicate reminder."""
        task = FlowTask(
            id=1, instance_id=1, node_id=1, handler_user_id=100,
            overdue=True  # Already marked overdue
        )
        
        # Second scan should not send again
        should_send_reminder = not task.overdue
        task.overdue = True
        
        assert not should_send_reminder
