# app/domains/sys/models.py - System domain models (FW-B03, FW-B04, FW-B07, FW-B08)
"""
System domain models.

Implements:
- FP-B03-01: User model with audit fields
- FP-B03-02: User-Department association
- FP-B04-01: Role model
- FP-B04-02: Menu model
- FP-B04-03: Role-Menu association, User-Role association
- FP-B04-04: Tenant and package
- FP-B07-01: Dictionary type and data
- FP-B07-02: System parameter
- FP-B08-01: Department model
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AssociationBase, AuditBase, PlatformBase


class User(AuditBase):
    """
    User model (FP-B03-01).

    Table: ims_sys_user

    Rules:
    - id cannot be modified after creation (error 1211)
    - FROZEN/RESIGNED users cannot login (error 1216)
    - Deletion only allowed if never logged in and no business references
    - Status transitions: ACTIVE↔FROZEN, any→RESIGNED (one-way)
    """

    __tablename__ = "ims_sys_user"
    __track_changes__ = True
    __scope_fields__ = {"owner": "id"}

    # Basic info
    username: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="用户名 4-30位字母数字下划线"
    )
    nickname: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="姓名(昵称)"
    )

    # Contact info (encrypted)
    mobile_enc: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="手机号AES密文"
    )
    mobile_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True, comment="手机号HMAC-SHA256用于匹配"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="邮箱"
    )

    # Authentication
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="密码bcrypt哈希"
    )

    # Status: ACTIVE, FROZEN, RESIGNED
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", comment="状态"
    )

    # Organization
    main_dept_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="主部门ID"
    )
    position_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="岗位字典值"
    )

    # Login security
    login_fail_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="连续登录失败次数"
    )
    lock_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="锁定截止时间"
    )
    last_login_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="最后登录时间"
    )
    last_login_ip: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="最后登录IP"
    )
    pwd_reset_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否需要重置密码"
    )

    # Token version for session invalidation (D5)
    # Reserved by B0a, used by B1 for password-change / leave / force-logout bump
    token_version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="令牌版本号，改密/离职/强制登出时递增",
    )

    # Source: LOCAL, DINGTALK, MIGRATED
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="LOCAL", comment="来源"
    )

    # 工号（FP-B1-BG-06）。钉钉 job_number，可空且不强制唯一。
    emp_no: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="工号"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "username", "deleted", name="uk_user_username"),
        Index("idx_user_mobile_hash", "mobile_hash"),
        Index("idx_user_status", "status"),
        Index("idx_user_emp_no", "tenant_id", "emp_no"),
    )


class UserDept(AssociationBase):
    """
    User-Department association (FP-B03-02).

    Table: ims_sys_user_dept

    Rules:
    - User can belong to multiple departments
    - Exactly one main department (is_main=1 matches user.main_dept_id)
    - Removing main department requires specifying a new one first
    - Users with no departments go to "待分配" system department
    """

    __tablename__ = "ims_sys_user_dept"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    dept_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    is_main: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="LOCAL", comment="DINGTALK/LOCAL"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "dept_id", name="uk_user_dept"),
    )


class UserMapping(AuditBase):
    """
    DingTalk user mapping (FP-B03-03).

    Table: ims_auth_user_mapping

    Rules:
    - One DingTalk userid maps to exactly one IMS user
    - One IMS user has at most one DingTalk mapping
    - DingTalk IDs are only stored here, not in business tables
    """

    __tablename__ = "ims_auth_user_mapping"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    dingtalk_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    union_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    dept_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="钉钉原始部门ID列表JSON"
    )
    sync_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    last_sync_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "dingtalk_user_id", "deleted", name="uk_mapping_dingtalk"),
        UniqueConstraint("tenant_id", "user_id", "deleted", name="uk_mapping_user"),
    )


class Dept(AuditBase):
    """
    Department model (FP-B08-01).

    Table: ims_sys_dept

    Rules:
    - Root department has parent_id=0
    - Path format: /1/5/12/ (includes self)
    - source=SYSTEM for "待分配", cannot be deleted/modified/moved/disabled
    - DINGTALK departments sync from DingTalk, local edits may be overwritten
    """

    __tablename__ = "ims_sys_dept"
    __track_changes__ = True

    parent_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="父部门ID,根为0"
    )
    path: Mapped[str] = mapped_column(
        String(500), nullable=False, default="/", comment="路径如/1/5/12/"
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="部门名称1-50字"
    )
    sort: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )
    leader_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="负责人用户ID"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ENABLED", comment="ENABLED/DISABLED"
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="LOCAL", comment="DINGTALK/LOCAL/SYSTEM"
    )
    dingtalk_dept_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="钉钉部门ID"
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="最后同步时间"
    )
    local_orphan: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="待确认本地部门标记"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "dingtalk_dept_id", "deleted",
            name="uk_dept_dingtalk"
        ),
        Index("idx_dept_parent", "parent_id"),
        Index("idx_dept_path", "path"),
    )


class Role(AuditBase):
    """
    Role model (FP-B04-01).

    Table: ims_sys_role

    Rules:
    - role_key must be unique per tenant
    - source: MANUAL (manual), DINGTALK_AUTO (auto from position)
    - status: ENABLED, DISABLED, PENDING_CONFIG
    - Standard roles (R1-R11) cannot be deleted
    - Roles with members cannot be deleted (error 1502, no cascade)
    """

    __tablename__ = "ims_sys_role"
    __track_changes__ = True

    role_key: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="角色标识"
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="角色名称"
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MANUAL", comment="MANUAL/DINGTALK_AUTO"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ENABLED",
        comment="ENABLED/DISABLED/PENDING_CONFIG"
    )
    data_scope: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="ALL/DEPT/IP_GROUP/SELF/空=未配置"
    )
    position_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="绑定岗位"
    )
    is_standard: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="标准角色R1-R11"
    )
    sort: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="备注"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "role_key", "deleted", name="uk_role_key"),
        UniqueConstraint("tenant_id", "position_code", "deleted", name="uk_role_position"),
    )


class Menu(PlatformBase):
    """
    Menu model (FP-B04-02).

    Table: ims_sys_menu

    Rules:
    - Platform-level data (tenant_id fixed to 1)
    - perm_code format: ims:<domain>:<resource>[:<action>]
    - MENU and BUTTON must have perm_code
    - perm_code must be globally unique
    """

    __tablename__ = "ims_sys_menu"

    parent_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="父菜单ID"
    )
    type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="DIR/MENU/BUTTON"
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="菜单名称"
    )
    perm_code: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="权限码"
    )
    path: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="路由路径"
    )
    component: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="组件路径"
    )
    icon: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="图标"
    )
    sort: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )
    visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否可见"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ENABLED", comment="状态"
    )

    __table_args__ = (
        UniqueConstraint("perm_code", "deleted", name="uk_menu_perm_code"),
        Index("idx_menu_parent", "parent_id"),
    )


class RoleMenu(AssociationBase):
    """
    Role-Menu association (FP-B04-03).

    Table: ims_sys_role_menu
    """

    __tablename__ = "ims_sys_role_menu"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    menu_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("role_id", "menu_id", name="uk_role_menu"),
    )


class RolePermDetail(AuditBase):
    """
    Role permission detail for R/W/D (FP-B04-03).

    Table: ims_role_perm_detail

    Rules:
    - W=1 or D=1 implies R=1
    """

    __tablename__ = "ims_role_perm_detail"

    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    perm_code: Mapped[str] = mapped_column(String(100), nullable=False)
    r: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="读")
    w: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="写")
    d: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="删")

    __table_args__ = (
        UniqueConstraint("role_id", "perm_code", name="uk_role_perm"),
    )


class UserRole(AssociationBase):
    """
    User-Role association (FP-B04-03).

    Table: ims_sys_user_role

    Rules:
    - User can have multiple roles
    - source: MANUAL (manual assignment), DINGTALK_AUTO (from position)
    - manual_removed=1 skips auto-supply for this user+role
    """

    __tablename__ = "ims_sys_user_role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MANUAL", comment="MANUAL/DINGTALK_AUTO"
    )
    manual_removed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="手工移除例外标记"
    )
    # 岗位供给扩展（FP-B1-BG-02/03）。本批只加列，供给逻辑在后续 PR。
    rule_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="授予来源规则"
    )
    rule_version: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="授予时的规则版本"
    )
    revoke_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="调岗缓冲到期回收时间"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uk_user_role"),
        Index("idx_user_role_rule", "rule_id"),
    )


class Tenant(PlatformBase):
    """
    Tenant model (FP-B04-04).

    Table: ims_sys_tenant

    Rules:
    - Platform-level data
    - tenant_id=1 is platform tenant with all menus
    - Disabled or expired tenant users cannot login (error 1008)
    """

    __tablename__ = "ims_sys_tenant"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="租户名称")
    package_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="套餐ID"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ENABLED", comment="状态"
    )
    expire_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="过期时间"
    )


class TenantPackage(PlatformBase):
    """
    Tenant package model (FP-B04-04).

    Table: ims_sys_tenant_package
    """

    __tablename__ = "ims_sys_tenant_package"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="套餐名称")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ENABLED", comment="状态"
    )


class TenantPackageMenu(AssociationBase):
    """
    Tenant package menu association (FP-B04-04).

    Table: ims_sys_tenant_package_menu
    """

    __tablename__ = "ims_sys_tenant_package_menu"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    package_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    menu_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("package_id", "menu_id", name="uk_package_menu"),
    )


class DictType(PlatformBase):
    """
    Dictionary type model (FP-B07-01).

    Table: ims_sys_dict_type

    Rules:
    - dict_type format: ^dict_[a-z][a-z0-9_]*$
    """

    __tablename__ = "ims_sys_dict_type"

    dict_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="字典类型"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="字典名称"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ENABLED", comment="状态"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="备注"
    )

    __table_args__ = (
        UniqueConstraint("dict_type", "deleted", name="uk_dict_type"),
    )


class DictData(PlatformBase):
    """
    Dictionary data model (FP-B07-01).

    Table: ims_sys_dict_data

    Rules:
    - dict_value format: ^[A-Z][A-Z0-9_]*$
    - color_type: primary|success|warning|danger|neutral|info|purple|yellow
    - Disabled values cannot be deleted (error 1502)
    - Built-in values (is_builtin=1) cannot be deleted or have dict_value changed
    """

    __tablename__ = "ims_sys_dict_data"

    dict_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="字典类型"
    )
    dict_value: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="字典值"
    )
    dict_label: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="字典标签"
    )
    color_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="neutral", comment="颜色类型"
    )
    sort: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ENABLED", comment="状态"
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否内置"
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="来源DINGTALK/LOCAL"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="备注"
    )

    __table_args__ = (
        UniqueConstraint("dict_type", "dict_value", "deleted", name="uk_dict_data"),
        Index("idx_dict_data_type", "dict_type"),
    )


class SysParam(PlatformBase):
    """
    System parameter model (FP-B07-02).

    Table: ims_sys_param

    Rules:
    - Parameters can only have values changed, not added/deleted/key changed
    - value_type: BOOLEAN, NUMBER, TEXT, ROLE_REF, ENUM, SECRET
    - SECRET values are encrypted and display masked
    - ROLE_REF references must exist (error 1500)
    - Unknown param_key on update returns error 1213
    """

    __tablename__ = "ims_sys_param"
    __track_changes__ = True

    param_key: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="参数键"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="参数名称"
    )
    group: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="参数分组"
    )
    value_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="BOOLEAN/NUMBER/TEXT/ROLE_REF/ENUM/SECRET"
    )
    value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="参数值"
    )
    default_value: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="默认值"
    )
    min_value: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="最小值"
    )
    max_value: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="最大值"
    )
    options: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="ENUM选项JSON"
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否内置"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="备注"
    )

    __table_args__ = (
        UniqueConstraint("param_key", "deleted", name="uk_param_key"),
    )


class OperateLog(AuditBase):
    """
    Operation log model (FP-F01-01).

    Table: ims_sys_operate_log

    Rules:
    - All write operations (non-GET) are automatically logged
    - Sensitive fields are masked
    - Logs are append-only, no update/delete
    - Retained for 180 days
    """

    __tablename__ = "ims_sys_operate_log"

    module: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="模块(路由tag中文)"
    )
    operation: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="操作(路由summary中文)"
    )
    object_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="对象类型"
    )
    object_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="对象ID"
    )
    result: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="SUCCESS/FAILED"
    )
    error_code: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="错误码"
    )
    ip: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="IP地址"
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="耗时毫秒"
    )
    request_path: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="请求路径"
    )
    request_method: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, comment="请求方法"
    )
    request_params: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="请求参数摘要(<=2KB)"
    )
    operator_name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="操作人姓名"
    )

    __table_args__ = (
        Index("idx_operate_log_time", "create_time"),
        Index("idx_operate_log_module", "module"),
    )


class LoginLog(AuditBase):
    """
    Login log model (FP-F01-02).

    Table: ims_sys_login_log

    Rules:
    - Records all login attempts
    - result: SUCCESS, BAD_CREDENTIAL, LOCKED, DISABLED, UNMAPPED, LOGOUT, KICKED
    - Retained for 180 days
    """

    __tablename__ = "ims_sys_login_log"

    username: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="用户名"
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="用户ID"
    )
    login_method: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="PASSWORD/DINGTALK"
    )
    result: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="结果"
    )
    ip: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="IP地址"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="User-Agent"
    )
    device: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="设备(解析自UA)"
    )

    __table_args__ = (
        Index("idx_login_log_time", "create_time"),
        Index("idx_login_log_user", "user_id"),
    )


class ChangeLog(AuditBase):
    """
    Field-level change log model (FP-F02-01).

    Table: ims_sys_change_log

    Rules:
    - Records field-level changes for tracked models
    - Sensitive field values are masked
    - reason: USER_EDIT, DINGTALK_OVERRIDE, SET_NULL_CASCADE, MIGRATION
    """

    __tablename__ = "ims_sys_change_log"

    biz_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="业务类型"
    )
    biz_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="业务ID"
    )
    field: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="字段名"
    )
    field_label: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="字段中文名"
    )
    before_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="变更前值"
    )
    after_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="变更后值"
    )
    reason: Mapped[str] = mapped_column(
        String(50), nullable=False, default="USER_EDIT", comment="变更原因"
    )

    __table_args__ = (
        Index("idx_change_log_biz", "biz_type", "biz_id"),
        Index("idx_change_log_time", "create_time"),
    )


class IntegrityIssue(AuditBase):
    """
    Reference integrity issue model (FP-B09-01).

    Table: ims_sys_integrity_issue
    """

    __tablename__ = "ims_sys_integrity_issue"

    scan_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    issue_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="ORPHAN/CROSS_TENANT/DISABLED_REF/CASCADE_MISSED"
    )
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    field: Mapped[str] = mapped_column(String(50), nullable=False)
    target_table: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    suggestion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", comment="OPEN/CLOSED"
    )
    last_seen_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class IntegrityScan(AuditBase):
    """
    Integrity scan batch model (FP-B09-01).

    Table: ims_sys_integrity_scan
    """

    __tablename__ = "ims_sys_integrity_scan"

    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tables_scanned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="RUNNING",
        comment="RUNNING/SUCCESS/FAILED"
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class OrgSyncBatch(AuditBase):
    """
    Organization sync batch model (FP-D07-04).

    Table: ims_sys_org_sync_batch

    Records each DingTalk sync operation with counts.
    """

    __tablename__ = "ims_sys_org_sync_batch"

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING",
        comment="PENDING/RUNNING/SUCCESS/FAILED"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="开始时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="完成时间"
    )
    added_depts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="新增部门数"
    )
    updated_depts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="更新部门数"
    )
    removed_depts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="删除部门数"
    )
    added_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="新增用户数"
    )
    updated_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="更新用户数"
    )
    removed_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="删除用户数"
    )
    error_msg: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    # B1 §0.5 加列。B0a 实现表名是 ims_sys_org_sync_batch，不另建 ims_auth_org_sync_batch。
    trigger_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="SCHEDULE/MANUAL"
    )
    operator_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="手动对账操作人"
    )
    diff_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="差异数"
    )
    fixed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="修正数"
    )
    fail_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="失败原因"
    )

    __table_args__ = (
        Index("idx_org_sync_batch_time", "started_at"),
    )


class TodoItem(AuditBase):
    """In-app todo created by position supply and org sync (FP-D05, FP-D07)."""

    __tablename__ = "ims_sys_todo"

    assignee_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    event_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")


class InboxMessage(AuditBase):
    """In-app message, including integrity scan notices (FP-B09)."""

    __tablename__ = "ims_sys_inbox"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")


class IdempotencyRecord(AuditBase):
    """Stored result of an idempotent request (FP-C04-03)."""

    __tablename__ = "ims_sys_idempotency"

    token: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "token", "deleted", name="uk_idem_token"),
    )


class StoredFile(AuditBase):
    """Uploaded file metadata (FP-E01)."""

    __tablename__ = "ims_file"

    scene: Mapped[str] = mapped_column(String(50), nullable=False)
    file_key: Mapped[str] = mapped_column(String(300), nullable=False)
    original_name: Mapped[str] = mapped_column(String(200), nullable=False)
    uploader_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    biz_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    biz_dept_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class WorkCalendarDay(AuditBase):
    """Holiday or extra workday (FP-H07)."""

    __tablename__ = "ims_work_calendar"

    day: Mapped[str] = mapped_column(String(10), nullable=False, comment="YYYY-MM-DD")
    kind: Mapped[str] = mapped_column(String(20), nullable=False, comment="HOLIDAY/WORKDAY")

    __table_args__ = (
        UniqueConstraint("tenant_id", "day", "deleted", name="uk_calendar_day"),
    )


class LeaveRecord(AuditBase):
    """Attendance leave row pulled from the attendance adapter (FP-H07)."""

    __tablename__ = "ims_att_leave"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    start_day: Mapped[str] = mapped_column(String(10), nullable=False)
    end_day: Mapped[str] = mapped_column(String(10), nullable=False)
    portion: Mapped[str] = mapped_column(String(10), nullable=False, default="1")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "start_day", "end_day", "deleted",
            name="uk_leave_span",
        ),
    )


class OutboxEvent(AuditBase):
    """Outbound sync event retried by the worker (FP-H06-04)."""

    __tablename__ = "ims_sys_outbox"

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="FAILED")
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class RefProbe(AuditBase):
    """Row scanned by the reference-integrity job (FP-B09)."""

    __tablename__ = "ims_ref_probe"

    dept_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    parent_probe_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    external_room_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class MigrationPending(AuditBase):
    """OPS rows that could not be imported (FP-H05-02)."""

    __tablename__ = "ims_mig_pending"

    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)


class ScopeSample(AuditBase):
    """Sample business row used to exercise data-scope rules (FP-C02)."""

    __tablename__ = "ims_scope_sample"
    __scope_fields__ = {
        "dept": "dept_id",
        "ip_group": "ip_group_id",
        "owner": "owner_user_id",
    }

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    dept_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ip_group_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    publish_dept_ids: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


class AttendanceSyncState(AuditBase):
    """Month-level attendance fetch status (FP-H07)."""

    __tablename__ = "ims_att_sync_state"

    month: Mapped[str] = mapped_column(String(7), nullable=False, comment="YYYY-MM")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OK")

    __table_args__ = (
        UniqueConstraint("tenant_id", "month", "deleted", name="uk_att_month"),
    )


class SeedApply(AuditBase):
    """种子已种过的标记（FP-H05-01）。

    默认授权写入后，管理员删除该授权不会在下次种子时被补回。
    """

    __tablename__ = "ims_sys_seed_apply"

    seed_key: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="种子项键"
    )

    __table_args__ = (
        UniqueConstraint("seed_key", "deleted", name="uk_seed_apply"),
    )


class PositionRoleRule(AuditBase):
    """岗位-角色供给规则（B0a FP-D05-01 + B1 §0.5）。

    本批只建表。供给、版本切换、归档不在本 PR。
    role_id 是主角色。
    """

    __tablename__ = "ims_auth_position_role_rule"

    position_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="岗位字典值"
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="主角色"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="当前版本"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ENABLED", comment="ENABLED/DISABLED"
    )
    archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否归档"
    )
    rule_name: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="规则名称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="说明"
    )

    __table_args__ = (
        Index("idx_position_rule_code", "position_code"),
        Index("idx_position_rule_role", "role_id"),
    )


class PositionRuleRole(AuditBase):
    """规则当前版本授予的角色（B1 §0.5）。

    唯一键带 deleted，便于逻辑删除后按同一规则和角色重建。
    """

    __tablename__ = "ims_auth_position_rule_role"

    rule_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="MAIN/EXTRA"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "rule_id", "role_id", "deleted",
            name="uk_position_rule_role",
        ),
    )


class PositionRuleVersion(AuditBase):
    """规则版本历史（B1 §0.5）。extra_role_ids 存 JSON 文本。"""

    __tablename__ = "ims_auth_position_rule_version"

    rule_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    main_role_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    extra_role_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="附加角色 ID 的 JSON 数组"
    )
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    change_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="CREATE/EDIT/ENABLE/DISABLE/REPLACED/ARCHIVE/UNARCHIVE/AUTO_CREATE",
    )
    operator_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "rule_id", "version", "deleted",
            name="uk_position_rule_version",
        ),
    )


class OrgSyncEvent(AuditBase):
    """组织同步事件（B0a FP-D07-01 + B1 §0.5）。本批只建表。"""

    __tablename__ = "ims_auth_org_sync_event"

    event_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="事件业务 ID")
    event_type: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="钉钉事件类型"
    )
    event_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="事件原文 JSON")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING",
        comment="PENDING/SUCCESS/RETRYING/DEAD",
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    biz_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="HIRE/TRANSFER/USER_UPDATE/RESIGN/DEPT_*"
    )
    subject_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    subject_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dept_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="数据范围用部门"
    )
    before_dept_names: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    after_dept_names: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    received_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processed_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delay_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "event_id", "deleted", name="uk_org_sync_event"
        ),
        Index("idx_org_sync_event_dept", "dept_id"),
        Index("idx_org_sync_event_status", "status"),
        Index("idx_org_sync_event_time", "event_time"),
    )


class OrgSyncEventAttempt(AuditBase):
    """事件处理时间线（B1 §0.5）。event_id 存事件表主键。"""

    __tablename__ = "ims_auth_org_sync_event_attempt"

    event_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="AUTO/RETRY/REPLAY"
    )
    operator_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="SUCCESS/FAIL"
    )
    error_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    error_msg: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class OrgSyncBatchItem(AuditBase):
    """对账明细（B1 §0.5）。本批只建表。"""

    __tablename__ = "ims_auth_org_sync_batch_item"

    batch_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="DEPT/USER/POSITION"
    )
    object_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    object_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dept_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    action: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    before_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="FIXED/FAILED/NOTICE"
    )
    error_msg: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


# Register shared-entity tables on the same metadata used by tests and Alembic.
from app.domains.shared import models as _shared_models  # noqa: E402, F401
