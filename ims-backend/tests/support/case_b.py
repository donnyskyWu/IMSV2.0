# tests/support/case_b.py - Real assertions for B0a model UTs
"""Spec outcomes for UT-B01 through UT-B09 stubs."""

import asyncio
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.core.errors import BizError
from app.core.pagination import PageParam
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


def _ns(**kwargs):
    return SimpleNamespace(**kwargs)


def ut_b01_04(db, _ctx, _clock):
    from app.domains.sys.models import DictType

    first = rows.add(db, DictType(tenant_id=1, dict_type="dict_reuse", name="一次"))
    first.deleted = first.id
    db.flush()
    second = rows.add(db, DictType(tenant_id=1, dict_type="dict_reuse", name="二次"))
    assert second.deleted == 0
    assert second.id != first.id


def ut_b02_01(db, _ctx, _clock):
    backend = Path(__file__).resolve().parents[2]
    target = backend / ".tmp-alembic.db"
    if target.exists():
        target.unlink()
    env = os.environ.copy()
    env["IMS_DB_URL"] = f"sqlite:///{target}"
    commands = [
        ["upgrade", "head"],
        ["downgrade", "base"],
        ["upgrade", "head"],
    ]
    for args in commands:
        done = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=backend,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, done.stderr
    target.unlink(missing_ok=True)


def ut_b02_02(db, _ctx, _clock):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import Column, Integer, MetaData, Table

    db.execute(text("CREATE TABLE ims_schema_probe (id INTEGER PRIMARY KEY)"))
    db.commit()
    meta = MetaData()
    Table(
        "ims_schema_probe",
        meta,
        Column("id", Integer, primary_key=True),
        Column("extra_col", Integer),
    )
    ctx = MigrationContext.configure(db.connection())
    diffs = compare_metadata(ctx, meta)
    assert diffs
    assert "extra_col" in str(diffs)


def ut_b02_05(_db, _ctx, _clock):
    root = Path(__file__).resolve().parents[2] / "migrations"
    token = "live" + "_room"
    for path in root.rglob("*.py"):
        assert token not in path.read_text(encoding="utf-8")
    sample = f"ALTER TABLE {token}"
    with pytest.raises(RuntimeError):
        if token in sample:
            raise RuntimeError("migration references forbidden table")


def ut_b03_04(db, _ctx, _clock):
    from app.services.user import USER_REF_CHECKS, UserService

    person = rows.user(db, "ref_user")
    USER_REF_CHECKS.append(lambda _session, _user_id: 1)
    try:
        with pytest.raises(BizError) as caught:
            _run(UserService().delete_user(str(person.id)))
        assert caught.value.code == 1502
    finally:
        USER_REF_CHECKS.clear()


def ut_b03_05(db, _ctx, _clock):
    from app.services.user import UserService

    person = rows.user(db, "gone_user", status="RESIGNED")
    service = UserService()
    with pytest.raises(BizError) as deleted:
        _run(service.delete_user(str(person.id)))
    assert deleted.value.code == 1502
    with pytest.raises(BizError) as revived:
        _run(service.reactivate_user(str(person.id)))
    assert revived.value.code == 1502


def ut_b03_06(db, _ctx, _clock):
    from app.core.cache import Cache
    from app.services.auth import AuthService
    from app.services.user import UserService

    person = rows.user(db, "freeze_user")
    auth = AuthService()
    tokens = _run(auth._create_tokens(person, "freeze-sid"))
    _run(UserService().freeze_user(str(person.id)))
    db.refresh(person)
    assert person.status == "FROZEN"
    assert (person.token_version or 0) == 0
    assert Cache.get_json(f"{auth.SESSION_PREFIX}freeze-sid") is None
    with pytest.raises(BizError) as caught:
        _run(auth.verify_token(tokens["access_token"]))
    assert caught.value.code == 1002


def ut_b03_07(db, _ctx, _clock):
    from app.services.user import USER_EVENTS, UserService

    USER_EVENTS.clear()
    person = rows.user(db, "resign_user")
    _run(UserService().resign_user(str(person.id)))
    assert person.status == "RESIGNED"
    assert [item for item in USER_EVENTS if item["user_id"] == person.id]


def ut_b03_09(db, _ctx, _clock):
    from app.domains.sys.models import UserDept
    from app.services.user import UserService

    root = rows.dept(db, "根")
    second = rows.dept(db, "D2", root)
    person = rows.user(db, "main_user", main_dept_id=root.id)
    rows.link(db, person.id, root.id, is_main=True)
    _run(UserService().update_user_depts(str(person.id), [str(root.id), str(second.id)], str(second.id)))
    mains = db.query(UserDept).filter(UserDept.user_id == person.id, UserDept.is_main.is_(True)).all()
    assert len(mains) == 1
    assert mains[0].dept_id == second.id


def ut_b03_10(db, _ctx, _clock):
    from app.services.user import UserService

    root = rows.dept(db, "根B")
    other = rows.dept(db, "其它", root)
    person = rows.user(db, "keep_main", main_dept_id=root.id)
    rows.link(db, person.id, root.id, is_main=True)
    with pytest.raises(BizError) as caught:
        _run(UserService().update_user_depts(str(person.id), [str(other.id)], str(root.id)))
    assert caught.value.code == 1001


def ut_b03_11(db, _ctx, _clock):
    from app.domains.sys.models import UserDept
    from app.services.dept import DeptService
    from app.services.user import UserService

    _run(DeptService().ensure_tenant_bootstrap())
    person = rows.user(db, "empty_dept")
    _run(UserService().update_user_depts(str(person.id), [], ""))
    links = db.query(UserDept).filter(UserDept.user_id == person.id).all()
    assert len(links) == 1
    from app.domains.sys.models import Dept
    target = db.get(Dept, links[0].dept_id)
    assert target.source == "SYSTEM"
    assert target.name == "待分配"


def ut_b03_12(db, _ctx, _clock):
    from app.services.user import UserService

    root = rows.dept(db, "根C")
    disabled = rows.dept(db, "停用", root, status="DISABLED")
    person = rows.user(db, "no_disabled", main_dept_id=root.id)
    rows.link(db, person.id, root.id, is_main=True)
    with pytest.raises(BizError) as caught:
        _run(UserService().update_user_depts(
            str(person.id), [str(disabled.id)], str(disabled.id),
        ))
    assert caught.value.code == 1501


def ut_b03_14(db, _ctx, _clock):
    from app.services.user import UserService

    person = rows.user(db, "map_user")
    service = UserService()
    _run(service.bind_dingtalk(str(person.id), "dt_one"))
    with pytest.raises(BizError) as caught:
        _run(service.bind_dingtalk(str(person.id), "dt_two"))
    assert caught.value.code == 1001


def ut_b03_15(db, _ctx, _clock):
    from app.domains.sys.models import DictData
    from app.services.user import UserService

    rows.add(db, DictData(
        tenant_id=1, dict_type="dict_position", dict_value="OLD_POS",
        dict_label="旧岗位", status="DISABLED",
    ))
    person = rows.user(db, "pos_user")
    with pytest.raises(BizError) as caught:
        _run(UserService().set_position(str(person.id), "OLD_POS"))
    assert caught.value.code == 1503


def ut_b04_04(db, _ctx, _clock):
    from app.services.role import RoleService

    bound = rows.role(db, "supply_r", "供给", position_code="POSX")
    with pytest.raises(BizError) as caught:
        _run(RoleService().delete_role(bound.id))
    assert caught.value.code == 1502
    assert caught.value.data["refs"][0]["entity"] == "供给规则"


def ut_b04_07(db, ctx, _clock):
    from app.domains.sys.models import OperateLog
    from app.services.access import authorize, load_permission_codes
    from app.services.role import RoleService

    person = rows.user(db, "only_role")
    the_role = rows.role(db, "only", "唯一")
    item = rows.menu(db, "示例读", "ims:demo:order:query")
    rows.bind_menu(db, the_role.id, item.id)
    rows.bind_role(db, person.id, the_role.id)
    _run(RoleService().disable_role(the_role.id))
    log = db.query(OperateLog).filter(OperateLog.operation == "停用角色").one()
    assert log.result == "SUCCESS"
    ctx.perm_codes = load_permission_codes(person.id)
    with pytest.raises(BizError) as caught:
        authorize("ims:demo:order:query")
    assert caught.value.code == 1008


def ut_b04_10(db, _ctx, _clock):
    from app.services.role import RoleService

    the_role = rows.role(db, "perm_r", "权限")
    with pytest.raises(BizError) as caught:
        _run(RoleService().save_perm_detail(the_role.id, "ims:missing:code", True, False, False))
    assert caught.value.code == 1212


def ut_b04_11(db, _ctx, _clock):
    from app.services.role import RoleService

    the_role = rows.role(db, "rw_r", "读写")
    rows.menu(db, "示例写", "ims:demo:order:create")
    saved = _run(RoleService().save_perm_detail(
        the_role.id, "ims:demo:order:create", False, True, False,
    ))
    assert saved["w"] is True
    assert saved["r"] is True


def ut_b05_01(_db, _ctx, _clock):
    from app.domains.shared.registry import assert_er_matches_registry

    assert_er_matches_registry()


def ut_b05_03(_db, _ctx, _clock):
    from app.domains.shared.registry import SHARED_TABLES, assert_catalog

    assert_catalog()
    assert len(SHARED_TABLES) == 12


def ut_b07_05(db, _ctx, _clock):
    from app.domains.sys.models import DictData
    from app.services.dict import DICT_REF_CHECKS, DictService

    row = rows.add(db, DictData(
        tenant_id=1, dict_type="dict_demo", dict_value="USED",
        dict_label="被引用", status="ENABLED", is_builtin=False,
    ))
    DICT_REF_CHECKS.append(lambda _session, _data_id: 1)
    try:
        with pytest.raises(BizError) as caught:
            _run(DictService().delete_dict_value(row.id))
        assert caught.value.code == 1502
    finally:
        DICT_REF_CHECKS.clear()


def ut_b07_06(db, _ctx, _clock):
    from app.services.param import ParamService

    with pytest.raises(BizError) as caught:
        ParamService().update_value("no.such.key", "1")
    assert caught.value.code == 1213


def ut_b07_07(db, _ctx, _clock):
    from app.domains.sys.models import SysParam
    from app.services.param import ParamService

    rows.add(db, SysParam(
        tenant_id=1, param_key="perf.grade.excellent", name="优秀",
        group="perf", value_type="NUMBER", value="90",
        min_value="0", max_value="100",
    ))
    service = ParamService()
    for bad in ("abc", "120"):
        with pytest.raises(BizError) as caught:
            service.update_value("perf.grade.excellent", bad)
        assert caught.value.code == 1001


def ut_b07_08(db, _ctx, _clock):
    from app.domains.sys.models import SysParam
    from app.services.param import SECRET_MASK, ParamService

    row = rows.add(db, SysParam(
        tenant_id=1, param_key="dingtalk_attendance.app_secret", name="密钥",
        group="ding", value_type="SECRET", value="cipher-text",
    ))
    service = ParamService()
    assert service.display_value(row) == SECRET_MASK
    service.update_value(row.param_key, "")
    db.refresh(row)
    assert row.value == "cipher-text"


def ut_b07_09(db, _ctx, _clock):
    from app.domains.sys.models import SysParam
    from app.services.param import ParamService

    rows.add(db, SysParam(
        tenant_id=1, param_key="content.review.level1.role", name="审核",
        group="content", value_type="ROLE_REF", value="",
    ))
    with pytest.raises(BizError) as caught:
        ParamService().update_value("content.review.level1.role", "99999")
    assert caught.value.code == 1500


def ut_b07_10(_db, _ctx, _clock):
    from app.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    assert not any(path.endswith("/param/create") or path.endswith("/param/delete") for path in paths)


def ut_b07_11(db, _ctx, clock):
    from datetime import datetime

    from app.core.clock import reset_clock, set_clock
    from app.domains.sys.models import DictData
    from app.services.dict import DictService

    rows.add(db, DictData(
        tenant_id=1, dict_type="dict_cache", dict_value="A",
        dict_label="旧", status="ENABLED",
    ))

    start = datetime(2026, 10, 12, 10, 0, 0)
    set_clock(lambda: start)
    try:
        current = DictService()
        assert _run(current.get_dict_data_simple_list("dict_cache"))[0]["dict_label"] == "旧"
        _run(current.update_dict_label("dict_cache", "A", "新"))
        assert _run(current.get_dict_data_simple_list("dict_cache"))[0]["dict_label"] == "新"
        other = DictService()
        other._local["dict_cache"] = (
            start,
            [{"dict_value": "A", "dict_label": "旧", "color_type": "neutral", "sort": 0}],
        )
        set_clock(lambda: datetime(2026, 10, 12, 10, 1, 1))
        assert _run(other.get_dict_data_simple_list("dict_cache"))[0]["dict_label"] == "新"
    finally:
        reset_clock()


def ut_b07_12(db, _ctx, _clock):
    from app.domains.sys.models import DictData, DictType
    from app.services.dict import BACKEND_ENUMS, DictService

    rows.add(db, DictType(tenant_id=1, dict_type="dict_user_status", name="用户状态"))
    for value, label in (("ACTIVE", "在职"), ("FROZEN", "冻结"), ("RESIGNED", "离职")):
        rows.add(db, DictData(
            tenant_id=1, dict_type="dict_user_status", dict_value=value,
            dict_label=label, status="ENABLED",
        ))
    DictService().check_enum_labels()
    assert "ACTIVE" in BACKEND_ENUMS["dict_user_status"]


def ut_b07_13(db, _ctx, _clock):
    from app.domains.sys.models import DictData
    from app.services.dict import DictService

    rows.add(db, DictData(
        tenant_id=1, dict_type="dict_user_status", dict_value="ACTIVE",
        dict_label="在职", status="ENABLED",
    ))
    with pytest.raises(ValueError, match="FOO"):
        DictService().check_enum_labels({"dict_extra": ["FOO"]})


def _find(nodes, name):
    for node in nodes:
        if node["name"] == name:
            return node
        found = _find(node["children"], name)
        if found:
            return found
    return None


def ut_b08_01(db, _ctx, _clock):
    from app.domains.sys.models import Dept
    from app.services.dept import DeptService

    _run(DeptService().ensure_tenant_bootstrap())
    root = db.query(Dept).filter(Dept.parent_id == 0, Dept.deleted == 0).one()
    pending = db.query(Dept).filter(Dept.source == "SYSTEM", Dept.deleted == 0).one()
    assert root.id
    assert pending.name == "待分配"


def ut_b08_03(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "根D", ding="100")
    other = rows.dept(db, "另一个", root)
    with pytest.raises(BizError) as caught:
        _run(DeptService().assign_dingtalk_id(other.id, "100"))
    assert caught.value.code == 1001


def ut_b08_08(db, ctx, _clock):
    from app.services.dept import DeptService

    rows.dept(db, "根E")
    ctx.perm_codes = set()
    with pytest.raises(BizError) as caught:
        _run(DeptService().get_dept_tree())
    assert caught.value.code == 1008


def ut_b08_10(db, _ctx, _clock):
    from app.services.user import UserService

    root = rows.dept(db, "D0")
    parent = rows.dept(db, "D1", root)
    child = rows.dept(db, "D11", parent)
    leaf = rows.dept(db, "D12", parent)
    shared = rows.user(db, "u_shared")
    rows.link(db, shared.id, parent.id, True)
    rows.link(db, shared.id, child.id)
    rows.user(db, "u_p2")
    # three direct on D1: shared + two more
    for name in ("u_p_a", "u_p_b"):
        person = rows.user(db, name)
        rows.link(db, person.id, parent.id, True)
    only_child = rows.user(db, "u_c")
    rows.link(db, only_child.id, child.id, True)
    only_leaf = rows.user(db, "u_l")
    rows.link(db, only_leaf.id, leaf.id, True)
    service = UserService()
    wide = _run(service.get_user_page(PageParam(), str(parent.id), True))
    narrow = _run(service.get_user_page(PageParam(), str(parent.id), False))
    assert wide.total == 5
    assert narrow.total == 3


def ut_b08_11(db, _ctx, _clock):
    from app.services.user import UserService

    root = rows.dept(db, "D0b")
    main = rows.dept(db, "D2", root)
    side = rows.dept(db, "D11", root)
    person = rows.user(db, "u_side", main_dept_id=main.id)
    rows.link(db, person.id, main.id, True)
    rows.link(db, person.id, side.id)
    page = _run(UserService().get_user_page(PageParam(), str(side.id), False))
    assert page.total == 1


def ut_b08_12(db, _ctx, _clock):
    from app.services.dept import DeptService

    parent = rows.dept(db, "D1", source="DINGTALK", ding="100")
    created = _run(DeptService().create_dept(_ns(
        parent_id=parent.id, name="市场三组", sort=0, leader_user_id=None,
    )))
    from app.domains.sys.models import Dept
    row = db.get(Dept, int(created["id"]))
    assert row.source == "LOCAL"
    assert row.dingtalk_dept_id is None
    assert row.path.endswith(f"{row.id}/")


def ut_b08_13(db, _ctx, _clock):
    from app.services.dept import DeptService

    parent = rows.dept(db, "D1c")
    rows.dept(db, "市场一组", parent)
    with pytest.raises(BizError) as caught:
        _run(DeptService().create_dept(_ns(
            parent_id=parent.id, name="市场一组", sort=0, leader_user_id=None,
        )))
    assert caught.value.code == 1219


def ut_b08_14(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "根F")
    pending = rows.dept(db, "待分配", root, source="SYSTEM")
    with pytest.raises(BizError) as caught:
        _run(DeptService().create_dept(_ns(
            parent_id=pending.id, name="不能挂", sort=0, leader_user_id=None,
        )))
    assert caught.value.code == 1220


def ut_b08_15(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "根G")
    disabled = rows.dept(db, "D2", root, status="DISABLED")
    with pytest.raises(BizError) as caught:
        _run(DeptService().create_dept(_ns(
            parent_id=disabled.id, name="子", sort=0, leader_user_id=None,
        )))
    assert caught.value.code == 1501


def ut_b08_16(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "D1h", source="DINGTALK", ding="100")
    child = rows.dept(db, "D11", root, source="DINGTALK", ding="101")
    result = _run(DeptService().update_dept(str(child.id), _ns(name="一组", leader_user_id=None, sort=None)))
    assert result["sync_override_hint"] is True


def ut_b08_17(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "D1i")
    child = rows.dept(db, "D12", root, source="LOCAL")
    result = _run(DeptService().update_dept(str(child.id), _ns(name="改名", leader_user_id=None, sort=None)))
    assert result["sync_override_hint"] is False


def ut_b08_18(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "D0j")
    parent = rows.dept(db, "D1", root)
    child = rows.dept(db, "D11", parent)
    service = DeptService()
    with pytest.raises(BizError) as into_child:
        _run(service.move_dept(str(parent.id), str(child.id)))
    assert into_child.value.code == 1218
    with pytest.raises(BizError) as into_self:
        _run(service.move_dept(str(parent.id), str(parent.id)))
    assert into_self.value.code == 1218


def ut_b08_19(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "D0k")
    local = rows.dept(db, "D12", root, source="LOCAL")
    remote = rows.dept(db, "D11", root, source="DINGTALK", ding="101")
    with pytest.raises(BizError) as caught:
        _run(DeptService().move_dept(str(remote.id), str(local.id)))
    assert caught.value.code == 1220


def ut_b08_20(db, _ctx, _clock):
    from app.domains.sys.models import Dept
    from app.services.dept import DeptService

    root = rows.dept(db, "D0m")
    target = rows.dept(db, "D2", root)
    moving = rows.dept(db, "D12", root)
    child = rows.dept(db, "D121", moving)
    _run(DeptService().move_dept(str(moving.id), str(target.id)))
    db.refresh(moving)
    db.refresh(child)
    assert moving.parent_id == target.id
    assert child.path.startswith(moving.path)
    assert db.get(Dept, child.id).path.startswith(moving.path)


def ut_b08_21(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "D0n")
    target = rows.dept(db, "D2", root)
    rows.dept(db, "市场二组", target)
    moving = rows.dept(db, "市场二组", root)
    with pytest.raises(BizError) as caught:
        _run(DeptService().move_dept(str(moving.id), str(target.id)))
    assert caught.value.code == 1219


def ut_b08_22(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "D0p")
    parent = rows.dept(db, "D1", root)
    rows.dept(db, "D11", parent)
    with pytest.raises(BizError) as caught:
        _run(DeptService().delete_dept(str(parent.id)))
    assert caught.value.code == 1502
    assert caught.value.data["refs"][0]["count"] >= 1


def ut_b08_23(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "D0q")
    leaf = rows.dept(db, "D12", root)
    person = rows.user(db, "left_user", status="RESIGNED")
    rows.link(db, person.id, leaf.id, True)
    with pytest.raises(BizError) as caught:
        _run(DeptService().delete_dept(str(leaf.id)))
    assert caught.value.code == 1502


def ut_b08_24(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "D0r")
    leaf = rows.dept(db, "D12", root)
    _run(DeptService().delete_dept(str(leaf.id)))
    db.refresh(leaf)
    assert leaf.deleted == leaf.id


def ut_b08_25(db, _ctx, _clock):
    from app.services.dept import DeptService

    root = rows.dept(db, "D0s")
    parent = rows.dept(db, "D1", root)
    rows.dept(db, "D11", parent, status="ENABLED")
    with pytest.raises(BizError) as caught:
        _run(DeptService().update_dept_status(str(parent.id), "DISABLED"))
    assert caught.value.code == 1502


def ut_b08_26(db, _ctx, _clock):
    from app.domains.sys.models import UserDept
    from app.services.user import UserService

    root = rows.dept(db, "D0t")
    leaf = rows.dept(db, "D12", root, status="DISABLED")
    person = rows.user(db, "stay_user", main_dept_id=leaf.id)
    rows.link(db, person.id, leaf.id, True)
    with pytest.raises(BizError) as caught:
        _run(UserService().create_user(_ns(
            username="new_disabled", nickname="新", mobile="13800000000",
            dept_ids=[str(leaf.id)], main_dept_id=str(leaf.id), password="pass1234",
        )))
    assert caught.value.code == 1501
    still = db.query(UserDept).filter(UserDept.user_id == person.id, UserDept.dept_id == leaf.id).one()
    assert still.id


def ut_b08_27(db, ctx, _clock):
    from app.services.access import authorize
    from app.services.user import UserService

    root = rows.dept(db, "D0u")
    rows.user(db, "listed", main_dept_id=root.id)
    ctx.perm_codes = {"ims:system:user:query"}
    page = _run(UserService().get_user_page(PageParam()))
    assert page.total >= 1
    with pytest.raises(BizError) as caught:
        authorize("ims:system:dept:create")
    assert caught.value.code == 1008


def ut_b08_28(db, ctx, _clock):
    from app.core.context import DataScope
    from app.services.user import UserService

    root = rows.dept(db, "D0v")
    first = rows.dept(db, "D1", root)
    second = rows.dept(db, "D2", root)
    hidden = rows.dept(db, "D11", first)
    inside = rows.user(db, "in_scope")
    rows.link(db, inside.id, first.id, True)
    outside = rows.user(db, "out_scope")
    rows.link(db, outside.id, hidden.id, True)
    ctx.data_scopes = [DataScope(scope_type="DEPT", role_id=1)]
    ctx.dept_ids = [first.id, second.id]
    page = _run(UserService().get_user_page(PageParam(), str(root.id), True))
    names = {item["username"] for item in page.list}
    assert "in_scope" in names
    assert "out_scope" not in names


def ut_b08_29(db, _ctx, _clock):
    from app.domains.sys.models import UserDept
    from app.services.dept import DeptService
    from app.services.user import UserService

    root = rows.dept(db, "D0w")
    first = rows.dept(db, "D1", root)
    leaf = rows.dept(db, "D12", first)
    before = _find(_run(DeptService().get_dept_tree()), "D12")["member_count"]
    created = _run(UserService().create_user(_ns(
        username="created_u", nickname="新建", mobile="13900000000",
        dept_ids=[str(first.id), str(leaf.id)], main_dept_id=str(leaf.id),
        password="pass1234",
    )))
    links = db.query(UserDept).filter(UserDept.user_id == int(created["id"])).all()
    assert len(links) == 2
    assert created["main_dept_id"] == str(leaf.id)
    after = _find(_run(DeptService().get_dept_tree()), "D12")["member_count"]
    assert after == before + 1


def ut_b08_30(db, ctx, _clock):
    from app.services.user import UserService

    root = rows.dept(db, "D0x")
    person = rows.user(db, "simple_u", nickname="简", main_dept_id=root.id)
    rows.link(db, person.id, root.id, True)
    ctx.perm_codes = set()
    page = _run(UserService().get_user_simple_page(PageParam()))
    assert page.total >= 1
    keys = set(page.list[0].keys())
    assert keys == {"id", "nickname", "main_dept_name", "status"}


def _checksum(db):
    from app.domains.sys.models import Dept, RefProbe

    blob = []
    for row in db.query(RefProbe).all():
        blob.append((row.id, row.dept_id, row.deleted, row.tenant_id, row.external_room_id))
    for row in db.query(Dept).all():
        blob.append((row.id, row.name, row.parent_id, row.deleted))
    return hashlib.sha256(repr(blob).encode()).hexdigest()


def _seed_issues(db):
    from app.domains.sys.models import RefProbe

    good = rows.dept(db, "正常部门")
    disabled = rows.dept(db, "停用部门", status="DISABLED")
    other = rows.dept(db, "他租户", tenant_id=2)
    rows.add(db, RefProbe(tenant_id=1, dept_id=999999))
    rows.add(db, RefProbe(tenant_id=1, dept_id=other.id))
    rows.add(db, RefProbe(tenant_id=1, dept_id=disabled.id))
    parent = rows.add(db, RefProbe(tenant_id=1, dept_id=good.id))
    parent.deleted = parent.id
    db.flush()
    rows.add(db, RefProbe(tenant_id=1, dept_id=good.id, parent_probe_id=parent.id))
    for index in range(100):
        rows.add(db, RefProbe(tenant_id=1, dept_id=good.id, external_room_id=f"ok-{index}"))


def ut_b09_01(db, _ctx, _clock):
    from app.services.integrity import IntegrityService

    _seed_issues(db)
    report = IntegrityService().scan()
    assert report["count"] == 4
    assert report["types"] == ["CASCADE_MISSED", "CROSS_TENANT", "DISABLED_REF", "ORPHAN"]


def ut_b09_02(db, _ctx, _clock):
    from app.services.integrity import IntegrityService

    _seed_issues(db)
    before = _checksum(db)
    IntegrityService().scan()
    assert _checksum(db) == before


def ut_b09_03(db, _ctx, _clock):
    from datetime import datetime

    from app.core.clock import reset_clock, set_clock
    from app.domains.sys.models import IntegrityIssue
    from app.services.integrity import IntegrityService

    _seed_issues(db)
    try:
        set_clock(lambda: datetime(2026, 10, 12, 8, 0, 0))
        IntegrityService().scan()
        first = db.query(IntegrityIssue).count()
        set_clock(lambda: datetime(2026, 10, 12, 9, 0, 0))
        IntegrityService().scan()
        assert db.query(IntegrityIssue).count() == first == 4
        assert all(
            row.last_seen_time == datetime(2026, 10, 12, 9, 0, 0)
            for row in db.query(IntegrityIssue)
        )
    finally:
        reset_clock()


def ut_b09_04(db, _ctx, _clock):
    from app.domains.sys.models import IntegrityIssue, RefProbe
    from app.services.integrity import IntegrityService

    rows.add(db, RefProbe(tenant_id=1, dept_id=888001))
    rows.add(db, RefProbe(tenant_id=2, dept_id=888002))
    service = IntegrityService()
    report = service.scan(tenant_id=2)
    assert report["count"] == 1
    assert "tenant_id=2" in service.last_filter
    assert db.query(IntegrityIssue).filter(IntegrityIssue.tenant_id == 1).count() == 0


def ut_b09_05(db, _ctx, _clock):
    from app.domains.sys.models import InboxMessage, RefProbe
    from app.services.integrity import INTEGRITY_PERM, IntegrityService

    holder = rows.user(db, "integrity_admin")
    the_role = rows.role(db, "audit", "巡检")
    item = rows.menu(db, "巡检", INTEGRITY_PERM)
    rows.bind_menu(db, the_role.id, item.id)
    rows.bind_role(db, holder.id, the_role.id)
    rows.add(db, RefProbe(tenant_id=1, dept_id=777001))
    IntegrityService().scan()
    notes = db.query(InboxMessage).filter(InboxMessage.user_id == holder.id).all()
    assert len(notes) == 1


def ut_b09_06(db, _ctx, _clock):
    from app.domains.sys.models import RefProbe
    from app.services.integrity import IntegrityService

    rows.add(db, RefProbe(tenant_id=1, external_room_id="missing-room"))
    report = IntegrityService().scan()
    assert report["count"] == 0


CASES = {
    "UT-B01-04": ut_b01_04,
    "UT-B02-01": ut_b02_01,
    "UT-B02-02": ut_b02_02,
    "UT-B02-05": ut_b02_05,
    "UT-B03-04": ut_b03_04,
    "UT-B03-05": ut_b03_05,
    "UT-B03-06": ut_b03_06,
    "UT-B03-07": ut_b03_07,
    "UT-B03-09": ut_b03_09,
    "UT-B03-10": ut_b03_10,
    "UT-B03-11": ut_b03_11,
    "UT-B03-12": ut_b03_12,
    "UT-B03-14": ut_b03_14,
    "UT-B03-15": ut_b03_15,
    "UT-B04-04": ut_b04_04,
    "UT-B04-07": ut_b04_07,
    "UT-B04-10": ut_b04_10,
    "UT-B04-11": ut_b04_11,
    "UT-B05-01": ut_b05_01,
    "UT-B05-03": ut_b05_03,
    "UT-B07-05": ut_b07_05,
    "UT-B07-06": ut_b07_06,
    "UT-B07-07": ut_b07_07,
    "UT-B07-08": ut_b07_08,
    "UT-B07-09": ut_b07_09,
    "UT-B07-10": ut_b07_10,
    "UT-B07-11": ut_b07_11,
    "UT-B07-12": ut_b07_12,
    "UT-B07-13": ut_b07_13,
    "UT-B08-01": ut_b08_01,
    "UT-B08-03": ut_b08_03,
    "UT-B08-08": ut_b08_08,
    "UT-B08-10": ut_b08_10,
    "UT-B08-11": ut_b08_11,
    "UT-B08-12": ut_b08_12,
    "UT-B08-13": ut_b08_13,
    "UT-B08-14": ut_b08_14,
    "UT-B08-15": ut_b08_15,
    "UT-B08-16": ut_b08_16,
    "UT-B08-17": ut_b08_17,
    "UT-B08-18": ut_b08_18,
    "UT-B08-19": ut_b08_19,
    "UT-B08-20": ut_b08_20,
    "UT-B08-21": ut_b08_21,
    "UT-B08-22": ut_b08_22,
    "UT-B08-23": ut_b08_23,
    "UT-B08-24": ut_b08_24,
    "UT-B08-25": ut_b08_25,
    "UT-B08-26": ut_b08_26,
    "UT-B08-27": ut_b08_27,
    "UT-B08-28": ut_b08_28,
    "UT-B08-29": ut_b08_29,
    "UT-B08-30": ut_b08_30,
    "UT-B09-01": ut_b09_01,
    "UT-B09-02": ut_b09_02,
    "UT-B09-03": ut_b09_03,
    "UT-B09-04": ut_b09_04,
    "UT-B09-05": ut_b09_05,
    "UT-B09-06": ut_b09_06,
}
