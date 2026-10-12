"""B1-M01 PR1 种子与迁移基础表（FP-B1-BG-08 / 01 §0.5）

版本: v1.0
日期: 2026-10-12

只加不减：用户工号、用户角色供给列、对账批次扩展列，以及岗位规则和同步事件相关新表。
不包含登录、钉钉回调、组织同步、岗位供给的业务逻辑。

对账批次沿用 B0a 已落地的 ims_sys_org_sync_batch，不另建 ims_auth_org_sync_batch。
Revision ID: 002_b1_m01_foundation
Revises: 001_initial
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

revision = "002_b1_m01_foundation"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """加列、建表，再做幂等回填。"""
    _add_user_columns()
    _add_user_role_columns()
    _add_batch_columns()
    _create_seed_apply()
    _create_position_tables()
    _create_sync_tables()
    _run_backfill()


def downgrade() -> None:
    """按相反顺序删掉本迁移新增的表和列。"""
    op.drop_table("ims_auth_org_sync_batch_item")
    op.drop_table("ims_auth_org_sync_event_attempt")
    op.drop_table("ims_auth_org_sync_event")
    op.drop_table("ims_auth_position_rule_version")
    op.drop_table("ims_auth_position_rule_role")
    op.drop_table("ims_auth_position_role_rule")
    op.drop_table("ims_sys_seed_apply")
    _drop_batch_columns()
    _drop_user_role_columns()
    _drop_user_columns()


def _add_user_columns() -> None:
    with op.batch_alter_table("ims_sys_user") as batch:
        batch.add_column(sa.Column("emp_no", sa.String(64), nullable=True, comment="工号"))
    op.create_index("idx_user_emp_no", "ims_sys_user", ["tenant_id", "emp_no"])


def _drop_user_columns() -> None:
    op.drop_index("idx_user_emp_no", table_name="ims_sys_user")
    with op.batch_alter_table("ims_sys_user") as batch:
        batch.drop_column("emp_no")


def _add_user_role_columns() -> None:
    with op.batch_alter_table("ims_sys_user_role") as batch:
        batch.add_column(sa.Column("rule_id", sa.BigInteger(), nullable=True, comment="授予来源规则"))
        batch.add_column(sa.Column("rule_version", sa.Integer(), nullable=True, comment="授予时的规则版本"))
        batch.add_column(sa.Column("revoke_at", sa.DateTime(), nullable=True, comment="调岗缓冲到期回收时间"))
    op.create_index("idx_user_role_rule", "ims_sys_user_role", ["rule_id"])


def _drop_user_role_columns() -> None:
    op.drop_index("idx_user_role_rule", table_name="ims_sys_user_role")
    with op.batch_alter_table("ims_sys_user_role") as batch:
        batch.drop_column("revoke_at")
        batch.drop_column("rule_version")
        batch.drop_column("rule_id")


def _add_batch_columns() -> None:
    with op.batch_alter_table("ims_sys_org_sync_batch") as batch:
        batch.add_column(sa.Column("trigger_type", sa.String(20), nullable=True, comment="SCHEDULE/MANUAL"))
        batch.add_column(sa.Column("operator_id", sa.BigInteger(), nullable=True, comment="手动对账操作人"))
        batch.add_column(
            sa.Column("diff_count", sa.Integer(), nullable=False, server_default="0", comment="差异数")
        )
        batch.add_column(
            sa.Column("fixed_count", sa.Integer(), nullable=False, server_default="0", comment="修正数")
        )
        batch.add_column(sa.Column("fail_reason", sa.Text(), nullable=True, comment="失败原因"))


def _drop_batch_columns() -> None:
    with op.batch_alter_table("ims_sys_org_sync_batch") as batch:
        batch.drop_column("fail_reason")
        batch.drop_column("fixed_count")
        batch.drop_column("diff_count")
        batch.drop_column("operator_id")
        batch.drop_column("trigger_type")


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
    ]


def _create_seed_apply() -> None:
    op.create_table(
        "ims_sys_seed_apply",
        *_audit_columns(),
        sa.Column("seed_key", sa.String(200), nullable=False, comment="种子项键"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seed_key", "deleted", name="uk_seed_apply"),
    )


def _create_position_tables() -> None:
    op.create_table(
        "ims_auth_position_role_rule",
        *_audit_columns(),
        sa.Column("position_code", sa.String(50), nullable=False, comment="岗位字典值"),
        sa.Column("role_id", sa.BigInteger(), nullable=False, comment="主角色"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ENABLED"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rule_name", sa.String(64), nullable=True, comment="规则名称"),
        sa.Column("description", sa.String(200), nullable=True, comment="说明"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_position_rule_code", "ims_auth_position_role_rule", ["position_code"])
    op.create_index("idx_position_rule_role", "ims_auth_position_role_rule", ["role_id"])

    op.create_table(
        "ims_auth_position_rule_role",
        *_audit_columns(),
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("role_type", sa.String(20), nullable=False, comment="MAIN/EXTRA"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "rule_id", "role_id", "deleted", name="uk_position_rule_role"
        ),
    )
    op.create_index("ix_ims_auth_position_rule_role_rule_id", "ims_auth_position_rule_role", ["rule_id"])
    op.create_index("ix_ims_auth_position_rule_role_role_id", "ims_auth_position_rule_role", ["role_id"])

    op.create_table(
        "ims_auth_position_rule_version",
        *_audit_columns(),
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rule_name", sa.String(64), nullable=True),
        sa.Column("main_role_id", sa.BigInteger(), nullable=True),
        sa.Column("extra_role_ids", sa.Text(), nullable=True, comment="附加角色 ID 的 JSON 数组"),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("change_type", sa.String(20), nullable=True),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "rule_id", "version", "deleted", name="uk_position_rule_version"
        ),
    )
    op.create_index(
        "ix_ims_auth_position_rule_version_rule_id",
        "ims_auth_position_rule_version",
        ["rule_id"],
    )


def _create_sync_tables() -> None:
    op.create_table(
        "ims_auth_org_sync_event",
        *_audit_columns(),
        sa.Column("event_id", sa.String(128), nullable=False, comment="事件业务 ID"),
        sa.Column("event_type", sa.String(64), nullable=True),
        sa.Column("event_time", sa.DateTime(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("biz_type", sa.String(32), nullable=True),
        sa.Column("subject_user_id", sa.BigInteger(), nullable=True),
        sa.Column("subject_name", sa.String(100), nullable=True),
        sa.Column("dept_id", sa.BigInteger(), nullable=True),
        sa.Column("before_dept_names", sa.String(500), nullable=True),
        sa.Column("after_dept_names", sa.String(500), nullable=True),
        sa.Column("received_time", sa.DateTime(), nullable=True),
        sa.Column("processed_time", sa.DateTime(), nullable=True),
        sa.Column("delay_seconds", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "event_id", "deleted", name="uk_org_sync_event"),
    )
    op.create_index("idx_org_sync_event_dept", "ims_auth_org_sync_event", ["dept_id"])
    op.create_index("idx_org_sync_event_status", "ims_auth_org_sync_event", ["status"])
    op.create_index("idx_org_sync_event_time", "ims_auth_org_sync_event", ["event_time"])

    op.create_table(
        "ims_auth_org_sync_event_attempt",
        *_audit_columns(),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(20), nullable=False, comment="AUTO/RETRY/REPLAY"),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("result", sa.String(20), nullable=True),
        sa.Column("error_code", sa.String(20), nullable=True),
        sa.Column("error_msg", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ims_auth_org_sync_event_attempt_event_id",
        "ims_auth_org_sync_event_attempt",
        ["event_id"],
    )

    op.create_table(
        "ims_auth_org_sync_batch_item",
        *_audit_columns(),
        sa.Column("batch_id", sa.BigInteger(), nullable=False),
        sa.Column("object_type", sa.String(20), nullable=False, comment="DEPT/USER/POSITION"),
        sa.Column("object_id", sa.String(64), nullable=True),
        sa.Column("object_name", sa.String(100), nullable=True),
        sa.Column("dept_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(32), nullable=True),
        sa.Column("before_value", sa.Text(), nullable=True),
        sa.Column("after_value", sa.Text(), nullable=True),
        sa.Column("result", sa.String(20), nullable=True, comment="FIXED/FAILED/NOTICE"),
        sa.Column("error_msg", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ims_auth_org_sync_batch_item_batch_id", "ims_auth_org_sync_batch_item", ["batch_id"])
    op.create_index("ix_ims_auth_org_sync_batch_item_dept_id", "ims_auth_org_sync_batch_item", ["dept_id"])


def _run_backfill() -> None:
    """在同一连接上回填。不单独 commit，交给 Alembic 事务。"""
    from app.services.b1_schema_backfill import backfill_b1_foundations

    session = Session(bind=op.get_bind())
    backfill_b1_foundations(session)
    session.flush()
    session.expunge_all()
