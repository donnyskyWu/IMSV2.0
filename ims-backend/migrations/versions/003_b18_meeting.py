"""B18-M18 会议模块 · 会议纪要、决议、行动项、附录

版本: v1.0
日期: 2026-10-13

新增 4 张业务表 + 1 张幂等键表 + 字典 + 菜单权限种子。

Revision ID: 003_b18_meeting
Revises: 002_b1_m01_foundation
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Session

revision = "003_b18_meeting"
down_revision = "002_b1_m01_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建会议模块表、字典和种子数据。"""
    _create_meeting_minutes()
    _create_meeting_decision()
    _create_meeting_action_item()
    _create_meeting_appendix()
    _create_client_token_table()
    _seed_dict()
    _seed_menu_perm()


def downgrade() -> None:
    """删除会议模块表、字典和种子数据。"""
    _remove_menu_perm()
    _remove_dict()
    op.drop_table("ims_meeting_client_token")
    op.drop_table("ims_meeting_appendix")
    op.drop_table("ims_meeting_action_item")
    op.drop_table("ims_meeting_decision")
    op.drop_table("ims_meeting_minutes")


def _audit_columns() -> list[sa.Column]:
    """审计字段（与 AuditBase 一致）。"""
    return [
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("creator", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("updater", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.BigInteger(), nullable=False, server_default="0"),
    ]


def _create_meeting_minutes() -> None:
    """ims_meeting_minutes 会议纪要主表。"""
    op.create_table(
        "ims_meeting_minutes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        *_audit_columns(),
        sa.Column("code", sa.String(20), nullable=False, comment="编号 MM+yyyyMMdd+3位流水"),
        sa.Column("title", sa.String(128), nullable=False, comment="会议主题"),
        sa.Column("meeting_date", sa.DateTime(), nullable=False, comment="会议时间"),
        sa.Column("meeting_room", sa.String(64), nullable=True, comment="会议室"),
        sa.Column("dept_id", sa.BigInteger(), nullable=False, comment="记录人主部门"),
        sa.Column("recorder_user_id", sa.BigInteger(), nullable=False, comment="记录人"),
        sa.Column("attendees", sa.JSON(), nullable=False, comment="{internal: [userId], external: [name]}"),
        sa.Column("summary", sa.Text(), nullable=True, comment="纪要正文（富文本白名单净化后存储）"),
        sa.Column("import_from_ai_minutes", sa.SmallInteger(), nullable=False, server_default="0", comment="预留：是否从钉钉 AI 听记导入"),
        sa.Column("status", sa.String(20), nullable=False, comment="REGISTERED/MINUTES_RECORDED/ARCHIVED"),
        sa.Column("archived_at", sa.DateTime(), nullable=True, comment="归档时间"),
        sa.Column("archived_by", sa.BigInteger(), nullable=True, comment="归档人"),
        sa.Column("remind_24h_at", sa.DateTime(), nullable=True, comment="已发送 24h 提醒时间（幂等用）"),
        sa.Column("remind_48h_at", sa.DateTime(), nullable=True, comment="已发送 48h 提醒时间（幂等用）"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1", comment="乐观锁版本号"),
        sa.UniqueConstraint("tenant_id", "code", "deleted", name="uk_minutes_code"),
    )
    op.create_index("idx_minutes_tenant_date", "ims_meeting_minutes", ["tenant_id", "meeting_date"])
    op.create_index("idx_minutes_recorder", "ims_meeting_minutes", ["recorder_user_id"])
    op.create_index("idx_minutes_status", "ims_meeting_minutes", ["tenant_id", "status"])
    op.create_index("idx_minutes_dept", "ims_meeting_minutes", ["tenant_id", "dept_id"])


def _create_meeting_decision() -> None:
    """ims_meeting_decision 决议事项子表。"""
    op.create_table(
        "ims_meeting_decision",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        *_audit_columns(),
        sa.Column("minutes_id", sa.BigInteger(), nullable=False, comment="关联纪要"),
        sa.Column("seq", sa.Integer(), nullable=False, comment="序号"),
        sa.Column("content", sa.String(512), nullable=False, comment="决议内容（HTML 转义存储）"),
        sa.UniqueConstraint("tenant_id", "minutes_id", "seq", "deleted", name="uk_decision_seq"),
    )
    op.create_index("idx_decision_minutes", "ims_meeting_decision", ["minutes_id"])
    op.create_index("idx_decision_tenant", "ims_meeting_decision", ["tenant_id"])


def _create_meeting_action_item() -> None:
    """ims_meeting_action_item 行动项子表。"""
    op.create_table(
        "ims_meeting_action_item",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        *_audit_columns(),
        sa.Column("minutes_id", sa.BigInteger(), nullable=False, comment="关联纪要"),
        sa.Column("description", sa.String(256), nullable=False, comment="行动项描述"),
        sa.Column("assignee_user_id", sa.BigInteger(), nullable=False, comment="责任人"),
        sa.Column("due_date", sa.Date(), nullable=False, comment="截止日期"),
        sa.Column("status", sa.String(20), nullable=False, comment="OPEN/OVERDUE/CLOSED"),
        sa.Column("close_remark", sa.String(512), nullable=True, comment="闭环说明"),
        sa.Column("evidence_url", sa.String(512), nullable=True, comment="证据链接（仅 http/https）"),
        sa.Column("closed_at", sa.DateTime(), nullable=True, comment="闭环时间"),
        sa.Column("todo_id", sa.BigInteger(), nullable=True, comment="关联待办 ID"),
        sa.Column("notified_at", sa.DateTime(), nullable=True, comment="逾期 1 天推送时间（幂等用）"),
        sa.Column("escalated_at", sa.DateTime(), nullable=True, comment="逾期 3 天升级时间（幂等用）"),
    )
    op.create_index("idx_action_minutes", "ims_meeting_action_item", ["minutes_id"])
    op.create_index("idx_action_assignee", "ims_meeting_action_item", ["assignee_user_id"])
    op.create_index("idx_action_due", "ims_meeting_action_item", ["due_date", "status"])
    op.create_index("idx_action_tenant", "ims_meeting_action_item", ["tenant_id"])


def _create_meeting_appendix() -> None:
    """ims_meeting_appendix 附录说明子表。"""
    op.create_table(
        "ims_meeting_appendix",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        *_audit_columns(),
        sa.Column("minutes_id", sa.BigInteger(), nullable=False, comment="关联纪要"),
        sa.Column("content", sa.String(1024), nullable=False, comment="附录内容（HTML 转义存储）"),
    )
    op.create_index("idx_appendix_minutes", "ims_meeting_appendix", ["minutes_id"])
    op.create_index("idx_appendix_tenant", "ims_meeting_appendix", ["tenant_id"])


def _create_client_token_table() -> None:
    """ims_meeting_client_token 幂等键存储。"""
    op.create_table(
        "ims_meeting_client_token",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("client_token", sa.String(64), nullable=False, comment="幂等键"),
        sa.Column("result_id", sa.BigInteger(), nullable=True, comment="创建结果 ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("expires_at", sa.DateTime(), nullable=False, comment="过期时间（24h）"),
        sa.UniqueConstraint("tenant_id", "client_token", name="uk_client_token"),
    )
    op.create_index("idx_client_token_expires", "ims_meeting_client_token", ["expires_at"])


def _seed_dict() -> None:
    """会议模块字典种子。"""
    bind = op.get_bind()
    session = Session(bind=bind)

    from datetime import datetime
    now = datetime.now()

    dict_type_rows = [
        {"id": 200, "tenant_id": 1, "name": "会议纪要状态", "type": "meet_minutes_status",
         "status": 0, "remark": "会议纪要状态", "creator": 0, "create_time": now, "deleted": 0},
        {"id": 201, "tenant_id": 1, "name": "行动项状态", "type": "meet_action_status",
         "status": 0, "remark": "行动项状态", "creator": 0, "create_time": now, "deleted": 0},
    ]

    dict_data_rows = [
        {"id": 2000, "tenant_id": 1, "dict_type": "meet_minutes_status", "label": "已登记",
         "value": "REGISTERED", "sort": 1, "status": 0, "color_type": "info",
         "creator": 0, "create_time": now, "deleted": 0},
        {"id": 2001, "tenant_id": 1, "dict_type": "meet_minutes_status", "label": "纪要已录入",
         "value": "MINUTES_RECORDED", "sort": 2, "status": 0, "color_type": "warning",
         "creator": 0, "create_time": now, "deleted": 0},
        {"id": 2002, "tenant_id": 1, "dict_type": "meet_minutes_status", "label": "已归档",
         "value": "ARCHIVED", "sort": 3, "status": 0, "color_type": "success",
         "creator": 0, "create_time": now, "deleted": 0},
        {"id": 2003, "tenant_id": 1, "dict_type": "meet_action_status", "label": "进行中",
         "value": "OPEN", "sort": 1, "status": 0, "color_type": "info",
         "creator": 0, "create_time": now, "deleted": 0},
        {"id": 2004, "tenant_id": 1, "dict_type": "meet_action_status", "label": "已逾期",
         "value": "OVERDUE", "sort": 2, "status": 0, "color_type": "danger",
         "creator": 0, "create_time": now, "deleted": 0},
        {"id": 2005, "tenant_id": 1, "dict_type": "meet_action_status", "label": "已闭环",
         "value": "CLOSED", "sort": 3, "status": 0, "color_type": "success",
         "creator": 0, "create_time": now, "deleted": 0},
    ]

    for row in dict_type_rows:
        session.execute(
            sa.text("""
                INSERT INTO ims_sys_dict_type (id, tenant_id, name, type, status, remark, creator, create_time, deleted)
                VALUES (:id, :tenant_id, :name, :type, :status, :remark, :creator, :create_time, :deleted)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
            """),
            row,
        )

    for row in dict_data_rows:
        session.execute(
            sa.text("""
                INSERT INTO ims_sys_dict_data (id, tenant_id, dict_type, label, value, sort, status, color_type, creator, create_time, deleted)
                VALUES (:id, :tenant_id, :dict_type, :label, :value, :sort, :status, :color_type, :creator, :create_time, :deleted)
                ON DUPLICATE KEY UPDATE label = VALUES(label)
            """),
            row,
        )

    session.commit()


def _remove_dict() -> None:
    """删除会议模块字典。"""
    bind = op.get_bind()
    session = Session(bind=bind)

    session.execute(
        sa.text("DELETE FROM ims_sys_dict_data WHERE dict_type IN ('meet_minutes_status', 'meet_action_status')")
    )
    session.execute(
        sa.text("DELETE FROM ims_sys_dict_type WHERE type IN ('meet_minutes_status', 'meet_action_status')")
    )
    session.commit()


def _seed_menu_perm() -> None:
    """会议模块菜单和权限种子。"""
    bind = op.get_bind()
    session = Session(bind=bind)

    from datetime import datetime
    now = datetime.now()

    menu_rows = [
        {"id": 1800, "tenant_id": 1, "parent_id": 0, "name": "会议", "type": "DIR",
         "path": "", "component": None, "perm_code": None, "icon": "meet", "sort": 18,
         "visible": 1, "creator": 0, "create_time": now, "deleted": 0},
        {"id": 1801, "tenant_id": 1, "parent_id": 1800, "name": "会议纪要", "type": "MENU",
         "path": "/ims/meet/minutes", "component": "meet/minutes/index", "perm_code": "ims:meet:minutes:query",
         "icon": None, "sort": 1, "visible": 1, "creator": 0, "create_time": now, "deleted": 0},
        {"id": 1802, "tenant_id": 1, "parent_id": 1801, "name": "仅查看本人会议", "type": "BUTTON",
         "path": "", "component": None, "perm_code": "ims:meet:minutes:query-self",
         "icon": None, "sort": 2, "visible": 1, "creator": 0, "create_time": now, "deleted": 0},
        {"id": 1803, "tenant_id": 1, "parent_id": 1801, "name": "登记会议", "type": "BUTTON",
         "path": "", "component": None, "perm_code": "ims:meet:minutes:add",
         "icon": None, "sort": 3, "visible": 1, "creator": 0, "create_time": now, "deleted": 0},
        {"id": 1804, "tenant_id": 1, "parent_id": 1801, "name": "编辑纪要", "type": "BUTTON",
         "path": "", "component": None, "perm_code": "ims:meet:minutes:edit",
         "icon": None, "sort": 4, "visible": 1, "creator": 0, "create_time": now, "deleted": 0},
        {"id": 1805, "tenant_id": 1, "parent_id": 1801, "name": "归档纪要", "type": "BUTTON",
         "path": "", "component": None, "perm_code": "ims:meet:minutes:archive",
         "icon": None, "sort": 5, "visible": 1, "creator": 0, "create_time": now, "deleted": 0},
        {"id": 1806, "tenant_id": 1, "parent_id": 1801, "name": "删除纪要", "type": "BUTTON",
         "path": "", "component": None, "perm_code": "ims:meet:minutes:delete",
         "icon": None, "sort": 6, "visible": 1, "creator": 0, "create_time": now, "deleted": 0},
        {"id": 1807, "tenant_id": 1, "parent_id": 1801, "name": "附录说明", "type": "BUTTON",
         "path": "", "component": None, "perm_code": "ims:meet:minutes:appendix",
         "icon": None, "sort": 7, "visible": 1, "creator": 0, "create_time": now, "deleted": 0},
        {"id": 1808, "tenant_id": 1, "parent_id": 1801, "name": "留痕率监督", "type": "BUTTON",
         "path": "", "component": None, "perm_code": "ims:meet:minutes:supervise",
         "icon": None, "sort": 8, "visible": 1, "creator": 0, "create_time": now, "deleted": 0},
    ]

    for row in menu_rows:
        session.execute(
            sa.text("""
                INSERT INTO ims_sys_menu (id, tenant_id, parent_id, name, type, path, component, perm_code, icon, sort, visible, creator, create_time, deleted)
                VALUES (:id, :tenant_id, :parent_id, :name, :type, :path, :component, :perm_code, :icon, :sort, :visible, :creator, :create_time, :deleted)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
            """),
            row,
        )

    role_menu_rows = []
    for menu in menu_rows:
        role_menu_rows.append({
            "tenant_id": 1,
            "role_id": 1,
            "menu_id": menu["id"],
            "creator": 0,
            "create_time": now,
        })

    for row in role_menu_rows:
        session.execute(
            sa.text("""
                INSERT INTO ims_sys_role_menu (tenant_id, role_id, menu_id, creator, create_time)
                VALUES (:tenant_id, :role_id, :menu_id, :creator, :create_time)
                ON DUPLICATE KEY UPDATE role_id = VALUES(role_id)
            """),
            row,
        )

    session.commit()


def _remove_menu_perm() -> None:
    """删除会议模块菜单和权限。"""
    bind = op.get_bind()
    session = Session(bind=bind)

    menu_ids = [1800, 1801, 1802, 1803, 1804, 1805, 1806, 1807, 1808]
    ids_str = ",".join(str(i) for i in menu_ids)

    session.execute(sa.text(f"DELETE FROM ims_sys_role_menu WHERE menu_id IN ({ids_str})"))
    session.execute(sa.text(f"DELETE FROM ims_sys_menu WHERE id IN ({ids_str})"))
    session.commit()
