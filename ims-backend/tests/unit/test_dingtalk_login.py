"""钉钉登录服务（FP-B1-LG-01/04/05/06/09）。

走真实会话，不替换 get_db。钉钉外呼只替换客户端。
"""

import logging

import pytest

from app.core.cache import Cache
from app.core.errors import BizError
from app.integrations.dingtalk.login_client import DingTalkIdentity, DingTalkLoginError
from app.services.dingtalk_login import (
    CHANNEL_H5,
    CHANNEL_QR,
    STATE_PREFIX,
    DingTalkLoginService,
    load_dingtalk_config,
    reset_dingtalk_login_client,
    safe_redirect,
    sso_error_location,
    use_dingtalk_login_client,
)
from tests.support import rows


class ScriptedDingTalk:
    """按用例返回身份或抛出钉钉错误。"""

    def __init__(self, identity=None, error_code=None):
        self.identity = identity
        self.error_code = error_code
        self.calls = []

    async def exchange(self, auth_code: str, channel: str):
        self.calls.append((auth_code, channel))
        if self.error_code:
            raise DingTalkLoginError(self.error_code)
        return self.identity


def _enable(monkeypatch, app_key="ding-client", mode="mock", corp_id="ding-corp"):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings.dingtalk, "app_key", app_key)
    monkeypatch.setattr(settings.dingtalk, "app_secret", "do-not-leak")
    monkeypatch.setattr(settings.dingtalk, "mode", mode)
    monkeypatch.setattr(settings.dingtalk, "corp_id", corp_id)


def _mobile(raw: str) -> str:
    from app.services.user import UserService

    return UserService()._hash_mobile(raw)


@pytest.fixture
def ding_client():
    """多次替换时按相反顺序还原，避免客户端漏到下一个用例。"""
    tokens = []

    def _set(client):
        tokens.append(use_dingtalk_login_client(client))
        return client

    yield _set
    while tokens:
        reset_dingtalk_login_client(tokens.pop())


class TestDingTalkConfig:
    """启用开关读参数，缺省回落到环境配置。"""

    def test_disabled_without_client_id(self, db_session):
        config = load_dingtalk_config()
        assert config["enabled"] is False
        options = DingTalkLoginService().login_options()
        assert options["dingtalk_enabled"] is False
        assert options["client_id"] == ""
        assert "do-not-leak" not in str(options)

    def test_enabled_from_settings(self, db_session, monkeypatch):
        _enable(monkeypatch)
        options = DingTalkLoginService().login_options()
        assert options["dingtalk_enabled"] is True
        assert options["client_id"] == "ding-client"
        assert options["corp_id"] == "ding-corp"
        assert "secret" not in options

    def test_param_turns_mode_off(self, db_session, monkeypatch):
        from app.domains.sys.models import SysParam

        _enable(monkeypatch)
        rows.add(db_session, SysParam(
            tenant_id=1, param_key="dingtalk.mode", name="模式",
            group="钉钉", value_type="TEXT", value="off",
        ))
        assert load_dingtalk_config()["enabled"] is False

    def test_param_supplies_client_and_corp(self, db_session, monkeypatch):
        from app.domains.sys.models import SysParam

        _enable(monkeypatch, app_key="", corp_id="")
        rows.add(db_session, SysParam(
            tenant_id=1, param_key="dingtalk.clientId", name="客户端",
            group="钉钉", value_type="TEXT", value="from-param",
        ))
        rows.add(db_session, SysParam(
            tenant_id=1, param_key="dingtalk.corpId", name="企业",
            group="钉钉", value_type="TEXT", value="corp-param",
        ))
        config = load_dingtalk_config()
        assert config["enabled"] is True
        assert config["client_id"] == "from-param"
        assert config["corp_id"] == "corp-param"

    def test_blank_param_falls_back(self, db_session, monkeypatch):
        from app.domains.sys.models import SysParam

        _enable(monkeypatch)
        rows.add(db_session, SysParam(
            tenant_id=1, param_key="dingtalk.clientId", name="客户端",
            group="钉钉", value_type="TEXT", value="  ",
        ))
        assert load_dingtalk_config()["client_id"] == "ding-client"

    def test_param_read_without_session(self):
        from app.db.session import _db_session
        from app.services.dingtalk_login import _param_value

        token = _db_session.set(None)
        try:
            assert _param_value("dingtalk.mode") is None
        finally:
            _db_session.reset(token)


class TestDingTalkState:
    """state 与跳转地址。"""

    @pytest.mark.asyncio
    async def test_authorize_and_redirect_reject_external(self, db_session, monkeypatch):
        _enable(monkeypatch)
        service = DingTalkLoginService()
        params = await service.authorize_params("//evil.example", "https://app.example/cb")
        assert params["client_id"] == "ding-client"
        assert params["redirect_uri"] == "https://app.example/cb"
        assert params["scope"] == "openid"
        assert len(params["state"]) == 32
        stored = Cache.get_json(f"{STATE_PREFIX}{params['state']}")
        assert stored == {"redirect": "/"}

        url = await service.build_redirect_url("/ims/home")
        assert url.startswith("https://login.dingtalk.com/oauth2/auth?state=")
        assert "client_id=ding-client" in url

    @pytest.mark.asyncio
    async def test_authorize_when_disabled(self, db_session):
        with pytest.raises(BizError) as caught:
            await DingTalkLoginService().authorize_params("/ims/home", "/cb")
        assert caught.value.code == 1008
        assert caught.value.msg == "钉钉登录未开启"

    def test_safe_redirect_and_error_location(self):
        assert safe_redirect("https://evil.example") == "/"
        assert safe_redirect("//evil.example") == "/"
        assert safe_redirect("") == "/"
        assert safe_redirect("/ims/home") == "/ims/home"
        assert sso_error_location(BizError(1217)) == "/login?ssoError=1217"


class TestDingTalkCallback:
    """回调匹配、错误和日志。"""

    def _state(self, redirect="/ims/home") -> str:
        state = "a" * 32
        Cache.set_json(f"{STATE_PREFIX}{state}", {"redirect": redirect}, ttl=300)
        return state

    @pytest.mark.asyncio
    async def test_missing_bad_and_reused_state(self, db_session, test_context, monkeypatch):
        from app.domains.sys.models import LoginLog

        _enable(monkeypatch)
        service = DingTalkLoginService()
        with pytest.raises(BizError) as missing:
            await service.handle_callback("code", "missing", "")
        assert missing.value.code == 1002

        Cache.set(f"{STATE_PREFIX}badjson", "not-json", ttl=60)
        with pytest.raises(BizError) as bad:
            await service.handle_callback("code", "badjson", "")
        assert bad.value.code == 1002

        Cache.set(f"{STATE_PREFIX}listjson", "[]", ttl=60)
        with pytest.raises(BizError) as listed:
            await service.handle_callback("code", "listjson", "")
        assert listed.value.code == 1002

        state = self._state()
        with pytest.raises(BizError) as empty_code:
            await service.handle_callback("  ", state, "")
        assert empty_code.value.code == 1001
        assert Cache.get(f"{STATE_PREFIX}{state}") is None

        results = [row.result for row in db_session.query(LoginLog).all()]
        assert "1002" in results
        assert "1001" in results

    @pytest.mark.asyncio
    async def test_non_string_state(self, db_session, test_context, monkeypatch):
        _enable(monkeypatch)

        def _raw(_key):
            return 1

        monkeypatch.setattr(Cache, "getdel", staticmethod(_raw))
        with pytest.raises(BizError) as caught:
            await DingTalkLoginService().handle_callback("code", "whatever", "")
        assert caught.value.code == 1002

    @pytest.mark.asyncio
    async def test_disabled_after_valid_state(self, db_session, test_context):
        state = self._state()
        with pytest.raises(BizError) as caught:
            await DingTalkLoginService().handle_callback("code", state, "")
        assert caught.value.code == 1008
        assert caught.value.msg == "钉钉登录未开启"

    @pytest.mark.asyncio
    async def test_cancel_drops_state_without_failure_log(self, db_session, test_context, monkeypatch):
        from app.domains.sys.models import LoginLog

        _enable(monkeypatch)
        state = self._state()
        target = await DingTalkLoginService().handle_callback("", state, "access_denied")
        assert target == "/login"
        assert Cache.get(f"{STATE_PREFIX}{state}") is None
        assert db_session.query(LoginLog).count() == 0
        again = await DingTalkLoginService().handle_callback("", "", "Cancel")
        assert again == "/login"

    @pytest.mark.asyncio
    async def test_timeout_api_error_and_empty_userid(
        self, db_session, test_context, monkeypatch, ding_client,
    ):
        _enable(monkeypatch)
        service = DingTalkLoginService()
        ding_client(ScriptedDingTalk(error_code=5003))
        with pytest.raises(BizError) as timeout:
            await service.handle_callback("code", self._state(), "")
        assert timeout.value.code == 5003

        ding_client(ScriptedDingTalk(error_code=1006))
        with pytest.raises(BizError) as api_error:
            await service.handle_callback("code", self._state(), "")
        assert api_error.value.code == 1006

        ding_client(ScriptedDingTalk(identity=DingTalkIdentity(user_id="")))
        with pytest.raises(BizError) as empty_id:
            await service.handle_callback("code", self._state(), "")
        assert empty_id.value.code == 1006

    @pytest.mark.asyncio
    async def test_unmapped_empty_mobile_does_not_create_user(
        self, db_session, test_context, monkeypatch, ding_client,
    ):
        from app.domains.sys.models import LoginLog, User

        _enable(monkeypatch)
        before = db_session.query(User).count()
        ding_client(ScriptedDingTalk(identity=DingTalkIdentity(user_id="dt-new", mobile="  ")))
        with pytest.raises(BizError) as caught:
            await DingTalkLoginService().handle_callback("code", self._state(), "")
        assert caught.value.code == 1217
        assert db_session.query(User).count() == before
        log = db_session.query(LoginLog).filter(LoginLog.result == "1217").one()
        assert log.login_method == CHANNEL_QR
        assert log.username == "dt-new"

    @pytest.mark.asyncio
    async def test_multiple_mobiles_logged(
        self, db_session, test_context, monkeypatch, ding_client, caplog,
    ):
        from app.domains.sys.models import UserMapping

        _enable(monkeypatch)
        mobile_hash = _mobile("13900002222")
        rows.user(db_session, "mob_a", mobile_hash=mobile_hash)
        rows.user(db_session, "mob_b", mobile_hash=mobile_hash)
        ding_client(ScriptedDingTalk(
            identity=DingTalkIdentity(user_id="dt-multi", mobile="13900002222"),
        ))
        with caplog.at_level(logging.WARNING):
            with pytest.raises(BizError) as caught:
                await DingTalkLoginService().handle_callback("code", self._state(), "")
        assert caught.value.code == 1217
        assert db_session.query(UserMapping).count() == 0
        assert "多个本地用户" in caplog.text

    @pytest.mark.asyncio
    async def test_mobile_match_creates_mapping_and_ignores_password_lock(
        self, db_session, test_context, monkeypatch, ding_client,
    ):
        from app.domains.sys.models import LoginLog, UserMapping
        from app.services.auth import AuthService

        _enable(monkeypatch)
        person = rows.user(
            db_session, "mob_one", mobile_hash=_mobile("13900003333"),
            login_fail_count=4, pwd_reset_required=True,
        )
        Cache.set_json(f"{AuthService.LOGIN_FAIL_PREFIX}mob_one", {"count": 4}, ttl=600)
        ding_client(ScriptedDingTalk(identity=DingTalkIdentity(
            user_id="dt-one", mobile="13900003333", union_id="union-1", name="甲",
        )))
        target = await DingTalkLoginService().handle_callback("code", self._state("/ok"), "")
        assert target.startswith("/sso-callback#")
        assert "accessToken=" in target
        assert "redirect=%2Fok" in target or "redirect=/ok" in target
        link = db_session.query(UserMapping).filter(UserMapping.dingtalk_user_id == "dt-one").one()
        assert link.user_id == person.id
        assert link.union_id == "union-1"
        db_session.refresh(person)
        assert person.login_fail_count == 4
        assert Cache.get_json(f"{AuthService.LOGIN_FAIL_PREFIX}mob_one")["count"] == 4
        log = db_session.query(LoginLog).filter(LoginLog.result == "SUCCESS").one()
        assert log.login_method == CHANNEL_QR
        assert log.username == "mob_one"

    @pytest.mark.asyncio
    async def test_mapped_frozen_resigned_tenant_and_cross_tenant(
        self, db_session, test_context, monkeypatch, ding_client,
    ):
        from app.domains.sys.models import Tenant, UserMapping

        _enable(monkeypatch)
        frozen = rows.user(db_session, "dt_frozen", status="FROZEN")
        rows.add(db_session, UserMapping(
            tenant_id=frozen.tenant_id, user_id=frozen.id, dingtalk_user_id="dt-frozen",
        ))
        ding_client(ScriptedDingTalk(identity=DingTalkIdentity(user_id="dt-frozen", mobile=None)))
        with pytest.raises(BizError) as frozen_err:
            await DingTalkLoginService().handle_callback("code", self._state(), "")
        assert frozen_err.value.code == 1216

        left = rows.user(db_session, "dt_left", status="RESIGNED")
        rows.add(db_session, UserMapping(
            tenant_id=left.tenant_id, user_id=left.id, dingtalk_user_id="dt-left",
        ))
        ding_client(ScriptedDingTalk(identity=DingTalkIdentity(user_id="dt-left")))
        with pytest.raises(BizError) as left_err:
            await DingTalkLoginService().handle_callback("code", self._state(), "")
        assert left_err.value.code == 1216

        rows.add(db_session, Tenant(id=2, tenant_id=1, name="停用公司", status="DISABLED"))
        stopped = rows.user(db_session, "dt_stopped", tenant_id=2)
        rows.add(db_session, UserMapping(
            tenant_id=2, user_id=stopped.id, dingtalk_user_id="dt-stopped",
        ))
        ding_client(ScriptedDingTalk(identity=DingTalkIdentity(user_id="dt-stopped")))
        with pytest.raises(BizError) as stopped_err:
            await DingTalkLoginService().handle_callback("code", self._state(), "")
        assert stopped_err.value.code == 1008
        assert stopped_err.value.msg == "所属组织已停用"

        other = rows.user(db_session, "dt_other", tenant_id=2)
        rows.add(db_session, UserMapping(
            tenant_id=1, user_id=other.id, dingtalk_user_id="dt-cross",
        ))
        ding_client(ScriptedDingTalk(identity=DingTalkIdentity(user_id="dt-cross")))
        with pytest.raises(BizError) as cross:
            await DingTalkLoginService().handle_callback("code", self._state(), "")
        assert cross.value.code == 1504

    @pytest.mark.asyncio
    async def test_mapping_without_user_or_already_bound(
        self, db_session, test_context, monkeypatch, ding_client,
    ):
        from app.domains.sys.models import UserMapping

        _enable(monkeypatch)
        rows.add(db_session, UserMapping(
            tenant_id=1, user_id=987654, dingtalk_user_id="dt-gone",
        ))
        ding_client(ScriptedDingTalk(identity=DingTalkIdentity(user_id="dt-gone", mobile="13900004444")))
        with pytest.raises(BizError) as gone:
            await DingTalkLoginService().handle_callback("code", self._state(), "")
        assert gone.value.code == 1217

        person = rows.user(db_session, "already", mobile_hash=_mobile("13900004444"))
        rows.add(db_session, UserMapping(
            tenant_id=person.tenant_id, user_id=person.id, dingtalk_user_id="dt-old",
        ))
        ding_client(ScriptedDingTalk(
            identity=DingTalkIdentity(user_id="dt-new2", mobile="13900004444"),
        ))
        with pytest.raises(BizError) as bound:
            await DingTalkLoginService().handle_callback("code", self._state(), "")
        assert bound.value.code == 1217
        assert db_session.query(UserMapping).filter(
            UserMapping.dingtalk_user_id == "dt-new2",
        ).count() == 0

    @pytest.mark.asyncio
    async def test_default_client_unmatched(self, db_session, test_context, monkeypatch):
        """不注入客户端时走 mock 适配器，未映射仍是 1217。"""
        _enable(monkeypatch)
        with pytest.raises(BizError) as caught:
            await DingTalkLoginService().handle_callback("code", self._state(), "")
        assert caught.value.code == 1217

    @pytest.mark.asyncio
    async def test_dict_state_from_cache(self, db_session, test_context, monkeypatch):
        _enable(monkeypatch)
        monkeypatch.setattr(Cache, "getdel", staticmethod(lambda _key: {"redirect": "/dict"}))
        with pytest.raises(BizError) as caught:
            await DingTalkLoginService().handle_callback("code", "dict-state", "")
        assert caught.value.code == 1217


class TestDingTalkH5:
    """免登与扫码共用匹配。"""

    @pytest.mark.asyncio
    async def test_h5_validation_and_success(self, db_session, test_context, monkeypatch, ding_client):
        from app.domains.sys.models import LoginLog, UserMapping

        with pytest.raises(BizError) as missing:
            await DingTalkLoginService().h5_login("")
        assert missing.value.code == 1001

        with pytest.raises(BizError) as disabled:
            await DingTalkLoginService().h5_login("code")
        assert disabled.value.code == 1008

        _enable(monkeypatch)
        person = rows.user(db_session, "h5_user")
        rows.add(db_session, UserMapping(
            tenant_id=person.tenant_id, user_id=person.id, dingtalk_user_id="dt-h5",
        ))
        client = ding_client(ScriptedDingTalk(identity=DingTalkIdentity(user_id="dt-h5")))
        result = await DingTalkLoginService().h5_login("h5-code")
        assert result["pwd_reset_required"] is False
        assert result["access_token"]
        assert result["expires_in"] > 0
        assert client.calls == [("h5-code", CHANNEL_H5)]
        log = db_session.query(LoginLog).filter(
            LoginLog.login_method == CHANNEL_H5,
            LoginLog.result == "SUCCESS",
        ).one()
        assert log.username == "h5_user"

        ding_client(ScriptedDingTalk(error_code=5003))
        with pytest.raises(BizError) as timeout:
            await DingTalkLoginService().h5_login("again")
        assert timeout.value.code == 5003
