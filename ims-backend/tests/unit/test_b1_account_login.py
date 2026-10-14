"""账号登录与改密（FP-B1-LG-02/03/08/09、FP-B1-PW-01）。"""

from datetime import datetime, timedelta

import pytest
from starlette.requests import Request

from app.core.clock import BEIJING_TZ, get_now
from app.core.context import RequestContext, ctx
from tests.support import rows


def _hash(raw: str) -> str:
    import bcrypt

    # 单测用较低 cost，校验逻辑与 cost=10 的种子哈希相同。
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt(rounds=4)).decode()


def _request(path: str) -> Request:
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    })


class TestLoginLockAndStatus:
    """锁定、冻结、离职、租户停用。"""

    @pytest.mark.asyncio
    async def test_fifth_failure_locks_for_15_minutes(self, db_session, test_context):
        from app.core.errors import BizError
        from app.domains.sys.models import LoginLog
        from app.services.auth import AuthService

        person = rows.user(db_session, "lock_me", password_hash=_hash("Test1234"))
        service = AuthService()
        for _ in range(4):
            with pytest.raises(BizError) as caught:
                await service.login("lock_me", "Wrong1234")
            assert caught.value.code == 1214
        with pytest.raises(BizError) as locked:
            await service.login("lock_me", "Wrong1234")
        assert locked.value.code == 1215
        assert locked.value.data["remainMinutes"] == 15
        assert "15" in locked.value.msg
        with pytest.raises(BizError) as still:
            await service.login("lock_me", "Test1234")
        assert still.value.code == 1215
        db_session.refresh(person)
        assert person.login_fail_count == 5
        results = [row.result for row in db_session.query(LoginLog).filter(LoginLog.username == "lock_me")]
        assert results.count("BAD_CREDENTIAL") == 4
        assert "LOCKED" in results

    @pytest.mark.asyncio
    async def test_lock_minutes_drop_then_expire(self, db_session, test_context, fixed_time):
        from app.core.cache import Cache
        from app.core.errors import BizError
        from app.services.auth import AuthService

        start = get_now()
        fixed_time(start)
        rows.user(db_session, "timed_lock", password_hash=_hash("Test1234"))
        service = AuthService()
        for _ in range(5):
            with pytest.raises(BizError):
                await service.login("timed_lock", "Wrong1234")

        fixed_time(start + timedelta(minutes=5))
        with pytest.raises(BizError) as mid:
            await service.login("timed_lock", "Test1234")
        assert mid.value.code == 1215
        assert mid.value.data["remainMinutes"] == 10

        fixed_time(start + timedelta(minutes=15, seconds=1))
        result = await service.login("timed_lock", "Test1234")
        assert result["pwd_reset_required"] is False
        assert Cache.get_json(f"{service.LOGIN_FAIL_PREFIX}timed_lock") is None

    @pytest.mark.asyncio
    async def test_missing_user_and_bad_hash_do_not_leak(self, db_session, test_context):
        from app.core.errors import BizError
        from app.domains.sys.models import LoginLog
        from app.services.auth import AuthService

        rows.user(db_session, "empty_hash", password_hash=None)
        rows.user(db_session, "bad_hash", password_hash="not-a-bcrypt-hash")
        service = AuthService()
        codes = []
        for _ in range(5):
            with pytest.raises(BizError) as caught:
                await service.login("nobody_x", "Test1234")
            codes.append(caught.value.code)
        assert codes == [1214, 1214, 1214, 1214, 1215]
        with pytest.raises(BizError) as empty:
            await service.login("empty_hash", "Test1234")
        assert empty.value.code == 1214
        with pytest.raises(BizError) as bad:
            await service.login("bad_hash", "Test1234")
        assert bad.value.code == 1214
        empty_rows = db_session.query(LoginLog).filter(LoginLog.username == "empty_hash").all()
        assert [row.result for row in empty_rows] == ["BAD_CREDENTIAL"]

    @pytest.mark.asyncio
    async def test_frozen_and_resigned_after_password(self, db_session, test_context):
        from app.core.errors import BizError
        from app.domains.sys.models import LoginLog
        from app.services.auth import AuthService

        rows.user(db_session, "frozen_u", status="FROZEN", password_hash=_hash("Test1234"))
        rows.user(db_session, "left_u", status="RESIGNED", password_hash=_hash("Test1234"))
        service = AuthService()
        with pytest.raises(BizError) as frozen_wrong:
            await service.login("frozen_u", "Wrong1234")
        assert frozen_wrong.value.code == 1214
        with pytest.raises(BizError) as frozen:
            await service.login("frozen_u", "Test1234")
        assert frozen.value.code == 1216
        with pytest.raises(BizError) as left:
            await service.login("left_u", "Test1234")
        assert left.value.code == 1216
        frozen_rows = db_session.query(LoginLog).filter(LoginLog.username == "frozen_u").all()
        assert any(row.result == "DISABLED" for row in frozen_rows)
        assert any(row.result == "BAD_CREDENTIAL" for row in frozen_rows)

    @pytest.mark.asyncio
    async def test_disabled_and_expired_tenant(self, db_session, test_context):
        from app.core.errors import BizError
        from app.domains.sys.models import Tenant
        from app.services.auth import TENANT_UNAVAILABLE_MSG, AuthService

        db_session.add(Tenant(id=8, tenant_id=1, name="停用", status="DISABLED"))
        db_session.add(Tenant(
            id=9,
            tenant_id=1,
            name="过期",
            status="ENABLED",
            expire_time=get_now().replace(tzinfo=None) - timedelta(days=1),
        ))
        db_session.add(Tenant(id=10, tenant_id=1, name="正常", status="ENABLED"))
        db_session.flush()
        rows.user(db_session, "off_tenant", tenant_id=8, password_hash=_hash("Test1234"))
        rows.user(db_session, "old_tenant", tenant_id=9, password_hash=_hash("Test1234"))
        rows.user(db_session, "ok_tenant", tenant_id=10, password_hash=_hash("Test1234"))
        service = AuthService()
        with pytest.raises(BizError) as disabled:
            await service.login("off_tenant", "Test1234")
        assert disabled.value.code == 1008
        assert disabled.value.msg == TENANT_UNAVAILABLE_MSG
        with pytest.raises(BizError) as expired:
            await service.login("old_tenant", "Test1234")
        assert expired.value.code == 1008
        ok = await service.login("ok_tenant", "Test1234")
        assert ok["pwd_reset_required"] is False

    @pytest.mark.asyncio
    async def test_login_log_without_request_context(self, db_session):
        from app.core.errors import BizError
        from app.domains.sys.models import LoginLog
        from app.services.auth import AuthService

        ctx.reset()
        service = AuthService()
        with pytest.raises(BizError) as caught:
            await service.login("ghost_user", "Wrong1234")
        assert caught.value.code == 1214
        row = db_session.query(LoginLog).filter(LoginLog.username == "ghost_user").one()
        assert row.tenant_id == 1
        assert row.ip == ""
        assert row.user_agent == ""

        ctx.set(RequestContext(trace_id="no-tenant", tenant_id=None, user_agent="x" * 600))
        service._write_login_log_sync(username="ctx_only", result="LOGOUT")
        logged = db_session.query(LoginLog).filter(LoginLog.username == "ctx_only").one()
        assert logged.tenant_id == 1
        assert len(logged.user_agent) == 500


class TestPasswordChange:
    """改密规则、落库和当前会话保留。"""

    @pytest.mark.asyncio
    async def test_rules_and_persistence(self, db_session, test_context):
        from app.core.errors import BizError
        from app.services.auth import AuthService, _as_naive

        person = rows.user(
            db_session, "reset_u", password_hash=_hash("Test1234"), pwd_reset_required=True,
        )
        service = AuthService()
        with pytest.raises(BizError) as missing:
            await service.change_own_password(987654321, "Test1234", "Abcd5678!", "sid")
        assert missing.value.code == 1002
        with pytest.raises(BizError) as wrong:
            await service.change_own_password(person.id, "Wrong1234", "Abcd5678!", "sid")
        assert wrong.value.code == 1214
        with pytest.raises(BizError) as weak:
            await service.change_own_password(person.id, "Test1234", "abcdefgh", "sid")
        assert weak.value.code == 1001
        with pytest.raises(BizError) as spaced:
            await service.change_own_password(person.id, "Test1234", "Abcd 5678", "sid")
        assert spaced.value.msg == "密码不能包含空格"
        with pytest.raises(BizError) as same:
            await service.change_own_password(person.id, "Test1234", "Test1234", "sid")
        assert same.value.code == 1001

        await service.change_own_password(person.id, "Test1234", "Abcd5678!", "sid")
        db_session.refresh(person)
        assert person.pwd_reset_required is False
        result = await service.login("reset_u", "Abcd5678!")
        assert result["pwd_reset_required"] is False
        with pytest.raises(BizError) as old:
            await service.login("reset_u", "Test1234")
        assert old.value.code == 1214

        naive = datetime(2026, 10, 12, 8, 0, 0)
        assert _as_naive(naive) == naive
        aware = naive.replace(tzinfo=BEIJING_TZ)
        assert _as_naive(aware).tzinfo is None

    @pytest.mark.asyncio
    async def test_current_session_survives_password_change(self, db_session, test_context):
        from app.core.errors import BizError
        from app.services.auth import AuthService

        person = rows.user(db_session, "keep_u", password_hash=_hash("Test1234"))
        service = AuthService()
        first = await service.login("keep_u", "Test1234")
        other = await service._create_tokens(person, "other-sid")
        await service.change_own_password(person.id, "Test1234", "Abcd5678!", "")
        with pytest.raises(BizError) as dropped:
            await service.verify_token(first["access_token"])
        assert dropped.value.code == 1002
        with pytest.raises(BizError):
            await service.verify_token(other["access_token"])

        again = await service.login("keep_u", "Abcd5678!")
        import jwt

        from app.core.config import get_settings

        payload = jwt.decode(
            again["access_token"],
            get_settings().jwt.secret,
            algorithms=[get_settings().jwt.algorithm],
            options={"verify_exp": False, "verify_iat": False},
        )
        await service.change_own_password(person.id, "Abcd5678!", "Efgh9012!", payload["sid"])
        kept = await service.verify_token(again["access_token"])
        assert kept["user_id"] == person.id
        assert kept["pwd_reset_required"] is False

    @pytest.mark.asyncio
    async def test_verify_without_user_row_stays_valid(self, db_session, test_context):
        from app.core.errors import BizError
        from app.services.auth import AuthService

        service = AuthService()

        class Missing:
            id = 424242
            tenant_id = 1

        tokens = await service._create_tokens(Missing(), "missing-user-sid")
        # B5 在线闸门：用户行不存在视为会话失效，不再继续组装权限。
        with pytest.raises(BizError) as missing:
            await service.verify_token(tokens["access_token"])
        assert missing.value.code == 1002


class TestPasswordResetGate:
    """须改密时只放行改密、退出和 /me。"""

    @pytest.mark.asyncio
    async def test_gate_blocks_other_paths(self, test_context):
        from app.api.deps import enforce_password_reset
        from app.core.errors import BizError

        ctx.reset()
        await enforce_password_reset(_request("/admin-api/ims/system/user/page"))

        ctx.set(RequestContext(trace_id="t", user_id=1, tenant_id=1, pwd_reset_required=False))
        await enforce_password_reset(_request("/admin-api/ims/system/user/page"))

        ctx.set(RequestContext(trace_id="t", user_id=1, tenant_id=1, pwd_reset_required=True))
        await enforce_password_reset(_request("/admin-api/ims/auth/me/"))
        await enforce_password_reset(_request("/admin-api/ims/auth/logout"))
        await enforce_password_reset(_request("/admin-api/ims/auth/password/change"))
        with pytest.raises(BizError) as blocked:
            await enforce_password_reset(_request("/admin-api/ims/system/dict-type/list"))
        assert blocked.value.code == 1008
        with pytest.raises(BizError) as root:
            await enforce_password_reset(_request("/"))
        assert root.value.code == 1008

    @pytest.mark.asyncio
    async def test_change_endpoint_requires_user_and_keeps_session(self, db_session, test_context):
        from app.api.auth import ChangePasswordRequest, change_password
        from app.api.deps import get_current_user_optional
        from app.core.errors import BizError
        from app.services.auth import AuthService

        body = ChangePasswordRequest(old_password="Test1234", new_password="Abcd5678!")
        ctx.reset()
        with pytest.raises(BizError) as missing_ctx:
            await change_password(body)
        assert missing_ctx.value.code == 1002

        ctx.set(RequestContext(trace_id="zero", user_id=0, tenant_id=1))
        with pytest.raises(BizError) as zero:
            await change_password(body)
        assert zero.value.code == 1002

        person = rows.user(db_session, "http_pw", password_hash=_hash("Test1234"), pwd_reset_required=True)
        logged = await AuthService().login("http_pw", "Test1234")
        ctx.reset()
        user_id = await get_current_user_optional(token=logged["access_token"])
        assert user_id == person.id
        assert ctx.current.client_ip == ""
        assert ctx.current.pwd_reset_required is True
        assert ctx.current.session_id

        ctx.current.user_agent = "pytest-agent"
        again = await get_current_user_optional(token=logged["access_token"])
        assert again == person.id
        assert ctx.current.user_agent == "pytest-agent"

        await change_password(body)
        db_session.refresh(person)
        assert person.pwd_reset_required is False
        kept = await AuthService().verify_token(logged["access_token"])
        assert kept["user_id"] == person.id


class TestMenuTree:
    """登录落地用的菜单树仍是目录套菜单，按钮只进权限码。"""

    @pytest.mark.asyncio
    async def test_tree_sorted_and_buttons_excluded(self, db_session, test_context):
        from app.domains.sys.models import Menu
        from app.services.auth import AuthService

        person = rows.user(db_session, "menu_u")
        role = rows.role(db_session, "menu_only", "菜单", data_scope="ALL")
        parent = Menu(
            tenant_id=1, parent_id=0, type="DIR", name="系统管理", path="/system",
            sort=2, status="ENABLED", visible=True,
        )
        later = Menu(
            tenant_id=1, parent_id=0, type="DIR", name="靠后", path="/later",
            sort=9, status="ENABLED", visible=True,
        )
        db_session.add_all([parent, later])
        db_session.flush()
        child = Menu(
            tenant_id=1, parent_id=parent.id, type="MENU", name="部门管理",
            path="/system/dept", perm_code="ims:system:dept:query", sort=1,
            status="ENABLED", visible=True,
        )
        button = Menu(
            tenant_id=1, parent_id=child.id, type="BUTTON", name="新建",
            perm_code="ims:system:dept:create", sort=1, status="ENABLED", visible=True,
        )
        db_session.add_all([child, button])
        db_session.flush()
        for menu in (child, button, parent, later):
            rows.bind_menu(db_session, role.id, menu.id)
        rows.bind_role(db_session, person.id, role.id)

        info = await AuthService().get_current_user_info(person.id)
        names = [item["name"] for item in info["menus"]]
        assert names == ["系统管理", "靠后"]
        assert info["menus"][0]["children"][0]["path"] == "/system/dept"
        assert info["menus"][0]["path"] == "/system"
        assert info["menus"][0]["children"][0]["children"] == []
        assert "ims:system:dept:create" in info["perm_codes"]
        assert info["data_scope_text"] == "全部"

    @pytest.mark.asyncio
    async def test_no_role_menu_prompt(self, db_session, test_context):
        from app.services.auth import AuthService

        person = rows.user(db_session, "none_u")
        info = await AuthService().get_current_user_info(person.id)
        assert info["menus"] == []
        assert info["data_scope_text"] == "您的账号尚未分配权限，请联系管理员"
