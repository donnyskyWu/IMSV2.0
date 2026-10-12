"""Initial migration - create all B0a framework tables

Revision ID: 001_initial
Revises:
Create Date: 2026-10-12

Tables created per FP-B01-01 through FP-B09-01:
- ims_sys_user (FP-B03-01)
- ims_sys_user_dept (FP-B03-02)
- ims_auth_user_mapping (FP-B03-03)
- ims_sys_dept (FP-B08-01)
- ims_sys_role (FP-B04-01)
- ims_sys_menu (FP-B04-02)
- ims_sys_role_menu (FP-B04-03)
- ims_role_perm_detail (FP-B04-03)
- ims_sys_user_role (FP-B04-03)
- ims_sys_tenant (FP-B04-04)
- ims_sys_tenant_package (FP-B04-04)
- ims_sys_tenant_package_menu (FP-B04-04)
- ims_sys_dict_type (FP-B07-01)
- ims_sys_dict_data (FP-B07-01)
- ims_sys_param (FP-B07-02)
- ims_sys_operate_log (FP-F01-01)
- ims_sys_login_log (FP-F01-02)
- ims_sys_change_log (FP-F02-01)
- ims_sys_integrity_issue (FP-B09-01)
- ims_sys_integrity_scan (FP-B09-01)
- ims_sys_org_sync_batch (FP-D07-04)
"""
import sqlalchemy as sa
from alembic import op

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ims_sys_tenant
    op.create_table(
        'ims_sys_tenant',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False, default=1),
        sa.Column('name', sa.String(100), nullable=False, comment='租户名称'),
        sa.Column('package_id', sa.BigInteger(), nullable=True, comment='套餐ID'),
        sa.Column('status', sa.String(20), nullable=False, default='ENABLED', comment='状态'),
        sa.Column('expire_time', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # ims_sys_tenant_package
    op.create_table(
        'ims_sys_tenant_package',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False, default=1),
        sa.Column('name', sa.String(100), nullable=False, comment='套餐名称'),
        sa.Column('status', sa.String(20), nullable=False, default='ENABLED', comment='状态'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # ims_sys_tenant_package_menu
    op.create_table(
        'ims_sys_tenant_package_menu',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False, default=1),
        sa.Column('package_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('menu_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('package_id', 'menu_id', name='uk_package_menu')
    )

    # ims_sys_menu
    op.create_table(
        'ims_sys_menu',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False, default=1),
        sa.Column('parent_id', sa.BigInteger(), nullable=False, default=0, comment='父菜单ID'),
        sa.Column('type', sa.String(20), nullable=False, comment='DIR/MENU/BUTTON'),
        sa.Column('name', sa.String(50), nullable=False, comment='菜单名称'),
        sa.Column('perm_code', sa.String(100), nullable=True, comment='权限码'),
        sa.Column('path', sa.String(200), nullable=True, comment='路由路径'),
        sa.Column('component', sa.String(200), nullable=True, comment='组件路径'),
        sa.Column('icon', sa.String(100), nullable=True, comment='图标'),
        sa.Column('sort', sa.Integer(), nullable=False, default=0, comment='排序'),
        sa.Column('visible', sa.Boolean(), nullable=False, default=True, comment='是否可见'),
        sa.Column('status', sa.String(20), nullable=False, default='ENABLED', comment='状态'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('perm_code', 'deleted', name='uk_menu_perm_code'),
        sa.Index('idx_menu_parent', 'parent_id')
    )

    # ims_sys_dept
    op.create_table(
        'ims_sys_dept',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('parent_id', sa.BigInteger(), nullable=False, default=0, comment='父部门ID,根为0'),
        sa.Column('path', sa.String(500), nullable=False, default='/', comment='路径如/1/5/12/'),
        sa.Column('name', sa.String(50), nullable=False, comment='部门名称1-50字'),
        sa.Column('sort', sa.Integer(), nullable=False, default=0, comment='排序'),
        sa.Column('leader_user_id', sa.BigInteger(), nullable=True, comment='负责人用户ID'),
        sa.Column('status', sa.String(20), nullable=False, default='ENABLED', comment='ENABLED/DISABLED'),
        sa.Column('source', sa.String(20), nullable=False, default='LOCAL', comment='DINGTALK/LOCAL/SYSTEM'),
        sa.Column('dingtalk_dept_id', sa.String(64), nullable=True, comment='钉钉部门ID'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True, comment='最后同步时间'),
        sa.Column('local_orphan', sa.Boolean(), nullable=False, default=False, comment='待确认本地部门标记'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'dingtalk_dept_id', 'deleted', name='uk_dept_dingtalk'),
        sa.Index('idx_dept_parent', 'parent_id'),
        sa.Index('idx_dept_path', 'path')
    )

    # ims_sys_user
    op.create_table(
        'ims_sys_user',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(30), nullable=False, comment='用户名4-30位字母数字下划线'),
        sa.Column('nickname', sa.String(50), nullable=False, comment='姓名(昵称)'),
        sa.Column('mobile_enc', sa.String(256), nullable=True, comment='手机号AES密文'),
        sa.Column('mobile_hash', sa.String(64), nullable=True, comment='手机号HMAC-SHA256'),
        sa.Column('email', sa.String(100), nullable=True, comment='邮箱'),
        sa.Column('password_hash', sa.String(128), nullable=True, comment='密码bcrypt哈希'),
        sa.Column('status', sa.String(20), nullable=False, default='ACTIVE', comment='状态'),
        sa.Column('main_dept_id', sa.BigInteger(), nullable=True, comment='主部门ID'),
        sa.Column('position_code', sa.String(50), nullable=True, comment='岗位字典值'),
        sa.Column('login_fail_count', sa.SmallInteger(), nullable=False, default=0, comment='连续登录失败次数'),
        sa.Column('lock_until', sa.DateTime(), nullable=True, comment='锁定截止时间'),
        sa.Column('last_login_time', sa.DateTime(), nullable=True, comment='最后登录时间'),
        sa.Column('last_login_ip', sa.String(50), nullable=True, comment='最后登录IP'),
        sa.Column('pwd_reset_required', sa.Boolean(), nullable=False, default=False, comment='是否需要重置密码'),
        sa.Column('source', sa.String(20), nullable=False, default='LOCAL', comment='来源'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'username', 'deleted', name='uk_user_username'),
        sa.Index('idx_user_mobile_hash', 'mobile_hash'),
        sa.Index('idx_user_status', 'status')
    )

    # ims_sys_user_dept
    op.create_table(
        'ims_sys_user_dept',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('dept_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('is_main', sa.Boolean(), nullable=False, default=False),
        sa.Column('source', sa.String(20), nullable=False, default='LOCAL', comment='DINGTALK/LOCAL'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'dept_id', name='uk_user_dept')
    )

    # ims_auth_user_mapping
    op.create_table(
        'ims_auth_user_mapping',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('dingtalk_user_id', sa.String(64), nullable=False),
        sa.Column('union_id', sa.String(64), nullable=True),
        sa.Column('dept_ids', sa.Text(), nullable=True, comment='钉钉原始部门ID列表JSON'),
        sa.Column('sync_status', sa.String(20), nullable=True),
        sa.Column('last_sync_time', sa.DateTime(), nullable=True),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'dingtalk_user_id', 'deleted', name='uk_mapping_dingtalk'),
        sa.UniqueConstraint('tenant_id', 'user_id', 'deleted', name='uk_mapping_user')
    )

    # ims_sys_role
    op.create_table(
        'ims_sys_role',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('role_key', sa.String(50), nullable=False, comment='角色标识'),
        sa.Column('name', sa.String(50), nullable=False, comment='角色名称'),
        sa.Column('source', sa.String(20), nullable=False, default='MANUAL', comment='MANUAL/DINGTALK_AUTO'),
        sa.Column('status', sa.String(20), nullable=False, default='ENABLED', comment='ENABLED/DISABLED/PENDING_CONFIG'),
        sa.Column('data_scope', sa.String(20), nullable=True, comment='ALL/DEPT/IP_GROUP/SELF/空=未配置'),
        sa.Column('position_code', sa.String(50), nullable=True, comment='绑定岗位'),
        sa.Column('is_standard', sa.Boolean(), nullable=False, default=False, comment='标准角色R1-R11'),
        sa.Column('sort', sa.Integer(), nullable=False, default=0, comment='排序'),
        sa.Column('remark', sa.String(500), nullable=True, comment='备注'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'role_key', 'deleted', name='uk_role_key'),
        sa.UniqueConstraint('tenant_id', 'position_code', 'deleted', name='uk_role_position')
    )

    # ims_sys_role_menu
    op.create_table(
        'ims_sys_role_menu',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False, default=1),
        sa.Column('role_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('menu_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'menu_id', name='uk_role_menu')
    )

    # ims_role_perm_detail
    op.create_table(
        'ims_role_perm_detail',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('role_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('perm_code', sa.String(100), nullable=False),
        sa.Column('r', sa.Boolean(), nullable=False, default=True, comment='读'),
        sa.Column('w', sa.Boolean(), nullable=False, default=False, comment='写'),
        sa.Column('d', sa.Boolean(), nullable=False, default=False, comment='删'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'perm_code', name='uk_role_perm')
    )

    # ims_sys_user_role
    op.create_table(
        'ims_sys_user_role',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('role_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('source', sa.String(20), nullable=False, default='MANUAL', comment='MANUAL/DINGTALK_AUTO'),
        sa.Column('manual_removed', sa.Boolean(), nullable=False, default=False, comment='手工移除例外标记'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', name='uk_user_role')
    )

    # ims_sys_dict_type
    op.create_table(
        'ims_sys_dict_type',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False, default=1),
        sa.Column('dict_type', sa.String(50), nullable=False, comment='字典类型'),
        sa.Column('name', sa.String(100), nullable=False, comment='字典名称'),
        sa.Column('status', sa.String(20), nullable=False, default='ENABLED', comment='状态'),
        sa.Column('remark', sa.String(500), nullable=True, comment='备注'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dict_type', 'deleted', name='uk_dict_type')
    )

    # ims_sys_dict_data
    op.create_table(
        'ims_sys_dict_data',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False, default=1),
        sa.Column('dict_type', sa.String(50), nullable=False, comment='字典类型'),
        sa.Column('dict_value', sa.String(50), nullable=False, comment='字典值'),
        sa.Column('dict_label', sa.String(100), nullable=False, comment='字典标签'),
        sa.Column('color_type', sa.String(20), nullable=False, default='neutral', comment='颜色类型'),
        sa.Column('sort', sa.Integer(), nullable=False, default=0, comment='排序'),
        sa.Column('status', sa.String(20), nullable=False, default='ENABLED', comment='状态'),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, default=False, comment='是否内置'),
        sa.Column('source', sa.String(20), nullable=True, comment='来源DINGTALK/LOCAL'),
        sa.Column('remark', sa.String(500), nullable=True, comment='备注'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dict_type', 'dict_value', 'deleted', name='uk_dict_data'),
        sa.Index('idx_dict_data_type', 'dict_type')
    )

    # ims_sys_param
    op.create_table(
        'ims_sys_param',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False, default=1),
        sa.Column('param_key', sa.String(100), nullable=False, comment='参数键'),
        sa.Column('name', sa.String(100), nullable=False, comment='参数名称'),
        sa.Column('group', sa.String(50), nullable=False, comment='参数分组'),
        sa.Column('value_type', sa.String(20), nullable=False, comment='BOOLEAN/NUMBER/TEXT/ROLE_REF/ENUM/SECRET'),
        sa.Column('value', sa.Text(), nullable=True, comment='参数值'),
        sa.Column('default_value', sa.String(500), nullable=True, comment='默认值'),
        sa.Column('min_value', sa.String(50), nullable=True, comment='最小值'),
        sa.Column('max_value', sa.String(50), nullable=True, comment='最大值'),
        sa.Column('options', sa.Text(), nullable=True, comment='ENUM选项JSON'),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, default=True, comment='是否内置'),
        sa.Column('remark', sa.String(500), nullable=True, comment='备注'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('param_key', 'deleted', name='uk_param_key')
    )

    # ims_sys_operate_log
    op.create_table(
        'ims_sys_operate_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('module', sa.String(50), nullable=False, comment='模块'),
        sa.Column('operation', sa.String(100), nullable=False, comment='操作'),
        sa.Column('object_type', sa.String(50), nullable=True, comment='对象类型'),
        sa.Column('object_id', sa.String(64), nullable=True, comment='对象ID'),
        sa.Column('result', sa.String(20), nullable=False, comment='SUCCESS/FAILED'),
        sa.Column('error_code', sa.Integer(), nullable=True, comment='错误码'),
        sa.Column('ip', sa.String(50), nullable=True, comment='IP地址'),
        sa.Column('duration_ms', sa.Integer(), nullable=True, comment='耗时毫秒'),
        sa.Column('request_path', sa.String(200), nullable=True, comment='请求路径'),
        sa.Column('request_method', sa.String(10), nullable=True, comment='请求方法'),
        sa.Column('request_params', sa.Text(), nullable=True, comment='请求参数摘要'),
        sa.Column('operator_name', sa.String(50), nullable=True, comment='操作人姓名'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_operate_log_time', 'create_time'),
        sa.Index('idx_operate_log_module', 'module')
    )

    # ims_sys_login_log
    op.create_table(
        'ims_sys_login_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(50), nullable=False, comment='用户名'),
        sa.Column('user_id', sa.BigInteger(), nullable=True, comment='用户ID'),
        sa.Column('login_method', sa.String(20), nullable=False, comment='PASSWORD/DINGTALK'),
        sa.Column('result', sa.String(20), nullable=False, comment='结果'),
        sa.Column('ip', sa.String(50), nullable=True, comment='IP地址'),
        sa.Column('user_agent', sa.String(500), nullable=True, comment='User-Agent'),
        sa.Column('device', sa.String(100), nullable=True, comment='设备'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_login_log_time', 'create_time'),
        sa.Index('idx_login_log_user', 'user_id')
    )

    # ims_sys_change_log
    op.create_table(
        'ims_sys_change_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('biz_type', sa.String(50), nullable=False, comment='业务类型'),
        sa.Column('biz_id', sa.String(64), nullable=False, comment='业务ID'),
        sa.Column('field', sa.String(50), nullable=False, comment='字段名'),
        sa.Column('field_label', sa.String(50), nullable=True, comment='字段中文名'),
        sa.Column('before_value', sa.Text(), nullable=True, comment='变更前值'),
        sa.Column('after_value', sa.Text(), nullable=True, comment='变更后值'),
        sa.Column('reason', sa.String(50), nullable=False, default='USER_EDIT', comment='变更原因'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_change_log_biz', 'biz_type', 'biz_id'),
        sa.Index('idx_change_log_time', 'create_time')
    )

    # ims_sys_integrity_issue
    op.create_table(
        'ims_sys_integrity_issue',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('scan_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('issue_type', sa.String(30), nullable=False, comment='ORPHAN/CROSS_TENANT/DISABLED_REF/CASCADE_MISSED'),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('record_id', sa.String(64), nullable=False),
        sa.Column('field', sa.String(50), nullable=False),
        sa.Column('target_table', sa.String(100), nullable=False),
        sa.Column('target_id', sa.String(64), nullable=False),
        sa.Column('suggestion', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='OPEN', comment='OPEN/CLOSED'),
        sa.Column('last_seen_time', sa.DateTime(), nullable=True),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # ims_sys_integrity_scan
    op.create_table(
        'ims_sys_integrity_scan',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('tables_scanned', sa.Text(), nullable=True),
        sa.Column('issue_count', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.String(20), nullable=False, default='RUNNING', comment='RUNNING/SUCCESS/FAILED'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # ims_sys_org_sync_batch
    op.create_table(
        'ims_sys_org_sync_batch',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='PENDING', comment='PENDING/RUNNING/SUCCESS/FAILED'),
        sa.Column('started_at', sa.DateTime(), nullable=True, comment='开始时间'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='完成时间'),
        sa.Column('added_depts', sa.Integer(), nullable=False, default=0, comment='新增部门数'),
        sa.Column('updated_depts', sa.Integer(), nullable=False, default=0, comment='更新部门数'),
        sa.Column('removed_depts', sa.Integer(), nullable=False, default=0, comment='删除部门数'),
        sa.Column('added_users', sa.Integer(), nullable=False, default=0, comment='新增用户数'),
        sa.Column('updated_users', sa.Integer(), nullable=False, default=0, comment='更新用户数'),
        sa.Column('removed_users', sa.Integer(), nullable=False, default=0, comment='删除用户数'),
        sa.Column('error_msg', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('creator', sa.BigInteger(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('updater', sa.BigInteger(), nullable=True),
        sa.Column('update_time', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.BigInteger(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_org_sync_batch_time', 'started_at')
    )


def downgrade() -> None:
    op.drop_table('ims_sys_org_sync_batch')
    op.drop_table('ims_sys_integrity_scan')
    op.drop_table('ims_sys_integrity_issue')
    op.drop_table('ims_sys_change_log')
    op.drop_table('ims_sys_login_log')
    op.drop_table('ims_sys_operate_log')
    op.drop_table('ims_sys_param')
    op.drop_table('ims_sys_dict_data')
    op.drop_table('ims_sys_dict_type')
    op.drop_table('ims_sys_user_role')
    op.drop_table('ims_role_perm_detail')
    op.drop_table('ims_sys_role_menu')
    op.drop_table('ims_sys_role')
    op.drop_table('ims_auth_user_mapping')
    op.drop_table('ims_sys_user_dept')
    op.drop_table('ims_sys_user')
    op.drop_table('ims_sys_dept')
    op.drop_table('ims_sys_menu')
    op.drop_table('ims_sys_tenant_package_menu')
    op.drop_table('ims_sys_tenant_package')
    op.drop_table('ims_sys_tenant')
