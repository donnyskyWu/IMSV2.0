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
    Column,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditBase, AssociationBase, PlatformBase


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
    
    # Source: LOCAL, DINGTALK, MIGRATED
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="LOCAL", comment="来源"
    )
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", "deleted", name="uk_user_username"),
        Index("idx_user_mobile_hash", "mobile_hash"),
        Index("idx_user_status", "status"),
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
    
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uk_user_role"),
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
