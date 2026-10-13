# app/integrations/dingtalk/login_client.py - 钉钉登录换票（可注入）
"""把扫码 authCode / H5 免登码换成钉钉身份。

业务服务只依赖 exchange()。测试替换整个客户端，不替换数据库或认证服务。
真实 HTTP 只在 mode=real 时发出；mock 返回适配器里的固定用户。
"""

from dataclasses import dataclass
from typing import Optional

import httpx

from app.integrations.dingtalk.client import DingTalkClient

# 扫码走新版 OAuth；H5 免登走企业内部应用 access_token + getuserinfo。
_QR_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/userAccessToken"
_QR_ME_URL = "https://api.dingtalk.com/v1.0/contact/users/me"
_APP_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
_H5_USERINFO_URL = "https://oapi.dingtalk.com/topapi/v2/user/getuserinfo"
_USER_GET_URL = "https://oapi.dingtalk.com/topapi/v2/user/get"


class DingTalkLoginError(Exception):
    """钉钉调用失败。code 只允许 5003（超时）或 1006（接口错误）。"""

    def __init__(self, code: int) -> None:
        self.code = code
        super().__init__(str(code))


@dataclass
class DingTalkIdentity:
    """登录匹配需要的身份。手机号可空，空则不能按手机号回落。"""

    user_id: str
    mobile: Optional[str] = None
    union_id: Optional[str] = None
    name: str = ""


class HttpxDingTalkLoginClient:
    """默认客户端。mode 不是 real 时不访问外网。"""

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        mode: str = "mock",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.app_key = app_key
        self.app_secret = app_secret
        self.mode = mode
        self.timeout = timeout_seconds

    async def exchange(self, auth_code: str, channel: str) -> DingTalkIdentity:
        """channel 为 DINGTALK_QR 或 DINGTALK_H5。"""
        if self.mode != "real":
            mock = DingTalkClient(mode="mock")._mock_user
            return DingTalkIdentity(
                user_id=mock.user_id,
                mobile=mock.mobile,
                union_id=mock.union_id,
                name=mock.name,
            )
        if channel == "DINGTALK_H5":
            return await self._exchange_h5(auth_code)
        return await self._exchange_qr(auth_code)

    async def _exchange_qr(self, auth_code: str) -> DingTalkIdentity:
        token_body = await self._json(
            "POST",
            _QR_TOKEN_URL,
            json={
                "clientId": self.app_key,
                "clientSecret": self.app_secret,
                "code": auth_code,
                "grantType": "authorization_code",
            },
        )
        access_token = str(token_body.get("accessToken") or "")
        if not access_token:
            raise DingTalkLoginError(1006)
        profile = await self._json(
            "GET",
            _QR_ME_URL,
            headers={"x-acs-dingtalk-access-token": access_token},
        )
        user_id = str(profile.get("unionId") or profile.get("openId") or "")
        if not user_id:
            raise DingTalkLoginError(1006)
        mobile = profile.get("mobile")
        return DingTalkIdentity(
            user_id=user_id,
            mobile=str(mobile) if mobile else None,
            union_id=str(profile.get("unionId") or "") or None,
            name=str(profile.get("nick") or ""),
        )

    async def _exchange_h5(self, auth_code: str) -> DingTalkIdentity:
        token_body = await self._json(
            "POST",
            _APP_TOKEN_URL,
            json={"appKey": self.app_key, "appSecret": self.app_secret},
        )
        access_token = str(token_body.get("accessToken") or "")
        if not access_token:
            raise DingTalkLoginError(1006)
        info = await self._json(
            "POST",
            _H5_USERINFO_URL,
            params={"access_token": access_token},
            json={"code": auth_code},
        )
        self._raise_if_errcode(info)
        result = info.get("result") or {}
        user_id = str(result.get("userid") or "")
        if not user_id:
            raise DingTalkLoginError(1006)
        mobile = None
        name = str(result.get("name") or "")
        try:
            detail = await self._json(
                "POST",
                _USER_GET_URL,
                params={"access_token": access_token},
                json={"userid": user_id},
            )
            self._raise_if_errcode(detail)
            detail_result = detail.get("result") or {}
            raw_mobile = detail_result.get("mobile")
            mobile = str(raw_mobile) if raw_mobile else None
            if detail_result.get("name"):
                name = str(detail_result["name"])
        except DingTalkLoginError:
            # 已经拿到 userid 时，手机号详情失败仍按 userid 匹配。
            mobile = None
        return DingTalkIdentity(
            user_id=user_id,
            mobile=mobile,
            union_id=str(result.get("unionid") or "") or None,
            name=name,
        )

    async def _json(self, method: str, url: str, **kwargs: object) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise DingTalkLoginError(5003) from exc
        except httpx.HTTPError as exc:
            raise DingTalkLoginError(1006) from exc
        if response.status_code >= 400:
            raise DingTalkLoginError(1006)
        try:
            body = response.json()
        except ValueError as exc:
            raise DingTalkLoginError(1006) from exc
        if not isinstance(body, dict):
            raise DingTalkLoginError(1006)
        return body

    @staticmethod
    def _raise_if_errcode(body: dict) -> None:
        errcode = body.get("errcode", 0)
        if errcode not in (0, "0", None):
            raise DingTalkLoginError(1006)
