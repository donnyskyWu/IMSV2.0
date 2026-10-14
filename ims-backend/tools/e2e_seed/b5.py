# B5 E2E 造数。版本 v1.0 · 2026-10-13
"""生产环境拒绝执行。密码 Test1234。证件删除不授给资源管理员。"""

from __future__ import annotations

import os

import bcrypt

from app.db.ids import assign_pk
from app.db.session import get_db_session
from app.domains.sys.models import Menu, Role, RoleMenu, User, UserRole

PASSWORD = "Test1234"


def assert_e2e_env() -> None:
    """IMS_ENV=prod 时拒绝。"""
    if os.getenv("IMS_ENV") == "prod":
        raise RuntimeError("拒绝在生产环境执行 B5 造数")


def seed_e2e_users() -> None:
    """在已有租户上补测试角色。不写标准角色 R2～R11。"""
    assert_e2e_env()
    session = get_db_session()
    digest = bcrypt.hashpw(PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    specs = [
        ("test_admin", "e2e_super", "测试-超管", "ALL", True),
        ("test_xz", "e2e_resource_admin", "测试-资源管理员", "ALL", False),
        ("test_xz2", "e2e_resource_admin", "测试-资源管理员", "ALL", False),
        ("test_ro", "e2e_readonly", "测试-只读", "ALL", False),
        ("test_self", "e2e_self", "测试-本人", "SELF", False),
        ("test_yg", "e2e_none", "测试-无权限", "SELF", False),
    ]
    for username, role_key, role_name, scope, is_admin in specs:
        role = session.query(Role).filter(Role.role_key == role_key, Role.deleted == 0).first()
        if role is None:
            role = Role(
                tenant_id=1,
                role_key=role_key,
                name=role_name,
                source="MANUAL",
                status="ENABLED",
                data_scope=scope,
            )
            assign_pk(session, role)
            session.add(role)
            session.flush()
        user = session.query(User).filter(User.username == username, User.deleted == 0).first()
        if user is None:
            user = User(
                tenant_id=1,
                username=username,
                nickname=role_name,
                password_hash=digest,
                status="ACTIVE",
                source="LOCAL",
            )
            assign_pk(session, user)
            session.add(user)
            session.flush()
        if session.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first() is None:
            link = UserRole(tenant_id=1, user_id=user.id, role_id=role.id)
            assign_pk(session, link)
            session.add(link)
        if is_admin:
            _grant_all_b5(session, role.id)
        elif role_key == "e2e_resource_admin":
            _grant_codes(session, role.id, _resource_codes())
        elif role_key == "e2e_readonly":
            _grant_codes(session, role.id, ["ims:cert:archive:query", "ims:corp:company:query"])
        elif role_key == "e2e_self":
            _grant_codes(session, role.id, ["ims:cert:archive:query-self"])
    session.flush()


def _resource_codes() -> list[str]:
    """档案 query / upload / review，不含 delete。"""
    return [
        "ims:corp:company:query",
        "ims:corp:company:create",
        "ims:corp:company:update",
        "ims:cert:archive:query",
        "ims:cert:archive:upload",
        "ims:cert:archive:review",
        "ims:cert:expire:query",
        "ims:cert:expire:renew",
        "ims:cert:security:audit",
    ]


def _grant_all_b5(session, role_id: int) -> None:
    from tools.seed.b5 import B5_PERMS
    _grant_codes(session, role_id, [code for code, _label in B5_PERMS])


def _grant_codes(session, role_id: int, codes: list[str]) -> None:
    for code in codes:
        menu = session.query(Menu).filter(Menu.perm_code == code, Menu.deleted == 0).first()
        if menu is None:
            menu = Menu(
                tenant_id=1,
                parent_id=0,
                name=code,
                type="BUTTON",
                status="ENABLED",
                perm_code=code,
            )
            assign_pk(session, menu)
            session.add(menu)
            session.flush()
        if session.query(RoleMenu).filter(RoleMenu.role_id == role_id, RoleMenu.menu_id == menu.id).first() is None:
            link = RoleMenu(tenant_id=1, role_id=role_id, menu_id=menu.id)
            assign_pk(session, link)
            session.add(link)
