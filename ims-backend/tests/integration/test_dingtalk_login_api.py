"""钉钉登录 HTTP。真实库、不替换 get_db 或鉴权，只替换钉钉客户端。"""

from fastapi.testclient import TestClient

from app.integrations.dingtalk.login_client import DingTalkIdentity, DingTalkLoginError
from app.services.dingtalk_login import reset_dingtalk_login_client, use_dingtalk_login_client
from tests.integration.test_real_db_api import _connect, _prepare_real_db, _release_real_db


class _Client:
    def __init__(self):
        self.by_code = {}
        self.fail_code = {}

    async def exchange(self, auth_code: str, channel: str):
        if auth_code in self.fail_code:
            raise DingTalkLoginError(self.fail_code[auth_code])
        return self.by_code[auth_code]


def _enable():
    from app.core.config import get_settings

    settings = get_settings()
    saved = (
        settings.dingtalk.app_key,
        settings.dingtalk.app_secret,
        settings.dingtalk.mode,
        settings.dingtalk.corp_id,
    )
    settings.dingtalk.app_key = "ding-client"
    settings.dingtalk.app_secret = "super-secret"
    settings.dingtalk.mode = "mock"
    settings.dingtalk.corp_id = "ding-corp"
    return settings, saved


def _restore(settings, saved) -> None:
    settings.dingtalk.app_key = saved[0]
    settings.dingtalk.app_secret = saved[1]
    settings.dingtalk.mode = saved[2]
    settings.dingtalk.corp_id = saved[3]


def _insert_user(session, username, ding_id, status="ACTIVE", tenant_id=1, mapping_tenant=None):
    from app.db.ids import assign_pk
    from app.domains.sys.models import User, UserMapping

    user = User(
        tenant_id=tenant_id,
        username=username,
        nickname=username,
        status=status,
        source="DINGTALK",
    )
    assign_pk(session, user)
    session.add(user)
    session.flush()
    mapping = UserMapping(
        tenant_id=tenant_id if mapping_tenant is None else mapping_tenant,
        user_id=user.id,
        dingtalk_user_id=ding_id,
    )
    assign_pk(session, mapping)
    session.add(mapping)
    session.commit()
    return user.id


def test_dingtalk_login_http_on_real_db(tmp_path):
    """登录选项、扫码回调、免登、未映射和须改密拦截。"""
    from app.domains.sys.models import LoginLog, User, UserMapping
    from app.main import app
    from tools.seed.users import E2E_PASSWORD

    db_url, original_url, context_token = _prepare_real_db(tmp_path)
    settings, saved = _enable()
    previous = use_dingtalk_login_client(_Client())
    try:
        engine, session = _connect(db_url)
        try:
            _insert_user(session, "dt_qr_user", "dt-ok")
            frozen = session.query(User).filter(User.username == "test_frozen").one()
            mapping = UserMapping(
                tenant_id=frozen.tenant_id,
                user_id=frozen.id,
                dingtalk_user_id="dt-frozen",
            )
            from app.db.ids import assign_pk
            assign_pk(session, mapping)
            session.add(mapping)
            stopped = session.query(User).filter(User.username == "test_t2").one()
            cross = UserMapping(
                tenant_id=1,
                user_id=stopped.id,
                dingtalk_user_id="dt-cross",
            )
            assign_pk(session, cross)
            session.add(cross)
            session.commit()
            before_users = session.query(User).count()
        finally:
            session.close()
            engine.dispose()

        client_obj = _Client()
        client_obj.by_code["ok"] = DingTalkIdentity(user_id="dt-ok", mobile=None)
        client_obj.by_code["none"] = DingTalkIdentity(user_id="dt-missing", mobile=None)
        client_obj.by_code["frozen"] = DingTalkIdentity(user_id="dt-frozen")
        client_obj.by_code["cross"] = DingTalkIdentity(user_id="dt-cross")
        client_obj.fail_code["slow"] = 5003
        reset_dingtalk_login_client(previous)
        previous = use_dingtalk_login_client(client_obj)

        with TestClient(app) as client:
            options = client.get("/admin-api/ims/auth/login-options")
            body = options.json()
            assert body["code"] == 0, body
            assert body["data"]["dingtalkEnabled"] is True
            assert body["data"]["clientId"] == "ding-client"
            assert body["data"]["corpId"] == "ding-corp"
            assert "super-secret" not in options.text

            params = client.get(
                "/admin-api/ims/auth/sso/dingtalk/authorize-params",
                params={"redirect": "/ims/home"},
            )
            param_body = params.json()
            assert param_body["code"] == 0, param_body
            state = param_body["data"]["state"]
            assert len(state) == 32

            callback = client.get(
                "/admin-api/ims/auth/sso/dingtalk/callback",
                params={"authCode": "ok", "state": state},
                follow_redirects=False,
            )
            assert callback.status_code == 302
            location = callback.headers["location"]
            assert location.startswith("/sso-callback#")
            assert "accessToken=" in location

            replay = client.get(
                "/admin-api/ims/auth/sso/dingtalk/callback",
                params={"authCode": "ok", "state": state},
                follow_redirects=False,
            )
            assert replay.status_code == 302
            assert "ssoError=1002" in replay.headers["location"]

            oauth_state = client.get(
                "/admin-api/ims/auth/sso/dingtalk/authorize-params",
                params={"redirect": "/ims/home"},
            ).json()["data"]["state"]
            oauth_code = client.get(
                "/admin-api/ims/auth/sso/dingtalk/callback",
                params={"code": "ok", "state": oauth_state},
                follow_redirects=False,
            )
            assert oauth_code.status_code == 302
            assert oauth_code.headers["location"].startswith("/sso-callback#")
            assert "accessToken=" in oauth_code.headers["location"]

            h5 = client.post(
                "/admin-api/ims/auth/sso/dingtalk/h5-login",
                json={"authCode": "ok"},
            )
            h5_body = h5.json()
            assert h5_body["code"] == 0, h5_body
            assert h5_body["data"]["accessToken"]
            assert h5_body["data"]["pwdResetRequired"] is False

            missing_state = client.get(
                "/admin-api/ims/auth/sso/dingtalk/authorize-params",
                params={"redirect": "/ims/home"},
            ).json()["data"]["state"]
            missing = client.get(
                "/admin-api/ims/auth/sso/dingtalk/callback",
                params={"authCode": "none", "state": missing_state},
                follow_redirects=False,
            )
            assert "ssoError=1217" in missing.headers["location"]

            frozen_state = client.get(
                "/admin-api/ims/auth/sso/dingtalk/authorize-params",
            ).json()["data"]["state"]
            frozen_resp = client.get(
                "/admin-api/ims/auth/sso/dingtalk/callback",
                params={"authCode": "frozen", "state": frozen_state},
                follow_redirects=False,
            )
            assert "ssoError=1216" in frozen_resp.headers["location"]

            cross_state = client.get(
                "/admin-api/ims/auth/sso/dingtalk/authorize-params",
            ).json()["data"]["state"]
            cross_resp = client.get(
                "/admin-api/ims/auth/sso/dingtalk/callback",
                params={"authCode": "cross", "state": cross_state},
                follow_redirects=False,
            )
            assert "ssoError=1504" in cross_resp.headers["location"]

            slow_state = client.get(
                "/admin-api/ims/auth/sso/dingtalk/authorize-params",
            ).json()["data"]["state"]
            slow = client.get(
                "/admin-api/ims/auth/sso/dingtalk/callback",
                params={"authCode": "slow", "state": slow_state},
                follow_redirects=False,
            )
            assert "ssoError=5003" in slow.headers["location"]

            cancel_state = client.get(
                "/admin-api/ims/auth/sso/dingtalk/authorize-params",
            ).json()["data"]["state"]
            cancel = client.get(
                "/admin-api/ims/auth/sso/dingtalk/callback",
                params={"error": "access_denied", "state": cancel_state},
                follow_redirects=False,
            )
            assert cancel.status_code == 302
            assert cancel.headers["location"] == "/login"

            password = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_admin", "password": E2E_PASSWORD},
            )
            assert password.json()["code"] == 0

            reset = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_reset", "password": E2E_PASSWORD},
            )
            token = reset.json()["data"]["accessToken"]
            blocked = client.get(
                "/admin-api/ims/auth/login-options",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert blocked.json()["code"] == 1008
            blocked_h5 = client.post(
                "/admin-api/ims/auth/sso/dingtalk/h5-login",
                headers={"Authorization": f"Bearer {token}"},
                json={"authCode": "ok"},
            )
            assert blocked_h5.json()["code"] == 1008
            anonymous = client.get("/admin-api/ims/auth/login-options")
            assert anonymous.json()["code"] == 0

        check_engine, check = _connect(db_url)
        try:
            assert check.query(User).count() == before_users
            methods = {
                row.login_method
                for row in check.query(LoginLog).filter(LoginLog.username == "dt_qr_user")
            }
            assert "DINGTALK_QR" in methods
            assert "DINGTALK_H5" in methods
        finally:
            check.close()
            check_engine.dispose()
    finally:
        reset_dingtalk_login_client(previous)
        _restore(settings, saved)
        _release_real_db(original_url, context_token)
