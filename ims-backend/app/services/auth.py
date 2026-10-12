# app/services/auth.py - Authentication service (FW-D01, FW-D02, FW-D06)
"""
Authentication and authorization service.

Implements:
- FP-D01-01: Local login with lock mechanism
- FP-D01-02: Password policy
- FP-D01-03: Token management
- FP-D01-04: Logout and session management
- FP-D02-01/02: DingTalk SSO
- FP-D06-01: Current user info with menus/permissions
"""

import secrets
from datetime import timedelta
from typing import Any, Optional
from uuid import uuid4

import bcrypt
import jwt

from app.core.cache import Cache
from app.core.clock import get_now
from app.core.config import get_settings
from app.core.context import DataScope, ctx
from app.core.errors import BizError
from app.db.session import get_db_session

settings = get_settings()


def _nest_menu_tree(menus: list) -> list[dict[str, Any]]:
    """目录和菜单按 parent_id 嵌套。调用方已经去掉按钮。"""
    nodes: dict[int, dict[str, Any]] = {}
    for menu in menus:
        nodes[menu.id] = {
            "id": str(menu.id),
            "parent_id": str(menu.parent_id) if menu.parent_id else None,
            "name": menu.name,
            "type": menu.type,
            "perm_code": menu.perm_code,
            "path": menu.path,
            "component": menu.component,
            "icon": menu.icon,
            "sort": menu.sort or 0,
            "visible": bool(menu.visible),
            "children": [],
        }

    roots: list[dict[str, Any]] = []
    for menu in menus:
        node = nodes[menu.id]
        parent = nodes.get(menu.parent_id)
        if parent is None:
            roots.append(node)
        else:
            parent["children"].append(node)

    def _sort(level: list[dict[str, Any]]) -> None:
        level.sort(key=lambda item: (item["sort"], int(item["id"])))
        for item in level:
            _sort(item["children"])

    _sort(roots)
    return roots


class AuthService:
    """Authentication and authorization service."""

    # Cache key prefixes
    SESSION_PREFIX = "ims:session:"
    USER_SESSIONS_PREFIX = "ims:user_sessions:"
    LOGIN_FAIL_PREFIX = "ims:login_fail:"
    TOKEN_BLACKLIST_PREFIX = "ims:token_blacklist:"
    SSO_STATE_PREFIX = "ims:sso_state:"
    PERM_CACHE_PREFIX = "ims:perm:"

    # Session limits
    MAX_SESSIONS = 3

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """
        Local username/password login.

        Rules per FP-D01-01:
        - User not exist or wrong password -> 1214
        - 5 consecutive failures -> lock 15 minutes -> 1215
        - FROZEN/RESIGNED -> 1216
        - Tenant disabled/expired -> 1008
        """
        # Check lock status first (even for non-existent users)
        lock_key = f"{self.LOGIN_FAIL_PREFIX}{username}"
        fail_data = Cache.get_json(lock_key)

        if fail_data:
            lock_until = fail_data.get("lock_until")
            if lock_until:
                now = get_now()
                from datetime import datetime
                lock_time = datetime.fromisoformat(lock_until)
                if now < lock_time:
                    remaining = int((lock_time - now).total_seconds() / 60) + 1
                    raise BizError(1215, n=remaining)

        # Find user
        from app.domains.sys.models import User
        session = get_db_session()

        user = session.query(User).filter(
            User.username == username,
            User.deleted == 0,
        ).first()

        # Track failure for non-existent users too (prevent enumeration)
        if user is None:
            await self._record_login_failure(username)
            raise BizError(1214)

        # Verify password
        if not user.password_hash or not bcrypt.checkpw(
            password.encode(), user.password_hash.encode()
        ):
            await self._record_login_failure(username)
            raise BizError(1214)

        # Check user status (after password check to not leak status)
        if user.status in ("FROZEN", "RESIGNED"):
            raise BizError(1216)

        # Check tenant
        # TODO: Verify tenant status

        # Clear failure count
        Cache.delete(lock_key)

        # Update login info
        now = get_now()
        user.last_login_time = now
        user.last_login_ip = ctx.current.client_ip if ctx.current_or_none else ""
        user.login_fail_count = 0
        user.lock_until = None
        session.flush()

        # Create session and tokens
        session_id = str(uuid4())
        tokens = await self._create_tokens(user, session_id)

        # Write login log
        await self._write_login_log(
            user_id=user.id,
            username=username,
            method="PASSWORD",
            result="SUCCESS",
        )

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_in": settings.jwt.access_token_ttl,
            "pwd_reset_required": user.pwd_reset_required or False,
        }

    async def _record_login_failure(self, username: str) -> None:
        """Record login failure and potentially lock account."""
        lock_key = f"{self.LOGIN_FAIL_PREFIX}{username}"
        fail_data = Cache.get_json(lock_key) or {"count": 0}

        fail_data["count"] = fail_data.get("count", 0) + 1

        if fail_data["count"] >= settings.lock.max_fail_count:
            # Lock the account
            lock_until = get_now() + timedelta(minutes=settings.lock.lock_minutes)
            fail_data["lock_until"] = lock_until.isoformat()

            # Write login log
            await self._write_login_log(
                username=username,
                method="PASSWORD",
                result="LOCKED",
            )

        # Store with 15 min TTL
        Cache.set_json(lock_key, fail_data, ttl=settings.lock.lock_minutes * 60)

    async def _create_tokens(self, user: Any, session_id: str) -> dict[str, str]:
        """Create access and refresh tokens."""
        now = get_now()

        # Access token
        access_payload = {
            "sub": str(user.id),
            "tid": str(user.tenant_id),
            "sid": session_id,
            "exp": now + timedelta(seconds=settings.jwt.access_token_ttl),
            "iat": now,
            "type": "access",
        }
        access_token = jwt.encode(
            access_payload,
            settings.jwt.secret,
            algorithm=settings.jwt.algorithm,
        )

        # Refresh token (random string)
        refresh_token = secrets.token_urlsafe(32)

        # Store session in Redis
        session_data = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "refresh_token": refresh_token,
            "created_at": now.isoformat(),
        }
        Cache.set_json(
            f"{self.SESSION_PREFIX}{session_id}",
            session_data,
            ttl=settings.jwt.refresh_token_ttl,
        )

        # Add to user's session list and enforce limit
        await self._add_user_session(user.id, session_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    async def _add_user_session(self, user_id: int, session_id: str) -> None:
        """Add session to user's list and enforce max sessions."""
        sessions_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"

        # Get current sessions
        sessions = list(Cache.smembers(sessions_key))

        # Add new session
        Cache.sadd(sessions_key, session_id)
        Cache.expire(sessions_key, settings.jwt.refresh_token_ttl)

        # If over limit, remove oldest
        if len(sessions) >= self.MAX_SESSIONS:
            # Sessions are stored without timestamp, so we check creation time
            oldest_session = None
            oldest_time = None

            for sid in sessions:
                session_data = Cache.get_json(f"{self.SESSION_PREFIX}{sid}")
                if session_data:
                    created = session_data.get("created_at")
                    if oldest_time is None or created < oldest_time:
                        oldest_time = created
                        oldest_session = sid

            if oldest_session:
                # Invalidate oldest session
                Cache.delete(f"{self.SESSION_PREFIX}{oldest_session}")
                Cache.srem(sessions_key, oldest_session)

    async def verify_token(self, token: str) -> dict[str, Any]:
        """
        Verify access token and return user info.

        Returns dict with user_id, tenant_id, perm_codes, data_scopes, etc.
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt.secret,
                algorithms=[settings.jwt.algorithm],
            )
        except jwt.ExpiredSignatureError as e:
            raise BizError(1002) from e
        except jwt.InvalidTokenError as e:
            raise BizError(1002) from e

        if payload.get("type") != "access":
            raise BizError(1002)

        session_id = payload.get("sid")
        user_id = int(payload.get("sub"))
        tenant_id = int(payload.get("tid"))

        # Check if session is still valid
        session_data = Cache.get_json(f"{self.SESSION_PREFIX}{session_id}")
        if not session_data:
            raise BizError(1002)

        # Check blacklist
        if Cache.get(f"{self.TOKEN_BLACKLIST_PREFIX}{session_id}"):
            raise BizError(1002)

        # Get user permissions
        perm_data = await self._get_user_permissions(user_id)

        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "perm_codes": perm_data.get("perm_codes", []),
            "data_scopes": perm_data.get("data_scopes", []),
            "dept_ids": perm_data.get("dept_ids", []),
            "ip_group_ids": perm_data.get("ip_group_ids", []),
        }

    async def _get_user_permissions(self, user_id: int) -> dict[str, Any]:
        """Get user's permission codes and data scopes."""
        # Try cache first
        cache_key = f"{self.PERM_CACHE_PREFIX}{user_id}"
        cached = Cache.get_json(cache_key)
        if cached:
            return cached

        # Load from database
        from app.domains.sys.models import Menu, Role, RoleMenu, UserDept, UserRole
        session = get_db_session()

        # Get user's enabled roles
        roles = session.query(Role).join(
            UserRole, UserRole.role_id == Role.id
        ).filter(
            UserRole.user_id == user_id,
            Role.status == "ENABLED",
            Role.deleted == 0,
        ).all()

        perm_codes = set()
        data_scopes = []

        for role in roles:
            # Get role's permission codes
            menus = session.query(Menu).join(
                RoleMenu, RoleMenu.menu_id == Menu.id
            ).filter(
                RoleMenu.role_id == role.id,
                Menu.status == "ENABLED",
                Menu.deleted == 0,
            ).all()

            for menu in menus:
                if menu.perm_code:
                    perm_codes.add(menu.perm_code)

            # Get role's data scope
            if role.data_scope:
                data_scopes.append(DataScope(
                    scope_type=role.data_scope,
                    role_id=role.id,
                ))

        # Get user's department IDs
        dept_ids = [ud.dept_id for ud in session.query(UserDept).filter(
            UserDept.user_id == user_id,
        ).all()]

        # Get user's IP group IDs (if applicable)
        ip_group_ids = []  # TODO: Load from IP group member table

        result = {
            "perm_codes": list(perm_codes),
            "data_scopes": [{"scope_type": ds.scope_type, "role_id": ds.role_id} for ds in data_scopes],
            "dept_ids": dept_ids,
            "ip_group_ids": ip_group_ids,
        }

        # Cache for 30 minutes
        Cache.set_json(cache_key, result, ttl=1800)

        return result

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token.

        Rules per FP-D01-03:
        - Valid refresh -> new access + new refresh
        - Old refresh immediately invalidated
        - Invalid/expired/reused -> 1002
        """
        # Find session by refresh token
        # This is inefficient but works for now - should use reverse index
        get_db_session()


        # Scan sessions (in production, use a refresh token -> session index)
        # For now, we'll need to store refresh tokens with user reference
        # This is a simplified implementation

        raise BizError(1002, msg="请重新登录")  # Placeholder

    async def logout(self, token: str) -> None:
        """
        Logout current session.

        Rules per FP-D01-04:
        - Delete session
        - Blacklist access token's session ID
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt.secret,
                algorithms=[settings.jwt.algorithm],
                options={"verify_exp": False},  # Allow expired tokens for logout
            )

            session_id = payload.get("sid")
            user_id = payload.get("sub")

            if session_id:
                # Delete session
                Cache.delete(f"{self.SESSION_PREFIX}{session_id}")

                # Blacklist the session ID
                exp = payload.get("exp")
                if exp:
                    from app.core.clock import get_now
                    remaining = max(0, exp - get_now().timestamp())
                    Cache.set(
                        f"{self.TOKEN_BLACKLIST_PREFIX}{session_id}",
                        "1",
                        ttl=int(remaining) + 60,
                    )

                # Remove from user's session list
                if user_id:
                    Cache.srem(f"{self.USER_SESSIONS_PREFIX}{user_id}", session_id)

            # Write logout log
            await self._write_login_log(
                user_id=int(user_id) if user_id else None,
                method="PASSWORD",
                result="LOGOUT",
            )
        except jwt.InvalidTokenError:
            pass  # Invalid token, nothing to logout

    async def get_current_user_info(self, user_id: int) -> dict[str, Any]:
        """
        Get current user's info, menus, and permissions.

        Rules per FP-D06-01:
        - Menu tree = tenant package ∩ role menus
        - Tree contains DIR and MENU only; BUTTON stays in perm_codes
        - dataScopeText in Chinese
        - Empty permissions -> empty menus with prompt
        """
        from app.domains.sys.models import Dept, User
        session = get_db_session()

        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise BizError(1002)

        # Get main department name
        main_dept_name = None
        if user.main_dept_id:
            dept = session.query(Dept).filter(Dept.id == user.main_dept_id).first()
            if dept:
                main_dept_name = dept.name

        # Get permissions
        perm_data = await self._get_user_permissions(user_id)

        # Build data scope text
        data_scope_text = await self._build_data_scope_text(perm_data, user_id)

        # Build menu tree
        menus = await self._build_user_menu_tree(user_id, user.tenant_id)

        return {
            "user": {
                "id": str(user.id),
                "username": user.username,
                "nickname": user.nickname,
                "avatar": None,  # TODO
                "main_dept_name": main_dept_name,
                "dept_names": [],  # TODO
                "position_label": None,  # TODO
                "pwd_reset_required": user.pwd_reset_required or False,
            },
            "menus": menus,
            "perm_codes": perm_data.get("perm_codes", []),
            "perm_details": {},  # TODO: R/W/D details
            "data_scope_text": data_scope_text,
        }

    async def _build_data_scope_text(
        self, perm_data: dict[str, Any], user_id: int
    ) -> str:
        """Build Chinese data scope description."""
        data_scopes = perm_data.get("data_scopes", [])

        if not data_scopes:
            return "您的账号尚未分配权限，请联系管理员"

        scope_types = {ds["scope_type"] for ds in data_scopes}

        if "ALL" in scope_types:
            return "全部"

        parts = []

        if "DEPT" in scope_types:
            dept_ids = perm_data.get("dept_ids", [])
            if dept_ids:
                from app.domains.sys.models import Dept
                session = get_db_session()
                depts = session.query(Dept).filter(Dept.id.in_(dept_ids)).all()
                dept_names = [d.name for d in depts]
                parts.append(f"本部门（{'、'.join(dept_names)}）")
            else:
                parts.append("本部门")

        if "IP_GROUP" in scope_types:
            parts.append("所属 IP 组")

        if "SELF" in scope_types:
            parts.append("仅本人")

        return "、".join(parts) if parts else "未配置数据范围"

    async def _build_user_menu_tree(
        self, user_id: int, tenant_id: int
    ) -> list[dict[str, Any]]:
        """Menu tree = tenant package menus ∩ enabled role menus (FP-D06-01)."""
        from app.domains.sys.models import Menu, Role, RoleMenu, Tenant, TenantPackageMenu, UserRole
        session = get_db_session()

        role_ids = [
            row.role_id
            for row in session.query(UserRole).join(
                Role, Role.id == UserRole.role_id
            ).filter(
                UserRole.user_id == user_id,
                Role.status == "ENABLED",
                Role.deleted == 0,
            ).all()
        ]
        if not role_ids:
            return []

        role_menu_ids = {
            row.menu_id
            for row in session.query(RoleMenu).filter(RoleMenu.role_id.in_(role_ids)).all()
        }
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant is not None and tenant.package_id:
            package_ids = {
                row.menu_id
                for row in session.query(TenantPackageMenu).filter(
                    TenantPackageMenu.package_id == tenant.package_id
                ).all()
            }
            role_menu_ids &= package_ids

        if not role_menu_ids:
            return []

        menus = session.query(Menu).filter(
            Menu.id.in_(role_menu_ids),
            Menu.status == "ENABLED",
            Menu.deleted == 0,
            Menu.type.in_(("DIR", "MENU")),
        ).all()
        return _nest_menu_tree(menus)

    async def change_password(
        self, user_id: int, new_password: str, keep_session_id: str
    ) -> None:
        """Change password and invalidate every session except the current one."""
        from app.domains.sys.models import User
        session = get_db_session()
        user = session.query(User).filter(User.id == user_id, User.deleted == 0).first()
        if user is None:
            raise BizError(1002)
        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        user.token_version = (user.token_version or 0) + 1
        user.pwd_reset_required = False
        sessions_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        for sid in list(Cache.smembers(sessions_key)):
            if sid == keep_session_id:
                continue
            Cache.delete(f"{self.SESSION_PREFIX}{sid}")
            Cache.set(f"{self.TOKEN_BLACKLIST_PREFIX}{sid}", "1", ttl=3600)
            Cache.srem(sessions_key, sid)
        session.flush()

    async def map_dingtalk_user_by_mobile(self, dingtalk_user_id: str, mobile: str) -> int:
        """Bind an unmapped DingTalk user to the local user with the same mobile."""
        from app.domains.sys.models import User, UserMapping
        from app.services.user import UserService

        session = get_db_session()
        mobile_hash = UserService()._hash_mobile(mobile)
        user = session.query(User).filter(
            User.mobile_hash == mobile_hash,
            User.deleted == 0,
        ).first()
        if user is None:
            raise BizError(1217)
        existing = session.query(UserMapping).filter(
            UserMapping.dingtalk_user_id == dingtalk_user_id,
            UserMapping.deleted == 0,
        ).first()
        if existing is None:
            session.add(UserMapping(
                tenant_id=user.tenant_id,
                user_id=user.id,
                dingtalk_user_id=dingtalk_user_id,
            ))
            session.flush()
        return user.id

    async def _write_login_log(
        self,
        user_id: Optional[int] = None,
        username: str = "",
        method: str = "PASSWORD",
        result: str = "SUCCESS",
    ) -> None:
        """Write login log entry."""
        # TODO: Implement login log writing
        pass

    async def get_dingtalk_redirect_url(self, redirect: str) -> str:
        """Get DingTalk SSO redirect URL."""
        # Validate redirect is site-relative
        if not redirect.startswith("/") or redirect.startswith("//"):
            redirect = "/"

        # Check if DingTalk is configured
        if not settings.dingtalk.app_key:
            raise BizError(1008, msg="钉钉登录未开启")

        # Generate state
        state = secrets.token_urlsafe(24)

        # Store state with redirect
        Cache.set_json(
            f"{self.SSO_STATE_PREFIX}{state}",
            {"redirect": redirect},
            ttl=300,  # 5 minutes
        )

        # Build DingTalk auth URL
        # TODO: Implement actual DingTalk URL
        auth_url = f"https://login.dingtalk.com/oauth2/auth?state={state}"

        return auth_url

    async def handle_dingtalk_callback(self, auth_code: str, state: str) -> str:
        """Handle DingTalk SSO callback."""
        # Verify and consume state (atomic GETDEL)
        state_data = Cache.getdel(f"{self.SSO_STATE_PREFIX}{state}")
        if not state_data:
            raise BizError(1002)

        import json
        state_info = json.loads(state_data) if isinstance(state_data, str) else state_data
        state_info.get("redirect", "/")

        # Exchange auth_code for DingTalk user info
        # TODO: Call DingTalk adapter

        raise BizError(1217)  # Placeholder - no match found
