# tests/unit/test_message_service.py - 消息服务单元测试（B3）
"""
消息服务测试。
"""

import pytest

from app.core.context import RequestContext, ctx
from app.services import message as message_service
from app.services.message import ReadStatus


@pytest.fixture
def message_context():
    """消息测试的上下文。"""
    context = RequestContext(
        trace_id="message-test",
        user_id=100,
        tenant_id=1,
        perm_codes={"ims:workbench:query"},
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


class TestMessageNotify:
    """消息通知测试。"""

    def test_notify_creates_message(self, db_session, message_context):
        """UT-B3-MS-01: 发送通知创建消息。"""
        messages = message_service.notify(
            db_session,
            event_type="test_event",
            biz_key="test_key_1",
            receivers=[100],
            title="测试消息",
            content="这是测试内容",
        )

        assert len(messages) == 1
        assert messages[0].title == "测试消息"
        assert messages[0].read_status == ReadStatus.UNREAD


class TestMessagePage:
    """消息分页测试。"""

    def test_get_my_page(self, db_session, message_context):
        """UT-B3-MS-01: 获取我的消息分页。"""
        message_service.notify(
            db_session,
            event_type="test",
            biz_key="key1",
            receivers=[100],
            title="消息1",
            content="内容1",
        )
        message_service.notify(
            db_session,
            event_type="test",
            biz_key="key2",
            receivers=[100],
            title="消息2",
            content="内容2",
        )
        db_session.flush()

        result = message_service.get_my_page(db_session, user_id=100)

        assert result["total"] == 2
        assert len(result["list"]) == 2

    def test_filter_by_read_status(self, db_session, message_context):
        """UT-B3-MS-01: 按已读状态筛选。"""
        msgs = message_service.notify(
            db_session,
            event_type="test",
            biz_key="key3",
            receivers=[100],
            title="消息",
            content="内容",
        )
        db_session.flush()

        # 标记已读
        message_service.mark_read(db_session, user_id=100, ids=[msgs[0].id])
        db_session.flush()

        # 查询未读
        unread = message_service.get_my_page(db_session, user_id=100, read_status="UNREAD")
        assert unread["total"] == 0

        # 查询已读
        read = message_service.get_my_page(db_session, user_id=100, read_status="READ")
        assert read["total"] == 1


class TestMessageMarkRead:
    """消息标记已读测试。"""

    def test_mark_read(self, db_session, message_context):
        """UT-B3-MS-02: 标记已读幂等。"""
        msgs = message_service.notify(
            db_session,
            event_type="test",
            biz_key="key4",
            receivers=[100],
            title="消息",
            content="内容",
        )
        db_session.flush()

        # 第一次标记
        result1 = message_service.mark_read(db_session, user_id=100, ids=[msgs[0].id])
        assert result1["updated"] == 1

        # 第二次标记（幂等）
        result2 = message_service.mark_read(db_session, user_id=100, ids=[msgs[0].id])
        assert result2["updated"] == 0

    def test_mark_read_all_or_nothing(self, db_session, message_context):
        """UT-B3-ERR-1504-10/11: 批量标已读 all or nothing。"""
        from app.core.errors import BizError

        msgs = message_service.notify(
            db_session,
            event_type="test",
            biz_key="key5",
            receivers=[100],
            title="消息",
            content="内容",
        )
        db_session.flush()

        # 包含不存在的 id
        with pytest.raises(BizError) as exc_info:
            message_service.mark_read(db_session, user_id=100, ids=[msgs[0].id, 99999])

        assert exc_info.value.code == 1504

        # 原消息仍然未读
        detail = message_service.get_my_detail(db_session, message_id=msgs[0].id, user_id=100)
        assert detail["readStatus"] == ReadStatus.UNREAD


class TestMessageMarkAllRead:
    """消息全部已读测试。"""

    def test_mark_all_read(self, db_session, message_context):
        """UT-B3-MS-03: 全部已读。"""
        for i in range(3):
            message_service.notify(
                db_session,
                event_type="test",
                biz_key=f"all_read_{i}",
                receivers=[100],
                title=f"消息{i}",
                content="内容",
            )
        db_session.flush()

        result = message_service.mark_all_read(db_session, user_id=100)

        assert result["updated"] == 3

        # 验证未读数为 0
        count = message_service.get_unread_count(db_session, user_id=100)
        assert count == 0


class TestMessageUnreadCount:
    """消息未读数测试。"""

    def test_get_unread_count(self, db_session, message_context):
        """UT-B3-MS-04: 获取未读数。"""
        for i in range(5):
            message_service.notify(
                db_session,
                event_type="test",
                biz_key=f"unread_{i}",
                receivers=[100],
                title=f"消息{i}",
                content="内容",
            )
        db_session.flush()

        count = message_service.get_unread_count(db_session, user_id=100)
        assert count == 5


class TestMessageDetail:
    """消息详情测试。"""

    def test_get_my_detail(self, db_session, message_context):
        """UT-B3-MS-05: 获取消息详情。"""
        msgs = message_service.notify(
            db_session,
            event_type="test",
            biz_key="detail_1",
            receivers=[100],
            title="详情测试",
            content="详情内容",
            route="/ims/test/1",
        )
        db_session.flush()

        detail = message_service.get_my_detail(db_session, message_id=msgs[0].id, user_id=100)

        assert detail["title"] == "详情测试"
        assert detail["route"] == "/ims/test/1"

    def test_cannot_view_others_message(self, db_session, message_context):
        """UT-B3-ERR-1504-07: 不能查看他人消息。"""
        from app.core.errors import BizError

        msgs = message_service.notify(
            db_session,
            event_type="test",
            biz_key="other_msg",
            receivers=[100],
            title="消息",
            content="内容",
        )
        db_session.flush()

        with pytest.raises(BizError) as exc_info:
            message_service.get_my_detail(db_session, message_id=msgs[0].id, user_id=200)

        assert exc_info.value.code == 1504
