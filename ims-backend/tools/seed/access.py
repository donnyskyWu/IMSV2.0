"""默认租户套餐、套餐菜单，以及 R1 的角色菜单。

只补当前库里已经有的菜单，不新增菜单、不写 B1 权限码，
也不给 R2/R4/R10 授权。已有行和已改过的套餐字段保持原样。
"""

from app.core.clock import get_now

# 平台租户还没挂套餐时使用的名称。租户已经指定套餐后不再按这个名字新建。
DEFAULT_PACKAGE_NAME = "默认套餐"


def seed_access(env: str, dry_run: bool = False) -> int:
    """补默认套餐、套餐-菜单、R1 角色-菜单。返回新插入的行数。"""
    if dry_run:
        from tools.seed.menus import MENUS, _count_menus

        menu_count = _count_menus(MENUS)
        print(f"  Would ensure default package and {menu_count} menu grants for R1")
        return 1 + menu_count * 2

    from app.db.session import get_db_session
    from app.domains.sys.models import (
        Menu,
        Role,
        RoleMenu,
        Tenant,
        TenantPackage,
        TenantPackageMenu,
    )

    session = get_db_session()
    now = get_now()
    inserted = 0

    tenant = session.query(Tenant).filter(Tenant.id == 1, Tenant.deleted == 0).first()
    package = _resolve_package(session, tenant)
    if package is None:
        package = TenantPackage(
            tenant_id=1,
            name=DEFAULT_PACKAGE_NAME,
            status="ENABLED",
            creator=0,
            create_time=now,
        )
        session.add(package)
        session.flush()
        inserted += 1

    # 只在租户还没有套餐时挂上，管理员改过的 package_id 不动。
    if tenant is not None and not tenant.package_id:
        tenant.package_id = package.id
        session.flush()

    role = session.query(Role).filter(
        Role.tenant_id == 1,
        Role.role_key == "R1",
        Role.deleted == 0,
    ).first()
    if role is None:
        raise RuntimeError("R1 role is missing; seed roles before access grants")

    menus = session.query(Menu).filter(Menu.deleted == 0).all()
    menu_ids = [menu.id for menu in menus]

    # 一次取出已有关联，按差集插入，避免逐条查询。
    package_menu_ids = {
        row.menu_id
        for row in session.query(TenantPackageMenu.menu_id).filter(
            TenantPackageMenu.package_id == package.id,
        )
    }
    role_menu_ids = {
        row.menu_id
        for row in session.query(RoleMenu.menu_id).filter(RoleMenu.role_id == role.id)
    }

    for menu_id in menu_ids:
        if menu_id not in package_menu_ids:
            session.add(TenantPackageMenu(
                tenant_id=1,
                package_id=package.id,
                menu_id=menu_id,
                creator=0,
                create_time=now,
            ))
            inserted += 1
        if menu_id not in role_menu_ids:
            session.add(RoleMenu(
                tenant_id=1,
                role_id=role.id,
                menu_id=menu_id,
                creator=0,
                create_time=now,
            ))
            inserted += 1

    session.commit()
    return inserted


def _resolve_package(session, tenant):
    """优先用租户已经挂上的套餐，其次按默认名称查找。都没有则返回 None。"""
    from app.domains.sys.models import TenantPackage

    if tenant is not None and tenant.package_id:
        linked = session.query(TenantPackage).filter(
            TenantPackage.id == tenant.package_id,
            TenantPackage.deleted == 0,
        ).first()
        if linked is not None:
            return linked

    return session.query(TenantPackage).filter(
        TenantPackage.name == DEFAULT_PACKAGE_NAME,
        TenantPackage.deleted == 0,
    ).first()
