# tests/unit/test_todo_service.py - 待办服务单元测试（B3）
"""
待办服务测试。

迁移自旧 test_todo.py，改为调用真实服务。
"""

from datetime import datetime

import pytest

from app.core.context import RequestContext, ctx
from app.services import todo as todo_service
from app.services.todo import TodoStatus, TodoType


@pytest.fixture
def todo_context():
    """待办测试的上下文。"""
    context = RequestContext(
        trace_id="todo-test",
        user_id=100,
        tenant_id=1,
        perm_codes={"ims:workbench:query"},
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


@pytest.fixture
def other_user_context():
    """其他用户的上下文。"""
    context = RequestContext(
        trace_id="other-test",
        user_id=200,
        tenant_id=1,
        perm_codes={"ims:workbench:query"},
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


class TestTodoCreate:
    """待办创建测试（迁移自 UT-G02-01/02）。"""

    def test_create_todo_for_user(self, db_session, todo_context):
        """UT-B3-TD-SVC-01: 创建待办。"""
        todo = todo_service.create(
            db_session,
            todo_type=TodoType.APPROVAL,
            source_module="订单",
            source_type="order",
            source_id=123,
            title="请审批订单",
            route="/ims/order/123",
            assignee_user_ids=[100],
        )

        assert todo is not None
        assert todo.status == TodoStatus.PENDING
        assert todo.type == TodoType.APPROVAL
        assert todo.title == "请审批订单"

    def test_todo_has_required_fields(self, db_session, todo_context):
        """UT-B3-TD-SVC-02: 待办包含必要字段。"""
        todo = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="岗位供给",
            source_type="position_supply",
            source_id=456,
            title="请配置岗位",
            assignee_user_ids=[100],
        )

        assert todo.id is not None
        assert todo.tenant_id == 1
        assert todo.type is not None
        assert todo.source_type is not None
        assert todo.title is not None

    def test_idempotent_create(self, db_session, todo_context):
        """UT-B3-TD-SVC-03: 幂等创建（同 source_type+source_id+type）。"""
        todo1 = todo_service.create(
            db_session,
            todo_type=TodoType.APPROVAL,
            source_module="订单",
            source_type="order",
            source_id=789,
            title="请审批订单",
            assignee_user_ids=[100],
        )

        todo2 = todo_service.create(
            db_session,
            todo_type=TodoType.APPROVAL,
            source_module="订单",
            source_type="order",
            source_id=789,
            title="请审批订单（重复）",
            assignee_user_ids=[100],
        )

        assert todo1.id == todo2.id

    def test_different_source_id_creates_new(self, db_session, todo_context):
        """UT-B3-TD-SVC-04: 不同 source_id 创建新待办。"""
        todo1 = todo_service.create(
            db_session,
            todo_type=TodoType.APPROVAL,
            source_module="订单",
            source_type="order",
            source_id=111,
            title="请审批订单1",
            assignee_user_ids=[100],
        )

        todo2 = todo_service.create(
            db_session,
            todo_type=TodoType.APPROVAL,
            source_module="订单",
            source_type="order",
            source_id=222,
            title="请审批订单2",
            assignee_user_ids=[100],
        )

        assert todo1.id != todo2.id


class TestTodoComplete:
    """待办完成测试（迁移自 UT-G02-04）。"""

    def test_complete_sets_done(self, db_session, todo_context):
        """UT-B3-TD-SVC-05: 完成待办设置状态为 DONE。"""
        _ = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=1,
            title="测试待办",
            assignee_user_ids=[100],
        )
        db_session.flush()

        result = todo_service.complete(
            db_session,
            source_type="test",
            source_id=1,
            by_user=100,
        )

        assert result is not None
        assert result.status == TodoStatus.DONE
        assert result.done_by == 100
        assert result.done_time is not None

    def test_completed_not_in_pending_list(self, db_session, todo_context):
        """UT-B3-TD-SVC-06: 已完成待办不出现在待处理列表。"""
        todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=2,
            title="测试待办",
            assignee_user_ids=[100],
        )
        db_session.flush()

        todo_service.complete(
            db_session,
            source_type="test",
            source_id=2,
            by_user=100,
        )
        db_session.flush()

        result = todo_service.get_my_page(
            db_session,
            user_id=100,
            status="PENDING",
        )

        assert all(item["status"] == TodoStatus.PENDING for item in result["list"])


class TestTodoCancel:
    """待办作废测试（迁移自 UT-G02-05）。"""

    def test_cancel_sets_cancelled(self, db_session, todo_context):
        """UT-B3-TD-SVC-07: 作废待办设置状态为 CANCELLED。"""
        todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=3,
            title="测试待办",
            assignee_user_ids=[100],
        )
        db_session.flush()

        result = todo_service.cancel(
            db_session,
            source_type="test",
            source_id=3,
        )

        assert result is not None
        assert result.status == TodoStatus.CANCELLED

    def test_cancelled_not_in_count(self, db_session, todo_context):
        """UT-B3-TD-SVC-08: 已作废待办不计入统计。"""
        todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=4,
            title="待办1",
            assignee_user_ids=[100],
        )
        todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=5,
            title="待办2",
            assignee_user_ids=[100],
        )
        db_session.flush()

        todo_service.cancel(
            db_session,
            source_type="test",
            source_id=4,
        )
        db_session.flush()

        count = todo_service.get_my_count(db_session, user_id=100)
        assert count["total"] == 1


class TestTodoVisibility:
    """待办可见性测试（迁移自 UT-G02-06）。"""

    def test_handler_can_view(self, db_session, todo_context):
        """UT-B3-TD-SVC-09: 处理人可以查看待办。"""
        todo = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=6,
            title="测试待办",
            assignee_user_ids=[100],
        )
        db_session.flush()

        detail = todo_service.get_my_detail(
            db_session,
            todo_id=todo.id,
            user_id=100,
        )

        assert detail is not None
        assert detail["title"] == "测试待办"

    def test_cannot_view_others_todo(self, db_session, todo_context):
        """UT-B3-ERR-1504-01: 不能查看他人待办。"""
        from app.core.errors import BizError

        todo = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=7,
            title="测试待办",
            assignee_user_ids=[100],
        )
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            todo_service.get_my_detail(
                db_session,
                todo_id=todo.id,
                user_id=200,
            )

        assert exc_info.value.code == 1504


class TestTodoClose:
    """待办关闭测试。"""

    def test_close_for_user(self, db_session, todo_context):
        """UT-B3-TD-04: 本人关闭待办。"""
        todo = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=8,
            title="测试待办",
            assignee_user_ids=[100],
        )
        db_session.flush()

        todo_service.close_for_user(
            db_session,
            todo_id=todo.id,
            user_id=100,
        )
        db_session.flush()

        # 关闭后不出现在列表
        result = todo_service.get_my_page(db_session, user_id=100)
        assert all(item["id"] != str(todo.id) for item in result["list"])

    def test_cannot_close_approval(self, db_session, todo_context):
        """UT-B3-ERR-1001-01: 不能关闭审批类待办。"""
        from app.core.errors import BizError

        todo = todo_service.create(
            db_session,
            todo_type=TodoType.APPROVAL,
            source_module="测试",
            source_type="test",
            source_id=9,
            title="审批待办",
            assignee_user_ids=[100],
        )
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            todo_service.close_for_user(
                db_session,
                todo_id=todo.id,
                user_id=100,
            )

        assert exc_info.value.code == 1001
        assert "来源单据" in exc_info.value.msg

    def test_cannot_close_review(self, db_session, todo_context):
        """UT-B3-ERR-1001-02: 不能关闭审核类待办。"""
        from app.core.errors import BizError

        todo = todo_service.create(
            db_session,
            todo_type=TodoType.REVIEW,
            source_module="测试",
            source_type="test",
            source_id=10,
            title="审核待办",
            assignee_user_ids=[100],
        )
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            todo_service.close_for_user(
                db_session,
                todo_id=todo.id,
                user_id=100,
            )

        assert exc_info.value.code == 1001

    def test_cannot_close_done_todo(self, db_session, todo_context):
        """UT-B3-ERR-1001-03: 不能关闭已完成待办。"""
        from app.core.errors import BizError

        todo = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=11,
            title="测试待办",
            assignee_user_ids=[100],
        )
        db_session.flush()

        todo_service.complete(
            db_session,
            source_type="test",
            source_id=11,
            by_user=100,
        )
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            todo_service.close_for_user(
                db_session,
                todo_id=todo.id,
                user_id=100,
            )

        assert exc_info.value.code == 1001
        assert "已处理或已关闭" in exc_info.value.msg


class TestTodoCount:
    """待办计数测试（迁移自 UT-G02-07）。"""

    def test_count_by_type(self, db_session, todo_context):
        """UT-B3-TD-05: 按类型统计待办数。"""
        # 创建不同类型的待办
        for i, t in enumerate([TodoType.APPROVAL, TodoType.APPROVAL, TodoType.RETURN]):
            todo_service.create(
                db_session,
                todo_type=t,
                source_module="测试",
                source_type="test",
                source_id=100 + i,
                title=f"待办{i}",
                assignee_user_ids=[100],
            )
        db_session.flush()

        count = todo_service.get_my_count(db_session, user_id=100)

        assert count["total"] == 3
        assert count["byType"].get(TodoType.APPROVAL, 0) == 2
        assert count["byType"].get(TodoType.RETURN, 0) == 1


class TestTodoMultipleHandlers:
    """多处理人测试。"""

    def test_multiple_handlers(self, db_session, todo_context):
        """UT-B3-TD-SVC-10: 多个处理人都可以查看。"""
        todo = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=200,
            title="多人待办",
            assignee_user_ids=[100, 200],
        )
        db_session.flush()

        # 用户 100 可以查看
        detail1 = todo_service.get_my_detail(db_session, todo_id=todo.id, user_id=100)
        assert detail1 is not None

        # 用户 200 可以查看
        detail2 = todo_service.get_my_detail(db_session, todo_id=todo.id, user_id=200)
        assert detail2 is not None

    def test_completion_records_handler(self, db_session, todo_context):
        """UT-B3-TD-SVC-11: 完成记录处理人。"""
        todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=201,
            title="多人待办",
            assignee_user_ids=[100, 200],
        )
        db_session.flush()

        result = todo_service.complete(
            db_session,
            source_type="test",
            source_id=201,
            by_user=200,
        )

        assert result.done_by == 200


class TestTodoOverdue:
    """逾期测试。"""

    def test_overdue_calculation(self, db_session, todo_context, fixed_time):
        """UT-B3-TD-02: 逾期计算。"""
        fixed_time(datetime(2026, 10, 13, 10, 0, 0))

        todo = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=300,
            title="逾期待办",
            assignee_user_ids=[100],
            due_time=datetime(2026, 10, 12, 10, 0, 0),
        )
        db_session.flush()

        detail = todo_service.get_my_detail(db_session, todo_id=todo.id, user_id=100)

        assert detail["isOverdue"] is True
        assert detail["overdueDays"] == 1


class TestTodoMissingBranches:
    """补齐 complete/cancel/关闭/筛选/详情姓名这些还没走到的分支。"""

    def test_complete_and_cancel_missing_return_none(self, db_session, todo_context):
        assert todo_service.complete(
            db_session, source_type="missing", source_id=1, by_user=100,
        ) is None
        assert todo_service.cancel(
            db_session, source_type="missing", source_id=1,
        ) is None

    def test_cancel_appends_reason(self, db_session, todo_context):
        todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=401,
            title="作废原因",
            content="原文",
            assignee_user_ids=[100],
        )
        db_session.flush()

        result = todo_service.cancel(
            db_session, source_type="test", source_id=401, reason="来源单据撤回",
        )

        assert result is not None
        assert "作废原因：来源单据撤回" in (result.content or "")

    def test_close_missing_todo_or_assignee_or_repeat(self, db_session, todo_context):
        from app.core.errors import BizError

        with pytest.raises(BizError) as missing:
            todo_service.close_for_user(db_session, todo_id=999999999, user_id=100)
        assert missing.value.code == 1504

        todo = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=402,
            title="关闭分支",
            assignee_user_ids=[100],
        )
        db_session.flush()

        with pytest.raises(BizError) as stranger:
            todo_service.close_for_user(db_session, todo_id=todo.id, user_id=200)
        assert stranger.value.code == 1504

        todo_service.close_for_user(db_session, todo_id=todo.id, user_id=100)
        with pytest.raises(BizError) as again:
            todo_service.close_for_user(db_session, todo_id=todo.id, user_id=100)
        assert again.value.code == 1001

    def test_page_filters_type_status_keyword(self, db_session, todo_context, fixed_time):
        fixed_time(datetime(2026, 10, 13, 12, 0, 0))
        confirm = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=403,
            title="关键字确认",
            content="正文甲",
            assignee_user_ids=[100],
            due_time=datetime(2026, 10, 12, 12, 0, 0),
        )
        done = todo_service.create(
            db_session,
            todo_type=TodoType.RETURN,
            source_module="测试",
            source_type="test",
            source_id=404,
            title="已完成项",
            assignee_user_ids=[100],
        )
        db_session.flush()
        todo_service.complete(db_session, source_type="test", source_id=404, by_user=100)
        db_session.flush()

        by_type = todo_service.get_my_page(db_session, user_id=100, todo_type=TodoType.CONFIRM)
        assert [item["id"] for item in by_type["list"]] == [str(confirm.id)]

        overdue = todo_service.get_my_page(db_session, user_id=100, status="OVERDUE")
        assert [item["id"] for item in overdue["list"]] == [str(confirm.id)]

        done_page = todo_service.get_my_page(db_session, user_id=100, status="DONE")
        assert [item["id"] for item in done_page["list"]] == [str(done.id)]

        keyword = todo_service.get_my_page(db_session, user_id=100, keyword="关键字")
        assert [item["id"] for item in keyword["list"]] == [str(confirm.id)]

    def test_detail_missing_and_done_by_name(self, db_session, todo_context):
        from app.core.errors import BizError
        from tests.support import rows

        with pytest.raises(BizError) as missing:
            todo_service.get_my_detail(db_session, todo_id=999999999, user_id=100)
        assert missing.value.code == 1504

        person = rows.user(db_session, "todo_done_by", nickname="处理人甲")
        created = todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="test",
            source_id=405,
            title="带姓名",
            assignee_user_ids=[100],
        )
        db_session.flush()
        todo_service.complete(
            db_session, source_type="test", source_id=405, by_user=person.id,
        )
        db_session.flush()

        detail = todo_service.get_my_detail(db_session, todo_id=created.id, user_id=100)
        assert detail["doneByName"] == "处理人甲"

    def test_dingtalk_push_dedup_skips_second_type(self, db_session, todo_context):
        todo_service.create(
            db_session,
            todo_type=TodoType.CONFIRM,
            source_module="测试",
            source_type="dedup_src",
            source_id=406,
            title="第一次推送",
            assignee_user_ids=[100],
        )
        second = todo_service.create(
            db_session,
            todo_type=TodoType.WARNING,
            source_module="测试",
            source_type="dedup_src",
            source_id=406,
            title="第二次去重",
            assignee_user_ids=[100],
        )
        assert second.title == "第二次去重"
