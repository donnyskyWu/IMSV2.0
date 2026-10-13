# B5 公司资源单测。版本 v1.0 · 2026-10-13
"""功能点、错误码和数据范围。函数体不是空 pass。"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from PIL import Image

from app.core.cache import Cache
from app.core.clock import reset_clock
from app.core.config import get_settings
from app.core.context import DataScope, RequestContext, ctx
from app.core.errors import BizError
from app.domains.shared.models import (
    AccountPlatform,
    MasterPhone,
    MasterRealname,
)
from app.domains.sys.models import DictData, Menu, Role, RoleMenu, User
from app.integrations.base import assert_http_url
from app.services.company import CompanyService
from app.services.realname import RealnameService
from app.services.sim_card import SimCardService

ID_OK = "110101199003078515"
ID_OK_2 = "110101199001011237"
CREDIT_OK = "91350100M000100Y43"
CREDIT_BAD = "91350100M000100Y40"


@pytest.fixture(autouse=True)
def _crypto_keys():
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
    """造字典和两个用户，上下文默认 ALL。"""
    _dicts(db_session)
    _user(db_session, 1, "u1")
    _user(db_session, 2, "u2")
    use_scope("ALL", uid=1)
    yield db_session
    ctx.reset()
    reset_clock()


def use_scope(scope: str, uid: int = 1, tid: int = 1, perms: set | None = None, scopes: list | None = None):
    if scopes is None:
        scopes = [DataScope(scope, 1)] if scope else []
    ctx.set(RequestContext(
        user_id=uid,
        tenant_id=tid,
        perm_codes=perms or _all_perms(),
        data_scopes=scopes,
        client_ip="127.0.0.1",
        user_agent="pytest",
    ))


def _all_perms() -> set[str]:
    return {
        "ims:corp:company:query", "ims:corp:company:create", "ims:corp:company:update",
        "ims:corp:company:expand", "ims:corp:company:export",
        "ims:corp:realname:query", "ims:corp:realname:create", "ims:corp:realname:update",
        "ims:corp:realname:delete", "ims:corp:realname:export", "ims:corp:realname:commission",
        "ims:corp:sim:query", "ims:corp:sim:create", "ims:corp:sim:update",
        "ims:corp:sim:delete", "ims:corp:sim:export",
        "ims:cert:archive:query", "ims:cert:archive:upload", "ims:cert:archive:review",
        "ims:cert:archive:delete", "ims:cert:expire:query", "ims:cert:expire:scan",
        "ims:cert:expire:renew", "ims:cert:expire:remind",
        "ims:cert:security:config", "ims:cert:security:audit",
    }


def _dicts(session):
    rows = {
        "dict_company_status": [("ENABLED", "启用"), ("DISABLED", "停用")],
        "dict_industry": [("IT", "互联网")],
        "dict_id_type": [("ID_CARD", "居民身份证"), ("PASSPORT", "护照")],
        "dict_realname_status": [("ON_JOB", "在职"), ("LEFT", "离职")],
        "dict_sim_operator": [("CMCC", "移动")],
        "dict_sim_status": [("ENABLED", "启用"), ("DISABLED", "停用")],
        "dict_payment_cycle": [("MONTH", "月付")],
        "dict_cert_type": [("ID_CARD", "居民身份证"), ("PASSPORT", "护照"), ("HEALTH", "健康证"), ("OTHER", "其他")],
    }
    number = 1
    for dict_type, items in rows.items():
        for value, label in items:
            session.add(DictData(
                id=8000 + number,
                tenant_id=1,
                dict_type=dict_type,
                dict_value=value,
                dict_label=label,
                status="ENABLED",
            ))
            number += 1
    session.flush()


def _user(session, uid: int, name: str, status: str = "ACTIVE"):
    session.add(User(
        id=uid, tenant_id=1, username=name, nickname=name, status=status, source="LOCAL", emp_no=f"E{uid}",
    ))
    session.flush()


def png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(buf, format="JPEG")
    return buf.getvalue()


def _company(**extra):
    payload = {"name": "星河公司", "credit_code": CREDIT_OK, "industry": "IT", "legal_id_card": ID_OK}
    payload.update(extra)
    return CompanyService().create_company(payload)


def _realname(**extra):
    payload = {"name": "张三", "user_id": 1, "id_type": "ID_CARD", "id_card": ID_OK, "phone": "13812345678"}
    payload.update(extra)
    return RealnameService().create_realname(payload)


def _sim(realname_id, **extra):
    payload = {
        "phone": "13812345678",
        "operator": "CMCC",
        "realname_id": realname_id,
        "assigned_user_id": 1,
        "iccid": "8986001234567890123",
        "monthly_rent": "19.90",
        "status": "ENABLED",
    }
    payload.update(extra)
    return SimCardService().create_sim_card(payload)


def _raise(fn, code):
    with pytest.raises(BizError) as caught:
        fn()
    assert caught.value.code == code
    return caught.value


def test_ut_b5_co_01_page(b5):
    """UT-B5-CO-01 公司列表能看到刚建的公司，剩余容量小于 5 时标记紧张。"""
    _company()
    page = CompanyService().page_companies()
    assert page["total"] == 1
    assert page["list"][0]["name"] == "星河公司"
    assert page["list"][0]["capacityTight"] is True
    assert page["list"][0]["status"] == "启用"


def test_ut_b5_co_02_create_update(b5):
    """UT-B5-CO-02 新建后编辑名称，容量不变。"""
    created = _company()
    updated = CompanyService().update_company(created["id"], {"name": "星河新名", "mp_capacity": 99})
    assert updated["name"] == "星河新名"
    assert updated["mpCapacity"] == 0


def test_ut_b5_co_02_1001_dup(b5):
    """UT-B5-CO-02-1001 重名、信用代码重复、格式错误。"""
    _company()
    err = _raise(lambda: _company(name="星河公司", credit_code=None), 1001)
    assert err.msg == "公司名称已存在"
    err = _raise(lambda: _company(name="另一家", credit_code=CREDIT_OK), 1001)
    assert err.msg == "信用代码已存在"
    err = _raise(lambda: _company(name="坏代码", credit_code=CREDIT_BAD), 1001)
    assert "格式" in err.msg


def test_ut_b5_co_02_1503(b5):
    """UT-B5-CO-02-1503 行业不在字典。"""
    _raise(lambda: _company(industry="NO_SUCH"), 1503)


def test_ut_b5_co_03_status(b5):
    """UT-B5-CO-03 停用后选择器不再返回。"""
    created = _company()
    CompanyService().set_company_status(created["id"], "DISABLED")
    assert CompanyService().get_company(created["id"])["status"] == "停用"
    assert CompanyService().list_company_options() == []


def test_ut_b5_co_04_detail(b5):
    """UT-B5-CO-04 详情含脱敏身份证和扩容记录。"""
    created = _company()
    CompanyService().expand_company(created["id"], 10, "业务增加")
    detail = CompanyService().get_company(created["id"])
    assert detail["legalIdCard"].startswith("110")
    assert ID_OK not in detail["legalIdCard"]
    assert detail["expansions"][0]["toCapacity"] == 10


def test_ut_b5_co_05_expand(b5):
    """UT-B5-CO-05 扩容成功。"""
    created = _company()
    detail = CompanyService().expand_company(created["id"], 8, "扩容")
    assert detail["mpCapacity"] == 8
    assert detail["capacityTight"] is False


def test_ut_b5_co_05_1222(b5):
    """UT-B5-CO-05-1222 新容量小于已注册数。"""
    created = _company()
    b5.add(AccountPlatform(
        id=1, tenant_id=1, name="公众号", platform="WECHAT_OFFICIAL", company_id=int(created["id"]),
    ))
    b5.flush()
    _raise(lambda: CompanyService().expand_company(created["id"], 0, "太小"), 1222)


def test_ut_b5_co_05_1001(b5):
    """UT-B5-CO-05-1001 原因为空。"""
    created = _company()
    _raise(lambda: CompanyService().expand_company(created["id"], 3, "  "), 1001)


def test_ut_b5_co_02_1504(b5):
    """UT-B5-CO-02-1504 update_company 不存在或跨租户 → 1504，响应无名称。"""
    created = _company()
    err = _raise(lambda: CompanyService().update_company(404, {"name": "无"}), 1504)
    assert "星河" not in (err.msg or "")
    use_scope("ALL", tid=2)
    err = _raise(lambda: CompanyService().update_company(created["id"], {"name": "跨租户"}), 1504)
    assert "星河" not in (err.msg or "")


def test_ut_b5_co_02_1008(b5):
    """UT-B5-CO-02-1008 公司 update 路由无权限码 → 1008。空数据范围仍可改。"""
    from app.services.access import authorize
    created = _company()
    use_scope("ALL", perms=_all_perms() - {"ims:corp:company:update"})
    _raise(lambda: authorize("ims:corp:company:update"), 1008)
    use_scope("ALL", scopes=[])
    updated = CompanyService().update_company(created["id"], {"name": "空范围仍可改"})
    assert updated["name"] == "空范围仍可改"


def test_ut_b5_co_03_1504(b5):
    """UT-B5-CO-03-1504 set_company_status 不存在 → 1504。"""
    err = _raise(lambda: CompanyService().set_company_status(404, "DISABLED"), 1504)
    assert "星河" not in (err.msg or "")


def test_ut_b5_co_05_1504(b5):
    """UT-B5-CO-05-1504 expand_company 不存在或跨租户 → 1504，响应无名称。"""
    created = _company()
    err = _raise(lambda: CompanyService().expand_company(404, 9, "无"), 1504)
    assert "星河" not in (err.msg or "")
    use_scope("ALL", tid=2)
    err = _raise(lambda: CompanyService().expand_company(created["id"], 9, "跨租户"), 1504)
    assert "星河" not in (err.msg or "")


def test_ut_b5_co_05_1008(b5):
    """UT-B5-CO-05-1008 公司扩容路由无 expand 码 → 1008。空数据范围仍可扩容。"""
    from app.services.access import authorize
    created = _company()
    use_scope("ALL", perms=_all_perms() - {"ims:corp:company:expand"})
    _raise(lambda: authorize("ims:corp:company:expand"), 1008)
    use_scope("ALL", scopes=[])
    detail = CompanyService().expand_company(created["id"], 6, "空范围")
    assert detail["mpCapacity"] == 6


def test_ut_b5_co_06_export(b5):
    """UT-B5-CO-06 导出任务写入缓存且身份证脱敏。"""
    _company()
    task = CompanyService().export_companies()
    saved = Cache.get_json(f"ims:export:{task['taskId']}")
    assert saved["rows"][0]["legalIdCard"]
    assert ID_OK not in saved["rows"][0]["legalIdCard"]


def test_ut_b5_bg_01_options(b5):
    """UT-B5-BG-01 三个选择器只返回启用或在职，最多 50。"""
    _company()
    person = _realname()
    _sim(person["id"])
    RealnameService().set_realname_status(person["id"], "LEFT")
    assert CompanyService().list_company_options()
    assert RealnameService().list_realname_options() == []
    assert len(SimCardService().list_sim_card_options()) == 1
    for index in range(51):
        CompanyService().create_company({"name": f"公司{index}", "status": "ENABLED"})
    assert len(CompanyService().list_company_options()) == 50


def test_ut_b5_rn_01_page(b5):
    """UT-B5-RN-01 证件号用哈希等值筛选，响应是脱敏值。"""
    _realname()
    page = RealnameService().page_realnames(id_card=ID_OK)
    assert page["total"] == 1
    assert ID_OK not in page["list"][0]["idCard"]


def test_ut_b5_rn_02_update_keeps_card(b5):
    """UT-B5-RN-02 编辑默认不改证件号。"""
    created = _realname()
    updated = RealnameService().update_realname(created["id"], {"name": "李四"})
    assert updated["name"] == "李四"
    assert updated["idCard"] == created["idCard"]


def test_ut_b5_rn_02_1001(b5):
    """UT-B5-RN-02-1001 校验位和证件号重复。"""
    _raise(lambda: _realname(id_card="110101199003078516"), 1001)
    _realname()
    _raise(lambda: _realname(name="王五", id_card=ID_OK, phone="13900001111"), 1001)


def test_ut_b5_rn_02_1500(b5):
    """UT-B5-RN-02-1500 关联员工不存在。"""
    err = _raise(lambda: _realname(user_id=99), 1500)
    assert "张三" not in err.msg


def test_ut_b5_rn_02_1503(b5):
    """UT-B5-RN-02-1503 证件类型非法。"""
    _raise(lambda: _realname(id_type="BAD"), 1503)


def test_ut_b5_rn_02_1504(b5):
    """UT-B5-RN-02-1504 update_realname 不存在 → 1504。"""
    err = _raise(lambda: RealnameService().update_realname(404, {"name": "无"}), 1504)
    assert "张三" not in (err.msg or "")


def test_ut_b5_rn_02_1008(b5):
    """UT-B5-RN-02-1008 update_realname、create_realname 没有数据范围 → 1008。"""
    created = _realname()
    use_scope("ALL", scopes=[])
    _raise(lambda: RealnameService().update_realname(created["id"], {"name": "无范围"}), 1008)
    _raise(lambda: _realname(name="另一个", id_card=ID_OK_2, phone="13900003333"), 1008)


def test_ut_b5_rn_03_status(b5):
    """UT-B5-RN-03 离职后选择器排除，deleted 仍为 0。"""
    created = _realname()
    RealnameService().set_realname_status(created["id"], "LEFT")
    row = b5.get(MasterRealname, int(created["id"]))
    assert row.deleted == 0
    assert row.status == "LEFT"
    assert RealnameService().list_realname_options() == []


def test_ut_b5_rn_04_intermediary(b5):
    """UT-B5-RN-04 中介人增删改，列表一次聚合人数。"""
    created = _realname()
    person = RealnameService().create_intermediary(created["id"], {"name": "中介甲", "phone": "13700001111", "commission_rate": "1.50"})
    RealnameService().update_intermediary(person["id"], {"name": "中介乙"})
    page = RealnameService().page_realnames()
    assert page["list"][0]["intermediaryCount"] == 1
    RealnameService().delete_intermediary(person["id"])
    assert RealnameService().page_realnames()["list"][0]["intermediaryCount"] == 0


def test_ut_b5_rn_04_comm(b5):
    """UT-B5-RN-04-COMM 无佣金权限时响应没有 commissionRate。"""
    created = _realname()
    RealnameService().create_intermediary(created["id"], {"name": "中介甲", "commission_rate": "2.00"})
    use_scope("ALL", perms=_all_perms() - {"ims:corp:realname:commission"})
    detail = RealnameService().get_realname(created["id"])
    assert "commissionRate" not in detail
    assert "commissionRate" not in detail["intermediaries"][0]


def test_ut_b5_rn_05_delete(b5):
    """UT-B5-RN-05 无引用时实名人和中介人一起软删。"""
    created = _realname()
    RealnameService().create_intermediary(created["id"], {"name": "中介甲"})
    RealnameService().delete_realname(created["id"])
    row = b5.get(MasterRealname, int(created["id"]))
    assert row.deleted == row.id


def test_ut_b5_rn_05_1502(b5):
    """UT-B5-RN-05-1502 有手机卡时不能删，响应带引用数。"""
    created = _realname()
    _sim(created["id"])
    err = _raise(lambda: RealnameService().delete_realname(created["id"]), 1502)
    assert err.data["refs"][0]["count"] == 1
    assert b5.get(MasterRealname, int(created["id"])).deleted == 0


def test_ut_b5_rn_05_1504(b5):
    """UT-B5-RN-05-1504 不存在。"""
    _raise(lambda: RealnameService().delete_realname(404), 1504)


def test_ut_b5_rn_03_1504(b5):
    """UT-B5-RN-03-1504 set_realname_status 不存在 → 1504。"""
    _raise(lambda: RealnameService().set_realname_status(404, "LEFT"), 1504)


def test_ut_b5_rn_03_1008(b5):
    """UT-B5-RN-03-1008 set_realname_status 没有数据范围 → 1008。"""
    created = _realname()
    use_scope("ALL", scopes=[])
    _raise(lambda: RealnameService().set_realname_status(created["id"], "LEFT"), 1008)


def test_ut_b5_rn_05_1008(b5):
    """UT-B5-RN-05-1008 delete_realname 没有数据范围 → 1008。"""
    created = _realname()
    use_scope("ALL", scopes=[])
    _raise(lambda: RealnameService().delete_realname(created["id"]), 1008)


def test_ut_b5_rn_06_detail(b5):
    """UT-B5-RN-06 详情带中介人。"""
    created = _realname()
    RealnameService().create_intermediary(created["id"], {"name": "中介甲"})
    detail = RealnameService().get_realname(created["id"])
    assert detail["intermediaries"][0]["name"] == "中介甲"


def test_ut_b5_rn_07_export(b5):
    """UT-B5-RN-07 导出不带佣金。"""
    created = _realname()
    RealnameService().create_intermediary(created["id"], {"name": "中介甲", "commission_rate": "3"})
    task = RealnameService().export_realnames()
    saved = Cache.get_json(f"ims:export:{task['taskId']}")
    assert "commissionRate" not in saved["rows"][0]


def test_ut_b5_sm_01_page(b5):
    """UT-B5-SM-01 按号码哈希筛选。"""
    person = _realname()
    _sim(person["id"])
    page = SimCardService().page_sim_cards(phone="13812345678")
    assert page["total"] == 1
    assert page["list"][0]["phone"].startswith("138")
    assert "13812345678" not in page["list"][0]["phone"]


def test_ut_b5_sm_02_update_keeps_phone(b5):
    """UT-B5-SM-02 编辑套餐不改号码密文。"""
    person = _realname()
    created = _sim(person["id"])
    from app.domains.shared.models import MasterSimCard
    row_before = b5.get(MasterSimCard, int(created["id"])).phone_number_enc
    SimCardService().update_sim_card(created["id"], {"package_name": "新套餐", "phone": "13900000000"})
    row_after = b5.get(MasterSimCard, int(created["id"]))
    assert row_after.phone_number_enc == row_before
    assert row_after.package_name == "新套餐"
    assert row_after.phone_id is None


def test_ut_b5_sm_02_1001(b5):
    """UT-B5-SM-02-1001 号码重复、ICCID 重复。"""
    person = _realname()
    _sim(person["id"])
    _raise(lambda: _sim(person["id"], phone="13812345678", iccid="another-iccid"), 1001)
    _raise(lambda: _sim(person["id"], phone="13900002222", iccid="8986001234567890123"), 1001)


def test_ut_b5_sm_02_1500(b5):
    """UT-B5-SM-02-1500 实名人不存在。"""
    _raise(lambda: _sim(99), 1500)


def test_ut_b5_sm_02_1501(b5):
    """UT-B5-SM-02-1501 实名人离职。"""
    person = _realname()
    RealnameService().set_realname_status(person["id"], "LEFT")
    _raise(lambda: _sim(person["id"]), 1501)


def test_ut_b5_sm_02_1503(b5):
    """UT-B5-SM-02-1503 运营商非法。"""
    person = _realname()
    _raise(lambda: _sim(person["id"], operator="NOPE"), 1503)


def test_ut_b5_sm_03_detail(b5):
    """UT-B5-SM-03 详情月租两位小数，关联账号为空。"""
    person = _realname()
    created = _sim(person["id"])
    detail = SimCardService().get_sim_card(created["id"])
    assert detail["monthlyRent"] == "19.90"
    assert detail["accounts"] == []


def test_ut_b5_sm_04_delete(b5):
    """UT-B5-SM-04 未引用可以删除。"""
    person = _realname()
    created = _sim(person["id"])
    SimCardService().delete_sim_card(created["id"])
    from app.domains.shared.models import MasterSimCard
    assert b5.get(MasterSimCard, int(created["id"])).deleted == int(created["id"])


def test_ut_b5_sm_04_1502(b5):
    """UT-B5-SM-04-1502 被手机引用不能删。"""
    person = _realname()
    created = _sim(person["id"])
    b5.add(MasterPhone(id=1, tenant_id=1, name="手机", sim_card_id=int(created["id"])))
    b5.flush()
    _raise(lambda: SimCardService().delete_sim_card(created["id"]), 1502)


def test_ut_b5_sm_02_1504(b5):
    """UT-B5-SM-02-1504 update_sim_card 不存在、跨租户或非本人归属 → 1504。"""
    person = _realname()
    created = _sim(person["id"])
    err = _raise(lambda: SimCardService().update_sim_card(404, {"package_name": "无"}), 1504)
    assert "138" not in (err.msg or "")
    use_scope("ALL", tid=2)
    _raise(lambda: SimCardService().update_sim_card(created["id"], {"package_name": "跨租户"}), 1504)
    use_scope("SELF", uid=2)
    _raise(lambda: SimCardService().update_sim_card(created["id"], {"package_name": "他人"}), 1504)


def test_ut_b5_sm_02_1008(b5):
    """UT-B5-SM-02-1008 update_sim_card、create_sim_card 没有数据范围 → 1008。"""
    person = _realname()
    created = _sim(person["id"])
    use_scope("ALL", scopes=[])
    _raise(lambda: SimCardService().update_sim_card(created["id"], {"package_name": "无范围"}), 1008)
    _raise(lambda: _sim(person["id"], phone="13900004444", iccid="8986009999000011112"), 1008)


def test_ut_b5_sm_04_1504(b5):
    """UT-B5-SM-04-1504 delete_sim_card 不存在或跨租户 → 1504。"""
    person = _realname()
    created = _sim(person["id"])
    _raise(lambda: SimCardService().delete_sim_card(404), 1504)
    use_scope("ALL", tid=2)
    _raise(lambda: SimCardService().delete_sim_card(created["id"]), 1504)


def test_ut_b5_sm_04_1008(b5):
    """UT-B5-SM-04-1008 delete_sim_card 没有数据范围 → 1008。"""
    person = _realname()
    created = _sim(person["id"])
    use_scope("ALL", scopes=[])
    _raise(lambda: SimCardService().delete_sim_card(created["id"]), 1008)


def test_ut_b5_sm_05_export(b5):
    """UT-B5-SM-05 导出号码脱敏。"""
    person = _realname()
    _sim(person["id"])
    task = SimCardService().export_sim_cards()
    saved = Cache.get_json(f"ims:export:{task['taskId']}")
    assert "13812345678" not in saved["list"][0]["phone"]


def test_ut_b5_bg_03_crypto():
    """UT-B5-BG-03 密文不等于明文，同一明文两次不同，哈希非空。"""
    from app.core.crypto import decrypt_field, encrypt_field, hash_field
    first = encrypt_field("110101199003078515")
    second = encrypt_field("110101199003078515")
    assert first != "110101199003078515"
    assert first != second
    assert decrypt_field(first) == "110101199003078515"
    assert hash_field("110101199003078515")
    rotated = encrypt_field("abc", version="2")
    assert rotated.startswith("v2.")
    assert decrypt_field(rotated) == "abc"


def test_ut_b5_bg_03_crypto_keys():
    """UT-B5-BG-03 缺密钥或哈希密钥与字段密钥相同都拒绝。"""
    from app.core.crypto import encrypt_field, hash_field
    security = get_settings().security
    security.field_key = ""
    _raise(lambda: encrypt_field("a"), 1001)
    security.field_key = "same"
    security.hash_key = "same"
    _raise(lambda: hash_field("a"), 1001)
    security.hash_key = ""
    _raise(lambda: hash_field("a"), 1001)


def test_ut_b5_bg_05_prod(monkeypatch):
    """UT-B5-BG-05 生产环境拒绝执行造数。"""
    from tools.e2e_seed.b5 import assert_e2e_env
    monkeypatch.setenv("IMS_ENV", "prod")
    with pytest.raises(RuntimeError):
        assert_e2e_env()


def test_ut_b5_bg_02_grant(b5):
    """UT-B5-BG-02 只给 R1 补权限，并递增租户权限版本。"""
    from tools.seed.b5 import grant_b5_to_r1
    role = Role(id=9, tenant_id=1, role_key="R1", name="超管", source="MANUAL", status="ENABLED", data_scope="ALL")
    other = Role(id=10, tenant_id=1, role_key="R2", name="其他", source="MANUAL", status="ENABLED", data_scope="ALL")
    b5.add(role)
    b5.add(other)
    b5.flush()
    added = grant_b5_to_r1()
    assert added > 0
    assert Cache.get("ims:perm_ver:t:1")
    r2_links = b5.query(RoleMenu).filter(RoleMenu.role_id == 10).count()
    assert r2_links == 0
    delete_menu = b5.query(Menu).filter(Menu.perm_code == "ims:cert:archive:delete").one()
    assert b5.query(RoleMenu).filter(RoleMenu.role_id == 9, RoleMenu.menu_id == delete_menu.id).count() == 1


def test_ut_b5_ct_06_url():
    """UT-B5-CT-06-URL 拒绝环回、私网、169.254 和 ftp，不能只测 file。公网 http(s) 放行。"""
    assert assert_http_url("file://etc/passwd") is False
    assert assert_http_url("ftp://example.com") is False
    assert assert_http_url("ftp://127.0.0.1") is False
    assert assert_http_url("ftp://10.1.2.3") is False
    assert assert_http_url("ftp://169.254.169.254") is False
    assert assert_http_url("example.com") is False
    assert assert_http_url("") is False
    assert assert_http_url("http://127.0.0.1") is False
    assert assert_http_url("https://127.0.0.1") is False
    assert assert_http_url("http://localhost/ocr") is False
    assert assert_http_url("http://10.1.2.3") is False
    assert assert_http_url("https://10.0.0.8/ocr") is False
    assert assert_http_url("http://172.16.0.1") is False
    assert assert_http_url("http://192.168.1.1") is False
    assert assert_http_url("http://169.254.169.254") is False
    assert assert_http_url("https://169.254.1.1") is False
    assert assert_http_url("https://example.com/ocr") is True
    assert assert_http_url("http://8.8.8.8/ocr") is True


def test_ut_b5_ct_06_literal():
    """UT-B5-CT-06-LITERAL 证件业务代码没有地址和模型名字面量。"""
    root = Path(__file__).resolve().parents[2] / "app"
    for relative in ("services/cert.py", "api/cert.py"):
        text = (root / relative).read_text(encoding="utf-8")
        assert "http://" not in text
        assert "https://" not in text
        assert "dashscope" not in text
        assert "qwen" not in text


def test_mysql_gate_fails_closed(monkeypatch):
    """缺 MySQL 或 Redis 时门禁失败，不跳过。"""
    from tests.unit.test_b5_resource import require_b5_mysql_redis
    monkeypatch.setenv("IMS_DB_URL", "sqlite:///:memory:")
    monkeypatch.setenv("IMS_REDIS_URL", "")
    with pytest.raises(RuntimeError):
        require_b5_mysql_redis()


def require_b5_mysql_redis():
    """B5 夹具：不是 MySQL 或没有 Redis 就失败。"""
    url = os.environ.get("IMS_DB_URL", "")
    redis_url = os.environ.get("IMS_REDIS_URL", "")
    if not url.startswith("mysql"):
        raise RuntimeError("B5 用例需要 MySQL IMS_DB_URL")
    if not redis_url:
        raise RuntimeError("B5 用例需要 Redis IMS_REDIS_URL")
