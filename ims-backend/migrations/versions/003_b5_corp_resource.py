"""B5 公司资源表。

版本: v1.0
日期: 2026-10-13

001/002 没有公司、实名人、手机卡、证件这些表。本迁移建全表，可升可降。
Revision ID: 003_b5_corp_resource
Revises: 002_b1_m01_foundation
"""

import sqlalchemy as sa
from alembic import op

revision = "003_b5_corp_resource"
down_revision = "002_b1_m01_foundation"
branch_labels = None
depends_on = None


def _audit() -> list:
    return [
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
    ]


def upgrade() -> None:
    op.create_table(
        "ims_org_company",
        *_audit(),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.Column("credit_code", sa.String(18), nullable=True),
        sa.Column("industry", sa.String(50), nullable=True),
        sa.Column("address", sa.String(200), nullable=True),
        sa.Column("legal_name", sa.String(50), nullable=True),
        sa.Column("legal_id_card_enc", sa.Text(), nullable=True),
        sa.Column("legal_id_card_hash", sa.String(64), nullable=True),
        sa.Column("mp_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ENABLED"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_company_credit", "ims_org_company", ["tenant_id", "credit_code", "deleted"])

    op.create_table(
        "ims_master_realname",
        *_audit(),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("id_type", sa.String(50), nullable=True),
        sa.Column("id_card_enc", sa.Text(), nullable=True),
        sa.Column("id_card_hash", sa.String(64), nullable=True),
        sa.Column("phone_enc", sa.Text(), nullable=True),
        sa.Column("phone_hash", sa.String(64), nullable=True),
        sa.Column("wechat", sa.String(64), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ON_JOB"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id_card_hash", "deleted", name="uk_realname_id_card"),
    )

    op.create_table(
        "ims_master_sim_card",
        *_audit(),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.Column("phone_number_enc", sa.Text(), nullable=True),
        sa.Column("phone_number_hash", sa.String(64), nullable=True),
        sa.Column("phone_id", sa.BigInteger(), nullable=True),
        sa.Column("realname_id", sa.BigInteger(), nullable=True),
        sa.Column("operator", sa.String(50), nullable=True),
        sa.Column("assigned_user_id", sa.BigInteger(), nullable=True),
        sa.Column("iccid_enc", sa.Text(), nullable=True),
        sa.Column("iccid_hash", sa.String(64), nullable=True),
        sa.Column("package_name", sa.String(100), nullable=True),
        sa.Column("monthly_rent", sa.Numeric(12, 2), nullable=True),
        sa.Column("activated_at", sa.Date(), nullable=True),
        sa.Column("payment_cycle", sa.String(50), nullable=True),
        sa.Column("next_payment_date", sa.Date(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(20), nullable=False, server_default="ENABLED"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "phone_number_hash", "deleted", name="uk_sim_phone"),
        sa.UniqueConstraint("tenant_id", "iccid_hash", "deleted", name="uk_sim_iccid"),
    )

    op.create_table(
        "ims_master_cert",
        *_audit(),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.Column("realname_id", sa.BigInteger(), nullable=True),
        sa.Column("holder_type", sa.String(20), nullable=True),
        sa.Column("holder_user_id", sa.BigInteger(), nullable=True),
        sa.Column("holder_name", sa.String(50), nullable=True),
        sa.Column("cert_type", sa.String(50), nullable=True),
        sa.Column("cert_no_enc", sa.Text(), nullable=True),
        sa.Column("cert_no_hash", sa.String(64), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("expire_date", sa.Date(), nullable=True),
        sa.Column("file_key", sa.String(300), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("warn_level", sa.String(20), nullable=True),
        sa.Column("review_by", sa.BigInteger(), nullable=True),
        sa.Column("review_time", sa.DateTime(), nullable=True),
        sa.Column("review_remark", sa.String(500), nullable=True),
        sa.Column("renew_from_id", sa.BigInteger(), nullable=True),
        sa.Column("ocr_result", sa.Text(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_cert_expire_scan",
        "ims_master_cert",
        ["tenant_id", "deleted", "status", "expire_date"],
    )

    op.create_table(
        "ims_account_platform",
        *_audit(),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.Column("author_id", sa.BigInteger(), nullable=True),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("company_id", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ims_org_company_expansion",
        *_audit(),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("from_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("to_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(200), nullable=False, server_default=""),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("operate_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_master_realname_intermediary",
        *_audit(),
        sa.Column("realname_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False, server_default=""),
        sa.Column("phone_enc", sa.Text(), nullable=True),
        sa.Column("phone_hash", sa.String(64), nullable=True),
        sa.Column("wechat", sa.String(64), nullable=True),
        sa.Column("relation_type", sa.String(20), nullable=False, server_default="DIRECT"),
        sa.Column("commission_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("remark", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_cert_expire_task",
        *_audit(),
        sa.Column("cert_id", sa.BigInteger(), nullable=False),
        sa.Column("level", sa.String(20), nullable=False, server_default="YELLOW"),
        sa.Column("status", sa.String(30), nullable=False, server_default="WARNING"),
        sa.Column("notified_levels", sa.String(100), nullable=False, server_default=""),
        sa.Column("last_remind_time", sa.DateTime(), nullable=True),
        sa.Column("remind_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_cert_level_rule",
        *_audit(),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("view_level", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_cert_l3_whitelist",
        *_audit(),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ims_cert_view_log",
        *_audit(),
        sa.Column("cert_id", sa.BigInteger(), nullable=False),
        sa.Column("viewer_user_id", sa.BigInteger(), nullable=False),
        sa.Column("view_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("watermark_text", sa.String(200), nullable=True),
        sa.Column("view_duration", sa.Integer(), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("device", sa.String(200), nullable=True),
        sa.Column("result", sa.String(30), nullable=False, server_default="OK"),
        sa.Column("view_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_cert_view_hour",
        "ims_cert_view_log",
        ["tenant_id", "viewer_user_id", "view_time"],
    )


def downgrade() -> None:
    op.drop_index("idx_cert_view_hour", table_name="ims_cert_view_log")
    op.drop_table("ims_cert_view_log")
    op.drop_table("ims_cert_l3_whitelist")
    op.drop_table("ims_cert_level_rule")
    op.drop_table("ims_cert_expire_task")
    op.drop_table("ims_master_realname_intermediary")
    op.drop_table("ims_org_company_expansion")
    op.drop_table("ims_account_platform")
    op.drop_index("idx_cert_expire_scan", table_name="ims_master_cert")
    op.drop_table("ims_master_cert")
    op.drop_table("ims_master_sim_card")
    op.drop_table("ims_master_realname")
    op.drop_index("idx_company_credit", table_name="ims_org_company")
    op.drop_table("ims_org_company")
