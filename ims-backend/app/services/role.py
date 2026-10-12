# app/services/role.py - Role service (FW-B04)
"""
Role service.

Implements:
- FP-B04-01: Role management
- FP-B04-03: Role authorization
- FP-D04-01: Data scope configuration
"""

from typing import Any, Optional

from app.core.context import ctx
from app.core.errors import BizError
from app.db.session import get_db_session


class RoleService:
    """Role management service."""

    async def get_role_simple_list(self) -> list[dict[str, Any]]:
        """
        Get enabled roles for selectors.

        LOGIN_ONLY - returns id, name, source only.

        Returns:
            List of simple role items
        """
        from app.domains.sys.models import Role
        session = get_db_session()

        tenant_id = ctx.tenant_id

        roles = session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.status == "ENABLED",
            Role.deleted == 0,
        ).order_by(Role.sort, Role.id).all()

        return [
            {
                "id": str(role.id),
                "name": role.name,
                "source": role.source,
            }
            for role in roles
        ]

    async def get_role_by_id(self, role_id: int) -> Optional[dict[str, Any]]:
        """
        Get role by ID.

        Args:
            role_id: Role ID

        Returns:
            Role data or None
        """
        from app.domains.sys.models import Role
        session = get_db_session()

        tenant_id = ctx.tenant_id

        role = session.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            return None

        return {
            "id": str(role.id),
            "role_key": role.role_key,
            "name": role.name,
            "source": role.source,
            "status": role.status,
            "data_scope": role.data_scope,
            "position_code": role.position_code,
            "is_standard": role.is_standard,
            "sort": role.sort,
            "remark": role.remark,
        }

    async def get_user_roles(self, user_id: int) -> list[dict[str, Any]]:
        """
        Get roles assigned to a user.

        Only returns enabled roles.

        Args:
            user_id: User ID

        Returns:
            List of role data
        """
        from app.domains.sys.models import Role, UserRole
        session = get_db_session()

        tenant_id = ctx.tenant_id

        roles = session.query(Role).join(
            UserRole, UserRole.role_id == Role.id
        ).filter(
            UserRole.user_id == user_id,
            Role.status == "ENABLED",
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).all()

        return [
            {
                "id": str(role.id),
                "role_key": role.role_key,
                "name": role.name,
                "data_scope": role.data_scope,
            }
            for role in roles
        ]

    async def get_role_permission_codes(self, role_id: int) -> list[str]:
        """
        Get permission codes for a role.

        Args:
            role_id: Role ID

        Returns:
            List of permission code strings
        """
        from app.domains.sys.models import Menu, RoleMenu
        session = get_db_session()

        menus = session.query(Menu).join(
            RoleMenu, RoleMenu.menu_id == Menu.id
        ).filter(
            RoleMenu.role_id == role_id,
            Menu.status == "ENABLED",
            Menu.deleted == 0,
        ).all()

        return [menu.perm_code for menu in menus if menu.perm_code]

    async def validate_role_exists(self, role_id: int) -> bool:
        """
        Validate role exists and is enabled.

        Args:
            role_id: Role ID to validate

        Returns:
            True if valid

        Raises:
            BizError(1500): Role not found
        """
        from app.domains.sys.models import Role
        session = get_db_session()

        tenant_id = ctx.tenant_id

        role = session.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1500)

        return True
