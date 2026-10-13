# B5 权限只补到 R1。版本 v1.0 · 2026-10-13
"""只补缺，不覆盖已有菜单。写完后递增租户权限版本。"""

from __future__ import annotations

from app.core.cache import Cache
from app.db.ids import assign_pk
from app.db.session import get_db_session
from app.domains.sys.models import Menu, Role, RoleMenu

# 本批权限码。删除和级别配置只出现在这份清单里，种子只授给 R1。
B5_PERMS = [
    ("ims:corp:company:query", "公司查询"),
    ("ims:corp:company:create", "公司新建"),
    ("ims:corp:company:update", "公司编辑"),
    ("ims:corp:company:expand", "公司扩容"),
    ("ims:corp:company:export", "公司导出"),
    ("ims:corp:realname:query", "实名人查询"),
    ("ims:corp:realname:create", "实名人新建"),
    ("ims:corp:realname:update", "实名人编辑"),
    ("ims:corp:realname:delete", "实名人删除"),
    ("ims:corp:realname:export", "实名人导出"),
    ("ims:corp:realname:commission", "佣金查看"),
    ("ims:corp:sim:query", "手机卡查询"),
    ("ims:corp:sim:create", "手机卡新建"),
    ("ims:corp:sim:update", "手机卡编辑"),
    ("ims:corp:sim:delete", "手机卡删除"),
    ("ims:corp:sim:export", "手机卡导出"),
    ("ims:cert:archive:query", "证件查询"),
    ("ims:cert:archive:query-self", "证件查本人"),
    ("ims:cert:archive:upload", "证件上传"),
    ("ims:cert:archive:review", "证件审核"),
    ("ims:cert:archive:delete", "证件删除"),
    ("ims:cert:expire:query", "到期查询"),
    ("ims:cert:expire:scan", "到期扫描"),
    ("ims:cert:expire:renew", "到期换证"),
    ("ims:cert:expire:remind", "到期催办"),
    ("ims:cert:security:config", "级别配置"),
    ("ims:cert:security:audit", "证件审计"),
]


def grant_b5_to_r1() -> int:
    """给每个租户的 R1 补齐权限，并递增该租户的权限版本。返回新授权条数。"""
    session = get_db_session()
    roles = session.query(Role).filter(Role.role_key == "R1", Role.deleted == 0).all()
    added = 0
    tenants = set()
    for role in roles:
        tenants.add(role.tenant_id)
        for code, label in B5_PERMS:
            menu = session.query(Menu).filter(Menu.perm_code == code, Menu.deleted == 0).first()
            if menu is None:
                menu = Menu(
                    tenant_id=role.tenant_id,
                    parent_id=0,
                    name=label,
                    type="BUTTON",
                    status="ENABLED",
                    perm_code=code,
                    sort=3,
                )
                assign_pk(session, menu)
                session.add(menu)
                session.flush()
            link = session.query(RoleMenu).filter(
                RoleMenu.role_id == role.id,
                RoleMenu.menu_id == menu.id,
            ).first()
            if link is None:
                link = RoleMenu(tenant_id=role.tenant_id, role_id=role.id, menu_id=menu.id)
                assign_pk(session, link)
                session.add(link)
                added += 1
    session.flush()
    for tid in tenants:
        Cache.incr(f"ims:perm_ver:t:{tid}")
    return added
