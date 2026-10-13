#!/usr/bin/env python3
"""
B3 个人工作台 E2E 造数脚本

依据: 个人工作台-实现理解 §4.4 BG-05

为 E2E 测试创建待办和消息数据：
- test_admin: 管理员，有多种类型待办和消息
- test_yg: 员工，有部分待办（用于关闭测试）
- test_sysro: 只读用户，仅工作台菜单
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.context import ctx_set, ctx
from app.db.session import SessionLocal
from app.domains.sys.models import User, TodoItem, TodoAssignee, InboxMessage
from app.db.ids import assign_pk
from app.services.todo import TodoType, TodoStatus


def get_user_by_username(session, username: str) -> User:
    """根据用户名获取用户。"""
    user = session.query(User).filter(User.username == username, User.deleted == 0).first()
    if not user:
        raise ValueError(f"User not found: {username}")
    return user


def create_todo(
    session,
    *,
    user_id: int,
    tenant_id: int,
    todo_type: str,
    title: str,
    source_module: str = "E2E测试",
    source_type: str = "e2e_test",
    source_id: int,
    route: str = None,
    content: str = None,
    due_time: datetime = None,
    status: str = TodoStatus.PENDING,
) -> TodoItem:
    """创建待办。"""
    todo = TodoItem(
        tenant_id=tenant_id,
        type=todo_type,
        source_module=source_module,
        source_type=source_type,
        source_id=source_id,
        title=title,
        route=route,
        content=content,
        due_time=due_time,
        status=status,
        assignee_user_id=user_id,
    )
    assign_pk(session, todo)
    session.add(todo)
    session.flush()

    assignee = TodoAssignee(
        tenant_id=tenant_id,
        todo_id=todo.id,
        user_id=user_id,
        closed=0,
    )
    assign_pk(session, assignee)
    session.add(assignee)

    return todo


def create_message(
    session,
    *,
    user_id: int,
    tenant_id: int,
    title: str,
    body: str,
    event_type: str = "e2e_test",
    source_module: str = "E2E测试",
    route: str = None,
    ref_type: str = None,
    ref_id: int = None,
    read_status: str = "UNREAD",
) -> InboxMessage:
    """创建消息。"""
    message = InboxMessage(
        tenant_id=tenant_id,
        user_id=user_id,
        title=title,
        body=body,
        event_type=event_type,
        source_module=source_module,
        route=route,
        ref_type=ref_type,
        ref_id=ref_id,
        read_status=read_status,
    )
    assign_pk(session, message)
    session.add(message)
    return message


def seed_b3_data():
    """创建 B3 E2E 测试数据。"""
    session = SessionLocal()
    try:
        admin = get_user_by_username(session, "test_admin")
        ctx_set(user_id=admin.id, tenant_id=admin.tenant_id)

        tenant_id = admin.tenant_id
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        next_week = now + timedelta(days=7)

        source_id_counter = 90000

        print("Creating todos for test_admin...")

        create_todo(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            todo_type=TodoType.APPROVAL,
            title="审批-订单审批#001",
            route="/ims/workbench",
            source_id=source_id_counter,
            due_time=tomorrow,
        )
        source_id_counter += 1

        create_todo(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            todo_type=TodoType.APPROVAL,
            title="审批-费用报销#002",
            source_id=source_id_counter,
            due_time=yesterday,
        )
        source_id_counter += 1

        create_todo(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            todo_type=TodoType.RETURN,
            title="归还-资产归还#001",
            route="/ims/workbench",
            source_id=source_id_counter,
            due_time=next_week,
        )
        source_id_counter += 1

        create_todo(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            todo_type=TodoType.REVIEW,
            title="审核-合同审核#001",
            source_id=source_id_counter,
        )
        source_id_counter += 1

        create_todo(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            todo_type=TodoType.CONFIRM,
            title="确认-资产领用确认#001",
            route="/ims/workbench",
            source_id=source_id_counter,
            due_time=tomorrow,
        )
        source_id_counter += 1

        create_todo(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            todo_type=TodoType.WARNING,
            title="预警-库存预警#001",
            content="库存数量低于安全库存",
            source_id=source_id_counter,
        )
        source_id_counter += 1

        create_todo(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            todo_type=TodoType.ALERT,
            title="告警-系统告警#001",
            content="CPU 使用率超过 90%",
            source_id=source_id_counter,
        )
        source_id_counter += 1

        print("Creating messages for test_admin...")

        create_message(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            title="订单审批通过",
            body="您提交的订单 ORD-2026-001 已审批通过",
            route="/ims/workbench",
        )

        create_message(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            title="资产领用申请已提交",
            body="您的资产领用申请 AST-2026-001 已提交，等待审批",
        )

        create_message(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            title="系统维护通知",
            body="系统将于今晚 22:00-24:00 进行维护",
            read_status="READ",
        )

        create_message(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            title="库存预警通知",
            body="物品 A001 库存已低于安全库存",
        )

        create_message(
            session,
            user_id=admin.id,
            tenant_id=tenant_id,
            title="流程超时提醒",
            body="您的报销申请 REI-2026-001 已超时，请尽快处理",
        )

        yg = get_user_by_username(session, "test_yg")
        print("Creating todos for test_yg...")

        create_todo(
            session,
            user_id=yg.id,
            tenant_id=tenant_id,
            todo_type=TodoType.CONFIRM,
            title="确认-test_yg领用确认#001",
            route="/ims/workbench",
            source_id=source_id_counter,
        )
        source_id_counter += 1

        create_todo(
            session,
            user_id=yg.id,
            tenant_id=tenant_id,
            todo_type=TodoType.CONFIRM,
            title="确认-test_yg领用确认#002",
            source_id=source_id_counter,
        )
        source_id_counter += 1

        create_message(
            session,
            user_id=yg.id,
            tenant_id=tenant_id,
            title="test_yg 的消息",
            body="这是 test_yg 的站内消息",
        )

        try:
            sysro = get_user_by_username(session, "test_sysro")
            print("Creating messages for test_sysro...")

            create_message(
                session,
                user_id=sysro.id,
                tenant_id=tenant_id,
                title="只读用户通知",
                body="您已被分配为只读用户",
            )
        except ValueError:
            print("test_sysro not found, skipping...")

        session.commit()
        print("B3 E2E seed data created successfully!")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_b3_data()
