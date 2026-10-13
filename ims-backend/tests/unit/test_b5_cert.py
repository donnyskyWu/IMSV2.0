# B5 证件、范围和鉴权单测。版本 v1.0 · 2026-10-13
"""上传、审核、查看、到期和 verify_token 闸门。"""

from __future__ import annotations

from datetime import datetime, timedelta

import jwt
import pytest

from app.core.cache import Cache
from app.core.clock import BEIJING_TZ, get_now, set_clock
from app.core.config import get_settings
from app.core.errors import BizError
from app.domains.corp.models import CertExpireTask, CertL3Whitelist, CertLevelRule, CertViewLog
from app.domains.shared.models import MasterCert
from app.domains.sys.models import (
    InboxMessage,
    Menu,
    Role,
    RoleMenu,
    Tenant,
    TodoItem,
    User,
    UserRole,
)
from app.services.cert import CertService, cert_is_locked
from app.services.cert_expire import CertExpireService, apply_test_clock, scan_cert_expire
from app.services.cert_file import apply_watermark, validate_cert_file
from app.services.cert_security import resolve_preview, sign_preview_url
from app.services.company import CompanyService
from app.services.realname import RealnameService
from app.services.sim_card import SimCardService
from tests.unit.test_b5_resource import (
    CREDIT_OK,
    ID_OK,
    _all_perms,
    _dicts,
    _raise,
    _realname,
    _sim,
    _user,
    jpeg_bytes,
    png_bytes,
    use_scope,
)

PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


@pytest.fixture(autouse=True)
def _crypto_keys():
    security = get_settings().security
    train = get_settings().train_ai
    old = (security.field_key, security.hash_key, train.mode, train.base_url, train.enabled)
    security.field_key = "b5-field-key"
    security.hash_key = "b5-hash-key"
    yield
    security.field_key, security.hash_key = old[0], old[1]
    train.mode, train.base_url, train.enabled = old[2], old[3], old[4]


@pytest.fixture
def b5(db_session):
    _dicts(db_session)
    _user(db_session, 1, "u1")
    _user(db_session, 2, "u2")
    use_scope("ALL", uid=2, perms=_all_perms() - {"ims:cert:archive:upload"})
    # 上传人是 1，审核人是 2，避免自审。
    use_scope("ALL", uid=1)
    yield db_session


def _upload(**extra):
    person = extra.pop("person", None) or _realname()
    payload = {
        "holder_type": "REALNAME",
        "realname_id": person["id"],
        "cert_type": "ID_CARD",
        "cert_no": ID_OK,
        "issue_date": "2020-01-01",
        "expire_date": "2030-01-01",
    }
    payload.update(extra)
    return CertService().upload_cert(payload, "card.png", "image/png", png_bytes()), person


def test_ut_b5_ct_01_list_and_metrics(b5):
    """UT-B5-CT-01 列表和数字化率。离职、软删证件不进分母分子。"""
    created, person = _upload()
    use_scope("ALL", uid=2)
    CertService().review_cert(created["id"], True, "")
    left = RealnameService().create_realname({
        "name": "离职人", "user_id": 2, "id_type": "PASSPORT", "id_card": "P123", "phone": "13900001111",
    })
    RealnameService().set_realname_status(left["id"], "LEFT")
    metrics = CertService().digital_metrics()
    assert metrics["total"] == 1
    assert metrics["covered"] == 1
    assert CertService().list_certs()["total"] >= 1


def test_ut_b5_ct_01_query_self(b5):
    """UT-B5-CT-01-QUERY-SELF 仅 query-self 且角色 ALL 仍只有本人证件。"""
    own, _person = _upload()
    use_scope("ALL", uid=2)
    RealnameService().create_realname({
        "name": "他人", "user_id": 2, "id_type": "ID_CARD", "id_card": "110101199001011237", "phone": "13900002222",
    })
    other_person = RealnameService().page_realnames(name="他人")["list"][0]
    use_scope("ALL", uid=2)
    CertService().upload_cert({
        "holder_type": "REALNAME",
        "realname_id": other_person["id"],
        "cert_type": "PASSPORT",
        "cert_no": "P999",
        "issue_date": "2020-01-01",
        "expire_date": "2030-01-01",
    }, "p.png", "image/png", png_bytes())
    use_scope("ALL", uid=1, perms={"ims:cert:archive:query-self"})
    listed = CertService().list_certs()
    assert listed["total"] == 1
    assert listed["list"][0]["id"] == own["id"]


def test_ut_b5_ct_02_upload(b5):
    """UT-B5-CT-02 上传后待审，版本为 1。"""
    created, _person = _upload()
    assert created["status"] == "PENDING_REVIEW"
    assert created["version"] == 1
    assert ID_OK not in created["certNo"]


def test_ut_b5_ct_02_1001(b5):
    """UT-B5-CT-02-1001 有效期和身份证校验位。"""
    person = _realname()
    _raise(lambda: CertService().upload_cert({
        "holder_type": "REALNAME", "realname_id": person["id"], "cert_type": "ID_CARD",
        "cert_no": ID_OK, "issue_date": "2030-01-01", "expire_date": "2020-01-01",
    }, "a.png", "image/png", png_bytes()), 1001)
    _raise(lambda: CertService().upload_cert({
        "holder_type": "REALNAME", "realname_id": person["id"], "cert_type": "ID_CARD",
        "cert_no": "110101199003078516", "issue_date": "2020-01-01", "expire_date": "2030-01-01",
    }, "a.png", "image/png", png_bytes()), 1001)


def test_ut_b5_ct_02_1032(b5):
    """UT-B5-CT-02-1032 已有待审档案不能再传。"""
    created, person = _upload()
    _raise(lambda: CertService().upload_cert({
        "holder_type": "REALNAME", "realname_id": person["id"], "cert_type": "ID_CARD",
        "cert_no": ID_OK, "issue_date": "2021-01-01", "expire_date": "2031-01-01",
    }, "b.png", "image/png", png_bytes()), 1032)
    _ = created


def test_ut_b5_ct_02_1500(b5):
    """UT-B5-CT-02-1500 实名人不存在。"""
    _raise(lambda: CertService().upload_cert({
        "holder_type": "REALNAME", "realname_id": 99, "cert_type": "PASSPORT", "cert_no": "P1",
        "issue_date": "2020-01-01", "expire_date": "2030-01-01",
    }, "a.png", "image/png", png_bytes()), 1500)


def test_ut_b5_ct_02_1501(b5):
    """UT-B5-CT-02-1501 实名人离职。"""
    person = _realname()
    RealnameService().set_realname_status(person["id"], "LEFT")
    _raise(lambda: CertService().upload_cert({
        "holder_type": "REALNAME", "realname_id": person["id"], "cert_type": "PASSPORT", "cert_no": "P1",
        "issue_date": "2020-01-01", "expire_date": "2030-01-01",
    }, "a.png", "image/png", png_bytes()), 1501)


def test_ut_b5_ct_02_1503(b5):
    """UT-B5-CT-02-1503 证件类型非法。"""
    person = _realname()
    _raise(lambda: CertService().upload_cert({
        "holder_type": "REALNAME", "realname_id": person["id"], "cert_type": "BAD", "cert_no": "P1",
    }, "a.png", "image/png", png_bytes()), 1503)


def test_ut_b5_ct_02_5005(b5):
    """UT-B5-CT-02-5005-EXT UT-B5-CT-02-5005-MIME UT-B5-CT-02-5005-MAGIC UT-B5-CT-02-5005-SIZE"""
    _raise(lambda: validate_cert_file("a.exe", "image/png", png_bytes()), 5005)
    _raise(lambda: validate_cert_file("a.png", "text/plain", png_bytes()), 5005)
    _raise(lambda: validate_cert_file("a.png", "image/png", b"not-png"), 5005)
    huge = jpeg_bytes() + b"0" * (20 * 1024 * 1024)
    _raise(lambda: validate_cert_file("a.jpg", "image/jpeg", huge), 5005)
    assert validate_cert_file("a.pdf", "application/pdf", PDF) == ".pdf"


def test_ut_b5_ct_03_review(b5):
    """UT-B5-CT-03 他人审核通过后生效。"""
    created, _person = _upload()
    use_scope("ALL", uid=2)
    reviewed = CertService().review_cert(created["id"], True, "通过")
    assert reviewed["status"] == "EFFECTIVE"


def test_ut_b5_ct_03_1033(b5):
    """UT-B5-CT-03-1033 非待审不能再审。"""
    created, _person = _upload()
    use_scope("ALL", uid=2)
    CertService().review_cert(created["id"], True, "")
    _raise(lambda: CertService().review_cert(created["id"], False, "再拒"), 1033)


def test_ut_b5_ct_03_1008(b5):
    """UT-B5-CT-03-1008 上传人不能审自己。"""
    created, _person = _upload()
    _raise(lambda: CertService().review_cert(created["id"], True, ""), 1008)


def test_ut_b5_ct_03_1504(b5):
    """UT-B5-CT-03-1504 不存在。"""
    use_scope("ALL", uid=2)
    _raise(lambda: CertService().review_cert(404, True, ""), 1504)


def test_ut_b5_ct_04_view_levels(b5):
    """UT-B5-CT-04 UT-B5-CT-04-1033 UT-B5-CT-04-1034 L1 拒绝，待审写 REJECTED_1033。"""
    created, _person = _upload()
    use_scope("ALL", uid=2)
    _raise(lambda: CertService().view_cert(created["id"]), 1033)
    log = b5.query(CertViewLog).filter(CertViewLog.cert_id == int(created["id"])).one()
    assert log.result == "REJECTED_1033"
    CertService().review_cert(created["id"], True, "")
    _raise(lambda: CertService().view_cert(created["id"]), 1034)
    b5.add(CertLevelRule(id=1, tenant_id=1, role_id=1, view_level=2))
    b5.flush()
    viewed = CertService().view_cert(created["id"])
    assert "previewUrl" in viewed
    assert "download" not in viewed
    assert ID_OK not in viewed["certNo"]
    b5.add(CertL3Whitelist(id=1, tenant_id=1, user_id=2))
    b5.flush()
    plain = CertService().view_cert(created["id"])
    assert plain["certNo"] == ID_OK
    assert plain["viewLevel"] == 3


def test_ut_b5_ct_04_1035(b5):
    """UT-B5-CT-04-1035 一小时内第 11 次拦截，白名单同样拦截。"""
    created, _person = _upload()
    use_scope("ALL", uid=2)
    CertService().review_cert(created["id"], True, "")
    b5.add(CertL3Whitelist(id=2, tenant_id=1, user_id=2))
    moment = datetime(2026, 10, 13, 9, 0, tzinfo=BEIJING_TZ)
    set_clock(lambda: moment)
    for index in range(10):
        b5.add(CertViewLog(
            id=100 + index, tenant_id=1, cert_id=int(created["id"]), viewer_user_id=2,
            view_level=3, result="OK", view_time=moment.replace(tzinfo=None),
        ))
    b5.flush()
    _raise(lambda: CertService().view_cert(created["id"]), 1035)


def test_ut_b5_ct_04_1504(b5):
    """UT-B5-CT-04-1504 跨租户查看没有证件号。"""
    created, _person = _upload()
    use_scope("ALL", uid=1, tid=2)
    err = _raise(lambda: CertService().view_cert(created["id"]), 1504)
    assert ID_OK not in err.msg
    assert "张三" not in (err.msg or "")


def test_ut_b5_ct_04_url(b5):
    """UT-B5-CT-04-URL 拨过 60 秒后预览地址失效。"""
    moment = datetime(2026, 10, 13, 9, 0, tzinfo=BEIJING_TZ)
    set_clock(lambda: moment)
    url = sign_preview_url("abc.png")
    token = url.rsplit("/", 1)[-1]
    assert resolve_preview(token)["fileKey"] == "abc.png"
    set_clock(lambda: moment + timedelta(seconds=61))
    _raise(lambda: resolve_preview(token), 1001)


def test_ut_b5_ct_05_get(b5):
    """UT-B5-CT-05 详情证件号脱敏。"""
    created, _person = _upload()
    detail = CertService().get_cert(created["id"])
    assert ID_OK not in detail["certNo"]


def test_ut_b5_ct_06_ocr(b5, monkeypatch):
    """UT-B5-CT-06 UT-B5-CT-06-FAIL 识别成功与失败都返回 code 语义。"""
    from app.domains.sys.models import StoredFile
    b5.add(StoredFile(
        id=1, tenant_id=1, scene="cert", file_key="mine.png", original_name="mine.png", uploader_id=1,
    ))
    b5.flush()
    settings = get_settings()
    settings.train_ai.mode = "mock"
    settings.train_ai.base_url = "https://example.com"
    settings.train_ai.enabled = True
    found = CertService().recognize_cert("mine.png")
    assert found["recognized"] is True
    assert found["certNo"] == ID_OK
    settings.train_ai.base_url = "http://127.0.0.1"
    assert CertService().recognize_cert("mine.png")["recognized"] is False
    settings.train_ai.base_url = "http://10.1.2.3"
    assert CertService().recognize_cert("mine.png")["recognized"] is False
    settings.train_ai.base_url = "https://169.254.169.254"
    assert CertService().recognize_cert("mine.png")["recognized"] is False
    settings.train_ai.base_url = "ftp://10.0.0.1"
    assert CertService().recognize_cert("mine.png")["recognized"] is False
    settings.train_ai.base_url = "file:///tmp/a"
    assert CertService().recognize_cert("mine.png")["recognized"] is False
    settings.train_ai.base_url = "https://example.com"
    settings.train_ai.mode = "timeout"
    assert CertService().recognize_cert("mine.png")["recognized"] is False
    settings.train_ai.mode = "fail"
    assert CertService().recognize_cert("mine.png")["recognized"] is False
    settings.train_ai.enabled = False
    assert CertService().recognize_cert("mine.png")["recognized"] is False


def test_ut_b5_ct_06_1001(b5):
    """UT-B5-CT-06-1001 文件不是本人上传。"""
    from app.domains.sys.models import StoredFile
    b5.add(StoredFile(
        id=2, tenant_id=1, scene="cert", file_key="other.png", original_name="o.png", uploader_id=2,
    ))
    b5.flush()
    _raise(lambda: CertService().recognize_cert("other.png"), 1001)


def test_ut_b5_ct_06_1008(b5):
    """UT-B5-CT-06-1008 无上传权限。"""
    use_scope("ALL", uid=1, perms={"ims:cert:archive:query"})
    _raise(lambda: CertService().recognize_cert("x"), 1008)


def test_ut_b5_ct_07_delete(b5):
    """UT-B5-CT-07-1502 UT-B5-CT-07-OK UT-B5-CT-07-1504 锁定不可删，成功后 deleted 等于 id。"""
    created, _person = _upload()
    row = b5.get(MasterCert, int(created["id"]))
    row.is_locked = True
    b5.flush()
    _raise(lambda: CertService().delete_cert(created["id"]), 1502)
    assert b5.get(MasterCert, int(created["id"])).deleted == 0
    row.is_locked = False
    b5.add(TodoItem(id=1, tenant_id=1, assignee_user_id=1, title="预警", event_id=f"CERT_EXPIRE:{row.id}", status="OPEN"))
    b5.add(CertExpireTask(id=1, tenant_id=1, cert_id=row.id, level="YELLOW", status="WARNING"))
    b5.flush()
    CertService().delete_cert(created["id"])
    assert b5.get(MasterCert, int(created["id"])).deleted == int(created["id"])
    assert b5.query(TodoItem).one().status == "CANCELLED"
    _raise(lambda: CertService().get_cert(created["id"]), 1504)


def test_ut_b5_ct_07_1008(b5):
    """UT-B5-CT-07-1008 无删除权限。"""
    created, _person = _upload()
    use_scope("ALL", uid=1, perms={"ims:cert:archive:query"})
    _raise(lambda: CertService().delete_cert(created["id"]), 1008)


def test_ut_b5_ex_01_scan(b5):
    """UT-B5-EX-01 UT-B5-EX-01-IDEM 到期扫描，同级别第二遍不新增待办。"""
    created, person = _upload()
    use_scope("ALL", uid=2)
    CertService().review_cert(created["id"], True, "")
    row = b5.get(MasterCert, int(created["id"]))
    row.expire_date = get_now().date() + timedelta(days=20)
    b5.flush()
    _grant_renew(b5, 1, "ALL")
    first = scan_cert_expire()
    assert first["notified"] == 1
    second = scan_cert_expire()
    assert second["notified"] == 0
    assert b5.query(TodoItem).count() == 1
    assert cert_is_locked(int(person["id"])) is False


def test_ut_b5_ex_02_up(b5):
    """UT-B5-EX-02-UP 升级后再通知一次。"""
    created, _person = _upload()
    use_scope("ALL", uid=2)
    CertService().review_cert(created["id"], True, "")
    row = b5.get(MasterCert, int(created["id"]))
    today = datetime(2026, 10, 1, 8, 0, tzinfo=BEIJING_TZ)
    set_clock(lambda: today)
    row.expire_date = today.date() + timedelta(days=20)
    b5.flush()
    _grant_renew(b5, 1, "ALL")
    scan_cert_expire()
    set_clock(lambda: today + timedelta(days=16))
    scan_cert_expire()
    assert b5.query(InboxMessage).count() == 2
    task = b5.query(CertExpireTask).one()
    assert "YELLOW" in task.notified_levels and "RED" in task.notified_levels


def test_ut_b5_ex_01_recv(b5):
    """UT-B5-EX-01-RECV 部门范围收不到证件通知。公司 DEPT 列表由显式谓词为空。"""
    created, _person = _upload()
    use_scope("ALL", uid=2)
    CertService().review_cert(created["id"], True, "")
    row = b5.get(MasterCert, int(created["id"]))
    row.expire_date = get_now().date() + timedelta(days=10)
    b5.flush()
    _grant_renew(b5, 2, "DEPT")
    CompanyService().create_company({"name": "仍可见", "credit_code": CREDIT_OK, "industry": "IT"})
    scan_cert_expire()
    assert b5.query(InboxMessage).filter(InboxMessage.user_id == 2).count() == 0
    use_scope("DEPT", uid=2)
    assert CompanyService().page_companies()["total"] == 0


def test_ut_b5_ex_02_list(b5):
    """UT-B5-EX-02 预警列表和统计。"""
    b5.add(CertExpireTask(id=3, tenant_id=1, cert_id=1, level="YELLOW", status="WARNING"))
    b5.flush()
    assert CertExpireService().list_expire_tasks()["total"] == 1
    assert CertExpireService().expire_stats()["YELLOW"] == 1


def test_ut_b5_ex_03(b5):
    """UT-B5-EX-03-1001 UT-B5-EX-03-OK 换证类型不同拒绝；归档后过期锁解除。"""
    created, person = _upload()
    use_scope("ALL", uid=2)
    CertService().review_cert(created["id"], True, "")
    row = b5.get(MasterCert, int(created["id"]))
    row.status = "EXPIRED"
    b5.flush()
    assert cert_is_locked(int(person["id"])) is True
    task = CertExpireTask(id=4, tenant_id=1, cert_id=row.id, level="LOCKED", status="WARNING")
    b5.add(task)
    b5.flush()
    use_scope("ALL", uid=1)
    _raise(lambda: CertExpireService().renew_cert(task.id, {
        "holder_type": "EXTERNAL", "holder_name": "外协", "cert_type": "PASSPORT", "cert_no": "P9",
        "issue_date": "2024-01-01", "expire_date": "2034-01-01",
    }, "n.png", "image/png", png_bytes()), 1001)
    renewed = CertExpireService().renew_cert(task.id, {
        "cert_no": ID_OK, "issue_date": "2024-01-01", "expire_date": "2034-01-01",
    }, "n.png", "image/png", png_bytes())
    use_scope("ALL", uid=2)
    CertService().review_cert(renewed["id"], True, "换证通过")
    assert b5.get(MasterCert, int(created["id"])).status == "RECYCLED"
    assert cert_is_locked(int(person["id"])) is False


def test_ut_b5_ex_04(b5):
    """UT-B5-EX-04-DEDUP UT-B5-EX-04-1001 十分钟内不重复催办，已解除拒绝。"""
    moment = datetime(2026, 10, 13, 9, 0, tzinfo=BEIJING_TZ)
    set_clock(lambda: moment)
    created, _person = _upload()
    task = CertExpireTask(id=5, tenant_id=1, cert_id=int(created["id"]), level="YELLOW", status="WARNING")
    b5.add(task)
    b5.flush()
    _grant_renew(b5, 1, "ALL")
    assert CertExpireService().remind_expire(task.id)["reminded"] is True
    again = CertExpireService().remind_expire(task.id)
    assert again["reminded"] is False
    assert again["remindCount"] == 1
    task.status = "RENEW_RESOLVED"
    b5.flush()
    _raise(lambda: CertExpireService().remind_expire(task.id), 1001)


def test_ut_b5_ex_01_clock(monkeypatch):
    """UT-B5-EX-01-CLOCK test 环境改钟，其他环境 1001。"""
    moment = datetime(2026, 1, 2, 3, 4, tzinfo=BEIJING_TZ)
    apply_test_clock(moment.isoformat())
    assert get_now() == moment
    monkeypatch.setattr(get_settings(), "env", "dev")
    with pytest.raises(BizError) as caught:
        apply_test_clock(moment.isoformat())
    assert caught.value.code == 1001


def test_ut_b5_sc_01(b5):
    """UT-B5-SC-01 UT-B5-SC-01-1008 保存级别后立即生效，无配置权限 1008。"""
    from app.services.cert_security import CertSecurityService, resolve_view_level
    saved = CertSecurityService().save_level_config({"rules": [{"roleId": "1", "viewLevel": 2}], "whitelist": []})
    assert saved["rules"][0]["viewLevel"] == 2
    assert resolve_view_level(1) == 2
    use_scope("ALL", perms={"ims:cert:archive:query"})
    _raise(lambda: CertSecurityService().save_level_config({"rules": [], "whitelist": []}), 1008)


def test_ut_b5_sc_02(b5):
    """UT-B5-SC-02 查看日志列表。"""
    from app.services.cert_security import CertSecurityService
    b5.add(CertViewLog(
        id=9, tenant_id=1, cert_id=1, viewer_user_id=1, view_level=1, result="OK",
        view_time=datetime(2026, 10, 13, 8, 0),
    ))
    b5.flush()
    assert CertSecurityService().list_view_logs()["total"] == 1


def test_ut_b5_sc_03(b5):
    """UT-B5-SC-03 一小时超过 10 次进入风险报告。"""
    from app.services.cert_security import CertSecurityService
    moment = datetime(2026, 10, 13, 9, 0, tzinfo=BEIJING_TZ)
    set_clock(lambda: moment)
    for index in range(11):
        b5.add(CertViewLog(
            id=200 + index, tenant_id=1, cert_id=1, viewer_user_id=1, view_level=1,
            result="OK", view_time=moment.replace(tzinfo=None),
        ))
    b5.flush()
    report = CertSecurityService().risk_report()
    assert report["users"][0]["count"] == 11


def test_ut_b5_scope(b5):
    """UT-B5-BG-04-SCOPE-ALL UT-B5-BG-04-SCOPE-DEPT UT-B5-BG-04-SCOPE-SELF"""
    from app.domains.shared.models import OrgCompany
    from app.services.corp_support import base_stmt, company_rows_hidden

    company = CompanyService().create_company({"name": "范围公司", "credit_code": CREDIT_OK, "industry": "IT"})
    person = _realname()
    sim = _sim(person["id"])
    cert, _ = _upload(person=person)
    use_scope("DEPT", uid=2)
    assert company_rows_hidden() is True
    assert OrgCompany.__scope_fields__ == {}
    assert b5.execute(base_stmt(OrgCompany)).scalars().all()
    assert CompanyService().page_companies()["total"] == 0
    err = _raise(lambda: CompanyService().get_company(company["id"]), 1504)
    assert "范围公司" not in (err.msg or "")
    task = CompanyService().export_companies()
    assert Cache.get_json(f"ims:export:{task['taskId']}")["total"] == 0
    assert RealnameService().page_realnames()["total"] == 0
    assert SimCardService().page_sim_cards()["total"] == 0
    assert CertService().list_certs()["total"] == 0
    _raise(lambda: RealnameService().get_realname(person["id"]), 1504)
    _raise(lambda: SimCardService().get_sim_card(sim["id"]), 1504)
    _raise(lambda: CertService().get_cert(cert["id"]), 1504)
    assert CompanyService().list_company_options()
    use_scope("SELF", uid=1)
    assert company_rows_hidden() is True
    assert CompanyService().page_companies()["total"] == 0
    _raise(lambda: CompanyService().get_company(company["id"]), 1504)
    assert RealnameService().page_realnames()["total"] == 1
    assert SimCardService().page_sim_cards()["total"] == 1
    assert CertService().list_certs()["total"] == 1
    use_scope("ALL", uid=2)
    assert company_rows_hidden() is False
    assert CompanyService().page_companies()["total"] == 1
    assert CompanyService().get_company(company["id"])["name"] == "范围公司"
    assert CertService().list_certs()["total"] == 1


def test_ut_b5_scope_startup():
    """UT-B5-BG-04-SCOPE-STARTUP 公司路由没有 scope_model，实名人和手机卡有。"""
    from app.core.route_policy import _iter_routes, validate_scope_models
    from app.main import app
    company = []
    scoped = []
    bound = []
    for path, route in _iter_routes(app.router):
        bound.append(route)
        if "/corp/resource/company/" in path and "simple-list" not in path:
            company.append(route)
        if path.endswith("/realname/page") or path.endswith("/sim-card/page"):
            scoped.append(route)
    assert company
    assert all(getattr(route, "scope_model", None) is None for route in company)
    from app.domains.shared.models import OrgCompany
    assert OrgCompany.__scope_fields__ == {}
    assert scoped
    assert all(getattr(route.scope_model, "__scope_fields__", None) for route in scoped)
    validate_scope_models(bound)


def test_ut_b5_bg_04_gates(b5):
    """UT-B5-BG-04-SESSION UT-B5-BG-04-1216 UT-B5-BG-04-TENANT UT-B5-BG-04-PERMVER"""
    import asyncio

    from app.services.auth import TENANT_UNAVAILABLE_MSG, AuthService
    user = b5.get(User, 1)
    service = AuthService()
    token = _token(service, user)

    def _run():
        return asyncio.run(service.verify_token(token))

    _run()
    user.deleted = user.id
    b5.flush()
    _raise(_run, 1002)
    user.deleted = 0
    user.status = "FROZEN"
    b5.flush()
    _raise(_run, 1216)
    user.status = "RESIGNED"
    b5.flush()
    _raise(_run, 1216)
    user.status = "ACTIVE"
    b5.add(Tenant(id=1, tenant_id=1, name="组织", status="DISABLED"))
    b5.flush()
    err = _raise(_run, 1008)
    assert err.msg == TENANT_UNAVAILABLE_MSG
    b5.query(Tenant).delete()
    b5.flush()
    Cache.incr("ims:perm_ver:u:1")
    _raise(_run, 1008)


def test_ut_b5_bg_04_missing_user(b5):
    """UT-B5-BG-04-SESSION 用户行不存在也是 1002，且发生在会话校验之后。"""
    import asyncio

    from app.services.auth import AuthService
    service = AuthService()
    token = _token(service, b5.get(User, 1), user_id=404)
    _raise(lambda: asyncio.run(service.verify_token(token)), 1002)


def test_ut_b5_watermark_pdf():
    """UT-B5-CT-04 图片加水印，PDF 字节不变。"""
    marked = apply_watermark(png_bytes(), "E1 张三")
    assert marked != png_bytes()
    assert apply_watermark(PDF, "E1 张三") == PDF


def test_deps_reraise_1216(monkeypatch):
    """冻结在线请求保持 1216，不吞成 1002。"""
    import asyncio

    from app.api.deps import get_current_user_optional

    async def _boom(_self, _token):
        raise BizError(1216)

    monkeypatch.setattr("app.services.auth.AuthService.verify_token", _boom)
    with pytest.raises(BizError) as caught:
        asyncio.run(get_current_user_optional("token"))
    assert caught.value.code == 1216


def _token(service, user, user_id=None):
    now = get_now()
    session_id = f"sid-{user_id or user.id}"
    Cache.set_json(f"{service.SESSION_PREFIX}{session_id}", {
        "user_id": user_id or user.id,
        "tenant_id": 1,
        "refresh_token": "r",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "perm_ver_u": 0,
        "perm_ver_t": 0,
    }, ttl=86400)
    payload = {
        "sub": str(user_id or user.id),
        "tid": "1",
        "sid": session_id,
        "exp": now + timedelta(hours=1),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, get_settings().jwt.secret, algorithm=get_settings().jwt.algorithm)


def _grant_renew(session, uid: int, scope: str):
    role = Role(
        id=300 + uid, tenant_id=1, role_key=f"e2e_{uid}", name="续期",
        source="MANUAL", status="ENABLED", data_scope=scope,
    )
    session.add(role)
    menu = Menu(
        id=400 + uid, tenant_id=1, parent_id=0, name="续期", type="BUTTON",
        status="ENABLED", perm_code="ims:cert:expire:renew",
    )
    query = Menu(
        id=500 + uid, tenant_id=1, parent_id=0, name="查询", type="BUTTON",
        status="ENABLED", perm_code="ims:cert:archive:query",
    )
    session.add(menu)
    session.add(query)
    session.add(UserRole(id=600 + uid, tenant_id=1, user_id=uid, role_id=role.id))
    session.add(RoleMenu(id=700 + uid, tenant_id=1, role_id=role.id, menu_id=menu.id))
    session.add(RoleMenu(id=800 + uid, tenant_id=1, role_id=role.id, menu_id=query.id))
    session.flush()
