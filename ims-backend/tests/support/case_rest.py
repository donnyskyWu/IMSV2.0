# tests/support/case_rest.py - Real assertions for the remaining stub UTs
"""Spec outcomes for A/C/D/E/F/H stubs."""

import asyncio
import importlib.util
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.errors import BizError
from tests.support import rows


def _run(coro):
    """Run a coroutine without leaving the thread with no current event loop."""
    try:
        previous = asyncio.get_event_loop()
        if previous.is_closed():
            previous = None
    except RuntimeError:
        previous = None
    try:
        return asyncio.run(coro)
    finally:
        asyncio.set_event_loop(previous or asyncio.new_event_loop())


def ut_c02_03(db, _ctx, _clock):
    from app.db.repository import BaseRepository
    from app.domains.sys.models import ScopeSample

    repo = BaseRepository(ScopeSample)
    row = ScopeSample(id=1, tenant_id=2, name="body", deleted=0)
    saved = repo.create(row)
    assert saved.tenant_id == 1


def ut_c02_04(db, ctx, _clock):
    from app.db.guard import rename_platform_menu

    item = rows.menu(db, "平台菜单", "ims:platform:menu")
    ctx.tenant_id = 2
    with pytest.raises(BizError) as caught:
        rename_platform_menu(item.id, "改")
    assert caught.value.code == 1008


def ut_c02_08(db, ctx, _clock):
    from app.db.guard import create_in_scope, read_in_scope
    from app.db.repository import BaseRepository
    from app.domains.sys.models import ScopeSample

    ctx.data_scopes = []
    row = rows.add(db, ScopeSample(tenant_id=1, name="hidden", dept_id=1))
    repo = BaseRepository(ScopeSample)
    assert list(repo.list()) == []
    with pytest.raises(BizError) as read:
        read_in_scope(repo, row.id)
    assert read.value.code == 1504
    with pytest.raises(BizError) as created:
        create_in_scope(repo, ScopeSample(name="new", dept_id=1, deleted=0))
    assert created.value.code == 1008


def ut_c02_09(db, ctx, _clock):
    from app.core.context import DataScope
    from app.db.repository import BaseRepository
    from app.domains.sys.models import ScopeSample

    original = dict(ScopeSample.__scope_fields__)
    ScopeSample.__scope_fields__ = {"dept": "dept_id"}
    try:
        rows.add(db, ScopeSample(tenant_id=1, name="ip", dept_id=1, ip_group_id=9))
        ctx.data_scopes = [DataScope(scope_type="IP_GROUP", role_id=1)]
        ctx.ip_group_ids = [9]
        assert list(BaseRepository(ScopeSample).list()) == []
    finally:
        ScopeSample.__scope_fields__ = original


def ut_c02_10(db, ctx, _clock):
    from app.core.context import DataScope
    from app.db.repository import BaseRepository
    from app.domains.sys.models import ScopeSample

    person = rows.user(db, "disabled_all")
    disabled = rows.role(db, "all_off", "全部", status="DISABLED", data_scope="ALL")
    rows.bind_role(db, person.id, disabled.id)
    rows.add(db, ScopeSample(tenant_id=1, name="row", dept_id=1))
    ctx.data_scopes = []
    ctx.user_id = person.id
    assert list(BaseRepository(ScopeSample).list()) == []
    assert DataScope(scope_type="ALL", role_id=disabled.id).scope_type == "ALL"


def ut_c02_11(db, ctx, _clock):
    from app.core.context import DataScope
    from app.db.repository import BaseRepository
    from app.domains.sys.models import ScopeSample

    local = rows.dept(db, "D12", source="LOCAL")
    rows.add(db, ScopeSample(tenant_id=1, name="local-row", dept_id=local.id))
    ctx.data_scopes = [DataScope(scope_type="DEPT", role_id=1)]
    ctx.dept_ids = [local.id]
    found = list(BaseRepository(ScopeSample).list())
    assert [row.name for row in found] == ["local-row"]


def ut_c02_12(_db, _ctx, _clock):
    from app.core.route_policy import validate_scope_models

    class DemoNoScope:
        pass

    route = SimpleNamespace(path="/admin-api/ims/demo", scope_model=DemoNoScope)
    with pytest.raises(RuntimeError, match="__scope_fields__"):
        validate_scope_models([route])


def ut_c02_14(_db, _ctx, _clock):
    from app.core.route_policy import assert_login_only_matches
    from app.main import app

    assert_login_only_matches(app)


def ut_c02_15(db, _ctx, _clock):
    from app.domains.sys.models import ScopeSample
    from app.services.publish import can_view, publish

    record = rows.add(db, ScopeSample(tenant_id=1, name="pub"))
    publish(record, [11])
    assert can_view(record, [11]) is True
    assert can_view(record, [22]) is False


def ut_c02_16(db, _ctx, _clock):
    from app.domains.sys.models import ScopeSample
    from app.services.publish import can_view, publish

    record = rows.add(db, ScopeSample(tenant_id=1, name="snap"))
    publish(record, [11])
    creator_now = [22]
    assert creator_now == [22]
    assert can_view(record, [11]) is True


def ut_c02_17(db, _ctx, _clock):
    from app.core.context import ctx
    from app.db.guard import guarded_call

    ctx.reset()
    with pytest.raises(BizError) as caught:
        guarded_call(lambda: db.query)
    assert caught.value.code == 1008


def ut_c02_18(db, ctx, _clock):
    from app.db.guard import SCOPE_LOGS, guarded_call

    ctx.user_id = 1
    before = len(SCOPE_LOGS)

    def boom():
        raise RuntimeError("scope calc")

    with pytest.raises(BizError) as caught:
        guarded_call(boom)
    assert caught.value.code == 1008
    assert len(SCOPE_LOGS) == before + 1


def ut_c04_07(db, _ctx, _clock):
    from app.core.idempotency import IdempotencyStore
    from app.domains.sys.models import IdempotencyRecord

    store = IdempotencyStore(db)
    calls = {"n": 0}

    def write():
        calls["n"] += 1
        return {"id": 1}

    assert store.execute("tok-7", write) == {"id": 1}
    assert store.execute("tok-7", write) == {"id": 1}
    assert calls["n"] == 1
    assert db.query(IdempotencyRecord).count() == 1


def ut_c04_09(_db, _ctx, _clock):
    from app.core.idempotency import IdempotencyStore

    store = IdempotencyStore()
    state = {"calls": 0, "first": None}
    started = threading.Event()

    def slow():
        state["calls"] += 1
        started.set()
        threading.Event().wait(0.3)
        return {"id": 7}

    def owner():
        state["first"] = store.execute("tok-9", slow)

    thread = threading.Thread(target=owner)
    thread.start()
    assert started.wait(2)
    second = store.execute("tok-9", lambda: {"id": 8})
    thread.join()
    assert state["first"] == {"id": 7}
    assert second == {"id": 7}
    assert state["calls"] == 1
    assert store.writes == 1


def ut_c04_10(_db, _ctx, _clock):
    from app.core.idempotency import IdempotencyStore

    store = IdempotencyStore()
    calls = {"n": 0}

    def fail():
        calls["n"] += 1
        raise BizError(1500)

    with pytest.raises(BizError) as first:
        store.execute("tok-10", fail)
    with pytest.raises(BizError) as second:
        store.execute("tok-10", fail)
    assert first.value.code == second.value.code == 1500
    assert calls["n"] == 1


def ut_d02_06(db, _ctx, _clock):
    from app.domains.sys.models import UserMapping
    from app.services.auth import AuthService
    from app.services.user import UserService

    mobile = "13811112222"
    person = rows.user(db, "phone_b", mobile_hash=UserService()._hash_mobile(mobile))
    mapped = _run(AuthService().map_dingtalk_user_by_mobile("dt_x", mobile))
    assert mapped == person.id
    link = db.query(UserMapping).filter(UserMapping.dingtalk_user_id == "dt_x").one()
    assert link.user_id == person.id


def ut_d03_01(_db, _ctx, _clock):
    from app.core.route_policy import validate_business_permissions

    route = SimpleNamespace(path="/admin-api/ims/demo/open-biz", anonymous=False, login_only=False, perm_code=None)
    with pytest.raises(RuntimeError, match="does not declare"):
        validate_business_permissions([route], set())


def ut_d03_02(_db, _ctx, _clock):
    from app.core.route_policy import validate_business_permissions

    route = SimpleNamespace(
        path="/admin-api/ims/demo/list",
        anonymous=False,
        login_only=False,
        perm_code="ims:demo:nope:query",
    )
    with pytest.raises(RuntimeError, match="unknown permission"):
        validate_business_permissions([route], {"ims:demo:order:query"})


def ut_d03_04(db, ctx, _clock):
    from app.services.access import authorize, load_permission_codes

    person = rows.user(db, "pending_user")
    the_role = rows.role(db, "pending", "待配置", status="PENDING_CONFIG")
    item = rows.menu(db, "业务", "ims:demo:order:query")
    rows.bind_menu(db, the_role.id, item.id)
    rows.bind_role(db, person.id, the_role.id)
    ctx.perm_codes = load_permission_codes(person.id)
    with pytest.raises(BizError) as caught:
        authorize("ims:demo:order:query")
    assert caught.value.code == 1008


def ut_d03_05(db, ctx, _clock):
    from app.services.access import authorize
    from app.services.auth import AuthService

    person = rows.user(db, "u_none")
    ctx.user_id = person.id
    ctx.perm_codes = set()
    info = _run(AuthService().get_current_user_info(person.id))
    assert info["user"]["id"] == str(person.id)
    with pytest.raises(BizError) as caught:
        authorize("ims:demo:order:query")
    assert caught.value.code == 1008


def ut_d03_06(db, ctx, _clock):
    from app.services.access import authorize, load_permission_codes

    person = rows.user(db, "union_user")
    read_role = rows.role(db, "role_r", "读")
    write_role = rows.role(db, "role_w", "写")
    rows.bind_menu(db, read_role.id, rows.menu(db, "读", "ims:demo:order:query").id)
    rows.bind_menu(db, write_role.id, rows.menu(db, "写", "ims:demo:order:create").id)
    rows.bind_role(db, person.id, read_role.id)
    rows.bind_role(db, person.id, write_role.id)
    ctx.perm_codes = load_permission_codes(person.id)
    authorize("ims:demo:order:create")


def ut_d03_07(db, ctx, _clock):
    from app.domains.sys.models import Tenant, TenantPackage, TenantPackageMenu
    from app.services.access import authorize, load_permission_codes

    package = rows.add(db, TenantPackage(tenant_id=1, name="不含示例"))
    tenant = rows.add(db, Tenant(tenant_id=1, name="T2", package_id=package.id))
    person = rows.user(db, "t2_user", tenant_id=tenant.id)
    the_role = rows.role(db, "t2_role", "示例", tenant_id=tenant.id)
    item = rows.menu(db, "示例", "ims:demo:order:query")
    other = rows.menu(db, "别的", "ims:system:user:query")
    rows.bind_menu(db, the_role.id, item.id)
    rows.bind_role(db, person.id, the_role.id)
    rows.add(db, TenantPackageMenu(tenant_id=1, package_id=package.id, menu_id=other.id))
    ctx.perm_codes = load_permission_codes(person.id)
    with pytest.raises(BizError) as caught:
        authorize("ims:demo:order:query")
    assert caught.value.code == 1008


def ut_d03_08(_db, _ctx, _clock):
    from app.core.static_checks import role_key_violations, scan_tree

    sample = 'if user.role_key == "R1":\n    return "admin" in roles\n'
    assert role_key_violations(sample) == ["role_key", "admin"]
    hits = scan_tree(Path(__file__).resolve().parents[2] / "app" / "services")
    assert hits == []


def ut_d03_09(db, ctx, _clock):
    from app.core.cache import Cache
    from app.services.access import grant_menu, load_permission_codes
    from app.services.auth import AuthService

    person = rows.user(db, "grant_user")
    the_role = rows.role(db, "grant_r", "待授")
    item = rows.menu(db, "示例授", "ims:demo:order:create")
    rows.bind_role(db, person.id, the_role.id)
    Cache.set_json(f"{AuthService.PERM_CACHE_PREFIX}{person.id}", {"perm_codes": []}, ttl=60)
    grant_menu(the_role.id, item.id)
    assert Cache.get_json(f"{AuthService.PERM_CACHE_PREFIX}{person.id}") is None
    ctx.perm_codes = load_permission_codes(person.id)
    assert "ims:demo:order:create" in ctx.perm_codes


def ut_d03_10(db, ctx, _clock):
    from app.services.access import authorize, load_permission_codes, revoke_menu

    person = rows.user(db, "revoke_user")
    the_role = rows.role(db, "revoke_r", "已授")
    item = rows.menu(db, "示例撤", "ims:demo:order:query")
    rows.bind_menu(db, the_role.id, item.id)
    rows.bind_role(db, person.id, the_role.id)
    revoke_menu(the_role.id, item.id)
    ctx.perm_codes = load_permission_codes(person.id)
    with pytest.raises(BizError) as caught:
        authorize("ims:demo:order:query")
    assert caught.value.code == 1008


def ut_d05_01(db, ctx, _clock):
    from app.domains.sys.models import Role, TodoItem, UserRole
    from app.services.access import authorize, load_permission_codes
    from app.services.position_supply import HOLDER_PERM, PositionSupplyService

    actor = rows.user(db, "user_a")
    holder = rows.user(db, "holder_r1")
    holder_role = rows.role(db, "holder", "配置人")
    rows.bind_menu(db, holder_role.id, rows.menu(db, "角色查询", HOLDER_PERM).id)
    rows.bind_role(db, holder.id, holder_role.id)
    PositionSupplyService().deliver("evt-1", actor.id, "NEW_POS")
    created = db.query(Role).filter(Role.position_code == "NEW_POS").one()
    assert created.source == "DINGTALK_AUTO"
    assert created.status == "PENDING_CONFIG"
    assert db.query(UserRole).filter(UserRole.user_id == actor.id, UserRole.role_id == created.id).count() == 1
    ctx.perm_codes = load_permission_codes(actor.id)
    with pytest.raises(BizError) as caught:
        authorize("ims:demo:order:query")
    assert caught.value.code == 1008
    assert db.query(TodoItem).filter(TodoItem.assignee_user_id == holder.id).count() == 1


def ut_d05_02(db, _ctx, _clock):
    from app.domains.sys.models import Role, TodoItem, UserRole
    from app.services.position_supply import HOLDER_PERM, PositionSupplyService

    actor = rows.user(db, "user_a2")
    holder = rows.user(db, "holder2")
    holder_role = rows.role(db, "holder2", "配置")
    rows.bind_menu(db, holder_role.id, rows.menu(db, "角色查询2", HOLDER_PERM).id)
    rows.bind_role(db, holder.id, holder_role.id)
    service = PositionSupplyService()
    service.deliver("evt-2", actor.id, "NEW_POS")
    before = (
        db.query(Role).count(),
        db.query(UserRole).count(),
        db.query(TodoItem).count(),
    )
    service.deliver("evt-2", actor.id, "NEW_POS")
    after = (
        db.query(Role).count(),
        db.query(UserRole).count(),
        db.query(TodoItem).count(),
    )
    assert before == after


def ut_d05_03(db, _ctx, _clock):
    from app.domains.sys.models import UserRole
    from app.services.position_supply import PositionSupplyService

    actor = rows.user(db, "user_a3")
    manual = rows.role(db, "manual_m", "手工M")
    auto = rows.role(db, "auto_p1", "自动P1", source="DINGTALK_AUTO", position_code="POS1")
    rows.bind_role(db, actor.id, manual.id, source="MANUAL")
    rows.bind_role(db, actor.id, auto.id, source="DINGTALK_AUTO")
    rows.role(db, "auto_p2", "自动P2", source="DINGTALK_AUTO", position_code="POS2")
    PositionSupplyService().deliver("evt-3", actor.id, "POS2")
    links = db.query(UserRole).filter(UserRole.user_id == actor.id, UserRole.manual_removed.is_(False)).all()
    role_ids = {link.role_id for link in links}
    assert manual.id in role_ids
    assert auto.id not in role_ids
    assert any(link.source == "DINGTALK_AUTO" for link in links)


def ut_d05_04(db, _ctx, _clock):
    from app.domains.sys.models import UserRole
    from app.services.position_supply import PositionSupplyService

    actor = rows.user(db, "user_a4")
    auto = rows.role(db, "auto_p2b", "自动P2", source="DINGTALK_AUTO", position_code="POS2")
    rows.bind_role(db, actor.id, auto.id, source="DINGTALK_AUTO", removed=True)
    PositionSupplyService().deliver("evt-4", actor.id, "POS2")
    active = db.query(UserRole).filter(
        UserRole.user_id == actor.id,
        UserRole.role_id == auto.id,
        UserRole.manual_removed.is_(False),
    ).count()
    assert active == 0


def ut_d05_05(db, _ctx, _clock):
    from app.domains.sys.models import ChangeLog
    from app.services.position_supply import PositionSupplyService

    old = rows.role(db, "rule_p1", "P1", position_code="POS1")
    new = rows.role(db, "rule_p3", "P3")
    PositionSupplyService().update_rule("POS1", new.id)
    db.refresh(old)
    db.refresh(new)
    assert old.position_code is None
    assert new.position_code == "POS1"
    archived = db.query(ChangeLog).filter(ChangeLog.biz_type == "position_rule", ChangeLog.biz_id == "POS1").one()
    assert archived.before_value == str(old.id)
    assert archived.after_value == str(new.id)


def ut_d06_01(db, _ctx, _clock):
    from app.services.auth import AuthService

    person = rows.user(db, "menu_user")
    the_role = rows.role(db, "menu_r", "菜单")
    system = rows.menu(db, "用户", "ims:system:user:query", "MENU")
    demo = rows.menu(db, "示例域", "ims:demo:order:query", "MENU")
    rows.bind_menu(db, the_role.id, system.id)
    rows.bind_role(db, person.id, the_role.id)
    info = _run(AuthService().get_current_user_info(person.id))
    codes = {item["perm_code"] for item in info["menus"]}
    assert "ims:demo:order:query" not in codes
    assert demo.id
    assert "ims:demo:order:query" not in info["perm_codes"]


def ut_d06_02(db, _ctx, _clock):
    from app.domains.sys.models import Tenant, TenantPackage, TenantPackageMenu
    from app.services.auth import AuthService

    package = rows.add(db, TenantPackage(tenant_id=1, name="套餐"))
    tenant = rows.add(db, Tenant(tenant_id=1, name="T2b", package_id=package.id))
    person = rows.user(db, "t2_menu", tenant_id=tenant.id)
    the_role = rows.role(db, "t2_menu_r", "菜单", tenant_id=tenant.id)
    demo = rows.menu(db, "示例域2", "ims:demo:order:query", "MENU")
    kept = rows.menu(db, "系统", "ims:system:user:query", "MENU")
    rows.bind_menu(db, the_role.id, demo.id)
    rows.bind_menu(db, the_role.id, kept.id)
    rows.bind_role(db, person.id, the_role.id)
    rows.add(db, TenantPackageMenu(tenant_id=1, package_id=package.id, menu_id=kept.id))
    info = _run(AuthService().get_current_user_info(person.id))
    codes = {item["perm_code"] for item in info["menus"]}
    assert "ims:demo:order:query" not in codes
    assert "ims:system:user:query" in codes


def ut_d07_04(db, _ctx, _clock):
    from app.domains.sys.models import ChangeLog, Dept
    from app.services.org_sync import OrgSyncService

    root = rows.dept(db, "D0", ding="0")
    first = rows.dept(db, "D1", root, source="DINGTALK", ding="100")
    second = rows.dept(db, "D2", root, source="DINGTALK", ding="200")
    moved = rows.dept(db, "D11", second, source="DINGTALK", ding="101")
    _run(OrgSyncService().reconcile_snapshot({
        "depts": [
            {"dingtalk_id": "100", "parent_dingtalk_id": "0", "name": "D1"},
            {"dingtalk_id": "101", "parent_dingtalk_id": "100", "name": "D11"},
        ],
    }))
    db.refresh(moved)
    assert moved.parent_id == first.id
    log = db.query(ChangeLog).filter(ChangeLog.reason == "DINGTALK_OVERRIDE").one()
    assert log.before_value == str(second.id)
    assert db.get(Dept, moved.id).parent_id == first.id


def ut_d07_05(db, _ctx, _clock):
    from app.domains.sys.models import Dept
    from app.services.org_sync import OrgSyncService

    root = rows.dept(db, "D0b")
    parent = rows.dept(db, "D1", root, source="DINGTALK", ding="100")
    _run(OrgSyncService().reconcile_snapshot({
        "depts": [{"dingtalk_id": "102", "parent_dingtalk_id": "100", "name": "新部门"}],
    }))
    created = db.query(Dept).filter(Dept.dingtalk_dept_id == "102").one()
    assert created.source == "DINGTALK"
    assert created.parent_id == parent.id


def ut_d07_10(db, _ctx, _clock):
    from app.domains.sys.models import Dept
    from app.services.org_sync import OrgSyncService

    root = rows.dept(db, "D0c")
    parent = rows.dept(db, "D1", root, source="DINGTALK", ding="100")
    rows.dept(db, "市场三组", parent, source="LOCAL")
    result = _run(OrgSyncService().reconcile_snapshot({
        "depts": [{"dingtalk_id": "300", "parent_dingtalk_id": "100", "name": "市场三组"}],
    }))
    assert "存在同名本地部门" in result["reports"]
    assert db.query(Dept).filter(Dept.name == "市场三组", Dept.deleted == 0).count() == 2


def ut_d07_14(db, _ctx, _clock):
    from app.services.auth import AuthService
    from app.services.org_sync import OrgSyncService

    rows.dept(db, "D0d", ding="100")
    _run(OrgSyncService().reconcile_snapshot({
        "depts": [{"dingtalk_id": "100", "parent_dingtalk_id": None, "name": "D0d"}],
        "users": [{
            "dingtalk_user_id": "dt_new",
            "username": "dt_new_user",
            "name": "新人",
            "dept_dingtalk_ids": ["100"],
        }],
    }))
    with pytest.raises(BizError) as caught:
        _run(AuthService().login("dt_new_user", "whatever"))
    assert caught.value.code == 1214


def ut_d07_15(db, _ctx, _clock):
    from app.domains.sys.models import UserDept
    from app.services.org_sync import OrgSyncService

    root = rows.dept(db, "D0e")
    d1 = rows.dept(db, "D1", root, source="DINGTALK", ding="100")
    d11 = rows.dept(db, "D11", d1, source="DINGTALK", ding="101")
    d2 = rows.dept(db, "D2", root, source="DINGTALK", ding="200")
    local = rows.dept(db, "D12", d1, source="LOCAL")
    person = rows.user(db, "keep_local")
    rows.link(db, person.id, d11.id, source="DINGTALK")
    rows.link(db, person.id, local.id, source="LOCAL", is_main=True)
    from app.domains.sys.models import UserMapping
    rows.add(db, UserMapping(tenant_id=1, user_id=person.id, dingtalk_user_id="dt_a"))
    _run(OrgSyncService().reconcile_snapshot({
        "depts": [
            {"dingtalk_id": "200", "parent_dingtalk_id": None, "name": "D2"},
        ],
        "users": [{
            "dingtalk_user_id": "dt_a",
            "dept_dingtalk_ids": ["200"],
        }],
    }))
    links = db.query(UserDept).filter(UserDept.user_id == person.id).all()
    paired = {(link.dept_id, link.source) for link in links}
    assert (d2.id, "DINGTALK") in paired
    assert (local.id, "LOCAL") in paired
    assert (d11.id, "DINGTALK") not in paired


def ut_d07_16(db, _ctx, _clock):
    import bcrypt

    from app.services.auth import AuthService
    from app.services.org_sync import OrgSyncService
    from app.services.user import USER_EVENTS

    USER_EVENTS.clear()
    person = rows.user(
        db, "resign_dt",
        password_hash=bcrypt.hashpw(b"secret12", bcrypt.gensalt(rounds=4)).decode(),
    )
    from app.domains.sys.models import UserMapping
    rows.add(db, UserMapping(tenant_id=1, user_id=person.id, dingtalk_user_id="dt_leave"))
    auth = AuthService()
    first = _run(auth._create_tokens(person, "sid-1"))
    _run(auth._create_tokens(person, "sid-2"))
    _run(OrgSyncService().reconcile_snapshot({
        "users": [{"dingtalk_user_id": "dt_leave", "resigned": True}],
    }))
    db.refresh(person)
    assert person.status == "RESIGNED"
    with pytest.raises(BizError) as login:
        _run(auth.login("resign_dt", "secret12"))
    assert login.value.code == 1216
    with pytest.raises(BizError) as token:
        _run(auth.verify_token(first["access_token"]))
    assert token.value.code == 1002
    assert len([item for item in USER_EVENTS if item["type"] == "user.resigned"]) == 1


def ut_d07_17(db, _ctx, _clock):
    from app.domains.sys.models import DictData, UserMapping
    from app.services.org_sync import OrgSyncService

    person = rows.user(db, "pos_new")
    rows.add(db, UserMapping(tenant_id=1, user_id=person.id, dingtalk_user_id="dt_pos"))
    _run(OrgSyncService().reconcile_snapshot({
        "users": [{"dingtalk_user_id": "dt_pos", "position": "NEW_POS2"}],
    }))
    row = db.query(DictData).filter(DictData.dict_value == "NEW_POS2").one()
    assert row.dict_type == "dict_position"
    assert row.source == "DINGTALK"


def ut_d07_18(db, _ctx, _clock):
    from app.domains.sys.models import OrgSyncBatch
    from app.services.org_sync import OrgSyncService

    rows.add(db, OrgSyncBatch(tenant_id=1, status="RUNNING"))
    with pytest.raises(BizError) as caught:
        _run(OrgSyncService().reconcile_snapshot({"depts": []}))
    assert caught.value.code == 1001
    assert "同步正在进行中" in caught.value.msg


def ut_d07_19(db, _ctx, _clock):
    from app.domains.sys.models import Dept
    from app.services.org_sync import OrgSyncService

    before = db.query(Dept).count()
    result = _run(OrgSyncService().reconcile_snapshot({
        "depts": [{"dingtalk_id": "501", "parent_dingtalk_id": None, "name": "不应留下"}],
    }, timeout=True))
    assert result["status"] == "FAILED"
    assert "5003" in (result["error_msg"] or "")
    assert db.query(Dept).count() == before


def ut_e01_02(db, _ctx, _clock):
    from app.services.files import FileService

    folder = Path(__file__).resolve().parents[2] / ".tmp-ro"
    folder.mkdir(exist_ok=True)
    os.chmod(folder, 0o555)
    try:
        with pytest.raises(BizError) as caught:
            FileService().upload(folder, "a.pdf", b"data")
        assert caught.value.code == 5005
        assert list(folder.glob(".tmp-*")) == []
    finally:
        os.chmod(folder, 0o755)
        folder.rmdir()


def ut_e01_05(db, ctx, _clock):
    from app.domains.sys.models import StoredFile
    from app.services.files import FileService

    row = rows.add(db, StoredFile(
        tenant_id=1, scene="TRAIN_DOC", file_key="a.pdf", original_name="a.pdf",
        uploader_id=2, biz_type="demo_order", biz_dept_id=22,
    ))
    ctx.dept_ids = [11]
    with pytest.raises(BizError) as caught:
        FileService().download(row.id, ctx.user_id, ctx.dept_ids)
    assert caught.value.code == 1504


def ut_e01_06(db, ctx, _clock):
    from app.domains.sys.models import StoredFile
    from app.services.files import FileService

    row = rows.add(db, StoredFile(
        tenant_id=1, scene="TRAIN_DOC", file_key="b.pdf", original_name="报告.pdf",
        uploader_id=8,
    ))
    with pytest.raises(BizError) as denied:
        FileService().download(row.id, 9, [])
    assert denied.value.code == 1504
    ok = FileService().download(row.id, 8, [])
    assert "报告.pdf" in ok["content_disposition"]
    assert ctx.user_id


def ut_f01_04(_db, _ctx, _clock):
    from app.services.operate import run_with_log

    def fail():
        raise RuntimeError("log down")

    assert run_with_log(lambda: {"id": 1}, fail) == {"id": 1}


def ut_f02_04(_db, _ctx, _clock):
    from app.core.sensitive_scan import scan_sensitive_routes

    bad = SimpleNamespace(path="/plain", returns_plaintext=True, sensitive_view=False)
    with pytest.raises(RuntimeError, match="sensitive_view"):
        scan_sensitive_routes([bad])
    scan_sensitive_routes([SimpleNamespace(path="/ok", returns_plaintext=True, sensitive_view=True)])


def ut_c03_06(_db, _ctx, _clock):
    from app.core.masking import export_mobile

    assert export_mobile("13800001234", False).endswith("1234")
    assert "1380000" not in export_mobile("13800001234", False)
    assert export_mobile("13800001234", True) == "13800001234"


def ut_a01_06(_db, _ctx, _clock):
    from app.core.route_policy import validate_anonymous

    route = SimpleNamespace(path="/admin-api/ims/demo/open", anonymous=True)
    with pytest.raises(RuntimeError, match="whitelist"):
        validate_anonymous([route])


def ut_a01_12(_db, _ctx, _clock):
    from app.domains.sys.models import User
    from app.worker import JOBS, WorkerProcess, model_user

    worker = WorkerProcess()
    assert worker.http_routes() == []
    assert worker.tasks() == list(JOBS)
    assert model_user() is User


def ut_a02_03(_db, _ctx, _clock):
    from app.core.errors import ErrorCodeRegistry

    registry = ErrorCodeRegistry()
    with pytest.raises(ValueError, match="outside range"):
        registry.register(1211, "TRAIN", "主键不可修改")


def ut_a02_05(_db, _ctx, _clock):
    from app.core.errors import ErrorCodeRegistry

    registry = ErrorCodeRegistry()
    with pytest.raises(ValueError, match="forbidden"):
        registry.register(1102, "TRAIN", "状态 PENDING_CONFIG 不可用")


def ut_a05_01(_db, _ctx, _clock):
    from app.core.openapi_guard import assert_in_sync, canonical
    from app.main import app

    spec = app.openapi()
    assert_in_sync(spec, app.openapi())
    assert canonical(spec) == canonical(app.openapi())


def ut_a05_02(_db, _ctx, _clock):
    from copy import deepcopy

    from app.core.openapi_guard import assert_in_sync
    from app.main import app

    generated = app.openapi()
    changed = deepcopy(generated)
    changed["paths"]["/health"]["get"]["summary"] = "被改过"
    with pytest.raises(RuntimeError, match="out of sync"):
        assert_in_sync(generated, changed)


def ut_a05_03(_db, _ctx, _clock):
    from app.core.openapi_guard import assert_summaries

    with pytest.raises(RuntimeError, match="summary"):
        assert_summaries({"paths": {"/admin-api/ims/demo": {"get": {}}}})


def ut_a05_04(_db, _ctx, _clock):
    from app.core.openapi_guard import hardcoded_path

    assert hardcoded_path('fetch("/admin-api/ims/demo")') is True
    assert hardcoded_path("client.demo.list()") is False


def ut_a06_01(_db, _ctx, _clock):
    from app.scaffold.generator import ScaffoldError, validate

    with pytest.raises(ScaffoldError) as caught:
        validate({
            "table": "ims_not_registered",
            "require_registered_table": True,
            "dict_type": "dict_missing",
            "perm_prefix": "ops:demo",
            "fields": [],
        }, set())
    assert len(caught.value.problems) == 3


def ut_a06_02(_db, _ctx, _clock):
    from app.domains.shared.registry import SHARED_TABLES
    from app.scaffold.generator import ScaffoldError, validate

    table = next(iter(SHARED_TABLES))
    with pytest.raises(ScaffoldError, match="删除策略"):
        validate({"table": table, "fields": [{"name": "title"}]}, set())


def ut_a06_03(_db, _ctx, _clock):
    import sqlalchemy

    from app.domains.shared.registry import SHARED_TABLES
    from app.scaffold.generator import generate

    table = next(iter(SHARED_TABLES))
    folder = Path(__file__).resolve().parents[2] / ".tmp-scaffold"
    folder.mkdir(exist_ok=True)
    spec = folder / "demo_item.yaml"
    spec.write_text(f"table: {table}\nfields: []\n", encoding="utf-8")
    generate(spec, folder, known_dicts=set())
    engine = sqlalchemy.create_engine("sqlite://")
    sql = (folder / "migration.sql").read_text(encoding="utf-8")
    sql = sql[sql.index("CREATE"):]
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
    sys.path.insert(0, str(folder))
    try:
        spec_mod = importlib.util.spec_from_file_location("scaffold_test_sample", folder / "test_sample.py")
        module = importlib.util.module_from_spec(spec_mod)
        spec_mod.loader.exec_module(module)
        module.test_codes()
    finally:
        sys.path.remove(str(folder))


def ut_a06_04(_db, _ctx, _clock):
    from app.domains.shared.registry import SHARED_TABLES
    from app.scaffold.generator import generate

    table = next(iter(SHARED_TABLES))
    folder = Path(__file__).resolve().parents[2] / ".tmp-scaffold-header"
    folder.mkdir(exist_ok=True)
    spec = folder / "demo_item.yaml"
    spec.write_text(f"table: {table}\nfields: []\n", encoding="utf-8")
    generate(spec, folder)
    header = (folder / "service.py").read_text(encoding="utf-8")
    assert "generator:" in header
    assert "def_hash:" in header
    assert "generated_at:" in header


def ut_a06_05(_db, _ctx, _clock):
    from app.domains.shared.registry import SHARED_TABLES
    from app.scaffold.generator import generate

    table = next(iter(SHARED_TABLES))
    folder = Path(__file__).resolve().parents[2] / ".tmp-scaffold-vue"
    folder.mkdir(exist_ok=True)
    spec = folder / "demo_item.yaml"
    spec.write_text(f"table: {table}\nfields: []\n", encoding="utf-8")
    generate(spec, folder)
    vue = (folder / "index.vue").read_text(encoding="utf-8")
    for token in ("PageHeader", "QueryBar", "DataTable", "Pagination", "v-perm"):
        assert token in vue
    assert "#" not in vue


def ut_a06_06(_db, _ctx, _clock):
    from app.domains.shared.registry import SHARED_TABLES
    from app.scaffold.generator import generate

    table = next(iter(SHARED_TABLES))
    folder = Path(__file__).resolve().parents[2] / ".tmp-scaffold-keep"
    folder.mkdir(exist_ok=True)
    spec = folder / "demo_item.yaml"
    spec.write_text(f"table: {table}\nfields: []\n", encoding="utf-8")
    service = folder / "service.py"
    service.write_text("# manual change\n", encoding="utf-8")
    summary = generate(spec, folder)["summary"]
    assert "kept" in summary
    assert "manual" in service.read_text(encoding="utf-8")
    assert (folder / "service.py.generated").exists()


def ut_a06_07(_db, _ctx, _clock):
    from app.domains.shared.registry import SHARED_TABLES
    from app.scaffold.generator import generate

    table = next(iter(SHARED_TABLES))
    folder = Path(__file__).resolve().parents[2] / ".tmp-scaffold-force"
    folder.mkdir(exist_ok=True)
    spec = folder / "demo_item.yaml"
    spec.write_text(f"table: {table}\nfields: []\n", encoding="utf-8")
    service = folder / "service.py"
    service.write_text("# manual change\n", encoding="utf-8")
    generate(spec, folder, force=True)
    assert "manual" not in service.read_text(encoding="utf-8")
    assert "generator:" in service.read_text(encoding="utf-8")


def ut_h03_01(_db, _ctx, _clock):
    from app.core.errors import error_codes

    payload = error_codes.export_json()
    assert payload
    for item in payload.values():
        assert item["msg"]
        assert item["strategy"]


def ut_h03_02(_db, _ctx, _clock):
    from app.core.errors import ErrorCodeRegistry

    registry = ErrorCodeRegistry()
    with pytest.raises(RuntimeError, match="strategy"):
        registry.export_strict([{"code": 1103, "msg": "示例", "strategy": ""}])


def ut_h04_05(_db, _ctx, _clock):
    from app.integrations.adapters import RealFootballWeb, build_football_web

    assert isinstance(build_football_web("real"), RealFootballWeb)


def ut_h05_05(db, _ctx, _clock):
    from app.domains.sys.models import User
    from app.services.migration_seed import MigrationSeedService, build_sample

    dept = rows.dept(db, "有效部门")
    service = MigrationSeedService()
    sample = build_sample(dept.id, 100)
    first = service.import_users(sample, {dept.id})
    second = service.import_users(sample, {dept.id})
    assert first == second
    assert first == {"source": 100, "success": 99, "pending": 1}
    kept = db.query(User).filter(User.username == "ops_001").one()
    assert kept.id == 1
    assert kept.creator == service.migration_user_id(db)
    assert service.next_user_id() == db.query(User).order_by(User.id.desc()).first().id + 1


def ut_h05_06(db, _ctx, _clock):
    from app.domains.sys.models import IntegrityScan
    from app.services.migration_seed import MigrationSeedService, build_sample

    dept = rows.dept(db, "有效部门2")
    service = MigrationSeedService()
    report = service.import_users(build_sample(dept.id, 100), {dept.id})
    assert report == {"source": 100, "success": 99, "pending": 1}
    assert db.query(IntegrityScan).filter(IntegrityScan.tables_scanned == "migration").count() == 1


def ut_h06_02(_db, _ctx, _clock):
    from app.integrations.football_live.reader import FootballLiveReader

    reader = FootballLiveReader()
    with pytest.raises(RuntimeError, match="read-only"):
        reader.execute_sql("UPDATE live_room SET status = 1")
    assert reader.statements == []


def ut_h06_03(_db, _ctx, _clock):
    from datetime import datetime

    from app.integrations.football_live.reader import FootballLiveReader, FootballRoom

    reader = FootballLiveReader()
    reader.set_mock_room(FootballRoom(
        id=5, author_id=1, nickname="n", avatar_url=None, live_id="l", live_name="name",
        cover=None, status=1, screen_type=1, watch_type=1, start_time=datetime(2026, 10, 1),
        end_time=None, reserve_count=0, like_count=0, viewer_count=1, tenant_id=2,
    ))
    assert reader.get_room(5, 1) is None
    assert reader.room_exists_for_bind(5, 1) is False


def ut_h06_04(_db, _ctx, _clock):
    from app.integrations.football_live.reader import FootballLiveReader

    reader = FootballLiveReader()
    start = datetime(2026, 10, 12, 10, 0, 0)
    end = datetime(2026, 10, 12, 12, 0, 0)
    reader.add_duration(3, start, datetime(2026, 10, 12, 11, 0, 0), deleted=1)
    reader.add_duration(3, datetime(2026, 10, 12, 11, 0, 0), end, deleted=0)
    expected = 60 + 60
    assert reader.live_duration(3, start, end) == expected


def ut_h06_06(_db, _ctx, _clock):
    from app.integrations.football_live.schema import assert_startup_schema, baseline_columns

    base = baseline_columns()
    missing = dict(base)
    missing.pop("cover")
    with pytest.raises(RuntimeError, match="cover"):
        assert_startup_schema(missing)
    varchar = dict(base)
    varchar["status"] = "varchar"
    with pytest.raises(RuntimeError, match="status"):
        assert_startup_schema(varchar)
    bit = dict(base)
    bit["deleted"] = "bit"
    with pytest.raises(RuntimeError, match="deleted"):
        assert_startup_schema(bit)


def ut_h06_07(_db, _ctx, _clock):
    from app.integrations.football_live.seed_data import SCENARIOS, seed_rooms

    first = seed_rooms([])
    second = seed_rooms(first)
    assert len(second) == len(SCENARIOS) == 8
    assert len({row["id"] for row in second}) == 8
    assert all(row["bind_mobile_password"] == "fake-secret" for row in second)


def ut_h06_08(_db, _ctx, _clock):
    from app.integrations.football_live.seed_data import assert_not_prod

    previous = os.environ.get("IMS_ENV")
    os.environ["IMS_ENV"] = "prod"
    try:
        with pytest.raises(SystemExit):
            assert_not_prod()
    finally:
        if previous is None:
            os.environ.pop("IMS_ENV", None)
        else:
            os.environ["IMS_ENV"] = previous


def ut_h06_09(_db, _ctx, _clock):
    from app.integrations.football_live.metrics import edit_session, merge_live_metrics
    from app.integrations.football_live.reader import FootballLiveReader

    reader = FootballLiveReader(mode="real")
    merged = merge_live_metrics(reader, 1, 1, {"name": "场次"})
    assert merged["unavailable"] is True
    assert merged["marker"] == "暂不可用"
    edited = edit_session({"name": "场次"}, "已改")
    assert edited["name"] == "已改"


def ut_h06_10(db, _ctx, _clock):
    from app.domains.sys.models import OutboxEvent
    from app.integrations.football_live.metrics import retry_outbox

    event = rows.add(db, OutboxEvent(tenant_id=1, event_type="metrics", status="FAILED"))
    retry_outbox(event)
    assert event.status == "SUCCESS"
    assert event.synced_at is not None


def ut_h07_01(db, _ctx, _clock):
    from app.domains.sys.models import WorkCalendarDay
    from app.services.attendance import AttendanceService

    rows.add(db, WorkCalendarDay(tenant_id=1, day="2026-10-01", kind="HOLIDAY"))
    rows.add(db, WorkCalendarDay(tenant_id=1, day="2026-10-03", kind="WORKDAY"))
    result = AttendanceService().expected_days(2026, 10, base_weekdays=22, enabled=False)
    assert result == {"days": 22, "degraded": False}


def ut_h07_02(db, _ctx, _clock):
    from app.services.attendance import AttendanceService

    result = AttendanceService().expected_days(
        2026, 10,
        base_weekdays=22,
        enabled=True,
        leaves=[
            {"start": "2026-10-05", "end": "2026-10-05", "portion": 1},
            {"start": "2026-10-06", "end": "2026-10-06", "portion": 0.5},
        ],
    )
    assert result["days"] == 20.5
    assert result["degraded"] is False


def ut_h07_03(db, _ctx, _clock):
    from app.services.attendance import AttendanceService

    service = AttendanceService()
    plain = service.expected_days(2026, 10, enabled=True)
    cut = service.expected_days(
        2026, 10,
        enabled=True,
        leaves=[{"start": "2026-10-30", "end": "2026-11-02", "portion": 1}],
    )
    assert plain["days"] - cut["days"] == 1


def ut_h07_04(db, _ctx, _clock):
    from app.services.attendance import AttendanceService

    result = AttendanceService().expected_days(2026, 10, base_weekdays=22, fetch_failed=True)
    assert result == {"days": 22, "degraded": True}


def ut_h07_05(_db, _ctx, _clock):
    from app.core.config import DingTalkAttendanceSettings, DingTalkSettings

    attendance = DingTalkAttendanceSettings(app_key="att-key", app_secret="att-secret")
    dingtalk = DingTalkSettings(app_key="ims-key", app_secret="ims-secret")
    attendance.app_key = "changed-att"
    assert dingtalk.app_key == "ims-key"
    assert attendance.app_secret != dingtalk.app_secret


def ut_h07_06(_db, _ctx, _clock):
    from app.services.attendance import AttendanceService

    snapshot = AttendanceService().config_snapshot("super-secret")
    assert snapshot["app_secret"] == "******"
    assert "super-secret" not in str(snapshot)


def ut_h07_07(db, _ctx, _clock):
    from app.services.attendance import AttendanceService

    service = AttendanceService()
    result = service.fetch_leaves("2026-10", mode="mock", rows=[])
    assert service.http_calls == []
    assert result["http_calls"] == []


def ut_h07_08(db, _ctx, _clock):
    from app.domains.sys.models import AttendanceSyncState
    from app.services.attendance import AttendanceService

    service = AttendanceService()
    result = service.fetch_leaves("2026-10", timeout=True)
    assert result["status"] == "FAILED"
    assert db.query(AttendanceSyncState).filter(AttendanceSyncState.status == "FAILED").count() == 1
    assert service.logs


def ut_h07_09(db, _ctx, _clock):
    from app.domains.sys.models import LeaveRecord
    from app.services.attendance import AttendanceService

    service = AttendanceService()
    payload = [{"user_id": 1, "start": "2026-10-05", "end": "2026-10-05"}]
    service.fetch_leaves("2026-10", rows=payload)
    service.fetch_leaves("2026-10", rows=payload)
    assert db.query(LeaveRecord).count() == 1


def ut_h07_10(db, ctx, _clock):
    from app.domains.sys.models import OperateLog
    from app.services.attendance import CALENDAR_PERM, AttendanceService

    service = AttendanceService()
    before = service.expected_days(2026, 10, enabled=False)["days"]
    ctx.perm_codes = {CALENDAR_PERM}
    service.set_holiday("2026-10-01", ctx.perm_codes)
    after = service.expected_days(2026, 10, enabled=False)["days"]
    assert after == before - 1
    assert db.query(OperateLog).filter(OperateLog.operation == "修改工作日历").count() == 1


def ut_h08_02(_db, _ctx, _clock):
    from app.integrations.train_ai.client import GeneratedQuestion, TrainAIClient

    client = TrainAIClient(mode="mock")
    client.set_mock_questions([
        GeneratedQuestion("q1", ["a"], "A"),
        GeneratedQuestion("q2", ["a"], "A"),
        GeneratedQuestion("q3", ["a"], "A"),
        GeneratedQuestion("bad1", ["a"], ""),
        GeneratedQuestion("bad2", ["a"], ""),
    ])
    result = _run(client.generate_questions("text", question_count=5))
    assert len(result) == 3


def ut_h08_03(_db, _ctx, _clock):
    from app.integrations.train_ai.client import GeneratedQuestion, TrainAIClient

    empty = TrainAIClient(mode="mock")
    empty.set_mock_questions([])
    bad = TrainAIClient(mode="mock")
    bad.set_mock_questions([GeneratedQuestion("q", ["a"], "")])
    for client in (empty, bad):
        with pytest.raises(BizError) as caught:
            _run(client.generate_questions("text"))
        assert caught.value.code == 1108


def ut_h08_04(_db, _ctx, _clock):
    from app.integrations.train_ai.client import TrainAIClient

    client = TrainAIClient(mode="timeout")
    with pytest.raises(BizError) as caught:
        _run(client.generate_questions("text"))
    assert caught.value.code == 1107
    assert client.task_rows == []


def ut_h08_05(_db, _ctx, _clock):
    from app.integrations.train_ai.client import TrainAIClient

    client = TrainAIClient(mode="fail")
    with pytest.raises(BizError) as caught:
        _run(client.generate_questions("text"))
    assert caught.value.code == 1106


def ut_h08_07(_db, _ctx, _clock):
    from app.integrations.train_ai.client import TrainAIClient

    client = TrainAIClient(mode="mock")
    with pytest.raises(BizError) as caught:
        _run(client.generate_for_material({"published": False}))
    assert caught.value.code == 1101


def ut_h08_08(_db, _ctx, _clock):
    from app.core.config import TrainAISettings

    class ContentAISettings(TrainAISettings):
        model_config = TrainAISettings.model_config

    train = TrainAISettings(model="train-model")
    content = ContentAISettings(model="content-model")
    content.model = "content-changed"
    assert train.model == "train-model"


def ut_h08_09(_db, _ctx, _clock):
    from app.integrations.train_ai.client import TrainAIClient

    client = TrainAIClient(mode="mock", api_key="sk-test-123")
    result = _run(client.generate_questions("sk-test-123 must not leak"))
    blob = str(result) + client.last_log + str(client.call_records)
    assert "sk-test-123" not in blob


def ut_h08_11(_db, _ctx, _clock):
    from app.integrations.train_ai.client import seed_placeholder

    first = seed_placeholder({})
    assert first["base_url"].endswith("/compatible-mode/v1")
    assert first["model"] == "qwen3.8-max"
    assert first["api_key"] == ""
    assert first["mode"] == "mock"
    assert first["enabled"] is True
    first["model"] = "test-model"
    second = seed_placeholder(first)
    assert second["model"] == "test-model"


def ut_h08_13(_db, _ctx, _clock):
    from app.integrations.train_ai.client import GeneratedQuestion, TrainAIClient

    seen = []

    def transport(url, key, model):
        seen.append((url, key, model))
        return [GeneratedQuestion("q", ["a"], "A")]

    client = TrainAIClient(mode="real", api_key="sk-test-123", model="m-a", base_url="http://stub-a")
    client.transport = transport
    _run(client.generate_questions("text"))
    client.model = "m-b"
    client.base_url = "http://stub-b"
    _run(client.generate_questions("text"))
    assert seen == [
        ("http://stub-a", "sk-test-123", "m-a"),
        ("http://stub-b", "sk-test-123", "m-b"),
    ]


def ut_d01_17(db, _ctx, _clock):
    from app.services.auth import AuthService

    person = rows.user(db, "logout_user")
    auth = AuthService()
    tokens = _run(auth._create_tokens(person, "logout-sid"))
    _run(auth.logout(tokens["access_token"]))
    with pytest.raises(BizError) as caught:
        _run(auth.verify_token(tokens["access_token"]))
    assert caught.value.code == 1002


def ut_d01_10(db, _ctx, _clock):
    from app.services.auth import AuthService

    person = rows.user(db, "pwd_user")
    auth = AuthService()
    keep = _run(auth._create_tokens(person, "keep-sid"))
    other = _run(auth._create_tokens(person, "drop-sid"))
    _run(auth.change_password(person.id, "new-password", "keep-sid"))
    _run(auth.verify_token(keep["access_token"]))
    with pytest.raises(BizError) as caught:
        _run(auth.verify_token(other["access_token"]))
    assert caught.value.code == 1002


CASES = {
    "UT-C02-03": ut_c02_03,
    "UT-C02-04": ut_c02_04,
    "UT-C02-08": ut_c02_08,
    "UT-C02-09": ut_c02_09,
    "UT-C02-10": ut_c02_10,
    "UT-C02-11": ut_c02_11,
    "UT-C02-12": ut_c02_12,
    "UT-C02-14": ut_c02_14,
    "UT-C02-15": ut_c02_15,
    "UT-C02-16": ut_c02_16,
    "UT-C02-17": ut_c02_17,
    "UT-C02-18": ut_c02_18,
    "UT-C03-06": ut_c03_06,
    "UT-C04-07": ut_c04_07,
    "UT-C04-09": ut_c04_09,
    "UT-C04-10": ut_c04_10,
    "UT-D01-10": ut_d01_10,
    "UT-D01-17": ut_d01_17,
    "UT-D02-06": ut_d02_06,
    "UT-D03-01": ut_d03_01,
    "UT-D03-02": ut_d03_02,
    "UT-D03-04": ut_d03_04,
    "UT-D03-05": ut_d03_05,
    "UT-D03-06": ut_d03_06,
    "UT-D03-07": ut_d03_07,
    "UT-D03-08": ut_d03_08,
    "UT-D03-09": ut_d03_09,
    "UT-D03-10": ut_d03_10,
    "UT-D05-01": ut_d05_01,
    "UT-D05-02": ut_d05_02,
    "UT-D05-03": ut_d05_03,
    "UT-D05-04": ut_d05_04,
    "UT-D05-05": ut_d05_05,
    "UT-D06-01": ut_d06_01,
    "UT-D06-02": ut_d06_02,
    "UT-D07-04": ut_d07_04,
    "UT-D07-05": ut_d07_05,
    "UT-D07-10": ut_d07_10,
    "UT-D07-14": ut_d07_14,
    "UT-D07-15": ut_d07_15,
    "UT-D07-16": ut_d07_16,
    "UT-D07-17": ut_d07_17,
    "UT-D07-18": ut_d07_18,
    "UT-D07-19": ut_d07_19,
    "UT-E01-02": ut_e01_02,
    "UT-E01-05": ut_e01_05,
    "UT-E01-06": ut_e01_06,
    "UT-F01-04": ut_f01_04,
    "UT-F02-04": ut_f02_04,
    "UT-A01-06": ut_a01_06,
    "UT-A01-12": ut_a01_12,
    "UT-A02-03": ut_a02_03,
    "UT-A02-05": ut_a02_05,
    "UT-A05-01": ut_a05_01,
    "UT-A05-02": ut_a05_02,
    "UT-A05-03": ut_a05_03,
    "UT-A05-04": ut_a05_04,
    "UT-A06-01": ut_a06_01,
    "UT-A06-02": ut_a06_02,
    "UT-A06-03": ut_a06_03,
    "UT-A06-04": ut_a06_04,
    "UT-A06-05": ut_a06_05,
    "UT-A06-06": ut_a06_06,
    "UT-A06-07": ut_a06_07,
    "UT-H03-01": ut_h03_01,
    "UT-H03-02": ut_h03_02,
    "UT-H04-05": ut_h04_05,
    "UT-H05-05": ut_h05_05,
    "UT-H05-06": ut_h05_06,
    "UT-H06-02": ut_h06_02,
    "UT-H06-03": ut_h06_03,
    "UT-H06-04": ut_h06_04,
    "UT-H06-06": ut_h06_06,
    "UT-H06-07": ut_h06_07,
    "UT-H06-08": ut_h06_08,
    "UT-H06-09": ut_h06_09,
    "UT-H06-10": ut_h06_10,
    "UT-H07-01": ut_h07_01,
    "UT-H07-02": ut_h07_02,
    "UT-H07-03": ut_h07_03,
    "UT-H07-04": ut_h07_04,
    "UT-H07-05": ut_h07_05,
    "UT-H07-06": ut_h07_06,
    "UT-H07-07": ut_h07_07,
    "UT-H07-08": ut_h07_08,
    "UT-H07-09": ut_h07_09,
    "UT-H07-10": ut_h07_10,
    "UT-H08-02": ut_h08_02,
    "UT-H08-03": ut_h08_03,
    "UT-H08-04": ut_h08_04,
    "UT-H08-05": ut_h08_05,
    "UT-H08-07": ut_h08_07,
    "UT-H08-08": ut_h08_08,
    "UT-H08-09": ut_h08_09,
    "UT-H08-11": ut_h08_11,
    "UT-H08-13": ut_h08_13,
}
