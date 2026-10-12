# tests/support/rows.py - Row builders for spec tests
"""Insert models with explicit ids so SQLite BIGINT keys succeed."""

from app.db.ids import assign_pk


def add(session, obj):
    assign_pk(session, obj)
    session.add(obj)
    session.flush()
    return obj


def dept(session, name, parent=None, source="LOCAL", status="ENABLED", ding=None, tenant_id=1):
    from app.domains.sys.models import Dept

    row = Dept(
        tenant_id=tenant_id,
        parent_id=0 if parent is None else parent.id,
        name=name,
        path="/",
        source=source,
        status=status,
        dingtalk_dept_id=ding,
    )
    add(session, row)
    prefix = "/" if parent is None else parent.path
    row.path = f"{prefix}{row.id}/"
    session.flush()
    return row


def user(session, username, nickname="用户", status="ACTIVE", tenant_id=1, **extra):
    from app.domains.sys.models import User

    row = User(
        tenant_id=tenant_id,
        username=username,
        nickname=nickname,
        status=status,
        source=extra.pop("source", "LOCAL"),
        **extra,
    )
    return add(session, row)


def link(session, user_id, dept_id, is_main=False, source="LOCAL", tenant_id=1):
    from app.domains.sys.models import UserDept

    return add(session, UserDept(
        tenant_id=tenant_id,
        user_id=user_id,
        dept_id=dept_id,
        is_main=is_main,
        source=source,
    ))


def role(session, key, name, **extra):
    from app.domains.sys.models import Role

    row = Role(
        tenant_id=extra.pop("tenant_id", 1),
        role_key=key,
        name=name,
        source=extra.pop("source", "MANUAL"),
        status=extra.pop("status", "ENABLED"),
        **extra,
    )
    return add(session, row)


def menu(session, name, perm, type_="BUTTON"):
    from app.domains.sys.models import Menu

    return add(session, Menu(
        tenant_id=1,
        parent_id=0,
        type=type_,
        name=name,
        perm_code=perm,
        status="ENABLED",
    ))


def bind_menu(session, role_id, menu_id):
    from app.domains.sys.models import RoleMenu

    return add(session, RoleMenu(tenant_id=1, role_id=role_id, menu_id=menu_id))


def bind_role(session, user_id, role_id, source="MANUAL", removed=False):
    from app.domains.sys.models import UserRole

    return add(session, UserRole(
        tenant_id=1,
        user_id=user_id,
        role_id=role_id,
        source=source,
        manual_removed=removed,
    ))
