"""钉钉扫码换票。企业 userid 来自 unionId 解析，不使用 unionId / openId。"""

import json

import httpx
import pytest

from app.integrations.dingtalk.login_client import (
    DingTalkLoginError,
    HttpxDingTalkLoginClient,
)


def _client(handler) -> HttpxDingTalkLoginClient:
    return HttpxDingTalkLoginClient(
        app_key="ding-key",
        app_secret="ding-secret",
        mode="real",
        transport=httpx.MockTransport(handler),
    )


def _qr_handler(union_body: dict, profile: dict | None = None, fail: Exception | None = None):
    """按路径回放扫码四步。fail 在解析企业 userid 时抛出。"""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/oauth2/userAccessToken"):
            return httpx.Response(200, json={"accessToken": "user-token"})
        if path.endswith("/contact/users/me"):
            body = profile or {
                "unionId": "union-1",
                "openId": "open-1",
                "nick": "张三",
                "mobile": "13800000000",
            }
            return httpx.Response(200, json=body)
        if path.endswith("/oauth2/accessToken"):
            return httpx.Response(200, json={"accessToken": "app-token"})
        if path.endswith("/user/getbyunionid"):
            if fail is not None:
                raise fail
            assert request.url.params["access_token"] == "app-token"
            assert json.loads(request.content)["unionid"] == "union-1"
            return httpx.Response(200, json=union_body)
        return httpx.Response(404, json={"errcode": 404})

    return handler


@pytest.mark.asyncio
async def test_qr_exchange_uses_enterprise_userid_not_union_or_open():
    client = _client(_qr_handler({"errcode": 0, "result": {"userid": "staff-9"}}))
    identity = await client.exchange("auth-code", "DINGTALK_QR")
    assert identity.user_id == "staff-9"
    assert identity.user_id not in {"union-1", "open-1"}
    assert identity.union_id == "union-1"
    assert identity.mobile == "13800000000"
    assert identity.name == "张三"


@pytest.mark.asyncio
async def test_qr_unionid_resolve_failure_is_1006():
    client = _client(_qr_handler({"errcode": 60121, "errmsg": "not in corp"}))
    with pytest.raises(DingTalkLoginError) as caught:
        await client.exchange("auth-code", "DINGTALK_QR")
    assert caught.value.code == 1006


@pytest.mark.asyncio
async def test_qr_unionid_without_userid_is_1006():
    client = _client(_qr_handler({"errcode": 0, "result": {}}))
    with pytest.raises(DingTalkLoginError) as caught:
        await client.exchange("auth-code", "DINGTALK_QR")
    assert caught.value.code == 1006


@pytest.mark.asyncio
async def test_qr_openid_alone_is_not_userid():
    client = _client(_qr_handler({}, profile={"openId": "open-1", "nick": "张三"}))
    with pytest.raises(DingTalkLoginError) as caught:
        await client.exchange("auth-code", "DINGTALK_QR")
    assert caught.value.code == 1006


@pytest.mark.asyncio
async def test_qr_unionid_resolve_timeout_is_5003():
    client = _client(_qr_handler({}, fail=httpx.ReadTimeout("slow")))
    with pytest.raises(DingTalkLoginError) as caught:
        await client.exchange("auth-code", "DINGTALK_QR")
    assert caught.value.code == 5003
