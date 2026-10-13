# app/services/access.py - Permission decisions used by routes (FP-D03)
"""Load the effective permission set and fail closed with 1008."""

from typing import Any

from app.core.context import ctx
from app.core.errors import BizError
from app.db.ids import assign_pk
from app.db.session import get_db_session


def authorize(perm_code: str) -> None:
    """Raise 1008 when the current user does not hold ``perm_code``."""
    context = ctx.current_or_none
    if context is None or not context.is_authenticated:
        raise BizError(1008)
    if perm_code not in context.perm_codes:
        raise BizError(1008)


def load_permission_codes(user_id: int) -> set[str]:
    """Enabled roles only, intersected with the tenant package when one is set."""
    from app.domains.sys.models import Menu, Role, RoleMenu, Tenant, User, UserRole

    session = get_db_session()
    roles = session.query(Role).join(UserRole, UserRole.role_id == Role.id).filter(
        UserRole.user_id == user_id,
        Role.status == "ENABLED",
        Role.deleted == 0,
    ).all()
    menu_ids: set[int] = set()
    for role in roles:
        for link in session.query(RoleMenu).filter(RoleMenu.role_id == role.id).all():
            menu_ids.add(link.menu_id)
    user = session.query(User).filter(User.id == user_id).first()
    tenant = None
    if user is not None:
        tenant = session.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if tenant is not None and tenant.package_id:
        from app.domains.sys.models import TenantPackageMenu

        allowed = {
            row.menu_id
            for row in session.query(TenantPackageMenu).filter(
                TenantPackageMenu.package_id == tenant.package_id,
            ).all()
        }
        menu_ids &= allowed
    if not menu_ids:
        return set()
    codes = set()
    for menu in session.query(Menu).filter(
        Menu.id.in_(menu_ids),
        Menu.status == "ENABLED",
        Menu.deleted == 0,
    ).all():
        if menu.perm_code:
            codes.add(menu.perm_code)
    return codes


def grant_menu(role_id: int, menu_id: int) -> None:
    """Attach a menu to a role and drop cached permission sets immediately."""
    from app.domains.sys.models import RoleMenu

    session = get_db_session()
    existing = session.query(RoleMenu).filter(
        RoleMenu.role_id == role_id,
        RoleMenu.menu_id == menu_id,
    ).first()
    if existing is None:
        link = RoleMenu(tenant_id=ctx.tenant_id, role_id=role_id, menu_id=menu_id)
        assign_pk(session, link)
        session.add(link)
        session.flush()
    _drop_cache(session, role_id)


def revoke_menu(role_id: int, menu_id: int) -> None:
    """Remove a menu from a role and drop cached permission sets immediately."""
    from app.domains.sys.models import RoleMenu

    session = get_db_session()
    session.query(RoleMenu).filter(
        RoleMenu.role_id == role_id,
        RoleMenu.menu_id == menu_id,
    ).delete()
    session.flush()
    _drop_cache(session, role_id)


def _drop_cache(session: Any, role_id: int) -> None:
    """Bump perm version for all users with this role (FP-D03-04).

    Uses version-based invalidation instead of Cache.delete.
    When permissions are read, the version is compared and cache is
    reloaded if mismatched.
    """
    from app.domains.sys.models import UserRole
    from app.services.auth import AuthService

    for link in session.query(UserRole).filter(UserRole.role_id == role_id).all():
        AuthService.bump_user_perm_version(link.user_id)
