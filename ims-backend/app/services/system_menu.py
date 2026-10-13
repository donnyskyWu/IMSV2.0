# app/services/system_menu.py - Menu management service (B2-M02)
"""
Menu management service.

Implements M-01 to M-04 from the B2 system management module:
- Menu tree query
- Menu CRUD operations
- Visibility toggle
"""

from typing import Any, Optional

from app.core.cache import Cache
from app.core.context import ctx
from app.core.errors import BizError
from app.db.session import get_db_session
from app.db.transaction import transactional


class SystemMenuService:
    """Menu management service for B2 system management."""

    def _bump_tenant_perm_version(self, tenant_id: int) -> None:
        """Increment tenant permission version when menu visibility changes."""
        Cache.incr(f"ims:perm_ver:t:{tenant_id}")

    async def get_menu_tree(self, keyword: Optional[str] = None) -> list[dict[str, Any]]:
        """Get full menu tree (M-01). Platform tenant only."""
        from app.domains.sys.models import Menu

        session = get_db_session()
        tenant_id = ctx.tenant_id

        # Menu management is platform-only
        if tenant_id != 1:
            raise BizError(1008)

        query = session.query(Menu).filter(
            Menu.deleted == 0,
        )

        if keyword:
            query = query.filter(Menu.name.like(f"%{keyword}%"))

        menus = query.order_by(Menu.sort, Menu.id).all()

        # Build tree
        return self._build_tree(menus)

    def _build_tree(self, menus: list) -> list[dict[str, Any]]:
        """Build nested tree from flat menu list."""
        nodes = {}
        for menu in menus:
            nodes[menu.id] = {
                "id": str(menu.id),
                "parent_id": str(menu.parent_id) if menu.parent_id else None,
                "type": menu.type,
                "name": menu.name,
                "perm_code": menu.perm_code,
                "path": menu.path,
                "component": menu.component,
                "icon": menu.icon,
                "sort": menu.sort or 0,
                "visible": menu.visible,
                "status": menu.status,
                "children": [],
            }

        roots = []
        for menu in menus:
            node = nodes[menu.id]
            parent = nodes.get(menu.parent_id)
            if parent is None:
                roots.append(node)
            else:
                parent["children"].append(node)

        def sort_children(items: list) -> None:
            items.sort(key=lambda x: (x["sort"], int(x["id"])))
            for item in items:
                sort_children(item["children"])

        sort_children(roots)
        return roots

    @transactional
    async def create_menu(self, request: Any) -> dict[str, Any]:
        """Create a new menu (M-02)."""
        from app.db.ids import assign_pk
        from app.domains.sys.models import Menu

        session = get_db_session()
        tenant_id = ctx.tenant_id

        # Platform-only
        if tenant_id != 1:
            raise BizError(1008)

        # Validate parent exists (if specified)
        if request.parent_id and int(request.parent_id) != 0:
            parent = session.query(Menu).filter(
                Menu.id == int(request.parent_id),
                Menu.deleted == 0,
            ).first()
            if not parent:
                raise BizError(1500)

        # Validate perm_code format and uniqueness
        if request.perm_code:
            # Format: ims:<domain>:<resource>[:<action>]
            if not request.perm_code.startswith("ims:"):
                raise BizError(1001, msg="权限码格式错误")

            existing = session.query(Menu).filter(
                Menu.perm_code == request.perm_code,
                Menu.deleted == 0,
            ).first()
            if existing:
                raise BizError(1001, msg="权限码已存在")

        menu = Menu(
            tenant_id=1,  # Always platform
            parent_id=int(request.parent_id) if request.parent_id else 0,
            type=request.type,
            name=request.name,
            perm_code=getattr(request, 'perm_code', None),
            path=getattr(request, 'path', None),
            component=getattr(request, 'component', None),
            icon=getattr(request, 'icon', None),
            sort=getattr(request, 'sort', 0),
            visible=getattr(request, 'visible', True),
            status="ENABLED",
        )
        assign_pk(session, menu)
        session.add(menu)
        session.flush()

        return {
            "id": str(menu.id),
            "name": menu.name,
            "type": menu.type,
            "perm_code": menu.perm_code,
        }

    @transactional
    async def update_menu(self, menu_id: str, request: Any) -> dict[str, Any]:
        """Update menu (M-02)."""
        from app.domains.sys.models import Menu

        session = get_db_session()
        tenant_id = ctx.tenant_id
        menu_id_int = int(menu_id)

        # Platform-only
        if tenant_id != 1:
            raise BizError(1008)

        menu = session.query(Menu).filter(
            Menu.id == menu_id_int,
            Menu.deleted == 0,
        ).first()

        if not menu:
            raise BizError(1504)

        # Update fields
        if hasattr(request, 'name') and request.name:
            menu.name = request.name
        if hasattr(request, 'path'):
            menu.path = request.path
        if hasattr(request, 'component'):
            menu.component = request.component
        if hasattr(request, 'icon'):
            menu.icon = request.icon
        if hasattr(request, 'sort') is not None:
            menu.sort = request.sort
        if hasattr(request, 'visible') is not None:
            old_visible = menu.visible
            menu.visible = request.visible
            # Visibility change affects permissions
            if old_visible != menu.visible:
                self._bump_tenant_perm_version(1)

        session.flush()

        return {
            "id": str(menu.id),
            "name": menu.name,
            "type": menu.type,
            "perm_code": menu.perm_code,
            "visible": menu.visible,
        }

    @transactional
    async def update_menu_visible(self, menu_id: str, visible: bool) -> None:
        """Toggle menu visibility (M-03)."""
        from app.domains.sys.models import Menu

        session = get_db_session()
        tenant_id = ctx.tenant_id
        menu_id_int = int(menu_id)

        # Platform-only
        if tenant_id != 1:
            raise BizError(1008)

        menu = session.query(Menu).filter(
            Menu.id == menu_id_int,
            Menu.deleted == 0,
        ).first()

        if not menu:
            raise BizError(1504)

        menu.visible = visible
        session.flush()

        # Bump tenant permission version
        self._bump_tenant_perm_version(1)

    @transactional
    async def delete_menu(self, menu_id: str) -> None:
        """Delete menu (M-04)."""
        from app.domains.sys.models import Menu, RoleMenu, TenantPackageMenu

        session = get_db_session()
        tenant_id = ctx.tenant_id
        menu_id_int = int(menu_id)

        # Platform-only
        if tenant_id != 1:
            raise BizError(1008)

        menu = session.query(Menu).filter(
            Menu.id == menu_id_int,
            Menu.deleted == 0,
        ).first()

        if not menu:
            raise BizError(1504)

        # Cannot delete menu with children
        child_count = session.query(Menu).filter(
            Menu.parent_id == menu_id_int,
            Menu.deleted == 0,
        ).count()

        if child_count:
            raise BizError(1502, refs=[{"entity": "子菜单", "count": child_count}])

        # Cannot delete menu referenced by roles
        role_ref_count = session.query(RoleMenu).filter(
            RoleMenu.menu_id == menu_id_int,
        ).count()

        if role_ref_count:
            raise BizError(1502, refs=[{"entity": "角色", "count": role_ref_count}])

        # Cannot delete menu referenced by packages
        package_ref_count = session.query(TenantPackageMenu).filter(
            TenantPackageMenu.menu_id == menu_id_int,
        ).count()

        if package_ref_count:
            raise BizError(1502, refs=[{"entity": "套餐", "count": package_ref_count}])

        # Soft delete
        menu.deleted = menu.id
        session.flush()
