"""B18 行动项待办字段（FP-G02-01 / Q-D6）。

Revision ID: 004_b18_todo_fields
Revises: 003_b18_meeting

ims_sys_todo 原先只在模型里，迁移链没有建表。本版本补齐整表；
若环境里已经有表，则只补待办来源字段。
"""

import sqlalchemy as sa
from alembic import op

revision = "004_b18_todo_fields"
down_revision = "003_b18_meeting"
branch_labels = None
depends_on = None

_NEW_COLUMNS = (
    ("todo_type", sa.String(20)),
    ("source_module", sa.String(50)),
    ("source_type", sa.String(64)),
    ("source_id", sa.String(64)),
    ("route", sa.String(200)),
    ("due_time", sa.DateTime()),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ims_sys_todo" not in inspector.get_table_names():
        op.create_table(
            "ims_sys_todo",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.BigInteger(), nullable=False),
            sa.Column("creator", sa.BigInteger(), nullable=True),
            sa.Column("create_time", sa.DateTime(), nullable=True),
            sa.Column("updater", sa.BigInteger(), nullable=True),
            sa.Column("update_time", sa.DateTime(), nullable=True),
            sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("assignee_user_id", sa.BigInteger(), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("event_id", sa.String(64), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
            sa.Column("todo_type", sa.String(20), nullable=True),
            sa.Column("source_module", sa.String(50), nullable=True),
            sa.Column("source_type", sa.String(64), nullable=True),
            sa.Column("source_id", sa.String(64), nullable=True),
            sa.Column("route", sa.String(200), nullable=True),
            sa.Column("due_time", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_ims_sys_todo_tenant_id", "ims_sys_todo", ["tenant_id"])
        op.create_index("ix_ims_sys_todo_assignee_user_id", "ims_sys_todo", ["assignee_user_id"])
        return

    existing = {col["name"] for col in inspector.get_columns("ims_sys_todo")}
    for name, column_type in _NEW_COLUMNS:
        if name not in existing:
            op.add_column("ims_sys_todo", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ims_sys_todo" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("ims_sys_todo")}
    for name, _column_type in reversed(_NEW_COLUMNS):
        if name in existing:
            op.drop_column("ims_sys_todo", name)
