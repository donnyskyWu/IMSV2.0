# B5 分支补测。版本 v1.0 · 2026-10-13
"""把 P0 服务里还没走到的分支跑一遍。断言业务结果，不是空 pass。"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta

import pytest

from app.core.clock import BEIJING_TZ, get_now, set_clock
from app.core.config import get_settings
from app.core.context import DataScope, RequestContext, ctx
from app.core.crypto import decrypt_field, encrypt_field
from app.core.errors import BizError
from app.domains.corp.models import CertExpireTask, CertL3Whitelist, CertLevelRule
from app.domains.shared.models import AccountPersonal, MasterCert
from app.domains.sys.models import Menu, Role, RoleMenu, UserRole
from app.services.auth import session_remaining_seconds
from app.services.cert import CertService, cert_visible_for
from app.services.cert_expire import (
    CertExpireService,
    _level,
    _recipients,
    apply_test_clock,
    scan_cert_expire,
)
from app.services.cert_security import (
    CertSecurityService,
    plain_cert_no,
    resolve_preview,
    resolve_view_level,
)
from app.services.company import CompanyService
from app.services.realname import RealnameService
from app.services.role import RoleService
from app.services.sim_card import SimCardService
from tests.unit.test_b5_cert import _upload
from tests.unit.test_b5_resource import (
    CREDIT_OK,
    ID_OK,
    ID_OK_2,
    _company,
    _dicts,
    _raise,
    _realname,
    _sim,
    _user,
    png_bytes,
    use_scope,
)


@pytest.fixture(autouse=True)
def _branch_crypto_keys():
    """本文件单独挂密钥，避免加密走到未配置。"""
    security = get_settings().security
    old = (security.field_key, security.hash_key, dict(security.field_key_versions))
    security.field_key = "b5-field-key"
    security.hash_key = "b5-hash-key"
    security.field_key_versions = {"2": "b5-field-key-v2"}
    yield
    security.field_key, security.hash_key = old[0], old[1]
    security.field_key_versions = old[2]


@pytest.fixture
def b5(db_session):
    """字典、两个用户，上下文默认 ALL。"""
    _dicts(db_session)
    _user(db_session, 1, "u1")
    _user(db_session, 2, "u2")
    use_scope("ALL", uid=1)
    yield db_session
    ctx.reset()

CREDIT_2 = "91350100M000200Y4T"
CREDIT_3 = "91110000MA0000000H"


def test_ut_b5_co_branches(b5):
    """公司编辑字段、筛选、选择器关键字、空名称、信用代码排除自身。"""
    created = _company(mpCapacity=1)
    assert created["mpCapacity"] == 1
    updated = CompanyService().update_company(created["id"], {
        "creditCode": CREDIT_2,
        "industry": "IT",
        "address": "中山路 1 号",
        "legalName": "李四",
        "legalIdCard": ID_OK_2,
    })
    assert updated["creditCode"] == CREDIT_2
    assert updated["legalName"] == "李四"
    CompanyService().update_company(created["id"], {"credit_code": CREDIT_OK, "legal_name": "王五"})
    other = _company(name="星河二号", credit_code=CREDIT_3)
    err = _raise(lambda: CompanyService().update_company(created["id"], {"creditCode": CREDIT_3}), 1001)
    assert "信用代码" in err.msg
    _raise(lambda: _company(name="   "), 1001)
    page = CompanyService().page_companies(name="星河", status="ENABLED")
    assert page["total"] == 2
    options = CompanyService().list_company_options("二号")
    assert options and options[0]["id"] == other["id"]


def test_ut_b5_rn_branches(b5):
    """实名人更新、中介字段、空姓名、坏手机号、引用计数。"""
    person = _realname()
    service = RealnameService()
    bare = service.create_realname({
        "name": "无账号", "id_type": "PASSPORT", "id_card": "P900", "phone": "13611112222",
    })
    assert bare["userId"] == ""
    service.update_realname(person["id"], {"wechat": "wx1", "gender": "M", "user_id": ""})
    service.update_realname(person["id"], {"changeIdCard": True, "id_card": ID_OK})
    _raise(lambda: service.create_realname({"name": "坏号", "phone": "12", "id_type": "PASSPORT", "id_card": "P1"}), 1001)
    _raise(lambda: service.create_realname({"name": "  "}), 1001)
    _raise(lambda: service.create_realname({
        "name": "幽灵", "user_id": "abc", "id_type": "PASSPORT", "id_card": "P2", "phone": "13611113333",
    }), 1500)
    page = service.page_realnames(name="张三")
    assert page["total"] >= 1
    assert service.list_realname_options("张")
    people = service.create_intermediary(person["id"], {
        "name": "中介甲", "phone": "13600001111", "wechat": "wx", "relation_type": "DIRECT",
        "commission_rate": "1.50", "remark": "备注",
    })
    service.update_intermediary(people["id"], {})
    updated = service.update_intermediary(people["id"], {
        "name": "",
        "phone": "13600002222",
        "wechat": "wx2",
        "relationType": "AGENT",
        "commissionRate": "2.00",
        "remark": "新备注",
    })
    assert updated["name"] == "中介甲"
    assert updated["relationType"] == "AGENT"
    _raise(lambda: service.create_intermediary(person["id"], {"name": "  "}), 1001)
    _raise(lambda: service.create_intermediary(person["id"], {"name": "坏手机", "phone": "12"}), 1001)
    _upload(person=person)
    b5.add(AccountPersonal(id=91, tenant_id=1, name="个人号", realname_id=int(person["id"])))
    b5.flush()
    err = _raise(lambda: service.delete_realname(person["id"]), 1502)
    kinds = {item["type"] for item in err.data["refs"]}
    assert "cert" in kinds and "account" in kinds


def test_ut_b5_sm_branches(b5):
    """手机卡别名、缺字段、编辑各列和日期换算。"""
    person = _realname()
    service = SimCardService()
    _raise(lambda: service.create_sim_card({"phone": "12", "operator": "CMCC", "realname_id": person["id"]}), 1001)
    _raise(lambda: service.create_sim_card({"phone": "13700001111", "operator": "CMCC"}), 1001)
    created = service.create_sim_card({
        "phone_number": "13700001111",
        "operator": "CMCC",
        "realnameId": person["id"],
        "payment_cycle": "MONTH",
        "status": "ENABLED",
    })
    assert created["phone"].startswith("137")
    service.update_sim_card(created["id"], {
        "operator": "CMCC",
        "realnameId": person["id"],
        "assignedUserId": "",
        "iccid": "8986009999888877776",
        "packageName": "畅享",
        "monthlyRent": "",
        "status": "DISABLED",
        "isPrimary": True,
    })
    other = _sim(person["id"], phone="13700002222", iccid="8986001111222233334")
    _raise(lambda: service._unique_phone("13700001111", int(other["id"])), 1001)
    service._unique_phone("13700001111", int(created["id"]))
    service._unique_iccid("", None)
    service._unique_iccid("8986009999888877776", int(created["id"]))
    assert service._optional_int("") is None
    assert service._rent("") is None
    assert service._date("") is None
    assert service._date(date(2020, 1, 2)) == date(2020, 1, 2)
    assert service._date(datetime(2020, 1, 3, 8, 0)) == date(2020, 1, 3)
    assert service._date("2020-01-04") == date(2020, 1, 4)
    named = service.list_sim_card_options("137")
    assert named


def test_ut_b5_ct_holder_and_warn(b5):
    """持有人三种、换证不一致、拒绝、预警天数、系统上下文。"""
    service = CertService()
    user_cert = service.upload_cert({
        "holder_type": "USER",
        "holder_user_id": 1,
        "cert_type": "PASSPORT",
        "cert_no": "P100",
        "issue_date": "2020-01-01",
        "expire_date": "2030-01-01",
    }, "u.png", "image/png", png_bytes())
    assert user_cert["holderType"] == "USER"
    external = service.upload_cert({
        "holderType": "EXTERNAL",
        "holderName": "外协甲",
        "certType": "HEALTH",
        "certNo": "H100",
    }, "e.png", "image/png", png_bytes())
    assert external["external"] is True
    _raise(lambda: service.upload_cert({
        "holder_type": "USER", "holderUserId": 404, "cert_type": "OTHER", "cert_no": "X",
    }, "m.png", "image/png", png_bytes()), 1500)
    _raise(lambda: service.upload_cert({
        "holder_type": "EXTERNAL", "holder_name": "  ", "cert_type": "OTHER", "cert_no": "X",
    }, "m.png", "image/png", png_bytes()), 1001)
    _raise(lambda: service.upload_cert({
        "holder_type": "NOPE", "cert_type": "OTHER", "cert_no": "X",
    }, "m.png", "image/png", png_bytes()), 1001)
    _raise(lambda: service.upload_cert({
        "holder_type": "USER", "holder_user_id": 1, "cert_type": "PASSPORT", "cert_no": "P200",
    }, "u2.png", "image/png", png_bytes()), 1032)
    _raise(lambda: service.upload_cert({
        "holder_type": "EXTERNAL", "holder_name": "外协甲", "cert_type": "HEALTH", "cert_no": "H200",
    }, "e2.png", "image/png", png_bytes()), 1032)
    use_scope("ALL", uid=2)
    rejected = service.review_cert(user_cert["id"], False, "照片模糊")
    assert rejected["status"] == "REJECTED"
    pending_ext = b5.get(MasterCert, int(external["id"]))
    _raise(lambda: service.review_cert(pending_ext.id, False, "  "), 1001)
    use_scope("ALL", uid=1)
    again = service.upload_cert({
        "holder_type": "USER", "holder_user_id": 1, "cert_type": "PASSPORT", "cert_no": "P300",
    }, "u3.png", "image/png", png_bytes())
    assert again["version"] == 2
    created, person = _upload()
    use_scope("ALL", uid=2)
    service.review_cert(created["id"], True, "")
    use_scope("ALL", uid=1)
    renewed = service.upload_cert({
        "holder_type": "REALNAME",
        "realname_id": person["id"],
        "cert_type": "ID_CARD",
        "cert_no": ID_OK,
        "renew_from_id": created["id"],
        "expire_date": "2031-01-01",
    }, "r.png", "image/png", png_bytes())
    row = b5.get(MasterCert, int(renewed["id"]))
    row.cert_type = "PASSPORT"
    b5.flush()
    use_scope("ALL", uid=2)
    _raise(lambda: service.review_cert(renewed["id"], True, ""), 1001)
    row.cert_type = "ID_CARD"
    row.realname_id = 999
    b5.flush()
    _raise(lambda: service.review_cert(renewed["id"], True, ""), 1001)
    use_scope("SELF", uid=2)
    _raise(lambda: service.review_cert(external["id"], True, ""), 1504)
    _raise(lambda: service.delete_cert(external["id"]), 1504)
    use_scope("ALL", uid=1)
    cert_row = b5.get(MasterCert, int(created["id"]))
    cert_row.expire_date = None
    service.refresh_warn_level(cert_row)
    assert cert_row.warn_level is None
    today = get_now().date()
    cert_row.expire_date = today
    service.refresh_warn_level(cert_row)
    assert cert_row.warn_level == "LOCKED"
    cert_row.expire_date = today + timedelta(days=3)
    service.refresh_warn_level(cert_row)
    assert cert_row.warn_level == "RED"
    cert_row.expire_date = today + timedelta(days=20)
    service.refresh_warn_level(cert_row)
    assert cert_row.warn_level == "YELLOW"
    assert service._day(None) is None
    assert service._day(datetime(2024, 5, 6, 1, 2)) == date(2024, 5, 6)
    assert service._day(date(2024, 5, 7)) == date(2024, 5, 7)
    lone = b5.get(MasterCert, int(user_cert["id"]))
    assert cert_visible_for(lone, 2, {"ims:cert:archive:query-self"}, {"ALL"}) is False
    linked = b5.get(MasterCert, int(created["id"]))
    assert cert_visible_for(linked, 1, {"ims:cert:archive:query"}, {"SELF"}) is True
    assert cert_visible_for(linked, 9, {"ims:cert:archive:query"}, {"ALL"}) is True
    assert cert_visible_for(linked, 1, set(), {"ALL"}) is False
    ctx.set(RequestContext(user_id=0, tenant_id=1, is_system=True))
    assert service.list_certs()["total"] >= 1
    use_scope("ALL", uid=1)


def test_ut_b5_ct_ocr_metrics_notify(b5, monkeypatch):
    """OCR 其他错误继续抛、识别失败、无人覆盖的数字化率、审计通知、非预警任务。"""
    from app.domains.sys.models import InboxMessage, StoredFile
    from app.integrations.train_ai.client import TrainAIClient

    bare = RealnameService().create_realname({
        "name": "无证", "user_id": 2, "id_type": "PASSPORT", "id_card": "P800", "phone": "13622223333",
    })
    metrics = CertService().digital_metrics()
    assert metrics["total"] >= 1
    assert metrics["covered"] == 0
    RealnameService().set_realname_status(bare["id"], "LEFT")
    assert CertService().digital_metrics()["rate"] == "0.00"

    b5.add(StoredFile(
        id=31, tenant_id=1, scene="cert", file_key="ocr.png", original_name="ocr.png", uploader_id=1,
    ))
    b5.flush()
    settings = get_settings()
    settings.train_ai.enabled = True
    settings.train_ai.base_url = "https://example.com"
    settings.train_ai.mode = "real"

    def _other(_self, _image):
        raise BizError(1001, msg="其他错误")

    original_recognize = TrainAIClient.recognize_image
    monkeypatch.setattr(TrainAIClient, "recognize_image", _other)
    _raise(lambda: CertService().recognize_cert("ocr.png"), 1001)
    monkeypatch.setattr(TrainAIClient, "recognize_image", original_recognize)
    monkeypatch.setattr(CertService, "_file_bytes", lambda self, _key: b"%PDF-1.4")
    found = CertService().recognize_cert("ocr.png")
    assert found["recognized"] is False

    created, _person = _upload()
    use_scope("ALL", uid=2)
    CertService().review_cert(created["id"], True, "")
    b5.add(CertL3Whitelist(id=31, tenant_id=1, user_id=2))
    role = Role(
        id=31, tenant_id=1, role_key="audit31", name="审计", source="MANUAL", status="ENABLED", data_scope="ALL",
    )
    menu = Menu(
        id=31, tenant_id=1, parent_id=0, name="审计", type="BUTTON",
        status="ENABLED", perm_code="ims:cert:security:audit",
    )
    b5.add(role)
    b5.add(menu)
    b5.add(UserRole(id=31, tenant_id=1, user_id=1, role_id=31))
    b5.add(RoleMenu(id=31, tenant_id=1, role_id=31, menu_id=31))
    moment = datetime(2026, 10, 13, 9, 0)
    for index in range(10):
        from app.domains.corp.models import CertViewLog
        b5.add(CertViewLog(
            id=400 + index, tenant_id=1, cert_id=int(created["id"]), viewer_user_id=2,
            view_level=3, result="OK", view_time=moment,
        ))
    b5.flush()
    set_clock(lambda: moment.replace(tzinfo=BEIJING_TZ))
    _raise(lambda: CertService().view_cert(created["id"]), 1035)
    assert b5.query(InboxMessage).count() >= 1

    use_scope("ALL", uid=1)
    locked = _upload(person=_realname(name="另一个", user_id=2, id_card=ID_OK_2, phone="13633334444"))
    task_cert = b5.get(MasterCert, int(locked[0]["id"]))
    b5.add(CertExpireTask(id=77, tenant_id=1, cert_id=task_cert.id, level="RED", status="LOCKED"))
    b5.flush()
    CertService().delete_cert(task_cert.id)
    assert b5.get(CertExpireTask, 77).status == "LOCKED"


def test_ut_b5_ex_branches(b5):
    """扫描跳过、锁定、超 30 天、催办间隔、换证实名不一致、接收人过滤。"""
    apply_test_clock(None)
    apply_test_clock("  ")
    assert _level(0) == "LOCKED"
    assert _level(31) is None
    created, person = _upload()
    use_scope("ALL", uid=2)
    CertService().review_cert(created["id"], True, "")
    row = b5.get(MasterCert, int(created["id"]))
    row.expire_date = None
    row.status = "EFFECTIVE"
    b5.flush()
    assert scan_cert_expire()["notified"] == 0
    row.expire_date = get_now().date() + timedelta(days=40)
    b5.flush()
    assert scan_cert_expire()["notified"] == 0
    row.status = "EFFECTIVE"
    row.expire_date = get_now().date()
    b5.flush()
    assert scan_cert_expire()["notified"] == 1
    b5.add(CertExpireTask(
        id=88, tenant_id=1, cert_id=row.id, level="YELLOW", status="RENEW_RESOLVED",
    ))
    # 已有任务会被 _task_for 取回。统计另插一条已解除，确认不计入。
    stats = CertExpireService().expire_stats()
    assert stats["LOCKED"] >= 1
    resolved = CertExpireTask(
        id=89, tenant_id=1, cert_id=row.id + 1, level="YELLOW", status="RENEW_RESOLVED",
    )
    b5.add(resolved)
    b5.flush()
    assert CertExpireService().expire_stats()["YELLOW"] == stats["YELLOW"]
    old = _realname(name="离职实名", user_id=2, id_card=ID_OK_2, phone="13644445555")
    RealnameService().set_realname_status(old["id"], "LEFT")
    left_cert = b5.get(MasterCert, int(created["id"]))
    left_cert.realname_id = int(old["id"])
    b5.flush()
    assert 2 not in _recipients(left_cert)
    user_only = b5.get(MasterCert, int(created["id"]))
    user_only.realname_id = None
    b5.flush()
    _recipients(user_only)
    task = b5.query(CertExpireTask).filter(CertExpireTask.status != "RENEW_RESOLVED").first()
    task.last_remind_time = get_now().replace(tzinfo=None) - timedelta(minutes=30)
    task.status = "WARNING"
    b5.flush()
    reminded = CertExpireService().remind_expire(task.id)
    assert reminded["reminded"] is True
    _raise(lambda: CertExpireService().renew_cert(
        task.id,
        {"realname_id": 999, "holder_type": "REALNAME", "cert_type": "ID_CARD"},
        "n.png",
        "image/png",
        png_bytes(),
    ), 1001)


def test_ut_b5_sc_branches(b5):
    """查看级别缺角色、坏预览、空证件号、覆盖保存、非法级别。"""
    ctx.reset()
    assert resolve_view_level(1) == 1
    use_scope("ALL", uid=1, scopes=[DataScope("ALL", 0)])
    assert resolve_view_level(1) == 1
    ctx.set(RequestContext(user_id=1, tenant_id=1, data_scopes=[{"scope_type": "DEPT"}]))
    assert resolve_view_level(1) == 1
    _raise(lambda: resolve_preview("missing-token"), 1001)
    assert plain_cert_no("") == ""
    assert plain_cert_no(None) == ""
    service = CertSecurityService()
    use_scope("ALL", uid=1)
    saved = service.save_level_config({"rules": [{"roleId": 1, "viewLevel": 2}], "whitelist": [1]})
    assert saved["whitelist"] == ["1"]
    _raise(lambda: service.save_level_config({"rules": [{"roleId": 1, "viewLevel": 9}], "whitelist": [2]}), 1001)
    again = service.save_level_config({"rules": [{"role_id": 1, "view_level": 3}], "whitelist": [2]})
    assert again["rules"][0]["viewLevel"] == 3
    assert b5.query(CertLevelRule).filter(CertLevelRule.deleted == 0).count() == 1
    assert b5.query(CertL3Whitelist).filter(CertL3Whitelist.deleted == 0).count() == 1


def test_ut_b5_crypto_none_and_bad():
    """空明文和坏密文都是 1001。"""
    _raise(lambda: encrypt_field(None), 1001)
    _raise(lambda: decrypt_field("bad"), 1001)
    _raise(lambda: decrypt_field(""), 1001)


def test_ut_b5_auth_session_without_times():
    """会话既没有到期时间也没有创建时间，按已过期。"""
    assert session_remaining_seconds({}) == 0


def test_ut_b5_deps_and_role_branches(b5):
    """登录依赖和角色查询的空、拒绝、命中。"""
    from app.api.deps import (
        PermissionChecker,
        get_current_user,
        get_token_from_header,
        require_all_permissions,
        require_any_permission,
        require_data_scope,
        require_login,
    )

    assert asyncio.run(get_token_from_header("Basic abc")) is None
    assert asyncio.run(get_token_from_header(None)) is None
    _raise(lambda: asyncio.run(get_current_user(None)), 1002)
    assert asyncio.run(get_current_user(1)) == 1
    ctx.reset()
    _raise(lambda: asyncio.run(require_login(1)), 1008)
    use_scope("ALL", uid=1)
    assert asyncio.run(require_login(1)) == 1
    ctx.reset()
    _raise(lambda: asyncio.run(require_any_permission(["ims:corp:company:query"])(1)), 1008)
    _raise(lambda: asyncio.run(require_all_permissions(["ims:corp:company:query"])(1)), 1008)
    _raise(lambda: asyncio.run(require_data_scope("OrgCompany")(1)), 1008)
    ctx.set(RequestContext(user_id=1, tenant_id=1, perm_codes=set(), data_scopes=[DataScope("ALL", 1)]))
    _raise(lambda: asyncio.run(require_any_permission(["ims:corp:company:query"])(1)), 1008)
    _raise(lambda: asyncio.run(require_all_permissions(["ims:corp:company:query"])(1)), 1008)
    use_scope("ALL", uid=1)
    assert asyncio.run(require_any_permission(["ims:corp:company:query"])(1)) == 1
    assert asyncio.run(require_all_permissions(["ims:corp:company:query"])(1)) == 1
    checker = PermissionChecker(read_perm="ims:a", write_perm="ims:b", delete_perm="ims:c")
    use_scope("ALL", uid=1, perms={"ims:a"})
    assert asyncio.run(checker.read(1)) == 1
    _raise(lambda: asyncio.run(checker.write(1)), 1008)
    _raise(lambda: asyncio.run(checker.delete(1)), 1008)
    use_scope("ALL", uid=1, perms={"ims:b", "ims:c"})
    assert asyncio.run(checker.write(1)) == 1
    assert asyncio.run(checker.delete(1)) == 1

    role_service = RoleService()
    assert asyncio.run(role_service.get_role_by_id(404)) is None
    _raise(lambda: asyncio.run(role_service.validate_role_exists(404)), 1500)
    b5.add(Role(
        id=910, tenant_id=1, role_key="branch910", name="分支角色",
        source="MANUAL", status="ENABLED", data_scope="ALL",
    ))
    b5.flush()
    found = asyncio.run(role_service.get_role_by_id(910))
    assert found["role_key"] == "branch910"
    assert asyncio.run(role_service.validate_role_exists(910)) is True
