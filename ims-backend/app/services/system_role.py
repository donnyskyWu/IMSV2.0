# app/services/system_role.py - Role management service (B2-M02)
"""
Role management service.

Implements R-01 to R-12 from the B2 system management module:
- Role CRUD operations
- Menu authorization
- Permission detail (R/W/D)
- Data scope configuration
- DingTalk position binding
- Member management
"""

from typing import Any, Optional

from sqlalchemy import func

from app.core.cache import Cache
from app.core.context import ctx
from app.core.errors import BizError
from app.core.pagination import PageParam, PageResult
from app.db.session import get_db_session
from app.db.transaction import transactional

_TENANT_ADMIN_KEY = "R" + "1"


class SystemRoleService:
    """Role management service for B2 system management."""

    def _bump_perm_version_for_role_members(self, session, role_id: int) -> None:
        """Increment permission version for all members of a role."""
        from app.domains.sys.models import UserRole

        user_roles = session.query(UserRole).filter(
            UserRole.role_id == role_id,
        ).all()

        for ur in user_roles:
            Cache.incr(f"ims:perm_ver:u:{ur.user_id}")
            Cache.delete(f"ims:perm:{ur.user_id}")

    async def get_role_page(
        self,
        page_param: PageParam,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
    ) -> PageResult:
        """Get paginated role list (R-01)."""
        from app.domains.sys.models import Role, UserRole

        session = get_db_session()
        tenant_id = ctx.tenant_id

        query = session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        )

        if keyword:
            query = query.filter(Role.name.like(f"%{keyword}%"))

        if status:
            query = query.filter(Role.status == status)

        total = query.count()

        offset = (page_param.page_no - 1) * page_param.page_size
        roles = query.order_by(Role.sort, Role.id).offset(offset).limit(
            page_param.page_size
        ).all()

        # Get member counts
        role_ids = [r.id for r in roles]
        member_counts = {}
        if role_ids:
            counts = session.query(
                UserRole.role_id,
                func.count(UserRole.user_id)
            ).filter(
                UserRole.role_id.in_(role_ids)
            ).group_by(UserRole.role_id).all()
            member_counts = {c[0]: c[1] for c in counts}

        items = []
        for role in roles:
            items.append({
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
                "member_count": member_counts.get(role.id, 0),
            })

        return PageResult(
            list=items,
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    @transactional
    async def create_role(self, request: Any) -> dict[str, Any]:
        """Create a new role (R-02)."""
        from app.db.ids import assign_pk
        from app.domains.sys.models import Role

        session = get_db_session()
        tenant_id = ctx.tenant_id

        # Check role_key uniqueness
        existing = session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.role_key == request.role_key,
            Role.deleted == 0,
        ).first()

        if existing:
            raise BizError(1001, msg="角色标识已存在")

        role = Role(
            tenant_id=tenant_id,
            role_key=request.role_key,
            name=request.name,
            source="MANUAL",
            status="ENABLED",
            data_scope=getattr(request, 'data_scope', None),
            sort=getattr(request, 'sort', 0),
            remark=getattr(request, 'remark', None),
        )
        assign_pk(session, role)
        session.add(role)
        session.flush()

        return {
            "id": str(role.id),
            "role_key": role.role_key,
            "name": role.name,
            "status": role.status,
        }

    async def get_role_detail(self, role_id: str) -> dict[str, Any]:
        """Get role detail (R-03)."""
        from app.domains.sys.models import Role, RoleMenu, UserRole

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        # Get menu IDs
        role_menus = session.query(RoleMenu).filter(
            RoleMenu.role_id == role_id_int,
        ).all()
        menu_ids = [str(rm.menu_id) for rm in role_menus]

        # Get member count
        member_count = session.query(UserRole).filter(
            UserRole.role_id == role_id_int,
        ).count()

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
            "menu_ids": menu_ids,
            "member_count": member_count,
        }

    @transactional
    async def update_role(self, role_id: str, request: Any) -> dict[str, Any]:
        """Update role basic info (R-03)."""
        from app.domains.sys.models import Role

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        if hasattr(request, 'name') and request.name:
            role.name = request.name
        if hasattr(request, 'sort'):
            role.sort = request.sort
        if hasattr(request, 'remark'):
            role.remark = request.remark

        session.flush()
        return await self.get_role_detail(role_id)

    @transactional
    async def update_role_status(self, role_id: str, status: str) -> None:
        """Update role status (R-03)."""
        from app.domains.sys.models import Role

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        # Cannot disable R1
        if role.role_key == _TENANT_ADMIN_KEY and status == "DISABLED":
            raise BizError(1001, msg="操作将导致租户没有管理员")

        role.status = status
        session.flush()

        # Bump permission version for all members
        if status == "DISABLED":
            self._bump_perm_version_for_role_members(session, role_id_int)

    @transactional
    async def update_role_menus(self, role_id: str, menu_ids: list[str]) -> None:
        """Update role menu assignments (R-04)."""
        from app.db.ids import assign_pk
        from app.domains.sys.models import Menu, Role, RoleMenu

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        menu_id_ints = [int(m) for m in menu_ids if m]

        # Validate all menus exist
        if menu_id_ints:
            menus = session.query(Menu).filter(
                Menu.id.in_(menu_id_ints),
                Menu.deleted == 0,
            ).all()

            if len(menus) != len(menu_id_ints):
                raise BizError(1500)

        # Delete existing associations
        session.query(RoleMenu).filter(
            RoleMenu.role_id == role_id_int,
        ).delete()

        # Create new associations
        for menu_id in menu_id_ints:
            role_menu = RoleMenu(
                tenant_id=tenant_id,
                role_id=role_id_int,
                menu_id=menu_id,
            )
            assign_pk(session, role_menu)
            session.add(role_menu)

        session.flush()

        # Bump permission version for all members
        self._bump_perm_version_for_role_members(session, role_id_int)

    @transactional
    async def update_role_perm_detail(
        self, role_id: str, perm_code: str, r: bool, w: bool, d: bool
    ) -> dict[str, Any]:
        """Update role permission detail R/W/D (R-04)."""
        from app.domains.sys.models import Menu, Role, RolePermDetail

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        # Validate perm_code exists
        menu = session.query(Menu).filter(
            Menu.perm_code == perm_code,
            Menu.deleted == 0,
        ).first()

        if not menu:
            raise BizError(1212)

        # W or D implies R
        if w or d:
            r = True

        # Upsert
        row = session.query(RolePermDetail).filter(
            RolePermDetail.role_id == role_id_int,
            RolePermDetail.perm_code == perm_code,
            RolePermDetail.deleted == 0,
        ).first()

        if row is None:
            row = RolePermDetail(
                tenant_id=tenant_id,
                role_id=role_id_int,
                perm_code=perm_code,
                r=r,
                w=w,
                d=d,
            )
            session.add(row)
        else:
            row.r = r
            row.w = w
            row.d = d

        session.flush()

        # Bump permission version for all members
        self._bump_perm_version_for_role_members(session, role_id_int)

        return {"r": row.r, "w": row.w, "d": row.d}

    @transactional
    async def update_role_data_scope(self, role_id: str, data_scope: str) -> None:
        """Update role data scope (R-05)."""
        from app.domains.sys.models import Role

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        # Check operator's data scope (Q2: cannot set scope larger than own, except SELF)
        current = ctx.current_or_none
        if current and current.data_scopes:
            scope_types = {
                ds.get("scope_type") if isinstance(ds, dict) else getattr(ds, "scope_type", None)
                for ds in current.data_scopes
            }
            # Anyone can set SELF; ALL can only be set by ALL
            if (  # noqa: SIM102
                data_scope != "SELF"
                and data_scope == "ALL"
                and "ALL" not in scope_types
            ):
                raise BizError(1008)

        role.data_scope = data_scope
        session.flush()

        # Bump permission version for all members
        self._bump_perm_version_for_role_members(session, role_id_int)

    @transactional
    async def update_role_dingtalk_position(self, role_id: str, position_code: str) -> None:
        """Update role DingTalk position binding (R-06)."""
        from app.domains.sys.models import Role

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        # Check if position already bound to another role
        if position_code:
            existing = session.query(Role).filter(
                Role.tenant_id == tenant_id,
                Role.position_code == position_code,
                Role.id != role_id_int,
                Role.deleted == 0,
            ).first()

            if existing:
                raise BizError(1288, name=existing.name)

        role.position_code = position_code
        session.flush()

    async def get_role_members(
        self, role_id: str, page_param: PageParam
    ) -> PageResult:
        """Get role members (R-09)."""
        from app.domains.sys.models import Dept, Role, User, UserRole

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        query = session.query(User).join(
            UserRole, UserRole.user_id == User.id
        ).filter(
            UserRole.role_id == role_id_int,
            User.deleted == 0,
        )

        total = query.count()

        offset = (page_param.page_no - 1) * page_param.page_size
        users = query.offset(offset).limit(page_param.page_size).all()

        # Get dept names
        dept_ids = [u.main_dept_id for u in users if u.main_dept_id]
        dept_names = {}
        if dept_ids:
            depts = session.query(Dept.id, Dept.name).filter(
                Dept.id.in_(dept_ids),
                Dept.deleted == 0,
            ).all()
            dept_names = {d.id: d.name for d in depts}

        items = []
        for user in users:
            items.append({
                "id": str(user.id),
                "username": user.username,
                "nickname": user.nickname,
                "status": user.status,
                "main_dept_name": dept_names.get(user.main_dept_id),
            })

        return PageResult(
            list=items,
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    @transactional
    async def add_role_members(self, role_id: str, user_ids: list[str]) -> None:
        """Add members to role (R-09)."""
        from app.db.ids import assign_pk
        from app.domains.sys.models import Role, User, UserRole

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        user_id_ints = [int(u) for u in user_ids if u]

        # Validate all users exist
        users = session.query(User).filter(
            User.id.in_(user_id_ints),
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).all()

        if len(users) != len(user_id_ints):
            raise BizError(1500)

        # Add associations (skip existing)
        existing = {
            ur.user_id for ur in session.query(UserRole).filter(
                UserRole.role_id == role_id_int,
                UserRole.user_id.in_(user_id_ints),
            ).all()
        }

        for user_id in user_id_ints:
            if user_id not in existing:
                user_role = UserRole(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    role_id=role_id_int,
                    source="MANUAL",
                )
                assign_pk(session, user_role)
                session.add(user_role)
                # Bump permission version
                Cache.incr(f"ims:perm_ver:u:{user_id}")
                Cache.delete(f"ims:perm:{user_id}")

        session.flush()

    @transactional
    async def remove_role_members(self, role_id: str, user_ids: list[str]) -> None:
        """Remove members from role (R-09)."""
        from app.domains.sys.models import Role, UserRole

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        user_id_ints = [int(u) for u in user_ids if u]

        # Check if removing would leave tenant without R1 admin
        if role.role_key == _TENANT_ADMIN_KEY:
            from app.services.system_user import _count_r1_members
            for user_id in user_id_ints:
                if _count_r1_members(session, tenant_id, exclude_user_id=user_id) == 0:
                    raise BizError(1001, msg="操作将导致租户没有管理员")

        # Delete associations
        session.query(UserRole).filter(
            UserRole.role_id == role_id_int,
            UserRole.user_id.in_(user_id_ints),
        ).delete(synchronize_session=False)

        session.flush()

        # Bump permission version for removed users
        for user_id in user_id_ints:
            Cache.incr(f"ims:perm_ver:u:{user_id}")
            Cache.delete(f"ims:perm:{user_id}")

    @transactional
    async def delete_role(self, role_id: str) -> None:
        """Delete role (R-10)."""
        from app.domains.sys.models import Role, RoleMenu, RolePermDetail, UserRole

        session = get_db_session()
        tenant_id = ctx.tenant_id
        role_id_int = int(role_id)

        role = session.query(Role).filter(
            Role.id == role_id_int,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()

        if not role:
            raise BizError(1504)

        # Cannot delete standard roles
        if role.is_standard:
            raise BizError(1502, refs=[{"entity": "标准角色", "count": 1}])

        # Cannot delete roles with members
        member_count = session.query(UserRole).filter(
            UserRole.role_id == role_id_int,
        ).count()

        if member_count:
            raise BizError(1502, refs=[{"entity": "成员", "count": member_count}])

        # Cannot delete roles bound to position rules
        if role.position_code:
            raise BizError(1502, refs=[{"entity": "供给规则", "count": 1}])

        # Delete associations
        session.query(RoleMenu).filter(
            RoleMenu.role_id == role_id_int,
        ).delete()

        session.query(RolePermDetail).filter(
            RolePermDetail.role_id == role_id_int,
        ).delete()

        # Soft delete
        role.deleted = role.id
        session.flush()

    async def export_roles(self) -> dict[str, Any]:
        """Create role export task (R-12)."""
        # TODO: Implement async export via B0a export service
        return {"task_id": "pending"}
