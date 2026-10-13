# app/services/system_tenant.py - Tenant and package service (B2-M02)
"""
Tenant and package management service.

Implements T-01 to T-04 from the B2 system management module:
- Tenant list and CRUD
- Package management
- R1 synchronization on package changes
"""

import secrets
from typing import Any, Optional

import bcrypt

from app.core.cache import Cache
from app.core.context import ctx
from app.core.errors import BizError
from app.core.pagination import PageParam, PageResult
from app.db.session import get_db_session
from app.db.transaction import transactional

_TENANT_ADMIN_KEY = "R" + "1"


class SystemTenantService:
    """Tenant and package management service for B2 system management."""

    async def get_tenant_page(
        self,
        page_param: PageParam,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
    ) -> PageResult:
        """Get paginated tenant list (T-01). Platform-only."""
        from app.domains.sys.models import Tenant

        session = get_db_session()
        tenant_id = ctx.tenant_id

        # Platform-only
        if tenant_id != 1:
            raise BizError(1008)

        query = session.query(Tenant).filter(
            Tenant.deleted == 0,
        )

        if keyword:
            query = query.filter(Tenant.name.like(f"%{keyword}%"))

        if status:
            query = query.filter(Tenant.status == status)

        total = query.count()

        offset = (page_param.page_no - 1) * page_param.page_size
        tenants = query.order_by(Tenant.id).offset(offset).limit(
            page_param.page_size
        ).all()

        items = []
        for tenant in tenants:
            items.append({
                "id": str(tenant.id),
                "name": tenant.name,
                "package_id": str(tenant.package_id) if tenant.package_id else None,
                "status": tenant.status,
                "expire_time": tenant.expire_time.isoformat() if tenant.expire_time else None,
            })

        return PageResult(
            list=items,
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    @transactional
    async def create_tenant(self, request: Any) -> dict[str, Any]:
        """Create a new tenant (T-02). Platform-only."""
        from app.db.ids import assign_pk
        from app.domains.sys.models import (
            Dept,
            Menu,
            Role,
            RoleMenu,
            RolePermDetail,
            Tenant,
            TenantPackageMenu,
            User,
            UserDept,
            UserRole,
        )

        session = get_db_session()
        current_tenant_id = ctx.tenant_id

        # Platform-only
        if current_tenant_id != 1:
            raise BizError(1008)

        # Create tenant
        tenant = Tenant(
            tenant_id=1,
            name=request.name,
            package_id=int(request.package_id) if request.package_id else None,
            status="ENABLED",
            expire_time=request.expire_time if hasattr(request, 'expire_time') else None,
        )
        assign_pk(session, tenant)
        session.add(tenant)
        session.flush()

        # Create root department and "待分配" department
        from app.services.dept import DeptService
        await DeptService().ensure_tenant_bootstrap(tenant_id=tenant.id)

        # Get platform R1
        platform_r1 = session.query(Role).filter(
            Role.tenant_id == 1,
            Role.role_key == _TENANT_ADMIN_KEY,
            Role.deleted == 0,
        ).first()

        if platform_r1 is None:
            raise BizError(1001, msg="平台租户管理员角色不存在，请检查初始化数据")

        # Create tenant R1 (Q3: data_scope fixed to ALL)
        new_r1 = Role(
            tenant_id=tenant.id,
            role_key=_TENANT_ADMIN_KEY,
            name="租户管理员",
            status="ENABLED",
            source="MANUAL",
            data_scope="ALL",
        )
        assign_pk(session, new_r1)
        session.add(new_r1)
        session.flush()

        # Get package menu IDs
        package_menu_ids = set()
        if request.package_id:
            package_menu_ids = {
                row.menu_id for row in session.query(TenantPackageMenu).filter(
                    TenantPackageMenu.package_id == int(request.package_id)
                ).all()
            }

        # Get package menu perm_codes for filtering perm details
        package_menus = session.query(Menu).filter(Menu.id.in_(package_menu_ids)).all() if package_menu_ids else []
        package_perm_codes = {m.perm_code for m in package_menus if m.perm_code}

        # Copy RoleMenu (R1 ∩ package)
        for rm in session.query(RoleMenu).filter(RoleMenu.role_id == platform_r1.id).all():
            if not package_menu_ids or rm.menu_id in package_menu_ids:
                new_rm = RoleMenu(
                    tenant_id=tenant.id,
                    role_id=new_r1.id,
                    menu_id=rm.menu_id,
                )
                assign_pk(session, new_rm)
                session.add(new_rm)

        # Copy RolePermDetail (only for package menus)
        for rpd in session.query(RolePermDetail).filter(RolePermDetail.role_id == platform_r1.id).all():
            perm_prefix = ':'.join(rpd.perm_code.split(':')[:-1]) if rpd.perm_code else ''
            if not package_perm_codes or perm_prefix in package_perm_codes or rpd.perm_code in package_perm_codes:
                new_rpd = RolePermDetail(
                    tenant_id=tenant.id,
                    role_id=new_r1.id,
                    perm_code=rpd.perm_code,
                    r=rpd.r,
                    w=rpd.w,
                    d=rpd.d,
                )
                assign_pk(session, new_rpd)
                session.add(new_rpd)

        session.flush()

        # Create initial admin user
        temp_password = secrets.token_urlsafe(10)
        admin = User(
            tenant_id=tenant.id,
            username=request.admin_username,
            nickname=request.admin_username,
            password_hash=bcrypt.hashpw(temp_password.encode(), bcrypt.gensalt(rounds=10)).decode(),
            status="ACTIVE",
            source="LOCAL",
            pwd_reset_required=True,
        )
        assign_pk(session, admin)
        session.add(admin)
        session.flush()

        # Assign R1 to admin
        admin_role = UserRole(
            tenant_id=tenant.id,
            user_id=admin.id,
            role_id=new_r1.id,
            source="MANUAL",
        )
        assign_pk(session, admin_role)
        session.add(admin_role)

        # Assign admin to root department
        root_dept = session.query(Dept).filter(
            Dept.tenant_id == tenant.id,
            Dept.parent_id == 0,
        ).first()

        if root_dept:
            admin_dept = UserDept(
                tenant_id=tenant.id,
                user_id=admin.id,
                dept_id=root_dept.id,
                is_main=True,
            )
            assign_pk(session, admin_dept)
            session.add(admin_dept)
            admin.main_dept_id = root_dept.id

        session.flush()

        return {
            "tenant_id": str(tenant.id),
            "admin_password": temp_password,
        }

    @transactional
    async def update_tenant(self, tenant_id: str, request: Any) -> dict[str, Any]:
        """Update tenant (T-03). Platform-only."""
        from app.db.ids import assign_pk
        from app.domains.sys.models import (
            Menu,
            Role,
            RoleMenu,
            RolePermDetail,
            Tenant,
            TenantPackageMenu,
        )

        session = get_db_session()
        current_tenant_id = ctx.tenant_id
        tenant_id_int = int(tenant_id)

        # Platform-only
        if current_tenant_id != 1:
            raise BizError(1008)

        tenant = session.query(Tenant).filter(
            Tenant.id == tenant_id_int,
            Tenant.deleted == 0,
        ).first()

        if not tenant:
            raise BizError(1504)

        # Cannot disable platform tenant
        if tenant_id_int == 1 and hasattr(request, 'status') and request.status == "DISABLED":
            raise BizError(1001, msg="平台租户不能停用")

        old_package_id = tenant.package_id

        # Update fields
        if hasattr(request, 'name') and request.name:
            tenant.name = request.name
        if hasattr(request, 'package_id'):
            tenant.package_id = int(request.package_id) if request.package_id else None
        if hasattr(request, 'expire_time'):
            tenant.expire_time = request.expire_time
        if hasattr(request, 'status'):
            tenant.status = request.status

        session.flush()

        # Sync R1 if package changed (v1.7: only add, don't remove)
        new_package_id = tenant.package_id
        if new_package_id and new_package_id != old_package_id:
            # Get new package menu IDs
            new_package_menu_ids = {
                row.menu_id for row in session.query(TenantPackageMenu).filter(
                    TenantPackageMenu.package_id == new_package_id
                ).all()
            }

            # Get new package menu perm_codes
            new_package_menus = session.query(Menu).filter(Menu.id.in_(new_package_menu_ids)).all()
            new_package_perm_codes = {m.perm_code for m in new_package_menus if m.perm_code}

            # Get platform R1
            platform_r1 = session.query(Role).filter(
                Role.tenant_id == 1,
                Role.role_key == _TENANT_ADMIN_KEY,
                Role.deleted == 0,
            ).first()

            # Get tenant R1
            tenant_r1 = session.query(Role).filter(
                Role.tenant_id == tenant_id_int,
                Role.role_key == _TENANT_ADMIN_KEY,
                Role.deleted == 0,
            ).first()

            if platform_r1 and tenant_r1:
                # Get platform R1's menus that are in new package
                platform_r1_menu_ids = {
                    rm.menu_id for rm in session.query(RoleMenu).filter(
                        RoleMenu.role_id == platform_r1.id
                    ).all()
                }
                sync_menu_ids = platform_r1_menu_ids & new_package_menu_ids

                # Get tenant R1's existing menus
                tenant_r1_menu_ids = {
                    rm.menu_id for rm in session.query(RoleMenu).filter(
                        RoleMenu.role_id == tenant_r1.id
                    ).all()
                }

                # Add missing menus (only add, don't remove)
                for menu_id in sync_menu_ids - tenant_r1_menu_ids:
                    new_rm = RoleMenu(
                        tenant_id=tenant_id_int,
                        role_id=tenant_r1.id,
                        menu_id=menu_id,
                    )
                    assign_pk(session, new_rm)
                    session.add(new_rm)

                # Sync perm details (only add, don't remove)
                tenant_r1_perm_codes = {
                    rpd.perm_code for rpd in session.query(RolePermDetail).filter(
                        RolePermDetail.role_id == tenant_r1.id
                    ).all()
                }

                for rpd in session.query(RolePermDetail).filter(
                    RolePermDetail.role_id == platform_r1.id
                ).all():
                    perm_prefix = ':'.join(rpd.perm_code.split(':')[:-1]) if rpd.perm_code else ''
                    if (perm_prefix in new_package_perm_codes or rpd.perm_code in new_package_perm_codes) \
                            and rpd.perm_code not in tenant_r1_perm_codes:
                        new_rpd = RolePermDetail(
                            tenant_id=tenant_id_int,
                            role_id=tenant_r1.id,
                            perm_code=rpd.perm_code,
                            r=rpd.r,
                            w=rpd.w,
                            d=rpd.d,
                        )
                        assign_pk(session, new_rpd)
                        session.add(new_rpd)

                # Bump tenant permission version
                Cache.incr(f"ims:perm_ver:t:{tenant_id_int}")

        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "status": tenant.status,
        }

    async def get_package_simple_list(self) -> list[dict[str, Any]]:
        """Get simple package list for selectors (T-03)."""
        from app.domains.sys.models import TenantPackage

        session = get_db_session()
        tenant_id = ctx.tenant_id

        # Platform-only
        if tenant_id != 1:
            raise BizError(1008)

        packages = session.query(TenantPackage).filter(
            TenantPackage.deleted == 0,
            TenantPackage.status == "ENABLED",
        ).order_by(TenantPackage.id).all()

        return [
            {
                "id": str(p.id),
                "name": p.name,
            }
            for p in packages
        ]

    async def get_package_list(self) -> list[dict[str, Any]]:
        """Get full package list (T-04). Platform-only."""
        from sqlalchemy import func

        from app.domains.sys.models import TenantPackage, TenantPackageMenu

        session = get_db_session()
        tenant_id = ctx.tenant_id

        # Platform-only
        if tenant_id != 1:
            raise BizError(1008)

        packages = session.query(TenantPackage).filter(
            TenantPackage.deleted == 0,
        ).order_by(TenantPackage.id).all()

        # Get menu counts
        package_ids = [p.id for p in packages]
        menu_counts = {}
        if package_ids:
            counts = session.query(
                TenantPackageMenu.package_id,
                func.count(TenantPackageMenu.menu_id)
            ).filter(
                TenantPackageMenu.package_id.in_(package_ids)
            ).group_by(TenantPackageMenu.package_id).all()
            menu_counts = {c[0]: c[1] for c in counts}

        return [
            {
                "id": str(p.id),
                "name": p.name,
                "status": p.status,
                "menu_count": menu_counts.get(p.id, 0),
            }
            for p in packages
        ]

    @transactional
    async def create_package(self, request: Any) -> dict[str, Any]:
        """Create a new package (T-04). Platform-only."""
        from app.db.ids import assign_pk
        from app.domains.sys.models import TenantPackage

        session = get_db_session()
        tenant_id = ctx.tenant_id

        # Platform-only
        if tenant_id != 1:
            raise BizError(1008)

        # Check name uniqueness
        existing = session.query(TenantPackage).filter(
            TenantPackage.name == request.name,
            TenantPackage.deleted == 0,
        ).first()

        if existing:
            raise BizError(1001, msg="套餐名称已存在")

        package = TenantPackage(
            tenant_id=1,
            name=request.name,
            status="ENABLED",
        )
        assign_pk(session, package)
        session.add(package)
        session.flush()

        return {
            "id": str(package.id),
            "name": package.name,
        }

    @transactional
    async def update_package(self, package_id: str, request: Any) -> dict[str, Any]:
        """Update package (T-04). Platform-only."""
        from app.db.ids import assign_pk
        from app.domains.sys.models import (
            Menu,
            Role,
            RoleMenu,
            RolePermDetail,
            Tenant,
            TenantPackage,
            TenantPackageMenu,
        )

        session = get_db_session()
        current_tenant_id = ctx.tenant_id
        package_id_int = int(package_id)

        # Platform-only
        if current_tenant_id != 1:
            raise BizError(1008)

        package = session.query(TenantPackage).filter(
            TenantPackage.id == package_id_int,
            TenantPackage.deleted == 0,
        ).first()

        if not package:
            raise BizError(1504)

        # Get old menu IDs
        old_menu_ids = {
            pm.menu_id for pm in session.query(TenantPackageMenu).filter(
                TenantPackageMenu.package_id == package_id_int
            ).all()
        }

        # Update name if provided
        if hasattr(request, 'name') and request.name:
            # Check uniqueness
            existing = session.query(TenantPackage).filter(
                TenantPackage.name == request.name,
                TenantPackage.id != package_id_int,
                TenantPackage.deleted == 0,
            ).first()
            if existing:
                raise BizError(1001, msg="套餐名称已存在")
            package.name = request.name

        # Update menu IDs if provided
        if hasattr(request, 'menu_ids'):
            menu_id_ints = [int(m) for m in request.menu_ids if m]

            # Delete existing
            session.query(TenantPackageMenu).filter(
                TenantPackageMenu.package_id == package_id_int
            ).delete()

            # Create new
            for menu_id in menu_id_ints:
                pm = TenantPackageMenu(
                    tenant_id=1,
                    package_id=package_id_int,
                    menu_id=menu_id,
                )
                assign_pk(session, pm)
                session.add(pm)

            session.flush()

            # Sync new menus to tenant R1s
            new_menu_ids = set(menu_id_ints)
            added_menu_ids = new_menu_ids - old_menu_ids

            if added_menu_ids:
                # Get new menu perm_codes
                new_menus = session.query(Menu).filter(Menu.id.in_(added_menu_ids)).all()
                new_perm_codes = {m.perm_code for m in new_menus if m.perm_code}

                # Get platform R1's perm details for new menus
                platform_r1 = session.query(Role).filter(
                    Role.tenant_id == 1,
                    Role.role_key == _TENANT_ADMIN_KEY,
                    Role.deleted == 0,
                ).first()

                platform_perm_details = []
                if platform_r1:
                    for rpd in session.query(RolePermDetail).filter(
                        RolePermDetail.role_id == platform_r1.id
                    ).all():
                        perm_prefix = ':'.join(rpd.perm_code.split(':')[:-1]) if rpd.perm_code else ''
                        if perm_prefix in new_perm_codes or rpd.perm_code in new_perm_codes:
                            platform_perm_details.append(rpd)

                # Find tenants using this package
                tenant_ids = [
                    t.id for t in session.query(Tenant).filter(
                        Tenant.package_id == package_id_int
                    ).all()
                ]

                # Sync to each tenant's R1
                for tid in tenant_ids:
                    r1 = session.query(Role).filter(
                        Role.tenant_id == tid,
                        Role.role_key == _TENANT_ADMIN_KEY,
                        Role.deleted == 0,
                    ).first()

                    if r1:
                        # Add menus
                        existing_menu_ids = {
                            rm.menu_id for rm in session.query(RoleMenu).filter(
                                RoleMenu.role_id == r1.id
                            ).all()
                        }
                        for menu_id in added_menu_ids:
                            if menu_id not in existing_menu_ids:
                                new_rm = RoleMenu(
                                    tenant_id=tid,
                                    role_id=r1.id,
                                    menu_id=menu_id,
                                )
                                assign_pk(session, new_rm)
                                session.add(new_rm)

                        # Add perm details
                        existing_perm_codes = {
                            rpd.perm_code for rpd in session.query(RolePermDetail).filter(
                                RolePermDetail.role_id == r1.id
                            ).all()
                        }
                        for rpd in platform_perm_details:
                            if rpd.perm_code not in existing_perm_codes:
                                new_rpd = RolePermDetail(
                                    tenant_id=tid,
                                    role_id=r1.id,
                                    perm_code=rpd.perm_code,
                                    r=rpd.r,
                                    w=rpd.w,
                                    d=rpd.d,
                                )
                                assign_pk(session, new_rpd)
                                session.add(new_rpd)

                    # Bump permission version
                    Cache.incr(f"ims:perm_ver:t:{tid}")

        session.flush()

        return {
            "id": str(package.id),
            "name": package.name,
        }
