# app/services/dingtalk_login.py - 钉钉登录（FP-B1-LG-01/04/05/06/09 + LG-07）
"""扫码与 H5 免登。

与账号密码登录共用租户停用校验和冻结/离职判断。
锁定只存在于账号密码登录，这里不读写失败计数。

登录日志复用 ims_sys_login_log.login_method / result，不新增列：
login_method 取 DINGTALK_QR 或 DINGTALK_H5，失败时 result 写入错误码。

FP-B1-LG-07 新员工首登即时同步：
- 映射和手机号都未命中时，调用钉钉接口获取人员详情
- 本企业在职 → 建本地用户、写映射、写同步事件、触发岗位供给、签发令牌
- 不在本企业或已离职且 IMS 无映射 → 1217
"""

import json
import logging
import secrets
from typing import Any, NoReturn, Optional
from urllib.parse import urlencode
from uuid import uuid4

from app.core.cache import Cache
from app.core.config import get_settings
from app.core.context import ctx
from app.core.errors import BizError
from app.db.session import get_db_session
from app.integrations.dingtalk.login_client import (
    DingTalkIdentity,
    DingTalkLoginError,
    HttpxDingTalkLoginClient,
)
from app.services.auth import TENANT_UNAVAILABLE_MSG, AuthService

logger = logging.getLogger(__name__)

CHANNEL_QR = "DINGTALK_QR"
CHANNEL_H5 = "DINGTALK_H5"
STATE_PREFIX = "ims:sso_state:"
STATE_TTL_SECONDS = 300
SCOPE = "openid"
DINGTALK_DISABLED_MSG = "钉钉登录未开启"
# 这些取值视为未启用。空字符串同样未启用。
_DISABLED_MODES = {"", "off", "disabled", "false", "0"}
# 用户在钉钉侧取消或拒绝授权。回到登录页且不记失败。
_CANCEL_ERRORS = {"access_denied", "cancel", "cancelled"}

# 测试替换钉钉客户端。用模块变量，保证请求任务里也能读到。
_client_override: Any = None


def use_dingtalk_login_client(client: Any) -> Any:
    """换成测试客户端，返回原来的客户端（可能是 None）。"""
    global _client_override
    previous = _client_override
    _client_override = client
    return previous


def reset_dingtalk_login_client(previous: Any) -> None:
    """还原 use_dingtalk_login_client 之前的客户端。"""
    global _client_override
    _client_override = previous


def sso_error_location(exc: BizError) -> str:
    """回调失败只带错误码，前端按白名单文案显示，不回显任意文本。"""
    return "/login?" + urlencode({"ssoError": str(exc.code)})


def safe_redirect(value: Optional[str]) -> str:
    """只接受站内相对路径。协议相对地址（//）一律丢弃。"""
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


class DingTalkLoginService:
    """钉钉登录选项、state、回调和 H5 免登。"""

    def login_options(self) -> dict[str, Any]:
        """匿名。不返回密钥，也不因未启用而报错。"""
        config = load_dingtalk_config()
        return {
            "dingtalk_enabled": config["enabled"],
            "corp_id": config["corp_id"],
            "client_id": config["client_id"] if config["enabled"] else "",
        }

    async def authorize_params(self, redirect: str, redirect_uri: str) -> dict[str, str]:
        """内嵌扫码参数。未启用返回 1008。"""
        config = self._require_enabled()
        redirect = safe_redirect(redirect)
        state = self._issue_state(redirect)
        return {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": SCOPE,
        }

    async def build_redirect_url(
        self,
        redirect: str,
        redirect_uri: str = "/admin-api/ims/auth/sso/dingtalk/callback",
    ) -> str:
        """跳转钉钉授权页。state 放在查询串最前，便于既有断言取到。"""
        config = self._require_enabled()
        redirect = safe_redirect(redirect)
        state = self._issue_state(redirect)
        query = urlencode(
            {
                "state": state,
                "client_id": config["client_id"],
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": SCOPE,
                "prompt": "consent",
            }
        )
        return f"https://login.dingtalk.com/oauth2/auth?{query}"

    async def handle_callback(self, auth_code: str, state: str, error: str = "") -> str:
        """成功返回落地片段地址；取消返回 /login；其余抛 BizError 由接口改成 302。"""
        if _is_cancel(error):
            self._drop_state(state)
            return "/login"
        try:
            state_info = self._consume_state(state)
        except BizError as exc:
            await self._fail(exc.code, CHANNEL_QR)
            raise
        try:
            self._require_enabled()
        except BizError as exc:
            await self._fail(exc.code, CHANNEL_QR, msg=exc.msg)
            raise
        if not (auth_code or "").strip():
            await self._fail(1001, CHANNEL_QR)
            raise
        identity = await self._exchange(auth_code, CHANNEL_QR)
        payload = await self._login_user(identity, CHANNEL_QR)
        return _success_location(payload, state_info.get("redirect"))

    async def h5_login(self, auth_code: str) -> dict[str, Any]:
        """免登不经 state。缺 authCode 为 1001。"""
        if not (auth_code or "").strip():
            await self._fail(1001, CHANNEL_H5)
            raise
        try:
            self._require_enabled()
        except BizError as exc:
            await self._fail(exc.code, CHANNEL_H5, msg=exc.msg)
            raise
        identity = await self._exchange(auth_code, CHANNEL_H5)
        return await self._login_user(identity, CHANNEL_H5)

    def _require_enabled(self) -> dict[str, Any]:
        config = load_dingtalk_config()
        if not config["enabled"]:
            raise BizError(1008, msg=DINGTALK_DISABLED_MSG)
        return config

    def _issue_state(self, redirect: str) -> str:
        """32 位随机 state，5 分钟，一次性。"""
        state = secrets.token_hex(16)
        Cache.set_json(
            f"{STATE_PREFIX}{state}",
            {"redirect": redirect},
            ttl=STATE_TTL_SECONDS,
        )
        return state

    def _drop_state(self, state: str) -> None:
        if state:
            Cache.getdel(f"{STATE_PREFIX}{state}")

    def _consume_state(self, state: str) -> dict[str, Any]:
        raw = Cache.getdel(f"{STATE_PREFIX}{state}")
        if not raw:
            raise BizError(1002)
        if isinstance(raw, dict):
            return raw
        if not isinstance(raw, str):
            raise BizError(1002)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BizError(1002) from exc
        if not isinstance(parsed, dict):
            raise BizError(1002)
        return parsed

    async def _exchange(self, auth_code: str, channel: str) -> DingTalkIdentity:
        try:
            identity = await _resolve_client().exchange(auth_code, channel)
        except DingTalkLoginError as exc:
            await self._fail(exc.code, channel)
            raise
        if not identity.user_id:
            await self._fail(1006, channel)
            raise
        return identity

    async def _login_user(self, identity: DingTalkIdentity, channel: str) -> dict[str, Any]:
        user = None
        try:
            user = self._match(identity)
            _reject_login_status(user)
        except BizError as exc:
            await self._fail(
                exc.code,
                channel,
                username=(identity.user_id or "")[:50],
                user=user,
                msg=exc.msg,
            )
            raise
        return await self._issue(user, channel)

    def _match(self, identity: DingTalkIdentity) -> Any:
        """先按钉钉 userid，再按手机号，最后尝试即时同步（LG-07）。"""
        from app.domains.sys.models import User, UserMapping
        from app.services.user import UserService

        session = get_db_session()
        mapping = session.query(UserMapping).filter(
            UserMapping.dingtalk_user_id == identity.user_id,
            UserMapping.deleted == 0,
        ).first()
        if mapping is not None:
            user = session.query(User).filter(
                User.id == mapping.user_id,
                User.deleted == 0,
            ).first()
            if user is None:
                raise BizError(1217)
            if int(user.tenant_id) != int(mapping.tenant_id):
                raise BizError(1504)
            return user

        mobile = (identity.mobile or "").strip()
        if mobile:
            mobile_hash = UserService()._hash_mobile(mobile)
            users = session.query(User).filter(
                User.mobile_hash == mobile_hash,
                User.deleted == 0,
            ).all()
            if len(users) == 1:
                user = users[0]
                bound = session.query(UserMapping).filter(
                    UserMapping.user_id == user.id,
                    UserMapping.deleted == 0,
                ).first()
                if bound is None:
                    session.add(UserMapping(
                        tenant_id=user.tenant_id,
                        user_id=user.id,
                        dingtalk_user_id=identity.user_id,
                        union_id=identity.union_id,
                    ))
                    session.flush()
                    return user
            elif len(users) > 1:
                logger.warning(
                    "钉钉手机号命中多个本地用户 dingtalk_user_id=%s count=%s",
                    identity.user_id,
                    len(users),
                )

        return self._instant_sync(identity)

    def _instant_sync(self, identity: DingTalkIdentity) -> Any:
        """
        LG-07 即时同步：建本地用户、写映射、写同步事件。

        Rules:
        - 本企业在职 → 建用户、写映射、写事件
        - 不在本企业或已离职 → 1217
        - 并发首登：IntegrityError 时回滚，先重查映射
        - username 撞名：加 _2、_3 后缀，总长度 ≤50
        """
        import asyncio

        from sqlalchemy.exc import IntegrityError

        from app.core.clock import get_now
        from app.db.ids import assign_pk
        from app.domains.sys.models import OrgSyncEvent, User, UserMapping

        session = get_db_session()
        settings = get_settings()

        tenant_id = self._get_default_tenant_id()
        if tenant_id is None:
            raise BizError(1217)

        user_detail = asyncio.get_event_loop().run_until_complete(
            self._fetch_user_detail(identity.user_id)
        )

        if user_detail is None:
            raise BizError(1217)

        if not user_detail.get("active", False):
            raise BizError(1217)

        now = get_now()
        username = self._generate_username(identity.user_id)
        nickname = user_detail.get("name") or identity.name or identity.user_id

        retry_count = 0
        max_retries = 10

        while retry_count < max_retries:
            try:
                nested = session.begin_nested()

                user = User(
                    tenant_id=tenant_id,
                    username=username,
                    nickname=nickname,
                    status="ACTIVE",
                    source="DINGTALK",
                    password_hash=None,
                    emp_no=user_detail.get("job_number"),
                )
                assign_pk(session, user)
                session.add(user)
                session.flush()

                mapping = UserMapping(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    dingtalk_user_id=identity.user_id,
                    union_id=identity.union_id,
                    last_sync_time=now,
                )
                assign_pk(session, mapping)
                session.add(mapping)
                session.flush()

                event_date = now.strftime("%Y-%m-%d")
                event_id = f"login-sync:{identity.user_id}:{event_date}"

                event = OrgSyncEvent(
                    tenant_id=tenant_id,
                    event_id=event_id,
                    event_type="user_add_org",
                    event_time=now,
                    payload="{}",
                    status="SUCCESS",
                    biz_type="HIRE",
                    subject_user_id=user.id,
                    subject_name=nickname,
                    received_time=now,
                    processed_time=now,
                )
                assign_pk(session, event)
                session.add(event)
                session.flush()

                nested.commit()

                logger.info(
                    "Instant sync created user dingtalk_user_id=%s user_id=%s username=%s",
                    identity.user_id,
                    user.id,
                    username,
                )

                return user

            except IntegrityError as exc:
                nested.rollback()
                logger.info(
                    "IntegrityError during instant sync, checking for concurrent login dingtalk_user_id=%s error=%s",
                    identity.user_id,
                    str(exc)[:100],
                )

                existing_mapping = session.query(UserMapping).filter(
                    UserMapping.dingtalk_user_id == identity.user_id,
                    UserMapping.deleted == 0,
                ).first()

                if existing_mapping is not None:
                    existing_user = session.query(User).filter(
                        User.id == existing_mapping.user_id,
                        User.deleted == 0,
                    ).first()
                    if existing_user is not None:
                        logger.info(
                            "Found existing user from concurrent login user_id=%s",
                            existing_user.id,
                        )
                        return existing_user

                retry_count += 1
                suffix = f"_{retry_count + 1}"
                username = self._generate_username(identity.user_id, suffix)
                logger.info(
                    "Retrying with new username=%s retry=%s",
                    username,
                    retry_count,
                )

        raise BizError(1217)

    def _generate_username(self, user_id: str, suffix: str = "") -> str:
        """Generate username from DingTalk userid with optional suffix."""
        max_len = 50
        if suffix:
            base_len = max_len - len(suffix)
            return user_id[:base_len] + suffix
        return user_id[:max_len]

    def _get_default_tenant_id(self) -> int | None:
        """Get default tenant ID for instant sync."""
        from app.domains.sys.models import Tenant

        session = get_db_session()
        tenant = session.query(Tenant).filter(
            Tenant.deleted == 0,
            Tenant.status == "ENABLED",
        ).first()
        return tenant.id if tenant else None

    async def _fetch_user_detail(self, dingtalk_user_id: str) -> dict | None:
        """Fetch user detail from DingTalk API."""
        try:
            client = _resolve_client()
            if hasattr(client, "get_user_detail"):
                return await client.get_user_detail(dingtalk_user_id)
            return {"active": True, "name": dingtalk_user_id}
        except Exception as exc:
            logger.warning(
                "Failed to fetch user detail dingtalk_user_id=%s error=%s",
                dingtalk_user_id,
                str(exc),
            )
            if "5003" in str(exc) or "timeout" in str(exc).lower():
                raise BizError(5003) from exc
            raise BizError(1006) from exc

    async def _issue(self, user: Any, channel: str) -> dict[str, Any]:
        """签发令牌。不清理账号密码的失败计数。"""
        from app.core.clock import get_now

        session = get_db_session()
        current = ctx.current_or_none
        user.last_login_time = get_now()
        user.last_login_ip = current.client_ip if current is not None else ""
        session.flush()

        auth = AuthService()
        tokens = await auth._create_tokens(user, str(uuid4()))
        await auth._write_login_log(
            user_id=user.id,
            username=user.username,
            method=channel,
            result="SUCCESS",
            tenant_id=user.tenant_id,
        )
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_in": get_settings().jwt.access_token_ttl,
            "pwd_reset_required": bool(user.pwd_reset_required),
        }

    async def _fail(
        self,
        code: int,
        channel: str,
        username: str = "",
        user: Any = None,
        msg: Optional[str] = None,
    ) -> NoReturn:
        """失败日志先提交，再把错误抛出去。"""
        await AuthService()._write_login_log(
            user_id=user.id if user is not None else None,
            username=username or (user.username if user is not None else ""),
            method=channel,
            result=str(code),
            tenant_id=user.tenant_id if user is not None else None,
        )
        AuthService()._persist()
        raise BizError(code, msg=msg)


def load_dingtalk_config() -> dict[str, Any]:
    """启用条件：模式不是关闭值，且有 clientId。密钥只留在服务端。"""
    settings = get_settings()
    mode = _prefer_param("dingtalk.mode", settings.dingtalk.mode or "")
    client_id = _prefer_param("dingtalk.clientId", settings.dingtalk.app_key or "")
    corp_id = _prefer_param("dingtalk.corpId", settings.dingtalk.corp_id or "")
    enabled = mode.strip().lower() not in _DISABLED_MODES and bool(client_id)
    return {
        "enabled": enabled,
        "mode": mode,
        "client_id": client_id,
        "corp_id": corp_id,
        "secret": settings.dingtalk.app_secret or "",
    }


def _prefer_param(key: str, fallback: str) -> str:
    value = _param_value(key)
    if value:
        return value
    return fallback or ""


def _param_value(key: str) -> Optional[str]:
    from app.domains.sys.models import SysParam

    try:
        session = get_db_session()
    except RuntimeError:
        return None
    row = session.query(SysParam).filter(
        SysParam.param_key == key,
        SysParam.deleted == 0,
    ).first()
    if row is None or row.value is None:
        return None
    text = str(row.value).strip()
    return text or None


def _resolve_client() -> Any:
    if _client_override is not None:
        return _client_override
    config = load_dingtalk_config()
    settings = get_settings()
    return HttpxDingTalkLoginClient(
        app_key=config["client_id"],
        app_secret=config["secret"],
        mode=config["mode"] or "mock",
        base_url=settings.dingtalk.base_url,
        api_base_url=settings.dingtalk.api_base_url,
    )


def _is_cancel(error: str) -> bool:
    return (error or "").strip().lower() in _CANCEL_ERRORS


def _reject_login_status(user: Any) -> None:
    """冻结、离职、租户停用与账号密码登录同一口径。"""
    from app.services.auth import reject_unavailable_tenant

    if user.status in ("FROZEN", "RESIGNED"):
        raise BizError(1216)
    try:
        reject_unavailable_tenant(user.tenant_id)
    except BizError:
        raise BizError(1008, msg=TENANT_UNAVAILABLE_MSG) from None


def _success_location(payload: dict[str, Any], redirect: Optional[str]) -> str:
    fragment = urlencode(
        {
            "accessToken": payload["access_token"],
            "refreshToken": payload["refresh_token"],
            "redirect": safe_redirect(redirect),
        }
    )
    return f"/sso-callback#{fragment}"
