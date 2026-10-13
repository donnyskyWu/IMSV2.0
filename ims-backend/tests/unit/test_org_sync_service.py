# tests/unit/test_org_sync_service.py - OrgSyncService reconcile coverage
"""Cover trigger, latest batch, and snapshot apply branches."""

from datetime import datetime

import pytest

from app.core.clock import reset_clock, set_clock
from app.core.errors import BizError
from app.services.org_sync import OrgSyncService
from tests.support import rows


@pytest.fixture
def fixed_clock():
    now = datetime(2026, 10, 13, 10, 0, 0)
    set_clock(lambda: now)
    yield now
    reset_clock()


@pytest.mark.asyncio
async def test_trigger_and_latest_batch(db_session, test_context, fixed_clock):
    service = OrgSyncService()
    assert await service.get_latest_batch() is None

    created = await service.trigger_reconcile()
    assert created["status"] == "PENDING"
    assert created["batch_id"]
    assert created["started_at"]
    assert created["completed_at"] is None
    assert created["added_depts"] == 0

    latest = await service.get_latest_batch()
    assert latest["batch_id"] == created["batch_id"]


@pytest.mark.asyncio
async def test_reconcile_snapshot_depts_and_users(db_session, test_context, fixed_clock):
    from app.domains.sys.models import ChangeLog, Dept, DictData, User, UserDept, UserMapping
    from app.services.user import USER_EVENTS

    service = OrgSyncService()
    parent = rows.dept(db_session, "钉钉父", ding="p1", source="DINGTALK")
    local = rows.dept(db_session, "同名本地", parent=parent, source="LOCAL")
    child = rows.dept(db_session, "钉钉子", parent=parent, ding="c1", source="DINGTALK")
    assert local.id

    USER_EVENTS.clear()
    result = await service.reconcile_snapshot({
        "depts": [
            {"dingtalk_id": "p1", "name": "钉钉父", "parent_dingtalk_id": None},
            {"dingtalk_id": "n1", "name": "同名本地", "parent_dingtalk_id": "p1"},
            {"dingtalk_id": "c1", "name": "钉钉子", "parent_dingtalk_id": "n1"},
        ],
        "users": [
            {
                "dingtalk_user_id": "u-new",
                "name": "新人",
                "position": "HOST",
                "dept_dingtalk_ids": ["n1", "missing"],
            },
            {
                "dingtalk_user_id": "u-new",
                "resigned": True,
            },
        ],
    })
    assert result["status"] == "SUCCESS"
    assert "存在同名本地部门" in result["reports"]

    created = db_session.query(Dept).filter(Dept.dingtalk_dept_id == "n1").one()
    assert created.parent_id == parent.id
    db_session.refresh(child)
    assert child.parent_id == created.id
    assert db_session.query(ChangeLog).filter(ChangeLog.biz_id == str(child.id)).count() == 1

    user = db_session.query(User).filter(User.username == "dt_u-new").one()
    assert user.status == "RESIGNED"
    assert user.position_code == "HOST"
    assert user.main_dept_id == created.id
    assert db_session.query(DictData).filter(DictData.dict_value == "HOST").count() == 1
    assert db_session.query(UserMapping).filter(UserMapping.dingtalk_user_id == "u-new").count() == 1
    assert db_session.query(UserDept).filter(UserDept.user_id == user.id).count() == 1
    assert any(item["user_id"] == user.id for item in USER_EVENTS)

    rows.add(db_session, DictData(
        tenant_id=1, dict_type="dict_position", dict_value="EDITOR",
        dict_label="编辑", status="ENABLED",
    ))
    second = await service.reconcile_snapshot({
        "depts": [],
        "users": [{
            "dingtalk_user_id": "u-known",
            "username": "known-name",
            "position": "EDITOR",
            "dept_dingtalk_ids": [],
        }],
    })
    assert second["status"] == "SUCCESS"
    known = db_session.query(User).filter(User.username == "known-name").one()
    assert known.position_code == "EDITOR"


@pytest.mark.asyncio
async def test_reconcile_timeout_and_running_guard(db_session, test_context, fixed_clock):
    from app.domains.sys.models import OrgSyncBatch

    service = OrgSyncService()
    failed = await service.reconcile_snapshot({"depts": [], "users": []}, timeout=True)
    assert failed["status"] == "FAILED"
    assert failed["error_msg"] == "5003"

    rows.add(db_session, OrgSyncBatch(tenant_id=1, status="RUNNING", started_at=fixed_clock))
    with pytest.raises(BizError) as caught:
        await service.reconcile_snapshot({"depts": []})
    assert caught.value.code == 1001
