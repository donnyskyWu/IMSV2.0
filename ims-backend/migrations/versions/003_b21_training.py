"""B21 Training Management Tables

Revision ID: 003_b21_training
Revises: 002_b1_m01_foundation
Create Date: 2026-10-13

8 tables per 00-工作包.md §0.5:
- ims_train_material_cate
- ims_train_material
- ims_train_material_version
- ims_train_task
- ims_train_task_record
- ims_train_study_log
- ims_train_stat_daily
- ims_train_dept_alert
"""
from alembic import op
import sqlalchemy as sa


revision = "003_b21_training"
down_revision = "002_b1_m01_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ims_train_material_cate
    op.create_table(
        "ims_train_material_cate",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("position_code", sa.String(50), nullable=True),
        sa.Column("cate_name", sa.String(64), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "parent_id", "cate_name", "deleted", name="uk_train_cate"),
        sa.Index("idx_train_cate_parent", "parent_id"),
        sa.Index("idx_train_cate_position", "position_code"),
    )

    # ims_train_material
    op.create_table(
        "ims_train_material",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("material_no", sa.String(20), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("cate_id", sa.BigInteger(), nullable=False),
        sa.Column("material_type", sa.String(20), nullable=False),
        sa.Column("file_key", sa.String(300), nullable=True),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column("position_codes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'DRAFT'"),
        sa.Column("convert_status", sa.String(20), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("uploader_user_id", sa.BigInteger(), nullable=True),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "material_no", "deleted", name="uk_train_mat_no"),
        sa.Index("idx_train_mat_cate", "cate_id"),
        sa.Index("idx_train_mat_status", "status"),
    )

    # ims_train_material_version
    op.create_table(
        "ims_train_material_version",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("material_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(128), nullable=True),
        sa.Column("file_key", sa.String(300), nullable=True),
        sa.Column("pdf_key", sa.String(300), nullable=True),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("editor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "material_id", "version", "deleted", name="uk_mat_version"),
        sa.Index("idx_mat_version_material", "material_id"),
    )

    # ims_train_task
    op.create_table(
        "ims_train_task",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("task_no", sa.String(20), nullable=False),
        sa.Column("task_name", sa.String(128), nullable=False),
        sa.Column("material_ids", sa.Text(), nullable=True),
        sa.Column("assign_scope", sa.String(20), nullable=False),
        sa.Column("deadline", sa.DateTime(), nullable=False),
        sa.Column("confirm_type", sa.String(20), nullable=False),
        sa.Column("required_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quiz", sa.Text(), nullable=True),
        sa.Column("pass_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="'IN_PROGRESS'"),
        sa.Column("source", sa.String(20), nullable=False, server_default="'MANUAL'"),
        sa.Column("source_position_code", sa.String(50), nullable=True),
        sa.Column("client_token", sa.String(64), nullable=True),
        sa.Column("creator_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "task_no", "deleted", name="uk_train_task_no"),
        sa.UniqueConstraint("tenant_id", "client_token", "deleted", name="uk_train_task_token"),
        sa.Index("idx_train_task_status", "status"),
        sa.Index("idx_train_task_creator_dept", "creator_dept_id"),
    )

    # ims_train_task_record
    op.create_table(
        "ims_train_task_record",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("progress", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("material_progress", sa.Text(), nullable=True),
        sa.Column("effective_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confirm_status", sa.String(20), nullable=False, server_default="'NOT_CONFIRMED'"),
        sa.Column("confirm_score", sa.Integer(), nullable=True),
        sa.Column("quiz_draft", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("is_overdue", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("todo_id", sa.BigInteger(), nullable=True),
        sa.Column("remind_due_at", sa.DateTime(), nullable=True),
        sa.Column("remind_overdue_at", sa.DateTime(), nullable=True),
        sa.Column("user_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "task_id", "user_id", "deleted", name="uk_train_record"),
        sa.Index("idx_train_record_task", "task_id"),
        sa.Index("idx_train_record_user", "user_id"),
        sa.Index("idx_train_record_user_dept", "user_dept_id"),
        sa.Index("idx_train_record_confirm", "confirm_status"),
    )

    # ims_train_study_log
    op.create_table(
        "ims_train_study_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("material_id", sa.BigInteger(), nullable=False),
        sa.Column("stat_date", sa.String(10), nullable=False),
        sa.Column("effective_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watched_intervals", sa.Text(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("last_position", sa.Integer(), nullable=True),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "record_id", "material_id", "stat_date", "deleted", name="uk_study_log"),
        sa.Index("idx_study_log_record", "record_id"),
        sa.Index("idx_study_log_material", "material_id"),
    )

    # ims_train_stat_daily
    op.create_table(
        "ims_train_stat_daily",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("stat_date", sa.String(10), nullable=False),
        sa.Column("dept_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finished_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overdue_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_duration_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finish_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_duration_minutes", sa.Numeric(8, 2), nullable=True),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "stat_date", "dept_id", name="uk_train_stat"),
        sa.Index("idx_train_stat_date", "stat_date"),
        sa.Index("idx_train_stat_dept", "dept_id"),
    )

    # ims_train_dept_alert
    op.create_table(
        "ims_train_dept_alert",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("dept_id", sa.BigInteger(), nullable=False),
        sa.Column("week_start", sa.String(10), nullable=False),
        sa.Column("notified_at", sa.DateTime(), nullable=False),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "dept_id", "week_start", name="uk_dept_alert"),
        sa.Index("idx_dept_alert_week", "week_start"),
    )

    # Dictionary seeds for training module
    # Use dialect-specific syntax for UPSERT
    dialect = op.get_bind().dialect.name

    if dialect == "sqlite":
        op.execute("""
            INSERT OR IGNORE INTO ims_sys_dict_type (id, tenant_id, dict_type, name, status, deleted)
            VALUES
                (901, 1, 'dict_train_material_type', '培训资料类型', 'ENABLED', 0),
                (902, 1, 'dict_train_material_status', '培训资料状态', 'ENABLED', 0),
                (903, 1, 'dict_train_task_status', '学习任务状态', 'ENABLED', 0),
                (904, 1, 'dict_train_confirm_type', '确认方式', 'ENABLED', 0),
                (905, 1, 'dict_train_assign_scope', '指派范围', 'ENABLED', 0)
        """)

        op.execute("""
            INSERT OR IGNORE INTO ims_sys_dict_data (id, tenant_id, dict_type, dict_value, dict_label, color_type, sort, status, is_builtin, deleted)
            VALUES
                (9001, 1, 'dict_train_material_type', 'DOC', '文档', 'primary', 1, 'ENABLED', 1, 0),
                (9002, 1, 'dict_train_material_type', 'VIDEO', '视频', 'success', 2, 'ENABLED', 1, 0),
                (9003, 1, 'dict_train_material_type', 'LINK', '外链', 'info', 3, 'ENABLED', 1, 0),
                (9004, 1, 'dict_train_material_status', 'DRAFT', '草稿', 'neutral', 1, 'ENABLED', 1, 0),
                (9005, 1, 'dict_train_material_status', 'PUBLISHED', '已发布', 'success', 2, 'ENABLED', 1, 0),
                (9006, 1, 'dict_train_material_status', 'OFFLINE', '已下架', 'danger', 3, 'ENABLED', 1, 0),
                (9007, 1, 'dict_train_task_status', 'IN_PROGRESS', '进行中', 'primary', 1, 'ENABLED', 1, 0),
                (9008, 1, 'dict_train_task_status', 'FINISHED', '已结束', 'neutral', 2, 'ENABLED', 1, 0),
                (9009, 1, 'dict_train_confirm_type', 'DURATION', '学时达标', 'primary', 1, 'ENABLED', 1, 0),
                (9010, 1, 'dict_train_confirm_type', 'QUIZ', '自测问卷', 'success', 2, 'ENABLED', 1, 0),
                (9011, 1, 'dict_train_assign_scope', 'BY_USER', '按人', 'primary', 1, 'ENABLED', 1, 0),
                (9012, 1, 'dict_train_assign_scope', 'BY_POSITION', '按岗位', 'success', 2, 'ENABLED', 1, 0)
        """)
    else:
        op.execute("""
            INSERT IGNORE INTO ims_sys_dict_type (id, tenant_id, dict_type, name, status, deleted)
            VALUES
                (901, 1, 'dict_train_material_type', '培训资料类型', 'ENABLED', 0),
                (902, 1, 'dict_train_material_status', '培训资料状态', 'ENABLED', 0),
                (903, 1, 'dict_train_task_status', '学习任务状态', 'ENABLED', 0),
                (904, 1, 'dict_train_confirm_type', '确认方式', 'ENABLED', 0),
                (905, 1, 'dict_train_assign_scope', '指派范围', 'ENABLED', 0)
        """)

        op.execute("""
            INSERT IGNORE INTO ims_sys_dict_data (id, tenant_id, dict_type, dict_value, dict_label, color_type, sort, status, is_builtin, deleted)
            VALUES
                (9001, 1, 'dict_train_material_type', 'DOC', '文档', 'primary', 1, 'ENABLED', 1, 0),
                (9002, 1, 'dict_train_material_type', 'VIDEO', '视频', 'success', 2, 'ENABLED', 1, 0),
                (9003, 1, 'dict_train_material_type', 'LINK', '外链', 'info', 3, 'ENABLED', 1, 0),
                (9004, 1, 'dict_train_material_status', 'DRAFT', '草稿', 'neutral', 1, 'ENABLED', 1, 0),
                (9005, 1, 'dict_train_material_status', 'PUBLISHED', '已发布', 'success', 2, 'ENABLED', 1, 0),
                (9006, 1, 'dict_train_material_status', 'OFFLINE', '已下架', 'danger', 3, 'ENABLED', 1, 0),
                (9007, 1, 'dict_train_task_status', 'IN_PROGRESS', '进行中', 'primary', 1, 'ENABLED', 1, 0),
                (9008, 1, 'dict_train_task_status', 'FINISHED', '已结束', 'neutral', 2, 'ENABLED', 1, 0),
                (9009, 1, 'dict_train_confirm_type', 'DURATION', '学时达标', 'primary', 1, 'ENABLED', 1, 0),
                (9010, 1, 'dict_train_confirm_type', 'QUIZ', '自测问卷', 'success', 2, 'ENABLED', 1, 0),
                (9011, 1, 'dict_train_assign_scope', 'BY_USER', '按人', 'primary', 1, 'ENABLED', 1, 0),
                (9012, 1, 'dict_train_assign_scope', 'BY_POSITION', '按岗位', 'success', 2, 'ENABLED', 1, 0)
        """)


def downgrade() -> None:
    op.drop_table("ims_train_dept_alert")
    op.drop_table("ims_train_stat_daily")
    op.drop_table("ims_train_study_log")
    op.drop_table("ims_train_task_record")
    op.drop_table("ims_train_task")
    op.drop_table("ims_train_material_version")
    op.drop_table("ims_train_material")
    op.drop_table("ims_train_material_cate")

    op.execute("DELETE FROM ims_sys_dict_data WHERE dict_type LIKE 'dict_train_%'")
    op.execute("DELETE FROM ims_sys_dict_type WHERE dict_type LIKE 'dict_train_%'")
