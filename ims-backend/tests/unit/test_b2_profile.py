"""个人中心 PC-01～04。"""

import pytest

from app.core.context import RequestContext, ctx
from app.core.errors import BizError
from tests.support import rows


def _hash(raw: str) -> str:
    import bcrypt

    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt(rounds=4)).decode()


class TestProfileMe:
    """UT-B2-PC-01-01 /me 增加脱敏手机号和角色名。"""

    @pytest.mark.asyncio
    async def test_me_masks_mobile_and_lists_roles(self, db_session, test_context):
        from app.domains.sys.models import UserRole
        from app.services.auth import AuthService, mask_mobile_for_me

        assert mask_mobile_for_me(None) is None
        assert mask_mobile_for_me("abc") is None
        assert mask_mobile_for_me("13800138000") == "138****8000"

        person = rows.user(
            db_session, "me_u", nickname="甲", password_hash=_hash("Test1234"),
            mobile_enc="13800138000",
        )
        role = rows.role(db_session, "pc_r", "运营")
        rows.add(db_session, UserRole(tenant_id=1, user_id=person.id, role_id=role.id, source="MANUAL"))
        info = await AuthService().get_current_user_info(person.id)
        assert info["user"]["mobile_masked"] == "138****8000"
        assert info["user"]["role_names"] == ["运营"]
        assert info["user"]["has_password"] is True

        blank = rows.user(db_session, "me_blank", password_hash="")
        blank_info = await AuthService().get_current_user_info(blank.id)
        assert blank_info["user"]["mobile_masked"] is None
        assert blank_info["user"]["role_names"] == []
        assert blank_info["user"]["has_password"] is False


class TestSetPassword:
    """UT-B2-PC-03-01～04 设置密码。"""

    @pytest.mark.asyncio
    async def test_set_password_keeps_current_and_drops_others(self, db_session, test_context):
        from app.api.auth import SetPasswordRequest, set_password
        from app.api.deps import get_current_user_optional
        from app.services.auth import AuthService

        person = rows.user(db_session, "set_u", password_hash="")
        service = AuthService()
        ctx.set(RequestContext(trace_id="t", user_id=person.id, tenant_id=1, user_agent="Chrome/120 Linux"))
        current = await service._create_tokens(person, "keep-sid")
        other = await service._create_tokens(person, "other-sid")

        ctx.reset()
        user_id = await get_current_user_optional(token=current["access_token"])
        assert user_id == person.id
        await set_password(SetPasswordRequest(new_password="Abcd5678!"))
        db_session.refresh(person)
        assert person.pwd_reset_required is False
        assert person.password_hash
        kept = await service.verify_token(current["access_token"])
        assert kept["user_id"] == person.id
        with pytest.raises(BizError) as dropped:
            await service.verify_token(other["access_token"])
        assert dropped.value.code == 1002

        again = await service.login("set_u", "Abcd5678!")
        assert again["access_token"]

        ctx.reset()
        await get_current_user_optional(token=again["access_token"])
        with pytest.raises(BizError) as second:
            await set_password(SetPasswordRequest(new_password="Efgh9012!"))
        assert second.value.code == 1001

    @pytest.mark.asyncio
    async def test_set_password_rules_and_missing_user(self, db_session, test_context):
        from app.services.auth import AuthService

        person = rows.user(db_session, "set_rule", password_hash="")
        service = AuthService()
        with pytest.raises(BizError) as short:
            await service.set_own_password(person.id, "abc", "sid")
        assert short.value.code == 1001
        with pytest.raises(BizError) as missing:
            await service.set_own_password(999999, "Abcd5678!", "sid")
        assert missing.value.code == 1002

        ctx.reset()
        with pytest.raises(BizError) as anon:
            from app.api.auth import SetPasswordRequest, set_password
            await set_password(SetPasswordRequest(new_password="Abcd5678!"))
        assert anon.value.code == 1002


class TestChangePasswordIgnoresExtra:
    """UT-B2-PC-02-01 改密请求里的越权字段不落库。"""

    @pytest.mark.asyncio
    async def test_extra_fields_do_not_change_user(self, db_session, test_context):
        from app.api.auth import ChangePasswordRequest, change_password
        from app.api.deps import get_current_user_optional
        from app.domains.sys.models import UserRole
        from app.services.auth import AuthService

        person = rows.user(
            db_session, "chg_u", password_hash=_hash("Test1234"), status="ACTIVE",
        )
        role = rows.role(db_session, "chg_r", "原角色")
        rows.add(db_session, UserRole(tenant_id=1, user_id=person.id, role_id=role.id, source="MANUAL"))
        logged = await AuthService().login("chg_u", "Test1234")
        ctx.reset()
        await get_current_user_optional(token=logged["access_token"])
        body = ChangePasswordRequest.model_validate({
            "oldPassword": "Test1234",
            "newPassword": "Abcd5678!",
            "roleIds": [99],
            "tenantId": 9,
            "status": "FROZEN",
            "deptId": 8,
        })
        await change_password(body)
        db_session.refresh(person)
        assert person.status == "ACTIVE"
        assert person.tenant_id == 1
        links = db_session.query(UserRole).filter(UserRole.user_id == person.id).all()
        assert [item.role_id for item in links] == [role.id]


class TestMySessions:
    """UT-B2-PC-04 会话列表与下线。"""

    @pytest.mark.asyncio
    async def test_list_and_delete(self, db_session, test_context):
        from app.api.auth import delete_my_session, list_my_sessions
        from app.api.deps import get_current_user_optional
        from app.core.cache import Cache
        from app.services.auth import AuthService, device_name

        assert device_name("") == ""
        assert device_name("Mozilla Chrome/120.0 Windows") == "Chrome/Windows"
        assert device_name("Mozilla Safari/1 Macintosh") == "Safari/macOS"
        assert device_name("Mozilla Edg/1") == "Edge/Unknown"
        assert device_name("Mozilla Firefox/1 Android") == "Firefox/Android"
        assert device_name("Mozilla iPhone") == "Browser/iOS"

        person = rows.user(db_session, "sess_u", password_hash=_hash("Test1234"))
        other = rows.user(db_session, "sess_other", password_hash=_hash("Test1234"))
        service = AuthService()
        ctx.set(RequestContext(
            trace_id="t", user_id=person.id, tenant_id=1,
            client_ip="10.1.1.8", user_agent="Mozilla Chrome/120.0 Windows",
        ))
        first = await service._create_tokens(person, "sid-a")
        ctx.set(RequestContext(
            trace_id="t", user_id=person.id, tenant_id=1,
            client_ip="10.1.1.9", user_agent="Mozilla Firefox/1 Linux",
        ))
        second = await service._create_tokens(person, "sid-b")
        foreign = await service._create_tokens(other, "sid-c")

        ctx.reset()
        await get_current_user_optional(token=first["access_token"])
        listed = await list_my_sessions()
        body = listed.data
        assert isinstance(body, dict)
        sids = [item["sid"] for item in body["list"]]
        assert "sid-a" in sids
        assert "sid-c" not in sids
        current = next(item for item in body["list"] if item["sid"] == "sid-a")
        assert current["current"] is True
        assert current["ip"] == "10.1.1.8"
        assert current["device_name"] == "Chrome/Windows"

        with pytest.raises(BizError) as empty:
            await delete_my_session("")
        assert empty.value.code == 1001
        with pytest.raises(BizError) as missing:
            await delete_my_session("missing-sid")
        assert missing.value.code == 1504
        with pytest.raises(BizError) as foreign_sid:
            await delete_my_session("sid-c")
        assert foreign_sid.value.code == 1504
        assert Cache.get_json(f"{service.SESSION_PREFIX}sid-c") is not None

        await delete_my_session("sid-b")
        with pytest.raises(BizError) as gone:
            await service.verify_token(second["access_token"])
        assert gone.value.code == 1002
        still = await service.verify_token(first["access_token"])
        assert still["user_id"] == person.id
        assert Cache.get(f"{service.REFRESH_INDEX_PREFIX}{second['refresh_token']}") is None

        await delete_my_session("sid-a")
        with pytest.raises(BizError) as self_out:
            await service.verify_token(first["access_token"])
        assert self_out.value.code == 1002
        assert foreign["access_token"]
