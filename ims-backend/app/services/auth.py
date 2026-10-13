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

import math
import re
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import bcrypt
import jwt

from app.core.cache import Cache
from app.core.clock import BEIJING_TZ, get_now, parse_datetime
from app.core.config import get_settings
from app.core.context import DataScope, ctx
from app.core.errors import BizError
from app.db.session import get_db_session

settings = get_settings()

# 租户停用 / 过期时登录和刷新都用这一句，避免两处文案或条件不一致。
TENANT_UNAVAILABLE_MSG = "所属组织已停用"

# 8～32 位，同时含字母和数字，允许特殊字符，不允许空白（工作包 Q7）。
_PASSWORD_RULE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)\S{8,32}$")


def reject_unavailable_tenant(tenant_id: int) -> None:
    """登录和刷新共用的租户校验（FP-B04-04 / UT-B04-14）。

    没有租户行时不拦截。行一旦存在：状态不是 ENABLED，或到期时间已到
    （含等于当前时刻），返回 1008。
    """
    from app.domains.sys.models import Tenant

    session = get_db_session()
    tenant = session.query(Tenant).filter(Tenant.id == int(tenant_id)).first()
    if tenant is None:
        return
    if tenant.status != "ENABLED" or _tenant_expire_reached(tenant.expire_time):
        raise BizError(1008, msg=TENANT_UNAVAILABLE_MSG)


def _tenant_expire_reached(expire_time: Optional[datetime]) -> bool:
    """到期时间已到视为过期。库存时间不带时区，按钟面比较。"""
    if expire_time is None:
        return False
    return get_now().replace(tzinfo=None) >= expire_time.replace(tzinfo=None)


def session_remaining_seconds(session_data: dict[str, Any]) -> int:
    """会话剩余秒数。到期时间在登录时写定，轮换不得把它往后推。

    优先用 expires_at。旧会话没有该字段时，用 created_at 加刷新有效期。
    两个时间都没有时返回 0，调用方按已过期拒绝。
    """
    raw = session_data.get("expires_at")
    if raw:
        deadline = parse_datetime(str(raw))
    else:
        created_raw = session_data.get("created_at")
        if not created_raw:
            return 0
        created = parse_datetime(str(created_raw))
        deadline = created + timedelta(seconds=settings.jwt.refresh_token_ttl)
    return int((deadline - get_now()).total_seconds())


def _access_token_time_rejected(payload: dict[str, Any]) -> bool:
    """access 的 exp / iat 跟注入时钟比，不跟机器墙钟比。

    PyJWT 默认用 time.time()。单测把时钟拨到登录后将近 7 天时，
    刚换发的 access 的 iat 会落在墙钟的未来，被误判成尚未生效，
    从而盖住「会话剩余时间到点」这条校验。
    """
    now = get_now()
    now_ts = now.timestamp()
    exp = payload.get("exp")
    if exp is not None and now_ts >= float(exp):
        return True
    iat = payload.get("iat")
    return iat is not None and now_ts < float(iat)


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
    # 刷新令牌 → 会话。领取时用 GETDEL，保证同一枚令牌只会被用走一次。
    REFRESH_INDEX_PREFIX = "ims:refresh:"
    # 已经轮换过的刷新令牌 → 会话。重放时凭它吊销整段会话。
    REFRESH_USED_PREFIX = "ims:refresh_used:"
    REFRESH_LOCK_PREFIX = "ims:refresh_lock:"
    USER_SESSIONS_PREFIX = "ims:user_sessions:"
    LOGIN_FAIL_PREFIX = "ims:login_fail:"
    TOKEN_BLACKLIST_PREFIX = "ims:token_blacklist:"
    SSO_STATE_PREFIX = "ims:sso_state:"
    PERM_CACHE_PREFIX = "ims:perm:"

    # Session limits
    MAX_SESSIONS = 3

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """
        账号密码登录（FP-D01-01、FP-B1-LG-02/03）。

        不存在和密码错误都是 1214。连续第 5 次失败返回 1215，并带 remainMinutes。
        冻结、离职在密码正确之后才返回 1216。租户停用或过期仍走 reject_unavailable_tenant（1008）。
        失败先提交锁定次数和登录日志，再把错误抛回；请求回滚不能把这次失败清掉。
        """
        lock_key = f"{self.LOGIN_FAIL_PREFIX}{username}"
        self._reject_if_locked(lock_key, username)

        from app.domains.sys.models import User
        session = get_db_session()

        user = session.query(User).filter(
            User.username == username,
            User.deleted == 0,
        ).first()

        # 没有密码（钉钉同步用户）和密码错误一样，不暴露账号是否存在。
        if user is None or not _password_matches(user.password_hash, password):
            fail_data = await self._record_login_failure(username)
            self._apply_fail_count(user, fail_data)
            self._persist()
            if fail_data.get("lock_until"):
                self._raise_locked(str(fail_data["lock_until"]))
            raise BizError(1214)

        # 密码已经对上，才告诉调用方账号不能登录。
        if user.status in ("FROZEN", "RESIGNED"):
            await self._write_login_log(
                user_id=user.id,
                username=username,
                method="PASSWORD",
                result="DISABLED",
                tenant_id=user.tenant_id,
            )
            self._persist()
            raise BizError(1216)

        # 与刷新共用：停用或过期租户不能登录（FP-B04-04）。文案保持「所属组织已停用」。
        try:
            reject_unavailable_tenant(user.tenant_id)
        except BizError:
            await self._write_login_log(
                user_id=user.id,
                username=username,
                method="PASSWORD",
                result="DISABLED",
                tenant_id=user.tenant_id,
            )
            self._persist()
            raise

        Cache.delete(lock_key)

        now = get_now()
        user.last_login_time = now
        user.last_login_ip = ctx.current.client_ip if ctx.current_or_none else ""
        user.login_fail_count = 0
        user.lock_until = None
        session.flush()

        session_id = str(uuid4())
        tokens = await self._create_tokens(user, session_id)

        await self._write_login_log(
            user_id=user.id,
            username=username,
            method="PASSWORD",
            result="SUCCESS",
            tenant_id=user.tenant_id,
        )

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_in": settings.jwt.access_token_ttl,
            "pwd_reset_required": bool(user.pwd_reset_required),
        }

    def _reject_if_locked(self, lock_key: str, username: str) -> None:
        """锁定期内直接 1215。过期则清掉计数，下一次失败从 1 开始。"""
        fail_data = Cache.get_json(lock_key)
        if not fail_data:
            return
        lock_until = fail_data.get("lock_until")
        if not lock_until:
            return
        lock_time = parse_datetime(str(lock_until))
        if get_now() < lock_time:
            # 锁定期内的尝试也记一笔，不再累加次数。
            self._write_login_log_sync(username=username, method="PASSWORD", result="LOCKED")
            self._persist()
            self._raise_locked(str(lock_until))
        Cache.delete(lock_key)

    def _raise_locked(self, lock_until: str) -> None:
        minutes = _remain_minutes(parse_datetime(lock_until), get_now())
        raise BizError(1215, n=minutes, data={"remainMinutes": minutes})

    def _apply_fail_count(self, user: Any, fail_data: dict[str, Any]) -> None:
        """把缓存里的失败次数写回用户行。用户不存在时只留缓存。"""
        if user is None:
            return
        user.login_fail_count = int(fail_data.get("count", 0))
        lock_until = fail_data.get("lock_until")
        user.lock_until = _as_naive(parse_datetime(str(lock_until))) if lock_until else None
        get_db_session().flush()

    async def _record_login_failure(self, username: str) -> dict[str, Any]:
        """失败次数 +1。到达阈值时写入锁定截止时间，并记登录日志。"""
        lock_key = f"{self.LOGIN_FAIL_PREFIX}{username}"
        fail_data = Cache.get_json(lock_key) or {"count": 0}

        fail_data["count"] = fail_data.get("count", 0) + 1

        if fail_data["count"] >= settings.lock.max_fail_count:
            lock_until = get_now() + timedelta(minutes=settings.lock.lock_minutes)
            fail_data["lock_until"] = lock_until.isoformat()
            await self._write_login_log(
                username=username,
                method="PASSWORD",
                result="LOCKED",
            )
        else:
            await self._write_login_log(
                username=username,
                method="PASSWORD",
                result="BAD_CREDENTIAL",
            )

        Cache.set_json(lock_key, fail_data, ttl=settings.lock.lock_minutes * 60)
        return fail_data

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
        # 绝对 7 天：到期时间在登录时写定，后面轮换只换令牌，不改这个时刻。
        deadline = now + timedelta(seconds=settings.jwt.refresh_token_ttl)

        # Store session in Redis
        session_data = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "refresh_token": refresh_token,
            "created_at": now.isoformat(),
            "expires_at": deadline.isoformat(),
        }
        Cache.set_json(
            f"{self.SESSION_PREFIX}{session_id}",
            session_data,
            ttl=settings.jwt.refresh_token_ttl,
        )
        # 反向索引，刷新时不必扫描全部会话。TTL 与会话同时到期。
        Cache.set(
            f"{self.REFRESH_INDEX_PREFIX}{refresh_token}",
            session_id,
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
                # 被挤掉的会话连同它的刷新令牌一起作废。
                self._forget_refresh_index(
                    Cache.get_json(f"{self.SESSION_PREFIX}{oldest_session}")
                )
                Cache.delete(f"{self.SESSION_PREFIX}{oldest_session}")
                Cache.srem(sessions_key, oldest_session)

    async def verify_token(self, token: str) -> dict[str, Any]:
        """
        Verify access token and return user info.

        Returns dict with user_id, tenant_id, perm_codes, data_scopes, etc.
        """
        try:
            # exp/iat 交给 _access_token_time_rejected，跟 get_now() 比。
            payload = jwt.decode(
                token,
                settings.jwt.secret,
                algorithms=[settings.jwt.algorithm],
                options={"verify_exp": False, "verify_iat": False},
            )
        except jwt.InvalidTokenError as e:
            raise BizError(1002) from e

        if _access_token_time_rejected(payload):
            raise BizError(1002)
        if payload.get("type") != "access":
            raise BizError(1002)

        session_id = payload.get("sid")
        user_id = int(payload.get("sub"))
        tenant_id = int(payload.get("tid"))

        # Check if session is still valid
        session_data = Cache.get_json(f"{self.SESSION_PREFIX}{session_id}")
        if not session_data:
            raise BizError(1002)
        # 会话从登录起绝对 7 天，到点后访问令牌也失效（不靠 Redis 滑动续期）。
        if session_remaining_seconds(session_data) <= 0:
            raise BizError(1002)

        # Check blacklist
        if Cache.get(f"{self.TOKEN_BLACKLIST_PREFIX}{session_id}"):
            raise BizError(1002)

        # 须改密标记以库里的当前值为准。用户行不存在时不在这里改 1002，
        # 绝对 7 天和会话吊销仍按上面的会话键判断（#18）。
        from app.domains.sys.models import User
        account = get_db_session().query(User).filter(
            User.id == user_id,
            User.deleted == 0,
        ).first()
        pwd_reset_required = bool(account.pwd_reset_required) if account is not None else False

        # Get user permissions
        perm_data = await self._get_user_permissions(user_id)

        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "pwd_reset_required": pwd_reset_required,
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

    def _forget_refresh_index(self, session_data: Any) -> None:
        """删掉会话上当前刷新令牌的反向索引，避免登出或改密后旧令牌还能被领走。"""
        if isinstance(session_data, dict):
            refresh_token = session_data.get("refresh_token")
            if refresh_token:
                Cache.delete(f"{self.REFRESH_INDEX_PREFIX}{refresh_token}")

    async def _revoke_session(self, session_id: str) -> None:
        """吊销整段会话：当前 access 与刚换发的 refresh 都失效。"""
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        session_data = Cache.get_json(session_key)
        self._forget_refresh_index(session_data)
        user_id = session_data.get("user_id") if isinstance(session_data, dict) else None
        Cache.delete(session_key)
        # 黑名单挡住同一 sid 的访问令牌，即使会话键被重新写回也不放行。
        Cache.set(
            f"{self.TOKEN_BLACKLIST_PREFIX}{session_id}",
            "1",
            ttl=settings.jwt.access_token_ttl,
        )
        if user_id is not None:
            Cache.srem(f"{self.USER_SESSIONS_PREFIX}{user_id}", session_id)

    async def _issue_rotated_tokens(
        self,
        session_id: str,
        refresh_token: str,
        used_key: str,
    ) -> dict[str, Any]:
        """校验会话后签发新的 access 与 refresh，并把旧刷新令牌记成已轮换。"""
        from app.domains.sys.models import User

        session_key = f"{self.SESSION_PREFIX}{session_id}"
        session_data = Cache.get_json(session_key)
        if not isinstance(session_data, dict) or session_data.get("refresh_token") != refresh_token:
            raise BizError(1002)
        if Cache.get(f"{self.TOKEN_BLACKLIST_PREFIX}{session_id}"):
            raise BizError(1002)

        db = get_db_session()
        user = db.query(User).filter(
            User.id == int(session_data["user_id"]),
            User.deleted == 0,
        ).first()
        if user is None or user.status in ("FROZEN", "RESIGNED"):
            raise BizError(1002)
        # 停用或过期租户不能靠刷新续命，与登录共用同一校验。
        # 调用方 refresh() 已经 GETDEL 领走旧令牌。这里返回 1008 时旧 refresh 不会退回，必须重新登录。
        reject_unavailable_tenant(user.tenant_id)

        now = get_now()
        # 剩余时长沿用登录时的 expires_at。到点拒绝，不再把 TTL 重置成 7 天。
        remaining = session_remaining_seconds(session_data)
        if remaining <= 0:
            raise BizError(1002)
        new_refresh = secrets.token_urlsafe(32)
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
        session_data["refresh_token"] = new_refresh
        Cache.set_json(session_key, session_data, ttl=remaining)
        Cache.set(
            f"{self.REFRESH_INDEX_PREFIX}{new_refresh}",
            session_id,
            ttl=remaining,
        )
        # 新令牌落库之后才标记旧令牌。重放旧令牌时凭这个标记吊销整段会话。
        # 已轮换标记的 TTL 同样用剩余时长，不重新给满 7 天。
        Cache.set(used_key, session_id, ttl=remaining)
        return {
            "access_token": access_token,
            "refresh_token": new_refresh,
            "expires_in": settings.jwt.access_token_ttl,
            "pwd_reset_required": bool(user.pwd_reset_required),
        }

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """
        轮换访问令牌和刷新令牌。

        旧刷新令牌用 Redis Lua（SET NX + GETDEL）一次领走：
        - 领到会话：签发新的 access 与 refresh，旧 refresh 立即失效
        - 轮换不滑动续期：到期时间沿用登录时写入的 expires_at，
          新 refresh 的 Redis TTL 等于剩余秒数
        - 登录起满 7 天（剩余 <= 0）→ 1002
        - 先 GETDEL 领走旧 refresh，再校验租户。租户停用或过期 → 1008
          （与登录共用 reject_unavailable_tenant）。1008 时旧 refresh 已消耗，必须重新登录
        - 同一枚令牌并发领取：只有一个成功，另一个 1002，且不吊销会话
        - GETDEL 为空且没有已轮换记录：1002
        - 重放已经轮换过的刷新令牌：1002，并吊销整段会话
          （刚签发的 access 与 refresh 一并失效）
        """
        if not refresh_token:
            raise BizError(1002)

        lock_key = f"{self.REFRESH_LOCK_PREFIX}{refresh_token}"
        index_key = f"{self.REFRESH_INDEX_PREFIX}{refresh_token}"
        used_key = f"{self.REFRESH_USED_PREFIX}{refresh_token}"
        # 先领走旧 refresh，再进 _issue_rotated_tokens 校验租户。
        # 租户停用或过期返回 1008 时，旧令牌已经消耗，调用方必须重新登录。
        # status: ok / concurrent / reuse / missing（GETDEL 为空且不是重放）
        session_id, status = Cache.claim_refresh(lock_key, index_key, used_key, lock_ttl=10)
        try:
            if status == "concurrent":
                raise BizError(1002)
            if status == "reuse":
                await self._revoke_session(session_id)
                raise BizError(1002)
            if status != "ok":
                # GETDEL 为空：令牌不存在、已过期，或登出/改密时索引已被删掉。
                raise BizError(1002)
            return await self._issue_rotated_tokens(session_id, refresh_token, used_key)
        finally:
            # 并发失败者没有拿到锁，不能把赢家的锁删掉。
            if status != "concurrent":
                Cache.delete(lock_key)

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
                session_key = f"{self.SESSION_PREFIX}{session_id}"
                # 先丢掉刷新令牌索引，再删会话。旧 refresh 不能再换发。
                self._forget_refresh_index(Cache.get_json(session_key))
                Cache.delete(session_key)

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
        # 目录 → 菜单嵌套。按钮不进树，只留在 permCodes。
        # 目录节点带上库里的 path（例如权限管理 /ims/auth），与嵌套树一致。
        return _nest_menu_tree(menus)

    async def change_own_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
        keep_session_id: str,
    ) -> None:
        """校验原密码和新密码规则后落库（FP-B1-PW-01）。"""
        from app.domains.sys.models import User

        session = get_db_session()
        user = session.query(User).filter(User.id == user_id, User.deleted == 0).first()
        if user is None:
            raise BizError(1002)
        if not _password_matches(user.password_hash, old_password):
            raise BizError(1214)
        _validate_new_password(old_password, new_password)
        await self.change_password(user_id, new_password, keep_session_id)

    async def change_password(
        self, user_id: int, new_password: str, keep_session_id: str
    ) -> None:
        """写入新密码，清掉须改密标记，并作废其他会话。当前会话保留。"""
        from app.domains.sys.models import User
        session = get_db_session()
        user = session.query(User).filter(User.id == user_id, User.deleted == 0).first()
        if user is None:
            raise BizError(1002)
        # cost=10，与种子账号一致，改密不必比登录慢一个数量级。
        user.password_hash = bcrypt.hashpw(
            new_password.encode(), bcrypt.gensalt(rounds=10)
        ).decode()
        user.token_version = (user.token_version or 0) + 1
        user.pwd_reset_required = False
        sessions_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        for sid in list(Cache.smembers(sessions_key)):
            if sid == keep_session_id:
                continue
            session_key = f"{self.SESSION_PREFIX}{sid}"
            # 其它会话的旧刷新令牌一并失效，当前这次登录的刷新令牌保留。
            self._forget_refresh_index(Cache.get_json(session_key))
            Cache.delete(session_key)
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
        tenant_id: Optional[int] = None,
    ) -> None:
        """写入登录日志。渠道用已有 login_method，失败原因用 result。"""
        self._write_login_log_sync(
            user_id=user_id,
            username=username,
            method=method,
            result=result,
            tenant_id=tenant_id,
        )

    def _write_login_log_sync(
        self,
        user_id: Optional[int] = None,
        username: str = "",
        method: str = "PASSWORD",
        result: str = "SUCCESS",
        tenant_id: Optional[int] = None,
    ) -> None:
        """同步写登录日志，供锁定期内的同步分支调用。不新增列。"""
        from app.domains.sys.models import LoginLog

        current = ctx.current_or_none
        if tenant_id is not None:
            resolved_tenant = tenant_id
        elif current is not None and current.tenant_id:
            resolved_tenant = current.tenant_id
        else:
            resolved_tenant = 1
        ip = ""
        agent = ""
        if current is not None:
            ip = current.client_ip or ""
            agent = (current.user_agent or "")[:500]
        log = LoginLog(
            tenant_id=resolved_tenant,
            username=username or "",
            user_id=user_id,
            login_method=method,
            result=result,
            ip=ip,
            user_agent=agent,
        )
        get_db_session().add(log)
        get_db_session().flush()

    def _persist(self) -> None:
        """失败登录先提交。请求若再抛错，依赖层回滚的是提交之后的空事务。"""
        get_db_session().commit()

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


def _password_matches(password_hash: Optional[str], password: str) -> bool:
    """空哈希或坏哈希都当作密码不匹配，避免抛出库异常。"""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def _validate_new_password(old_password: str, new_password: str) -> None:
    """新密码规则。文案与前端改密页一致，错误码用 1001。"""
    if re.search(r"\s", new_password):
        raise BizError(1001, msg="密码不能包含空格")
    if _PASSWORD_RULE.fullmatch(new_password) is None:
        raise BizError(1001, msg="密码需 8～32 位，且同时包含字母和数字")
    if new_password == old_password:
        raise BizError(1001, msg="新密码不能与当前密码相同")


def _remain_minutes(lock_time: datetime, now: datetime) -> int:
    """剩余分钟向上取整。刚锁定 15 分钟时返回 15，不足 1 分钟时返回 1。"""
    seconds = (lock_time - now).total_seconds()
    return max(1, math.ceil(seconds / 60))


def _as_naive(value: datetime) -> datetime:
    """库存 DATETIME 不带时区，写入先换成北京时间的朴素时间。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(BEIJING_TZ).replace(tzinfo=None)
