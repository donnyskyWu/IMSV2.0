# tests/unit/test_p0_branch_gaps.py
"""补认证、权限判定、用户服务里原先没走到的分支。

断言都检查业务结果或错误码，不用空断言凑覆盖率。
"""

import jwt
import pytest

from app.core.cache import Cache
from app.core.errors import BizError
from app.core.pagination import PageParam
from app.services.access import authorize, grant_menu, load_permission_codes, revoke_menu
from app.services.auth import AuthService
from app.services.user import USER_REF_CHECKS, UserService
from tests.support import rows


def _page() -> PageParam:
    return PageParam(page_no=1, page_size=10)


def _token(payload: dict) -> str:
    from app.core.config import get_settings

    settings = get_settings()
    return jwt.encode(payload, settings.jwt.secret, algorithm=settings.jwt.algorithm)


class TestAuthBranches:
    """AuthService 决策分支。"""

    @pytest.mark.asyncio
    async def test_lock_record_without_deadline_still_checks_password(self, db_session, test_context):
        """有失败计数但没有 lock_until 时，继续验密码，而不是报锁定。"""
        import bcrypt

        service = AuthService()
        password_hash = bcrypt.hashpw(b"Correct123", bcrypt.gensalt()).decode()
        user = rows.user(db_session, "nolock", password_hash=password_hash)
        Cache.set_json(f"{service.LOGIN_FAIL_PREFIX}{user.username}", {"count": 2}, ttl=900)

        with pytest.raises(BizError) as exc_info:
            await service.login(user.username, "Wrong1234")
        assert exc_info.value.code == 1214

    @pytest.mark.asyncio
    async def test_session_cap_ignores_sessions_without_payload(self, db_session, test_context):
        """超出并发上限时，没有创建时间的会话不参与淘汰。"""
        service = AuthService()
        key = f"{service.USER_SESSIONS_PREFIX}41"
        for index in range(service.MAX_SESSIONS):
            Cache.sadd(key, f"bare-{index}")

        await service._add_user_session(41, "fresh")

        assert "fresh" in Cache.smembers(key)
        for index in range(service.MAX_SESSIONS):
            assert f"bare-{index}" in Cache.smembers(key)
            assert Cache.get_json(f"{service.SESSION_PREFIX}bare-{index}") is None

    @pytest.mark.asyncio
    async def test_permission_cache_and_blank_perm_code(self, db_session, test_context):
        """命中权限缓存直接返回；菜单权限码为空时不放进集合。"""
        service = AuthService()
        user = rows.user(db_session, "cached-user")
        cached = {
            "perm_codes": ["ims:system:user:query"],
            "data_scopes": [],
            "dept_ids": [],
            "ip_group_ids": [],
            "_perm_ver": service.get_user_perm_version(user.id),
            "_tenant_id": user.tenant_id,
            "_tenant_perm_ver": service.get_tenant_perm_version(user.tenant_id),
        }
        Cache.set_json(f"{service.PERM_CACHE_PREFIX}{user.id}", cached, ttl=60)
        assert await service._get_user_permissions(user.id) == cached

        Cache.delete(f"{service.PERM_CACHE_PREFIX}{user.id}")
        role = rows.role(db_session, "blank-perm", "空权限码", data_scope="DEPT")
        blank = rows.menu(db_session, "无码", None)
        coded = rows.menu(db_session, "有码", "ims:demo:item:query")
        rows.bind_menu(db_session, role.id, blank.id)
        rows.bind_menu(db_session, role.id, coded.id)
        rows.bind_role(db_session, user.id, role.id)

        loaded = await service._get_user_permissions(user.id)
        assert loaded["perm_codes"] == ["ims:demo:item:query"]
        assert loaded["data_scopes"] == [{"scope_type": "DEPT", "role_id": role.id}]

    @pytest.mark.asyncio
    async def test_logout_branches_and_invalid_token(self, db_session, test_context):
        """登出：无 sid、无过期时间、无用户、非法令牌，都不应抛错。"""
        service = AuthService()
        await service.logout(_token({"type": "access"}))
        await service.logout(_token({"type": "access", "sid": "sid-only"}))
        await service.logout(_token({"type": "access", "sid": "with-user", "sub": "8"}))
        await service.logout("not-a-jwt")
        assert Cache.get(f"{service.SESSION_PREFIX}sid-only") is None

    @pytest.mark.asyncio
    async def test_me_missing_user_and_missing_dept(self, db_session, test_context):
        """用户不存在报 1002；主部门 id 对不上时部门名为空。"""
        service = AuthService()
        with pytest.raises(BizError) as missing:
            await service.get_current_user_info(987654)
        assert missing.value.code == 1002

        user = rows.user(db_session, "no-dept", main_dept_id=424242)
        info = await service.get_current_user_info(user.id)
        assert info["user"]["main_dept_name"] is None
        assert info["menus"] == []

    @pytest.mark.asyncio
    async def test_menu_tree_without_role_menus(self, db_session, test_context):
        """有启用角色但没有菜单时，菜单树为空。"""
        service = AuthService()
        user = rows.user(db_session, "role-only")
        role = rows.role(db_session, "no-menus", "无菜单")
        rows.bind_role(db_session, user.id, role.id)
        assert await service._build_user_menu_tree(user.id, user.tenant_id) == []

    @pytest.mark.asyncio
    async def test_data_scope_text_variants(self, db_session, test_context):
        """数据范围文案覆盖全部、本部门、IP 组、仅本人和未配置。"""
        service = AuthService()
        user = rows.user(db_session, "scope-text")
        dept = rows.dept(db_session, "市场部")

        empty = await service._build_data_scope_text({"data_scopes": []}, user.id)
        assert empty == "您的账号尚未分配权限，请联系管理员"

        everything = await service._build_data_scope_text(
            {"data_scopes": [{"scope_type": "ALL"}]}, user.id,
        )
        assert everything == "全部"

        dept_only = await service._build_data_scope_text(
            {"data_scopes": [{"scope_type": "DEPT"}], "dept_ids": [dept.id]}, user.id,
        )
        assert dept_only == "本部门（市场部）"

        dept_without_ids = await service._build_data_scope_text(
            {"data_scopes": [{"scope_type": "DEPT"}], "dept_ids": []}, user.id,
        )
        assert dept_without_ids == "本部门"

        other = await service._build_data_scope_text(
            {"data_scopes": [{"scope_type": "IP_GROUP"}, {"scope_type": "SELF"}]}, user.id,
        )
        assert other == "所属 IP 组、仅本人"

        unknown = await service._build_data_scope_text(
            {"data_scopes": [{"scope_type": "CUSTOM"}]}, user.id,
        )
        assert unknown == "未配置数据范围"

    @pytest.mark.asyncio
    async def test_change_password_missing_user_and_keep_current_session(self, db_session, test_context):
        """改密：用户不存在报 1002；当前会话保留，其它会话作废。"""
        service = AuthService()
        with pytest.raises(BizError) as missing:
            await service.change_password(987655, "NewPass123", "keep")
        assert missing.value.code == 1002

        user = rows.user(db_session, "changer")
        key = f"{service.USER_SESSIONS_PREFIX}{user.id}"
        Cache.sadd(key, "keep")
        Cache.sadd(key, "drop")
        Cache.set(f"{service.SESSION_PREFIX}drop", "1", ttl=60)

        await service.change_password(user.id, "NewPass123", "keep")

        assert "keep" in Cache.smembers(key)
        assert "drop" not in Cache.smembers(key)
        assert Cache.get(f"{service.SESSION_PREFIX}drop") is None
        assert user.pwd_reset_required is False

    @pytest.mark.asyncio
    async def test_dingtalk_mapping_and_callback_state(self, db_session, test_context, monkeypatch):
        """钉钉映射：找不到人报 1217；已有映射不重复插入。回调 state 缺失报 1002。"""
        from app.domains.sys.models import UserMapping

        service = AuthService()
        import app.services.auth as auth_mod
        monkeypatch.setattr(auth_mod.settings.dingtalk, "app_key", "ding-key")
        monkeypatch.setattr(auth_mod.settings.dingtalk, "mode", "mock")
        mobile = "13800138000"
        with pytest.raises(BizError) as missing_user:
            await service.map_dingtalk_user_by_mobile("dt-missing", mobile)
        assert missing_user.value.code == 1217

        user = rows.user(
            db_session, "ding-user",
            mobile_hash=UserService()._hash_mobile(mobile),
        )
        rows.add(db_session, UserMapping(
            tenant_id=user.tenant_id, user_id=user.id, dingtalk_user_id="dt-1",
        ))
        mapped = await service.map_dingtalk_user_by_mobile("dt-1", mobile)
        assert mapped == user.id
        assert db_session.query(UserMapping).filter(UserMapping.user_id == user.id).count() == 1

        with pytest.raises(BizError) as missing_state:
            await service.handle_dingtalk_callback("auth-code", "missing-state")
        assert missing_state.value.code == 1002

        Cache.set_json(f"{service.SSO_STATE_PREFIX}ok-state", {"redirect": "/home"}, ttl=60)
        with pytest.raises(BizError) as unmatched:
            await service.handle_dingtalk_callback("auth-code", "ok-state")
        assert unmatched.value.code == 1217

        monkeypatch.setattr(Cache, "getdel", staticmethod(lambda _key: {"redirect": "/dict"}))
        with pytest.raises(BizError) as dict_state:
            await service.handle_dingtalk_callback("auth-code", "dict-state")
        assert dict_state.value.code == 1217

    @pytest.mark.asyncio
    async def test_dingtalk_redirect_rejects_external_and_disabled(self, monkeypatch):
        """站外 redirect 被换成 /；未配置钉钉时报 1008；配了 key 才返回带 state 的地址。"""
        import app.services.auth as auth_mod

        service = AuthService()
        monkeypatch.setattr(auth_mod.settings.dingtalk, "app_key", "")
        with pytest.raises(BizError) as disabled:
            await service.get_dingtalk_redirect_url("//evil.example")
        assert disabled.value.code == 1008

        monkeypatch.setattr(auth_mod.settings.dingtalk, "app_key", "ding-key")
        url = await service.get_dingtalk_redirect_url("/ims/home")
        assert url.startswith("https://login.dingtalk.com/oauth2/auth?")
        from urllib.parse import parse_qs, urlparse
        state = parse_qs(urlparse(url).query)["state"][0]
        assert len(state) == 32
        stored = Cache.get_json(f"{service.SSO_STATE_PREFIX}{state}")
        assert stored == {"redirect": "/ims/home"}


class TestAccessBranches:
    """权限判定：没有用户、空权限码、重复授权。"""

    def test_unknown_user_has_no_permissions(self, db_session, test_context):
        assert load_permission_codes(987656) == set()

    def test_blank_perm_and_package_intersection(self, db_session, test_context):
        """套餐取交集；权限码为空的菜单不进入结果。"""
        from app.domains.sys.models import Tenant, TenantPackage, TenantPackageMenu

        user = rows.user(db_session, "pkg-user")
        role = rows.role(db_session, "pkg-role", "套餐角色")
        kept = rows.menu(db_session, "保留", "ims:system:user:query")
        blank = rows.menu(db_session, "空码菜单", None)
        dropped = rows.menu(db_session, "套餐外", "ims:system:role:query")
        rows.bind_menu(db_session, role.id, kept.id)
        rows.bind_menu(db_session, role.id, blank.id)
        rows.bind_menu(db_session, role.id, dropped.id)
        rows.bind_role(db_session, user.id, role.id)

        package = rows.add(db_session, TenantPackage(tenant_id=1, name="基础套餐", status="ENABLED"))
        rows.add(db_session, TenantPackageMenu(
            tenant_id=1, package_id=package.id, menu_id=kept.id,
        ))
        rows.add(db_session, TenantPackageMenu(
            tenant_id=1, package_id=package.id, menu_id=blank.id,
        ))
        rows.add(db_session, Tenant(
            tenant_id=1, name="平台", status="ENABLED", package_id=package.id,
        ))

        assert load_permission_codes(user.id) == {"ims:system:user:query"}

    def test_grant_is_idempotent_and_revoke_drops_cache(self, db_session, test_context):
        role = rows.role(db_session, "grant-role", "授权")
        menu = rows.menu(db_session, "授权菜单", "ims:system:dept:query")
        user = rows.user(db_session, "grant-user")
        rows.bind_role(db_session, user.id, role.id)
        Cache.set_json(f"{AuthService.PERM_CACHE_PREFIX}{user.id}", {"perm_codes": ["old"]}, ttl=60)

        grant_menu(role.id, menu.id)
        grant_menu(role.id, menu.id)
        from app.domains.sys.models import RoleMenu
        assert db_session.query(RoleMenu).filter(RoleMenu.role_id == role.id).count() == 1
        assert Cache.get_json(f"{AuthService.PERM_CACHE_PREFIX}{user.id}") is None

        revoke_menu(role.id, menu.id)
        assert db_session.query(RoleMenu).filter(RoleMenu.role_id == role.id).count() == 0

    def test_authorize_rejects_missing_context_and_missing_code(self):
        from app.core.context import ctx

        ctx.reset()
        with pytest.raises(BizError) as missing:
            authorize("ims:system:user:query")
        assert missing.value.code == 1008


class TestUserBranches:
    """UserService 列表过滤、部门调整和删除保护。"""

    @pytest.mark.asyncio
    async def test_user_page_filters(self, db_session, test_context):
        service = UserService()
        parent = rows.dept(db_session, "父部门")
        child = rows.dept(db_session, "子部门", parent=parent)
        inside = rows.user(db_session, "inside", nickname="张三", status="ACTIVE", main_dept_id=child.id)
        outside = rows.user(db_session, "outside", nickname="李四", status="FROZEN")
        rows.link(db_session, inside.id, child.id, is_main=True)
        rows.link(db_session, outside.id, parent.id, is_main=True)

        missing_dept = await service.get_user_page(_page(), dept_id="999999", include_children=True)
        assert missing_dept.total == 2

        direct = await service.get_user_page(
            _page(), dept_id=str(parent.id), include_children=False,
        )
        assert [item["username"] for item in direct.list] == ["outside"]

        named = await service.get_user_page(_page(), keyword="张三", status="ACTIVE")
        assert [item["username"] for item in named.list] == ["inside"]
        assert named.list[0]["main_dept_name"] == "子部门"

        test_context.data_scopes = [{"scope_type": "ALL", "role_id": 1}]
        assert (await service.get_user_page(_page())).total == 2

        test_context.data_scopes = [{"scope_type": "DEPT", "role_id": 1}]
        test_context.dept_ids = [child.id]
        dept_scoped = await service.get_user_page(_page())
        assert [item["username"] for item in dept_scoped.list] == ["inside"]

        class _Scope:
            def __init__(self, scope_type: str) -> None:
                self.scope_type = scope_type

        test_context.data_scopes = [_Scope("SELF")]
        assert (await service.get_user_page(_page())).total == 0

    @pytest.mark.asyncio
    async def test_simple_page_without_dept_name(self, db_session, test_context):
        service = UserService()
        rows.user(db_session, "plain", nickname="无部门")
        page = await service.get_user_simple_page(_page(), keyword="无部门")
        assert page.total == 1
        assert page.list[0]["main_dept_name"] is None

    @pytest.mark.asyncio
    async def test_update_depts_edges(self, db_session, test_context):
        service = UserService()
        user = rows.user(db_session, "mover")
        enabled = rows.dept(db_session, "启用部门")
        disabled = rows.dept(db_session, "停用部门", status="DISABLED")

        with pytest.raises(BizError) as no_system:
            await service.update_user_depts(str(user.id), [], "")
        assert no_system.value.code == 1001

        system = rows.dept(db_session, "待分配", source="SYSTEM")
        await service.update_user_depts(str(user.id), [], "")
        assert user.main_dept_id == system.id

        with pytest.raises(BizError) as no_main:
            await service.update_user_depts(str(user.id), [str(enabled.id)], "")
        assert no_main.value.code == 1001

        with pytest.raises(BizError) as gone:
            await service.update_user_depts(str(user.id), ["999998"], "999998")
        assert gone.value.code == 1500

        with pytest.raises(BizError) as stopped:
            await service.update_user_depts(str(user.id), [str(disabled.id)], str(disabled.id))
        assert stopped.value.code == 1501

        with pytest.raises(BizError) as missing_user:
            await service.update_user_depts("999997", [str(enabled.id)], str(enabled.id))
        assert missing_user.value.code == 1504

    @pytest.mark.asyncio
    async def test_delete_freeze_resign_position_and_binding(self, db_session, test_context):
        from datetime import datetime

        from app.domains.sys.models import DictData, UserMapping

        service = UserService()
        with pytest.raises(BizError) as missing:
            await service.delete_user("999996")
        assert missing.value.code == 1504

        resigned = rows.user(db_session, "gone", status="RESIGNED")
        with pytest.raises(BizError) as cannot_delete:
            await service.delete_user(str(resigned.id))
        assert cannot_delete.value.code == 1502
        with pytest.raises(BizError) as cannot_reactivate:
            await service.reactivate_user(str(resigned.id))
        assert cannot_reactivate.value.code == 1502
        with pytest.raises(BizError) as already:
            await service.resign_user(str(resigned.id))
        assert already.value.code == 1502

        logged = rows.user(db_session, "logged", last_login_time=datetime(2020, 1, 1))
        with pytest.raises(BizError) as has_login:
            await service.delete_user(str(logged.id))
        assert has_login.value.code == 1001

        fresh = rows.user(db_session, "fresh")

        def _zero(_session, _user_id):
            return 0

        def _used(_session, _user_id):
            return 2

        USER_REF_CHECKS.append(_zero)
        try:
            referenced = rows.user(db_session, "referenced")
            USER_REF_CHECKS.append(_used)
            with pytest.raises(BizError) as blocked:
                await service.delete_user(str(referenced.id))
            assert blocked.value.code == 1502
            USER_REF_CHECKS.remove(_used)

            await service.delete_user(str(fresh.id))
            assert fresh.deleted == fresh.id
        finally:
            if _zero in USER_REF_CHECKS:
                USER_REF_CHECKS.remove(_zero)
            if _used in USER_REF_CHECKS:
                USER_REF_CHECKS.remove(_used)

        active = rows.user(db_session, "active-one", token_version=0)
        await service.freeze_user(str(active.id))
        assert active.status == "FROZEN"
        assert active.token_version == 0
        await service.reactivate_user(str(active.id))
        assert active.status == "ACTIVE"
        await service.resign_user(str(active.id))
        assert active.status == "RESIGNED"

        positioned = rows.user(db_session, "positioned")
        with pytest.raises(BizError) as bad_position:
            await service.set_position(str(positioned.id), "MISSING")
        assert bad_position.value.code == 1503
        rows.add(db_session, DictData(
            tenant_id=1, dict_type="dict_position", dict_value="EDITOR",
            dict_label="编辑", status="DISABLED",
        ))
        with pytest.raises(BizError) as disabled_position:
            await service.set_position(str(positioned.id), "EDITOR")
        assert disabled_position.value.code == 1503
        rows.add(db_session, DictData(
            tenant_id=1, dict_type="dict_position", dict_value="HOST",
            dict_label="主播", status="ENABLED",
        ))
        await service.set_position(str(positioned.id), "HOST")
        assert positioned.position_code == "HOST"

        bound = rows.user(db_session, "bound")
        await service.bind_dingtalk(str(bound.id), "dt-bound")
        await service.bind_dingtalk(str(bound.id), "dt-bound")
        assert db_session.query(UserMapping).filter(UserMapping.user_id == bound.id).count() == 1
        with pytest.raises(BizError) as rebound:
            await service.bind_dingtalk(str(bound.id), "dt-other")
        assert rebound.value.code == 1001
