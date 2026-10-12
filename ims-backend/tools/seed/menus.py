"""
Menu seed data (FP-B04-02, FP-H05-01, FP-B1-BG-07).

Menu tree with all ims:* permission codes.
Permission code format: ims:<domain>:<resource>[:<action>]

已有菜单不改名称、排序、图标。
parent_id 仍是 0、而种子父级不是根时，补成目录 → 菜单 → 按钮。
已经挂到别的父级视为管理员调整，不再改。
B0a 的「组织同步」若名称和路径都还是占位值，才同时改名称和路径。
"""

from tools.seed.timeutil import seed_now

# B0a 占位。只有名称和路径都没被改过，才迁到 B1 菜单。
B0A_ORG_MENU = {
    "name": "组织同步",
    "path": "/system/org-sync",
    "perm_code": "ims:system:org-sync:query",
}

# Menu tree structure
# type: DIR (directory), MENU (page), BUTTON (action)
MENUS = [
    # 系统管理
    {
        "name": "系统管理",
        "type": "DIR",
        "path": "/system",
        "icon": "setting",
        "sort": 1,
        "children": [
            {
                "name": "部门管理",
                "type": "MENU",
                "path": "/system/dept",
                "component": "system/dept/index",
                "perm_code": "ims:system:dept:query",
                "sort": 1,
                "children": [
                    {"name": "新建部门", "type": "BUTTON", "perm_code": "ims:system:dept:create", "sort": 1},
                    {"name": "编辑部门", "type": "BUTTON", "perm_code": "ims:system:dept:update", "sort": 2},
                    {"name": "删除部门", "type": "BUTTON", "perm_code": "ims:system:dept:delete", "sort": 3},
                ],
            },
            {
                "name": "用户管理",
                "type": "MENU",
                "path": "/system/user",
                "component": "system/user/index",
                "perm_code": "ims:system:user:query",
                "sort": 2,
                "children": [
                    {"name": "新建用户", "type": "BUTTON", "perm_code": "ims:system:user:create", "sort": 1},
                    {"name": "编辑用户", "type": "BUTTON", "perm_code": "ims:system:user:update", "sort": 2},
                    {"name": "删除用户", "type": "BUTTON", "perm_code": "ims:system:user:delete", "sort": 3},
                    {"name": "强制下线", "type": "BUTTON", "perm_code": "ims:system:user:kick", "sort": 4},
                    {"name": "解锁账号", "type": "BUTTON", "perm_code": "ims:system:user:unlock", "sort": 5},
                ],
            },
            {
                "name": "角色管理",
                "type": "MENU",
                "path": "/system/role",
                "component": "system/role/index",
                "perm_code": "ims:system:role:query",
                "sort": 3,
                "children": [
                    {"name": "新建角色", "type": "BUTTON", "perm_code": "ims:system:role:create", "sort": 1},
                    {"name": "编辑角色", "type": "BUTTON", "perm_code": "ims:system:role:update", "sort": 2},
                    {"name": "删除角色", "type": "BUTTON", "perm_code": "ims:system:role:delete", "sort": 3},
                ],
            },
            {
                "name": "菜单管理",
                "type": "MENU",
                "path": "/system/menu",
                "component": "system/menu/index",
                "perm_code": "ims:system:menu:query",
                "sort": 4,
                "children": [
                    {"name": "新建菜单", "type": "BUTTON", "perm_code": "ims:system:menu:create", "sort": 1},
                    {"name": "编辑菜单", "type": "BUTTON", "perm_code": "ims:system:menu:update", "sort": 2},
                    {"name": "删除菜单", "type": "BUTTON", "perm_code": "ims:system:menu:delete", "sort": 3},
                ],
            },
            {
                "name": "字典管理",
                "type": "MENU",
                "path": "/system/dict",
                "component": "system/dict/index",
                "perm_code": "ims:system:dict:query",
                "sort": 5,
                "children": [
                    {"name": "新建字典", "type": "BUTTON", "perm_code": "ims:system:dict:create", "sort": 1},
                    {"name": "编辑字典", "type": "BUTTON", "perm_code": "ims:system:dict:update", "sort": 2},
                    {"name": "删除字典", "type": "BUTTON", "perm_code": "ims:system:dict:delete", "sort": 3},
                ],
            },
            {
                "name": "参数设置",
                "type": "MENU",
                "path": "/system/param",
                "component": "system/param/index",
                "perm_code": "ims:system:param:query",
                "sort": 6,
                "children": [
                    {"name": "修改参数", "type": "BUTTON", "perm_code": "ims:system:param:update", "sort": 1},
                ],
            },
            {
                "name": "操作日志",
                "type": "MENU",
                "path": "/system/operate-log",
                "component": "system/operate-log/index",
                "perm_code": "ims:system:operate-log:query",
                "sort": 8,
            },
            {
                "name": "登录日志",
                "type": "MENU",
                "path": "/system/login-log",
                "component": "system/login-log/index",
                "perm_code": "ims:system:login-log:query",
                "sort": 9,
            },
            {
                "name": "数据完整性",
                "type": "MENU",
                "path": "/system/integrity",
                "component": "system/integrity/index",
                "perm_code": "ims:system:integrity:query",
                "sort": 10,
                "children": [
                    {"name": "执行检查", "type": "BUTTON", "perm_code": "ims:system:integrity:run", "sort": 1},
                ],
            },
            {
                "name": "工作日历",
                "type": "MENU",
                "path": "/system/calendar",
                "component": "system/calendar/index",
                "perm_code": "ims:system:calendar:query",
                "sort": 11,
                "children": [
                    {"name": "编辑日历", "type": "BUTTON", "perm_code": "ims:system:calendar:update", "sort": 1},
                ],
            },
        ],
    },
    # Q18：工作台到 B3 才有菜单。在此之前「权限管理」排第 2（系统管理 sort=1）是允许的。
    {
        "name": "权限管理",
        "type": "DIR",
        "path": "/ims/auth",
        "icon": "lock",
        "sort": 2,
        "children": [
            {
                "name": "组织架构同步",
                "type": "MENU",
                "path": "/ims/auth/org",
                "component": "ims/auth/org/index",
                "perm_code": "ims:system:org-sync:query",
                "sort": 1,
                "children": [
                    {"name": "执行同步", "type": "BUTTON", "perm_code": "ims:system:org-sync:run", "sort": 1},
                    {"name": "导出", "type": "BUTTON", "perm_code": "ims:system:org-sync:export", "sort": 2},
                ],
            },
            {
                "name": "岗位-角色供给规则",
                "type": "MENU",
                "path": "/ims/auth/position",
                "component": "ims/auth/position/index",
                "perm_code": "ims:auth:position-rule:query",
                "sort": 2,
                "children": [
                    {"name": "新建规则", "type": "BUTTON", "perm_code": "ims:auth:position-rule:create", "sort": 1},
                    {"name": "编辑规则", "type": "BUTTON", "perm_code": "ims:auth:position-rule:update", "sort": 2},
                    {"name": "删除规则", "type": "BUTTON", "perm_code": "ims:auth:position-rule:delete", "sort": 3},
                    {"name": "按新版本刷新", "type": "BUTTON", "perm_code": "ims:auth:position-rule:refresh", "sort": 4},
                ],
            },
        ],
    },
]


def seed_menus(env: str, dry_run: bool = False) -> int:
    """
    Seed menu tree.

    Rules per FP-H05-01:
    - Upsert by perm_code (for MENU/BUTTON) or path (for DIR)
    - Does not overwrite admin-modified fields (name, sort, icon)

    Returns:
        Number of records upserted
    """
    if dry_run:
        count = _count_menus(MENUS)
        print(f"  Would seed {count} menu items")
        return count

    from app.db.session import get_db_session

    session = get_db_session()
    now = seed_now()

    count = _seed_menu_tree(session, MENUS, parent_id=0, now=now)

    session.commit()
    return count


def _count_menus(menus: list) -> int:
    """Count total menu items."""
    count = len(menus)
    for m in menus:
        count += _count_menus(m.get("children", []))
    return count


def _seed_menu_tree(session, menus: list, parent_id: int, now) -> int:
    """递归补菜单。已有行不改名称、排序、图标。"""
    from app.domains.sys.models import Menu

    count = 0

    for m in menus:
        existing = _find_menu(session, Menu, m)

        if not existing:
            menu = Menu(
                tenant_id=1,
                parent_id=parent_id,
                type=m["type"],
                name=m["name"],
                perm_code=m.get("perm_code"),
                path=m.get("path"),
                component=m.get("component"),
                icon=m.get("icon"),
                sort=m.get("sort", 0),
                visible=True,
                status="ENABLED",
                creator=0,
                create_time=now,
            )
            session.add(menu)
            session.flush()
            count += 1
            children = m.get("children", [])
            if children:
                count += _seed_menu_tree(session, children, menu.id, now)
            continue

        # 仍是 B0a 占位时迁到权限管理。管理员改过名称或路径则不改这两项。
        if _is_untouched_b0a_org(existing, m):
            existing.parent_id = parent_id
            existing.name = m["name"]
            existing.path = m.get("path")
            existing.component = m.get("component")
        elif _needs_flat_parent(existing, parent_id):
            existing.parent_id = parent_id
        children = m.get("children", [])
        if children:
            count += _seed_menu_tree(session, children, existing.id, now)

    return count


def _find_menu(session, menu_cls, item: dict):
    """按钮和菜单按权限码找，目录按路径找。"""
    if item.get("perm_code"):
        return session.query(menu_cls).filter(
            menu_cls.perm_code == item["perm_code"],
            menu_cls.deleted == 0,
        ).first()
    if item.get("path"):
        return session.query(menu_cls).filter(
            menu_cls.path == item["path"],
            menu_cls.type == item["type"],
            menu_cls.deleted == 0,
        ).first()
    return None


def _needs_flat_parent(existing, parent_id: int) -> bool:
    """旧数据挂在根上时补父级。父级已经不是 0，说明管理员移动过，保持不动。"""
    return bool(parent_id) and (existing.parent_id or 0) == 0


def _is_untouched_b0a_org(existing, item: dict) -> bool:
    """名称和路径仍等于 B0a 种子时，才允许迁到 B1 路径。"""
    return (
        item.get("perm_code") == B0A_ORG_MENU["perm_code"]
        and existing.name == B0A_ORG_MENU["name"]
        and existing.path == B0A_ORG_MENU["path"]
    )
