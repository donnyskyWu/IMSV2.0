# app/services/system_user.py - User lifecycle service (B2-M02)
"""
User lifecycle service.

Implements U-05 to U-16 from the B2 system management module:
- User CRUD operations
- Status management (freeze, resign, reactivate)
- Password reset
- Account unlock
- Kick sessions
- User export
"""

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import Cache
from app.core.context import ctx
from app.core.errors import BizError
from app.db.session import get_db_session
from app.db.transaction import transactional

_TENANT_ADMIN_KEY = "R" + "1"


def _count_r1_members(session: Session, tenant_id: int, exclude_user_id: int = None) -> int:
    """Count R1 members (active users with enabled R1 role)."""
    from sqlalchemy import distinct

    from app.domains.sys.models import Role, User, UserRole

    query = session.query(func.count(distinct(UserRole.user_id))).join(
        Role, Role.id == UserRole.role_id
    ).join(
        User, User.id == UserRole.user_id
    ).filter(
        Role.tenant_id == tenant_id,
        Role.role_key == _TENANT_ADMIN_KEY,
        Role.status == "ENABLED",
        Role.deleted == 0,
        User.status == "ACTIVE",
        User.deleted == 0,
    )
    if exclude_user_id:
        query = query.filter(UserRole.user_id != exclude_user_id)
    return query.scalar() or 0


def _is_r1_member(session: Session, user_id: int, tenant_id: int) -> bool:
    """Check if user is an R1 member."""
    from app.domains.sys.models import Role, UserRole

    return session.query(UserRole).join(
        Role, Role.id == UserRole.role_id
    ).filter(
        UserRole.user_id == user_id,
        Role.tenant_id == tenant_id,
        Role.role_key == _TENANT_ADMIN_KEY,
        Role.status == "ENABLED",
        Role.deleted == 0,
    ).first() is not None


class SystemUserService:
    """User lifecycle service for B2 system management."""

    def _drop_sessions(self, user_id: int) -> None:
        """Drop all sessions for a user and blacklist them."""
        from app.services.auth import AuthService

        auth = AuthService()
        key = f"{auth.USER_SESSIONS_PREFIX}{user_id}"
        for sid in list(Cache.smembers(key)):
            session_data = Cache.get_json(f"{auth.SESSION_PREFIX}{sid}")
            if isinstance(session_data, dict):
                refresh_token = session_data.get("refresh_token")
                if refresh_token:
                    Cache.delete(f"{auth.REFRESH_INDEX_PREFIX}{refresh_token}")
            Cache.delete(f"{auth.SESSION_PREFIX}{sid}")
            Cache.set(f"{auth.TOKEN_BLACKLIST_PREFIX}{sid}", "1", ttl=3600)
            Cache.srem(key, sid)

    def _bump_perm_version(self, user_id: int) -> None:
        """Increment user's permission version and clear cache."""
        Cache.incr(f"ims:perm_ver:u:{user_id}")
        Cache.delete(f"ims:perm:{user_id}")

    async def get_user_detail(self, user_id: str) -> dict[str, Any]:
        """Get user detail by ID (U-06)."""
        from app.domains.sys.models import Dept, Role, User, UserDept, UserRole

        session = get_db_session()
        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        # Get departments
        user_depts = session.query(UserDept).filter(
            UserDept.user_id == user_id_int,
            UserDept.tenant_id == tenant_id,
        ).all()
        dept_ids = [ud.dept_id for ud in user_depts]

        dept_names = {}
        if dept_ids:
            depts = session.query(Dept.id, Dept.name).filter(
                Dept.id.in_(dept_ids),
                Dept.deleted == 0,
            ).all()
            dept_names = {d.id: d.name for d in depts}

        # Get roles
        user_roles = session.query(UserRole).filter(
            UserRole.user_id == user_id_int,
        ).all()
        role_ids = [ur.role_id for ur in user_roles]

        role_names = {}
        if role_ids:
            roles = session.query(Role.id, Role.name).filter(
                Role.id.in_(role_ids),
                Role.deleted == 0,
            ).all()
            role_names = {r.id: r.name for r in roles}

        return {
            "id": str(user.id),
            "username": user.username,
            "nickname": user.nickname,
            "mobile": self._mask_mobile(user.mobile_enc) if user.mobile_enc else None,
            "email": user.email,
            "status": user.status,
            "main_dept_id": str(user.main_dept_id) if user.main_dept_id else None,
            "main_dept_name": dept_names.get(user.main_dept_id),
            "dept_ids": [str(d) for d in dept_ids],
            "dept_names": [dept_names.get(d) for d in dept_ids if dept_names.get(d)],
            "role_ids": [str(r) for r in role_ids],
            "role_names": [role_names.get(r) for r in role_ids if role_names.get(r)],
            "position_code": user.position_code,
            "emp_no": user.emp_no,
            "source": user.source,
            "pwd_reset_required": user.pwd_reset_required or False,
            "last_login_time": user.last_login_time.isoformat() if user.last_login_time else None,
        }

    @transactional
    async def update_user(self, user_id: str, request: Any) -> dict[str, Any]:
        """Update user basic info (U-06)."""
        from app.domains.sys.models import User

        session = get_db_session()
        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        # Update allowed fields
        if hasattr(request, 'nickname') and request.nickname:
            user.nickname = request.nickname
        if hasattr(request, 'email'):
            user.email = request.email
        if hasattr(request, 'emp_no'):
            user.emp_no = request.emp_no
        if hasattr(request, 'mobile') and request.mobile:
            # Check mobile uniqueness
            existing = session.query(User).filter(
                User.mobile_hash == self._hash_mobile(request.mobile),
                User.id != user_id_int,
                User.tenant_id == tenant_id,
                User.deleted == 0,
            ).first()
            if existing:
                raise BizError(1287)
            user.mobile_enc = self._encrypt_mobile(request.mobile)
            user.mobile_hash = self._hash_mobile(request.mobile)

        session.flush()
        return await self.get_user_detail(user_id)

    @transactional
    async def update_user_roles(self, user_id: str, role_ids: list[str]) -> None:
        """Update user's role assignments (U-08)."""
        from app.domains.sys.models import Role, User, UserRole

        session = get_db_session()
        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        role_id_ints = [int(r) for r in role_ids if r]

        # Check if removing R1 would leave tenant without admin
        current_roles = session.query(UserRole).filter(
            UserRole.user_id == user_id_int,
        ).all()
        current_role_ids = {ur.role_id for ur in current_roles}

        r1 = session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.role_key == _TENANT_ADMIN_KEY,
            Role.deleted == 0,
        ).first()

        if (  # noqa: SIM102
            r1 and r1.id in current_role_ids and r1.id not in role_id_ints
        ):
            # User had R1, now losing it
            if _count_r1_members(session, tenant_id, exclude_user_id=user_id_int) == 0:
                raise BizError(1001, msg="操作将导致租户没有管理员")

        # Validate all roles exist
        roles = session.query(Role).filter(
            Role.id.in_(role_id_ints),
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).all()

        if len(roles) != len(role_id_ints):
            raise BizError(1500)

        # Delete existing associations
        session.query(UserRole).filter(
            UserRole.user_id == user_id_int,
        ).delete()

        # Create new associations
        from app.db.ids import assign_pk
        for role_id in role_id_ints:
            user_role = UserRole(
                tenant_id=tenant_id,
                user_id=user_id_int,
                role_id=role_id,
                source="MANUAL",
            )
            assign_pk(session, user_role)
            session.add(user_role)

        session.flush()

        # Bump permission version
        self._bump_perm_version(user_id_int)

    @transactional
    async def update_user_status(self, user_id: str, status: str) -> None:
        """Update user status - freeze or reactivate (U-09)."""
        from app.domains.sys.models import User

        session = get_db_session()
        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)
        current_user_id = ctx.user_id

        # Cannot freeze self
        if user_id_int == current_user_id and status == "FROZEN":
            raise BizError(1001, msg="不能冻结当前登录账号")

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        if status == "FROZEN":
            # Check if freezing would leave tenant without admin
            if (  # noqa: SIM102
                _is_r1_member(session, user_id_int, tenant_id)
                and _count_r1_members(session, tenant_id, exclude_user_id=user_id_int) == 0
            ):
                raise BizError(1001, msg="操作将导致租户没有管理员")

            user.status = "FROZEN"
            self._drop_sessions(user_id_int)
        elif status == "ACTIVE":
            if user.status == "RESIGNED":
                raise BizError(1502, refs=[{"entity": "已离职用户", "count": 1}])
            user.status = "ACTIVE"

        session.flush()

    @transactional
    async def resign_user(self, user_id: str) -> None:
        """Mark user as resigned (U-10)."""
        from app.domains.sys.models import User

        session = get_db_session()
        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)
        current_user_id = ctx.user_id

        # Cannot resign self
        if user_id_int == current_user_id:
            raise BizError(1001, msg="不能将自己设为离职")

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        if user.status == "RESIGNED":
            raise BizError(1502, refs=[{"entity": "已离职用户", "count": 1}])

        # Check if resigning would leave tenant without admin
        if (  # noqa: SIM102
            _is_r1_member(session, user_id_int, tenant_id)
            and _count_r1_members(session, tenant_id, exclude_user_id=user_id_int) == 0
        ):
            raise BizError(1001, msg="操作将导致租户没有管理员")

        user.status = "RESIGNED"
        self._drop_sessions(user_id_int)
        session.flush()

    @transactional
    async def reset_password(self, user_id: str) -> dict[str, str]:
        """Reset user password to a random value (U-11)."""
        import secrets

        import bcrypt

        from app.domains.sys.models import User

        session = get_db_session()
        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        new_password = secrets.token_urlsafe(10)
        user.password_hash = bcrypt.hashpw(
            new_password.encode(), bcrypt.gensalt(rounds=10)
        ).decode()
        user.pwd_reset_required = True

        # Drop all sessions except none (force re-login)
        self._drop_sessions(user_id_int)
        session.flush()

        return {"new_password": new_password}

    @transactional
    async def unlock_user(self, user_id: str) -> None:
        """Unlock a locked user account (U-12)."""
        from app.domains.sys.models import User
        from app.services.auth import AuthService

        session = get_db_session()
        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        # Clear lock state
        user.login_fail_count = 0
        user.lock_until = None

        # Clear Redis lock key
        auth = AuthService()
        lock_key = f"{auth.LOGIN_FAIL_PREFIX}{user.username}"
        Cache.delete(lock_key)

        session.flush()

    @transactional
    async def kick_user(self, user_id: str) -> None:
        """Kick user's all sessions offline (U-13)."""
        from app.domains.sys.models import User

        session = get_db_session()
        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        self._drop_sessions(user_id_int)

    @transactional
    async def delete_user(self, user_id: str) -> None:
        """Delete user (U-14). Only never-logged-in users can be deleted."""
        from app.domains.sys.models import User, UserDept, UserRole

        session = get_db_session()
        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)
        current_user_id = ctx.user_id

        # Cannot delete self
        if user_id_int == current_user_id:
            raise BizError(1001, msg="不能删除当前登录账号")

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        # Cannot delete resigned users
        if user.status == "RESIGNED":
            raise BizError(1502, refs=[{"entity": "已离职用户", "count": 1}])

        # Cannot delete users who have logged in
        if user.last_login_time is not None:
            raise BizError(1502, refs=[{"entity": "有登录记录的用户", "count": 1}])

        # Check if deleting would leave tenant without admin
        if (  # noqa: SIM102
            _is_r1_member(session, user_id_int, tenant_id)
            and _count_r1_members(session, tenant_id, exclude_user_id=user_id_int) == 0
        ):
            raise BizError(1001, msg="操作将导致租户没有管理员")

        # Delete associations
        session.query(UserDept).filter(
            UserDept.user_id == user_id_int,
            UserDept.tenant_id == tenant_id,
        ).delete()

        session.query(UserRole).filter(
            UserRole.user_id == user_id_int,
        ).delete()

        # Soft delete user
        user.deleted = user.id

        # Drop sessions
        self._drop_sessions(user_id_int)

        session.flush()

    async def export_users(self) -> dict[str, Any]:
        """Create user export task (U-15)."""
        # TODO: Implement async export via B0a export service
        return {"task_id": "pending"}

    def _mask_mobile(self, encrypted: str) -> str:
        """Mask mobile number for display."""
        # TODO: Decrypt and mask properly
        if encrypted and len(encrypted) >= 11:
            return encrypted[:3] + "****" + encrypted[-4:]
        return "***********"

    def _encrypt_mobile(self, mobile: str) -> str:
        """Encrypt mobile with AES."""
        # TODO: Implement proper AES encryption
        return mobile

    def _hash_mobile(self, mobile: str) -> str:
        """Create HMAC hash of mobile for matching."""
        import hashlib
        import hmac
        key = b"ims_mobile_hash_key"
        return hmac.new(key, mobile.encode(), hashlib.sha256).hexdigest()
