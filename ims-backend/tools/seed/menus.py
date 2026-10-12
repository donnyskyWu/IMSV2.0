"""
Menu seed data (FP-B04-02, FP-H05-01).

Menu tree with all ims:* permission codes.
Permission code format: ims:<domain>:<resource>[:<action>]
"""

from datetime import datetime

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
                "name": "组织同步",
                "type": "MENU",
                "path": "/system/org-sync",
                "component": "system/org-sync/index",
                "perm_code": "ims:system:org-sync:query",
                "sort": 7,
                "children": [
                    {"name": "执行同步", "type": "BUTTON", "perm_code": "ims:system:org-sync:run", "sort": 1},
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
    now = datetime.now()

    count = _seed_menu_tree(session, MENUS, parent_id=0, now=now)

    session.commit()
    return count


def _count_menus(menus: list) -> int:
    """Count total menu items."""
    count = len(menus)
    for m in menus:
        count += _count_menus(m.get("children", []))
    return count


def _seed_menu_tree(session, menus: list, parent_id: int, now: datetime) -> int:
    """Recursively seed menu tree."""
    from app.domains.sys.models import Menu

    count = 0

    for m in menus:
        # Find by perm_code or path
        existing = None
        if m.get("perm_code"):
            existing = session.query(Menu).filter(
                Menu.perm_code == m["perm_code"],
                Menu.deleted == 0,
            ).first()
        elif m.get("path"):
            existing = session.query(Menu).filter(
                Menu.path == m["path"],
                Menu.deleted == 0,
            ).first()

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

            # Seed children
            children = m.get("children", [])
            if children:
                count += _seed_menu_tree(session, children, menu.id, now)
        else:
            # Update parent_id if needed, seed children
            children = m.get("children", [])
            if children:
                count += _seed_menu_tree(session, children, existing.id, now)

    return count
