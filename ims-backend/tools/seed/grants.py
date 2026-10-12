"""B1 默认菜单授权（FP-B1-BG-07，FP-H05-01）。

版本: v1.0
日期: 2026-10-12

R1 授予本批全部权限码。R2、R4 只授予查询、导出、岗位规则查询。
「全部」指 01 §0.3 列出的本批权限码，不是系统管理下的全部菜单。

只补缺：
- 角色菜单关联已存在则不改、不删；
- 种子标记已写过、但关联被管理员删掉时，不再补回。
"""

from tools.seed.timeutil import seed_now

# 01 §0.3。查询码挂在菜单上，其余挂在按钮上。
B1_PERM_ALL = [
    "ims:system:org-sync:query",
    "ims:system:org-sync:run",
    "ims:system:org-sync:export",
    "ims:auth:position-rule:query",
    "ims:auth:position-rule:create",
    "ims:auth:position-rule:update",
    "ims:auth:position-rule:delete",
    "ims:auth:position-rule:refresh",
]

B1_PERM_READONLY = [
    "ims:system:org-sync:query",
    "ims:system:org-sync:export",
    "ims:auth:position-rule:query",
]

# 标准角色默认授权。键是种子 role_key，只用于查种子行，不在 app 业务代码里做角色判断。
DEFAULT_ROLE_PERMS = {
    "R1": B1_PERM_ALL,
    "R2": B1_PERM_READONLY,
    "R4": B1_PERM_READONLY,
}

# 02 §0.2 test_scope 使用的 E2E 角色，权限与 R2/R4 的本批只读码相同。
E2E_ROLE_PERMS = {
    "e2e_dept_view": B1_PERM_READONLY,
}

AUTH_DIR_PATH = "/ims/auth"


def planned_grant_count(env: str) -> int:
    """dry-run 预计新增的角色-菜单行数（含权限管理目录）。"""
    mapping = dict(DEFAULT_ROLE_PERMS)
    if env == "e2e":
        mapping.update(E2E_ROLE_PERMS)
    return sum(len(perms) + 1 for perms in mapping.values())


def seed_grants(env: str, dry_run: bool = False) -> int:
    """按 BG-07 补默认授权。重复执行不覆盖管理员改过的授权。"""
    if dry_run:
        count = planned_grant_count(env)
        print(f"  Would ensure {count} role-menu grants")
        return count

    from app.db.session import get_db_session
    from app.domains.sys.models import Menu, Role, RoleMenu, SeedApply

    session = get_db_session()
    now = seed_now()
    mapping = dict(DEFAULT_ROLE_PERMS)
    if env == "e2e":
        mapping.update(E2E_ROLE_PERMS)

    menus = session.query(Menu).filter(Menu.deleted == 0).all()
    by_perm = {menu.perm_code: menu for menu in menus if menu.perm_code}
    directory = next(
        (menu for menu in menus if menu.type == "DIR" and menu.path == AUTH_DIR_PATH),
        None,
    )

    count = 0
    for role_key, perm_codes in mapping.items():
        role = session.query(Role).filter(
            Role.tenant_id == 1,
            Role.role_key == role_key,
            Role.deleted == 0,
        ).first()
        if role is None:
            print(f"  skip grants, role missing: {role_key}")
            continue
        if directory is not None:
            count += _ensure_link(
                session, role, directory, f"grant:{role_key}:path:{AUTH_DIR_PATH}", now,
                RoleMenu, SeedApply,
            )
        for perm_code in perm_codes:
            menu = by_perm.get(perm_code)
            if menu is None:
                print(f"  skip grant, menu missing: {perm_code}")
                continue
            count += _ensure_link(
                session, role, menu, f"grant:{role_key}:perm:{perm_code}", now,
                RoleMenu, SeedApply,
            )

    session.commit()
    return count


def _ensure_link(session, role, menu, marker_key: str, now, role_menu_cls, marker_cls) -> int:
    """没有标记且没有关联时插入。已有关联或管理员已删除则返回 0。"""
    marker = session.query(marker_cls).filter(
        marker_cls.seed_key == marker_key,
        marker_cls.deleted == 0,
    ).first()
    link = session.query(role_menu_cls).filter(
        role_menu_cls.role_id == role.id,
        role_menu_cls.menu_id == menu.id,
    ).first()
    if link is not None:
        if marker is None:
            session.add(marker_cls(
                tenant_id=1,
                seed_key=marker_key,
                creator=0,
                create_time=now,
            ))
        return 0
    if marker is not None:
        return 0
    session.add(role_menu_cls(
        tenant_id=1,
        role_id=role.id,
        menu_id=menu.id,
        creator=0,
        create_time=now,
    ))
    session.add(marker_cls(
        tenant_id=1,
        seed_key=marker_key,
        creator=0,
        create_time=now,
    ))
    return 1
