# tests/unit/test_workbench.py - 工作台服务单元测试（B3）
"""
工作台服务测试。
"""

import pytest

from app.core.context import RequestContext, ctx
from app.services import message as message_service
from app.services import todo as todo_service
from app.services import workbench as workbench_service
from app.services.todo import TodoType


@pytest.fixture
def workbench_context():
    """工作台测试的上下文。"""
    context = RequestContext(
        trace_id="workbench-test",
        user_id=100,
        tenant_id=1,
        perm_codes={"ims:workbench:query"},
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


class TestWorkbenchDashboard:
    """工作台仪表盘测试。"""

    def test_get_dashboard(self, db_session, workbench_context):
        """UT-B3-WB-03: 仪表盘返回正确数据。"""
        # 创建待办
        todo_service.create(
            db_session,
            todo_type=TodoType.APPROVAL,
            source_module="测试",
            source_type="test",
            source_id=1,
            title="待办1",
            assignee_user_ids=[100],
        )
        todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=2,
            title="待办2",
            assignee_user_ids=[100],
        )

        # 创建消息
        message_service.notify(
            db_session,
            event_type="test",
            biz_key="msg1",
            receivers=[100],
            title="消息1",
            content="内容",
        )
        message_service.notify(
            db_session,
            event_type="test",
            biz_key="msg2",
            receivers=[100],
            title="消息2",
            content="内容",
        )
        message_service.notify(
            db_session,
            event_type="test",
            biz_key="msg3",
            receivers=[100],
            title="消息3",
            content="内容",
        )
        db_session.flush()

        dashboard = workbench_service.get_dashboard(db_session, user_id=100)

        assert dashboard["todoCount"] == 2
        assert dashboard["unreadMessageCount"] == 3
        assert dashboard["todoByType"][TodoType.APPROVAL] == 1
        assert dashboard["todoByType"][TodoType.CONFIRM] == 1

    def test_dashboard_null_fields(self, db_session, workbench_context):
        """UT-B3-WB-03: 其余字段返回 null（Q4）。"""
        dashboard = workbench_service.get_dashboard(db_session, user_id=100)

        assert dashboard["myAccountCount"] is None
        assert dashboard["myAssetCount"] is None
        assert dashboard["myApprovalCount"] is None
        assert dashboard["myAttendanceCount"] is None
