"""B2 导出任务与手机号加解密。"""

import pytest

from app.core.context import RequestContext, ctx
from app.core.masking import decrypt_mobile, encrypt_mobile, mask_mobile_display
from app.services.system_export import create_export_task, get_export_task


def test_mobile_roundtrip_and_mask():
    token = encrypt_mobile("13812345678")
    assert token != "13812345678"
    assert decrypt_mobile(token) == "13812345678"
    assert mask_mobile_display(token) == "138****5678"
    assert mask_mobile_display("13812345678") == "138****5678"
    assert mask_mobile_display("123") is None


def test_export_task_is_not_a_placeholder():
    result = create_export_task("user", [{"id": "1", "mobile": "138****5678"}])
    assert result["status"] == "SUCCESS"
    assert result["task_id"] != "pending"
    assert result["row_count"] == 1
    stored = get_export_task(result["task_id"])
    assert stored is not None
    assert "138****5678" in stored["csv"]
    assert "13812345678" not in stored["csv"]


@pytest.fixture
def user_ctx():
    context = RequestContext(
        trace_id="export-trace",
        user_id=1,
        tenant_id=1,
        perm_codes=set(),
        dept_ids=[1],
        client_ip="127.0.0.1",
        session_id="export-session",
    )
    ctx.set(context)
    yield context
    ctx.reset()


@pytest.mark.asyncio
async def test_export_services_finish_instead_of_pending(db_session, user_ctx):
    from app.services.system_log import SystemLogService
    from app.services.system_role import SystemRoleService
    from app.services.system_user import SystemUserService

    results = [
        await SystemUserService().export_users(),
        await SystemRoleService().export_roles(),
        await SystemLogService().export_operate_logs(),
        await SystemLogService().export_login_logs(),
    ]
    for result in results:
        assert result["status"] == "SUCCESS"
        assert result["task_id"] != "pending"
        stored = get_export_task(result["task_id"])
        assert stored is not None
        assert "request_path" not in stored["csv"]
