"""B3-M03 个人工作台表结构变更

版本: v1.0
日期: 2026-10-13

变更：
1. ims_sys_todo 扩展字段：type, source_module, source_type, source_id, route, content, due_time, done_by, done_time
2. ims_sys_todo status 默认值从 OPEN 改为 PENDING，存量数据迁移
3. 新建 ims_sys_todo_assignee 表
4. ims_sys_inbox 扩展字段：event_type, source_module, route, ref_type, ref_id, read_status, read_time

Revision ID: 003_b3_workbench
Revises: 002_b1_m01_foundation
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

revision = "003_b3_workbench"
down_revision = "002_b1_m01_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """扩展表结构，创建新表，回填数据。"""
    _extend_todo_table()
    _create_todo_assignee_table()
    _extend_inbox_table()
    _migrate_todo_status()
    _backfill_todo_type()
    _backfill_todo_assignee()


def downgrade() -> None:
    """按相反顺序删除本迁移新增的表和列。"""
    op.drop_table("ims_sys_todo_assignee")
    _drop_inbox_columns()
    _drop_todo_columns()
    _rollback_todo_status()


def _extend_todo_table() -> None:
    """扩展 ims_sys_todo 表。"""
    with op.batch_alter_table("ims_sys_todo") as batch:
        batch.add_column(sa.Column("type", sa.String(30), nullable=True, comment="待办类型"))
        batch.add_column(sa.Column("source_module", sa.String(50), nullable=True, comment="来源模块"))
        batch.add_column(sa.Column("source_type", sa.String(50), nullable=True, comment="来源单据类型"))
        batch.add_column(sa.Column("source_id", sa.BigInteger, nullable=True, comment="来源单据 ID"))
        batch.add_column(sa.Column("route", sa.String(300), nullable=True, comment="跳转路由"))
        batch.add_column(sa.Column("content", sa.Text, nullable=True, comment="待办内容"))
        batch.add_column(sa.Column("due_time", sa.DateTime, nullable=True, comment="截止时间"))
        batch.add_column(sa.Column("done_by", sa.BigInteger, nullable=True, comment="处理人 user_id"))
        batch.add_column(sa.Column("done_time", sa.DateTime, nullable=True, comment="处理时间"))
        # 将 assignee_user_id 改为可空（双写策略）
        batch.alter_column("assignee_user_id", existing_type=sa.BigInteger, nullable=True)

    op.create_index(
        "idx_todo_tenant_status_due",
        "ims_sys_todo",
        ["tenant_id", "status", "due_time"],
    )


def _drop_todo_columns() -> None:
    """删除 ims_sys_todo 扩展列。"""
    op.drop_index("idx_todo_tenant_status_due", table_name="ims_sys_todo")
    with op.batch_alter_table("ims_sys_todo") as batch:
        batch.drop_column("done_time")
        batch.drop_column("done_by")
        batch.drop_column("due_time")
        batch.drop_column("content")
        batch.drop_column("route")
        batch.drop_column("source_id")
        batch.drop_column("source_type")
        batch.drop_column("source_module")
        batch.drop_column("type")
        batch.alter_column("assignee_user_id", existing_type=sa.BigInteger, nullable=False)


def _create_todo_assignee_table() -> None:
    """创建 ims_sys_todo_assignee 表。"""
    op.create_table(
        "ims_sys_todo_assignee",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False, index=True),
        sa.Column("todo_id", sa.BigInteger, nullable=False, index=True),
        sa.Column("user_id", sa.BigInteger, nullable=False, index=True),
        sa.Column("closed", sa.SmallInteger, nullable=False, default=0),
        sa.Column("closed_time", sa.DateTime, nullable=True),
        sa.Column("creator", sa.BigInteger, nullable=True),
        sa.Column("create_time", sa.DateTime, nullable=True),
        sa.Column("updater", sa.BigInteger, nullable=True),
        sa.Column("update_time", sa.DateTime, nullable=True),
        sa.Column("deleted", sa.BigInteger, nullable=False, default=0),
    )
    op.create_unique_constraint(
        "uk_todo_assignee",
        "ims_sys_todo_assignee",
        ["todo_id", "user_id", "deleted"],
    )


def _extend_inbox_table() -> None:
    """扩展 ims_sys_inbox 表。"""
    with op.batch_alter_table("ims_sys_inbox") as batch:
        batch.add_column(sa.Column("event_type", sa.String(50), nullable=True, comment="消息事件类型"))
        batch.add_column(sa.Column("source_module", sa.String(50), nullable=True, comment="来源模块"))
        batch.add_column(sa.Column("route", sa.String(300), nullable=True, comment="跳转路由"))
        batch.add_column(sa.Column("ref_type", sa.String(50), nullable=True, comment="关联业务类型"))
        batch.add_column(sa.Column("ref_id", sa.BigInteger, nullable=True, comment="关联业务 ID"))
        batch.add_column(
            sa.Column("read_status", sa.String(20), nullable=False, server_default="UNREAD", comment="已读状态")
        )
        batch.add_column(sa.Column("read_time", sa.DateTime, nullable=True, comment="已读时间"))

    op.create_index(
        "idx_inbox_user_read",
        "ims_sys_inbox",
        ["user_id", "read_status", "create_time"],
    )


def _drop_inbox_columns() -> None:
    """删除 ims_sys_inbox 扩展列。"""
    op.drop_index("idx_inbox_user_read", table_name="ims_sys_inbox")
    with op.batch_alter_table("ims_sys_inbox") as batch:
        batch.drop_column("read_time")
        batch.drop_column("read_status")
        batch.drop_column("ref_id")
        batch.drop_column("ref_type")
        batch.drop_column("route")
        batch.drop_column("source_module")
        batch.drop_column("event_type")


def _migrate_todo_status() -> None:
    """存量数据状态迁移：OPEN → PENDING。"""
    op.execute("UPDATE ims_sys_todo SET status = 'PENDING' WHERE status = 'OPEN'")


def _rollback_todo_status() -> None:
    """回滚状态迁移：PENDING → OPEN。"""
    op.execute("UPDATE ims_sys_todo SET status = 'OPEN' WHERE status = 'PENDING'")


def _backfill_todo_type() -> None:
    """回填 type 字段。存量数据来自 position_supply。"""
    # 先按标题匹配岗位相关
    op.execute("""
        UPDATE ims_sys_todo 
        SET type = 'CONFIRM', source_module = '岗位供给', route = '/ims/auth/position'
        WHERE type IS NULL AND title LIKE '%岗位%' AND deleted = 0
    """)
    # 兜底：所有剩余 NULL 行统一设为 CONFIRM
    op.execute("UPDATE ims_sys_todo SET type = 'CONFIRM' WHERE type IS NULL")


def _backfill_todo_assignee() -> None:
    """回填 todo_assignee 表。"""
    bind = op.get_bind()
    session = Session(bind=bind)

    # 延迟导入避免循环依赖
    from app.db.ids import assign_pk
    from app.domains.sys.models import TodoAssignee, TodoItem

    todos = session.query(TodoItem).filter(
        TodoItem.deleted == 0,
        TodoItem.assignee_user_id.isnot(None),
    ).all()

    for todo in todos:
        # 检查是否已存在
        existing = session.query(TodoAssignee).filter(
            TodoAssignee.todo_id == todo.id,
            TodoAssignee.user_id == todo.assignee_user_id,
            TodoAssignee.deleted == 0,
        ).first()
        if existing:
            continue

        assignee = TodoAssignee(
            tenant_id=todo.tenant_id,
            todo_id=todo.id,
            user_id=todo.assignee_user_id,
            closed=0,
            create_time=todo.create_time,
            creator=todo.creator,
            deleted=0,
        )
        assign_pk(session, assignee)
        session.add(assignee)

    session.commit()
