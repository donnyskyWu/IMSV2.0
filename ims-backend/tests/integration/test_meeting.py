# tests/integration/test_meeting.py - Meeting module tests (B18-M18)
"""
Meeting module integration tests.

Tests use real MySQL/Redis (CI environment). No mock for DB/Redis, only perm_ver can be stubbed.
All tests per §6 of 会议-实现理解.md.

Error codes registered in app/core/errors.py by this module:
- 1116: 录入/归档超时提示 (warnings, not blocking)
- 1117: 已归档纪要不可操作
- 1118: 非行动项责任人，无权回填

P0 Services (app/domains/meet/service.py):
- MeetingService (all methods)
- meeting_reminder_job (app/domains/meet/jobs.py)
- meeting_overdue_job (app/domains/meet/jobs.py)
"""

from datetime import datetime, timedelta

import pytest

from app.core.clock import BEIJING_TZ, get_now
from app.core.context import RequestContext, ctx
from app.core.errors import BizError, error_codes
from app.db.session import get_db_session


@pytest.fixture
def meet_admin_context():
    """Admin context with all meeting permissions."""
    context = RequestContext(
        trace_id="meet-admin-trace",
        user_id=1,
        tenant_id=1,
        perm_codes={
            "ims:meet:minutes:query",
            "ims:meet:minutes:query-self",
            "ims:meet:minutes:add",
            "ims:meet:minutes:edit",
            "ims:meet:minutes:archive",
            "ims:meet:minutes:delete",
            "ims:meet:minutes:appendix",
            "ims:meet:minutes:supervise",
        },
        data_scopes=[{"scope_type": "ALL", "role_id": 1}],
        dept_ids=[1],
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


@pytest.fixture
def meet_self_only_context():
    """Context with only query-self permission."""
    context = RequestContext(
        trace_id="meet-self-trace",
        user_id=2,
        tenant_id=1,
        perm_codes={"ims:meet:minutes:query-self"},
        data_scopes=[{"scope_type": "SELF", "role_id": 2}],
        dept_ids=[2],
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


@pytest.fixture
def meet_no_perm_context():
    """Context with no meeting permissions."""
    context = RequestContext(
        trace_id="meet-no-perm-trace",
        user_id=3,
        tenant_id=1,
        perm_codes=set(),
        data_scopes=[],
        dept_ids=[],
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


@pytest.fixture
def sample_users_for_meet(db_session, meet_admin_context):
    """Create sample users for meeting tests."""
    from app.domains.sys.models import Dept, User

    dept = Dept(
        id=1,
        tenant_id=1,
        parent_id=0,
        path="/1/",
        name="Test Dept",
        status="ENABLED",
        source="LOCAL",
    )
    db_session.add(dept)

    dept2 = Dept(
        id=2,
        tenant_id=1,
        parent_id=0,
        path="/2/",
        name="Other Dept",
        status="ENABLED",
        source="LOCAL",
    )
    db_session.add(dept2)

    user1 = User(
        id=1,
        tenant_id=1,
        username="recorder",
        nickname="Recorder",
        main_dept_id=1,
        status="ACTIVE",
        source="LOCAL",
    )
    db_session.add(user1)

    user2 = User(
        id=2,
        tenant_id=1,
        username="attendee",
        nickname="Attendee",
        main_dept_id=2,
        status="ACTIVE",
        source="LOCAL",
    )
    db_session.add(user2)

    user3 = User(
        id=3,
        tenant_id=1,
        username="outsider",
        nickname="Outsider",
        main_dept_id=2,
        status="ACTIVE",
        source="LOCAL",
    )
    db_session.add(user3)

    resigned_user = User(
        id=4,
        tenant_id=1,
        username="resigned",
        nickname="Resigned User",
        main_dept_id=1,
        status="RESIGNED",
        source="LOCAL",
    )
    db_session.add(resigned_user)

    frozen_user = User(
        id=6,
        tenant_id=1,
        username="frozen",
        nickname="Frozen User",
        main_dept_id=1,
        status="FROZEN",
        source="LOCAL",
    )
    db_session.add(frozen_user)

    db_session.flush()

    return {"user1": user1, "user2": user2, "user3": user3, "resigned": resigned_user, "frozen": frozen_user}


class TestErrorCodeRegistration:
    """验证错误码已在 errors.py 注册且文案正确。"""

    def test_error_1116_registered(self):
        """1116 录入/归档超时提示已注册。"""
        info = error_codes.get(1116)
        assert info is not None, "错误码 1116 未在 errors.py 注册"
        assert info.domain == "MEET", f"错误码 1116 domain 应为 MEET，实际为 {info.domain}"
        assert "超时" in info.msg or "录入" in info.msg, f"错误码 1116 文案应含'超时'或'录入'，实际为: {info.msg}"

    def test_error_1117_registered(self):
        """1117 已归档纪要不可操作已注册。"""
        info = error_codes.get(1117)
        assert info is not None, "错误码 1117 未在 errors.py 注册"
        assert info.domain == "MEET", f"错误码 1117 domain 应为 MEET，实际为 {info.domain}"
        assert "归档" in info.msg, f"错误码 1117 文案应含'归档'，实际为: {info.msg}"

    def test_error_1118_registered(self):
        """1118 非行动项责任人已注册。"""
        info = error_codes.get(1118)
        assert info is not None, "错误码 1118 未在 errors.py 注册"
        assert info.domain == "MEET", f"错误码 1118 domain 应为 MEET，实际为 {info.domain}"
        assert "责任人" in info.msg, f"错误码 1118 文案应含'责任人'，实际为: {info.msg}"


class TestMeetingMinutesCreate:
    """MN-02, MN-03 创建会议纪要测试。"""

    @pytest.mark.asyncio
    async def test_create_registered_success(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-01: 正常登记（正文空）→ REGISTERED，外部参会人不发通知（Q-D13）。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1, 2], external=["外部参会人A"]),
            client_token="test-token-001",
        )

        result = await service.create_minutes(request)

        assert result["data"].status == "REGISTERED"
        assert result["data"].code.startswith("MM")
        assert len(result["data"].code) >= 11
        assert not result["warnings"]
        assert "外部参会人A" in result["data"].attendees.external

    @pytest.mark.asyncio
    async def test_create_recorded_success(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-03-01: 正常录入（正文非空+行动项）→ MINUTES_RECORDED。"""
        from app.domains.meet.schemas import (
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting with Summary",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1, 2], external=["外部人员"]),
            summary="<p>This is the meeting summary.</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=2,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-002",
        )

        result = await service.create_minutes(request)

        assert result["data"].status == "MINUTES_RECORDED"
        assert len(result["data"].action_items) == 1
        from app.domains.sys.models import TodoItem
        todo = db_session.query(TodoItem).filter(
            TodoItem.source_type == "MEET_ACTION_ITEM",
            TodoItem.assignee_user_id == 2,
            TodoItem.deleted == 0,
        ).one()
        assert todo.todo_type == "确认"
        assert todo.status == "PENDING"
        assert todo.source_id == result["data"].action_items[0].id

    @pytest.mark.asyncio
    async def test_create_title_too_long(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-02: 主题 129 字 → 1001。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq

        with pytest.raises(ValueError):
            MeetingMinutesCreateReq(
                title="A" * 129,
                meeting_date=get_now(),
                attendees=AttendeesSchema(internal=[1], external=[]),
                client_token="test-token-003",
            )

    @pytest.mark.asyncio
    async def test_create_empty_attendees(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-03: 参会人为空 → 1001。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq

        with pytest.raises(ValueError):
            MeetingMinutesCreateReq(
                title="Test Meeting",
                meeting_date=get_now(),
                attendees=AttendeesSchema(internal=[], external=[]),
                client_token="test-token-004",
            )

    @pytest.mark.asyncio
    async def test_create_recorder_not_exists(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-05: 记录人不存在 → 1500。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=get_now(),
            recorder_user_id=9999,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-005",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1500

    @pytest.mark.asyncio
    async def test_create_recorder_resigned(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-06: 记录人已离职 → 1501。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=get_now(),
            recorder_user_id=4,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-006",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1501

    @pytest.mark.asyncio
    async def test_create_attendee_not_exists(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-07: 内部参会人不存在 → 1500。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=get_now(),
            attendees=AttendeesSchema(internal=[1, 9999], external=[]),
            client_token="test-token-attendee-not-exist",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1500

    @pytest.mark.asyncio
    async def test_create_attendee_frozen(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-08: 内部参会人已冻结 → 1501。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=get_now(),
            attendees=AttendeesSchema(internal=[1, 6], external=[]),
            client_token="test-token-attendee-frozen",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1501

    @pytest.mark.asyncio
    async def test_create_assignee_not_exists(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-AI-01-03: 行动项责任人不存在 → 1500。"""
        from app.domains.meet.schemas import (
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=9999,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-assignee-not-exist",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1500

    @pytest.mark.asyncio
    async def test_create_action_item_due_yesterday(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-03-02: 行动项期限为昨天 → 1001。"""
        from app.domains.meet.schemas import (
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        yesterday = (now - timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1, 2], external=[]),
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=2,
                    due_date=yesterday,
                )
            ],
            client_token="test-token-007",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1001

    @pytest.mark.asyncio
    async def test_create_action_item_due_today(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-MN-03-04: 行动项期限=今天 → 成功（Q-D10 边界）。"""
        from app.domains.meet.schemas import (
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        now = datetime(2026, 10, 13, 9, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        service = MeetingService()

        today = now.date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1, 2], external=[]),
            action_items=[
                ActionItemCreateSchema(
                    description="Action due today",
                    assignee_user_id=2,
                    due_date=today,
                )
            ],
            client_token="test-token-due-today",
        )

        result = await service.create_minutes(request)
        assert result["data"].action_items[0].due_date == today


class TestTimeBoundaries:
    """时钟边界测试：刚好24h、刚好48h、跨零点；全部用 get_now()。"""

    @pytest.mark.asyncio
    async def test_create_exactly_24h_no_warning(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-MN-03-05: 会后刚好 24h 录入 → 无 warnings（边界前）。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        service = MeetingService()

        meeting_time = now - timedelta(hours=24)

        request = MeetingMinutesCreateReq(
            title="Exactly 24h Meeting",
            meeting_date=meeting_time,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Recording at exactly 24h</p>",
            client_token="test-token-24h-exact",
        )

        result = await service.create_minutes(request)

        assert 1116 not in result["warnings"]

    @pytest.mark.asyncio
    async def test_create_over_24h_warning(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-MN-03-03: 会后超过 24h 录入 → warnings 含 1116。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        service = MeetingService()

        meeting_time = now - timedelta(hours=24, minutes=1)

        request = MeetingMinutesCreateReq(
            title="Over 24h Meeting",
            meeting_date=meeting_time,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Late recording</p>",
            client_token="test-token-over-24h",
        )

        result = await service.create_minutes(request)

        assert 1116 in result["warnings"]

    @pytest.mark.asyncio
    async def test_archive_exactly_48h_no_warning(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-MN-05-05: 会后刚好 48h 归档 → 无 warnings（边界前）。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        service = MeetingService()

        meeting_time = now - timedelta(hours=48)

        request = MeetingMinutesCreateReq(
            title="Exactly 48h Archive Meeting",
            meeting_date=meeting_time,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            client_token="test-token-48h-exact",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        archive_result = await service.archive_minutes(minutes_id)

        assert 1116 not in archive_result["warnings"]

    @pytest.mark.asyncio
    async def test_archive_over_48h_warning(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-MN-05-06: 会后超过 48h 归档 → warnings 含 1116。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        service = MeetingService()

        meeting_time = now - timedelta(hours=48, minutes=1)

        request = MeetingMinutesCreateReq(
            title="Over 48h Archive Meeting",
            meeting_date=meeting_time,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            client_token="test-token-over-48h",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        archive_result = await service.archive_minutes(minutes_id)

        assert 1116 in archive_result["warnings"]

    @pytest.mark.asyncio
    async def test_cross_midnight_boundary(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-MN-03-06: 跨零点场景（23:59 会议，次日 00:01 录入）。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        now = datetime(2026, 10, 14, 0, 1, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        service = MeetingService()

        meeting_time = datetime(2026, 10, 13, 23, 59, 0, tzinfo=BEIJING_TZ)

        request = MeetingMinutesCreateReq(
            title="Cross Midnight Meeting",
            meeting_date=meeting_time,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Cross midnight recording</p>",
            client_token="test-token-cross-midnight",
        )

        result = await service.create_minutes(request)

        assert 1116 not in result["warnings"]


class TestMeetingMinutesList:
    """MN-01 列表查询测试。"""

    @pytest.mark.asyncio
    async def test_list_no_permission(self, db_session, meet_no_perm_context, sample_users_for_meet):
        """UT-B18-MN-01-04: 无 query/query-self → 1008。"""
        from app.domains.meet.router import list_minutes

        ctx.set(meet_no_perm_context)
        with pytest.raises(BizError) as exc:
            await list_minutes()

        assert exc.value.code == 1008


class TestMeetingMinutesArchive:
    """MN-05 归档测试。"""

    @pytest.mark.asyncio
    async def test_archive_registered_fails(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-05-02: REGISTERED 归档 → 1001，文案含"请先录入纪要"。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-archive-001",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        with pytest.raises(BizError) as exc:
            await service.archive_minutes(minutes_id)

        assert exc.value.code == 1001
        assert "请先录入纪要" in exc.value.msg

    @pytest.mark.asyncio
    async def test_archive_success(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-05-01: 正常归档 → ARCHIVED。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Summary content</p>",
            client_token="test-token-archive-002",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        archive_result = await service.archive_minutes(minutes_id)

        assert archive_result["data"].status == "ARCHIVED"
        assert archive_result["data"].archived_at is not None

    @pytest.mark.asyncio
    async def test_archive_already_archived(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-05-03: 已归档再归档 → 1117，文案含"已归档"。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Summary content</p>",
            client_token="test-token-archive-003",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        await service.archive_minutes(minutes_id)

        with pytest.raises(BizError) as exc:
            await service.archive_minutes(minutes_id)

        assert exc.value.code == 1117
        assert "已归档" in exc.value.msg


class TestMeetingMinutesAppendix:
    """MN-06 附录测试。"""

    @pytest.mark.asyncio
    async def test_appendix_not_archived(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-06-02: 未归档追加附录 → 1117，文案含"未归档"。"""
        from app.domains.meet.schemas import (
            AppendixCreateReq,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Summary content</p>",
            client_token="test-token-appendix-001",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        appendix_req = AppendixCreateReq(content="This is an appendix")

        with pytest.raises(BizError) as exc:
            await service.add_appendix(minutes_id, appendix_req)

        assert exc.value.code == 1117
        assert "未归档" in exc.value.msg

    @pytest.mark.asyncio
    async def test_appendix_success(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-06-01: 已归档追加附录 → 成功。"""
        from app.domains.meet.schemas import (
            AppendixCreateReq,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Summary content</p>",
            client_token="test-token-appendix-002",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        await service.archive_minutes(minutes_id)

        appendix_req = AppendixCreateReq(content="This is an appendix")
        appendix_result = await service.add_appendix(minutes_id, appendix_req)

        assert len(appendix_result.appendices) == 1


class TestMeetingMinutesDelete:
    """MN-07 删除测试。"""

    @pytest.mark.asyncio
    async def test_delete_archived_fails(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-07-02: 删除已归档 → 1117，文案含"已归档"。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Summary content</p>",
            client_token="test-token-delete-001",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        await service.archive_minutes(minutes_id)

        with pytest.raises(BizError) as exc:
            await service.delete_minutes(minutes_id)

        assert exc.value.code == 1117
        assert "已归档" in exc.value.msg

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-07-01: 删除未归档 → 成功。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-delete-002",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        await service.delete_minutes(minutes_id)

        with pytest.raises(BizError) as exc:
            await service.get_minutes(minutes_id)

        assert exc.value.code == 1504


class TestActionItemClose:
    """AI-02 行动项回填测试。"""

    @pytest.mark.asyncio
    async def test_close_not_assignee(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-AI-02-02: 非责任人回填 → 1118，文案含"非行动项责任人"。"""
        from app.domains.meet.models import MeetingActionItem
        from app.domains.meet.schemas import (
            ActionItemCloseReq,
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1, 2], external=[]),
            summary="<p>Summary</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=2,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-close-001",
        )

        result = await service.create_minutes(request)

        session = get_db_session()
        item = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == int(result["data"].id),
            MeetingActionItem.deleted == 0,
        ).first()

        close_req = ActionItemCloseReq(close_remark="Completed")

        with pytest.raises(BizError) as exc:
            await service.close_action_item(item.id, close_req)

        assert exc.value.code == 1118
        assert "非行动项责任人" in exc.value.msg

    @pytest.mark.asyncio
    async def test_close_invalid_url(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-AI-02-03: evidenceUrl 为 javascript:xxx → 1001。"""
        from app.domains.meet.models import MeetingActionItem
        from app.domains.meet.schemas import (
            ActionItemCloseReq,
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1, 2], external=[]),
            summary="<p>Summary</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=1,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-close-002",
        )

        result = await service.create_minutes(request)

        session = get_db_session()
        item = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == int(result["data"].id),
            MeetingActionItem.deleted == 0,
        ).first()

        close_req = ActionItemCloseReq(
            close_remark="Completed",
            evidence_url="javascript:alert(1)",
        )

        with pytest.raises(BizError) as exc:
            await service.close_action_item(item.id, close_req)

        assert exc.value.code == 1001


class TestArchiveRate:
    """ST-01 留痕率统计测试。"""

    @pytest.mark.asyncio
    async def test_archive_rate_no_permission(self, db_session, meet_no_perm_context, sample_users_for_meet):
        """UT-B18-ST-01-02: 无 supervise 权限 → 1008。"""
        from app.domains.meet.router import get_archive_rate

        ctx.set(meet_no_perm_context)
        with pytest.raises(BizError) as exc:
            await get_archive_rate()

        assert exc.value.code == 1008

    @pytest.mark.asyncio
    async def test_archive_rate_empty(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-ST-01-03: 分母为 0 → archiveRate = 100。"""
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        result = await service.get_archive_rate()

        assert result.total_meetings == 0
        assert result.archive_rate == 100.0


class TestExternalAttendeeAsAssignee:
    """Q-D13: 外部参会人当责任人测试。"""

    @pytest.mark.asyncio
    async def test_external_cannot_be_assignee(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-Q-D13-01: 外部参会人不能当责任人 → 1001（只有内部用户可做责任人）。"""
        from app.domains.meet.schemas import (
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=["外部人员张三"]),
            summary="<p>Content</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=9999,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-external-assignee",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1500


class TestRecorderDefault:
    """Q-D10: 记录人默认当前用户测试。"""

    @pytest.mark.asyncio
    async def test_recorder_defaults_to_current_user(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-Q-D10-01: 不指定记录人时默认当前登录用户。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1, 2], external=[]),
            client_token="test-token-recorder-default",
        )

        result = await service.create_minutes(request)

        assert result["data"].recorder_user_id == str(meet_admin_context.user_id)


class TestSecurityCrossTenant:
    """安全测试：跨租户 1504 覆盖全部接口。"""

    @pytest.fixture
    def other_tenant_context(self):
        """他租户上下文。"""
        context = RequestContext(
            trace_id="other-tenant-trace",
            user_id=100,
            tenant_id=999,
            perm_codes={
                "ims:meet:minutes:query",
                "ims:meet:minutes:add",
                "ims:meet:minutes:edit",
                "ims:meet:minutes:archive",
                "ims:meet:minutes:delete",
                "ims:meet:minutes:appendix",
                "ims:meet:minutes:supervise",
            },
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.mark.asyncio
    async def test_cross_tenant_get_minutes(self, db_session, meet_admin_context, sample_users_for_meet, other_tenant_context):
        """UT-B18-SEC-01: 跨租户获取详情 → 1504。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Tenant 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-cross-001",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(other_tenant_context)

        with pytest.raises(BizError) as exc:
            await service.get_minutes(minutes_id)

        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_cross_tenant_update_minutes(self, db_session, meet_admin_context, sample_users_for_meet, other_tenant_context):
        """UT-B18-SEC-02: 跨租户编辑 → 1504。"""
        from app.domains.meet.schemas import (
            AttendeesSchema,
            MeetingMinutesCreateReq,
            MeetingMinutesUpdateReq,
        )
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Tenant 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-cross-002",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(other_tenant_context)

        update_req = MeetingMinutesUpdateReq(
            title="Hacked Title",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            base_version=1,
        )

        with pytest.raises(BizError) as exc:
            await service.update_minutes(minutes_id, update_req)

        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_cross_tenant_archive(self, db_session, meet_admin_context, sample_users_for_meet, other_tenant_context):
        """UT-B18-SEC-03: 跨租户归档 → 1504。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Tenant 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            client_token="test-token-cross-003",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(other_tenant_context)

        with pytest.raises(BizError) as exc:
            await service.archive_minutes(minutes_id)

        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_cross_tenant_appendix(self, db_session, meet_admin_context, sample_users_for_meet, other_tenant_context):
        """UT-B18-SEC-04: 跨租户附录 → 1504。"""
        from app.domains.meet.schemas import (
            AppendixCreateReq,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Tenant 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            client_token="test-token-cross-004",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        await service.archive_minutes(minutes_id)

        ctx.set(other_tenant_context)

        appendix_req = AppendixCreateReq(content="Hacked appendix")

        with pytest.raises(BizError) as exc:
            await service.add_appendix(minutes_id, appendix_req)

        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_cross_tenant_delete(self, db_session, meet_admin_context, sample_users_for_meet, other_tenant_context):
        """UT-B18-SEC-05: 跨租户删除 → 1504。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Tenant 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-cross-005",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(other_tenant_context)

        with pytest.raises(BizError) as exc:
            await service.delete_minutes(minutes_id)

        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_cross_tenant_close_action_item(self, db_session, meet_admin_context, sample_users_for_meet, other_tenant_context):
        """UT-B18-SEC-06: 跨租户回填行动项 → 1504。"""
        from app.domains.meet.models import MeetingActionItem
        from app.domains.meet.schemas import (
            ActionItemCloseReq,
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Tenant 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=1,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-cross-006",
        )
        result = await service.create_minutes(request)

        session = get_db_session()
        item = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == int(result["data"].id),
            MeetingActionItem.deleted == 0,
        ).first()

        ctx.set(other_tenant_context)

        close_req = ActionItemCloseReq(close_remark="Hacked close")

        with pytest.raises(BizError) as exc:
            await service.close_action_item(item.id, close_req)

        assert exc.value.code == 1504


class TestSecurityDataScope:
    """安全测试：数据范围校验。"""

    @pytest.fixture
    def other_dept_context(self):
        """他部门上下文（DEPT 范围）。"""
        context = RequestContext(
            trace_id="other-dept-trace",
            user_id=10,
            tenant_id=1,
            perm_codes={
                "ims:meet:minutes:query",
                "ims:meet:minutes:edit",
                "ims:meet:minutes:archive",
                "ims:meet:minutes:delete",
                "ims:meet:minutes:appendix",
            },
            data_scopes=[{"scope_type": "DEPT", "role_id": 2}],
            dept_ids=[99],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.mark.asyncio
    async def test_data_scope_get_other_dept(self, db_session, meet_admin_context, sample_users_for_meet, other_dept_context):
        """UT-B18-SEC-07: DEPT 范围获取他部门会议 → 1504。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Dept 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-scope-001",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(other_dept_context)

        with pytest.raises(BizError) as exc:
            await service.get_minutes(minutes_id)

        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_data_scope_edit_other_dept(self, db_session, meet_admin_context, sample_users_for_meet, other_dept_context):
        """UT-B18-SEC-08: DEPT 范围编辑他部门会议 → 1504。"""
        from app.domains.meet.schemas import (
            AttendeesSchema,
            MeetingMinutesCreateReq,
            MeetingMinutesUpdateReq,
        )
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Dept 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-scope-002",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(other_dept_context)

        update_req = MeetingMinutesUpdateReq(
            title="Hacked Title",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            base_version=1,
        )

        with pytest.raises(BizError) as exc:
            await service.update_minutes(minutes_id, update_req)

        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_data_scope_archive_other_dept(self, db_session, meet_admin_context, sample_users_for_meet, other_dept_context):
        """UT-B18-SEC-09: DEPT 范围归档他部门会议 → 1504。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Dept 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            client_token="test-token-scope-003",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(other_dept_context)

        with pytest.raises(BizError) as exc:
            await service.archive_minutes(minutes_id)

        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_data_scope_delete_other_dept(self, db_session, meet_admin_context, sample_users_for_meet, other_dept_context):
        """UT-B18-SEC-10: DEPT 范围删除他部门会议 → 1504。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Dept 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-scope-004",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(other_dept_context)

        with pytest.raises(BizError) as exc:
            await service.delete_minutes(minutes_id)

        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_action_item_close_scope_before_assignee(self, db_session, meet_admin_context, sample_users_for_meet, other_dept_context):
        """UT-B18-SEC-11: 回填先校验数据范围再校验责任人（不在范围 → 1504，不泄露存在性）。"""
        from app.domains.meet.models import MeetingActionItem
        from app.domains.meet.schemas import (
            ActionItemCloseReq,
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Dept 1 Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=1,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-scope-005",
        )
        result = await service.create_minutes(request)

        session = get_db_session()
        item = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == int(result["data"].id),
            MeetingActionItem.deleted == 0,
        ).first()

        ctx.set(other_dept_context)

        close_req = ActionItemCloseReq(close_remark="Trying to close")

        with pytest.raises(BizError) as exc:
            await service.close_action_item(item.id, close_req)

        assert exc.value.code == 1504


class TestSecurityFrozenResigned:
    """安全测试：1501 冻结/离职用户。"""

    @pytest.mark.asyncio
    async def test_resigned_user_as_recorder(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-SEC-12: 离职用户作为记录人 → 1501。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            recorder_user_id=4,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-resigned-001",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1501

    @pytest.mark.asyncio
    async def test_resigned_user_as_attendee(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-SEC-13: 离职用户作为参会人 → 1501。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1, 4], external=[]),
            client_token="test-token-resigned-002",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1501

    @pytest.mark.asyncio
    async def test_resigned_user_as_assignee(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-SEC-14: 离职用户作为行动项责任人 → 1501。"""
        from app.domains.meet.schemas import (
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=4,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-resigned-003",
        )

        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)

        assert exc.value.code == 1501


class TestPermissionChecks:
    """权限校验测试（1008 无权限）。"""

    @pytest.fixture
    def recorder_context(self):
        """记录人上下文（无 archive/appendix/delete 权限）。"""
        context = RequestContext(
            trace_id="recorder-trace",
            user_id=5,
            tenant_id=1,
            perm_codes={
                "ims:meet:minutes:query",
                "ims:meet:minutes:add",
            },
            data_scopes=[{"scope_type": "ALL", "role_id": 1}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        )
        ctx.set(context)
        yield context
        ctx.reset()

    @pytest.mark.asyncio
    async def test_archive_no_permission(self, db_session, meet_admin_context, sample_users_for_meet, recorder_context):
        """UT-B18-MN-05-04: 非记录人无 archive 权限归档 → 1008。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService
        from app.domains.sys.models import User

        session = db_session
        user5 = User(
            id=5,
            tenant_id=1,
            username="user5",
            nickname="User 5",
            main_dept_id=1,
            status="ACTIVE",
            source="LOCAL",
        )
        session.add(user5)
        session.flush()

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            recorder_user_id=1,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            client_token="test-token-perm-001",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(recorder_context)

        from app.domains.meet.router import archive_minutes
        with pytest.raises(BizError) as exc:
            await archive_minutes(minutes_id)

        assert exc.value.code == 1008

    @pytest.mark.asyncio
    async def test_appendix_no_permission(self, db_session, meet_admin_context, sample_users_for_meet, recorder_context):
        """UT-B18-MN-06-03: 非记录人无 appendix 权限附录 → 1008。"""
        from app.domains.meet.schemas import (
            AppendixCreateReq,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService
        from app.domains.sys.models import User

        session = db_session
        if not session.query(User).filter(User.id == 5).first():
            user5 = User(
                id=5,
                tenant_id=1,
                username="user5",
                nickname="User 5",
                main_dept_id=1,
                status="ACTIVE",
                source="LOCAL",
            )
            session.add(user5)
            session.flush()

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            recorder_user_id=1,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            client_token="test-token-perm-002",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        await service.archive_minutes(minutes_id)

        ctx.set(recorder_context)

        from app.domains.meet.router import add_appendix
        appendix_req = AppendixCreateReq(content="Appendix content")
        with pytest.raises(BizError) as exc:
            await add_appendix(minutes_id, appendix_req)

        assert exc.value.code == 1008

    @pytest.mark.asyncio
    async def test_delete_no_permission(self, db_session, meet_admin_context, sample_users_for_meet, recorder_context):
        """UT-B18-MN-07-03: 无 delete 权限删除 → 1008。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService
        from app.domains.sys.models import User

        session = db_session
        if not session.query(User).filter(User.id == 5).first():
            user5 = User(
                id=5,
                tenant_id=1,
                username="user5",
                nickname="User 5",
                main_dept_id=1,
                status="ACTIVE",
                source="LOCAL",
            )
            session.add(user5)
            session.flush()

        ctx.set(meet_admin_context)
        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            recorder_user_id=1,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-perm-003",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        ctx.set(recorder_context)

        from app.domains.meet.router import delete_minutes
        with pytest.raises(BizError) as exc:
            await delete_minutes(minutes_id)

        assert exc.value.code == 1008


class TestClosedActionItem:
    """已闭环行动项测试。"""

    @pytest.mark.asyncio
    async def test_close_already_closed(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-AI-02-04: 已闭环再回填 → 1001。"""
        from app.domains.meet.models import MeetingActionItem
        from app.domains.meet.schemas import (
            ActionItemCloseReq,
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=1,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-closed-001",
        )
        result = await service.create_minutes(request)

        session = get_db_session()
        item = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == int(result["data"].id),
            MeetingActionItem.deleted == 0,
        ).first()

        close_req = ActionItemCloseReq(close_remark="Completed")
        await service.close_action_item(item.id, close_req)

        with pytest.raises(BizError) as exc:
            await service.close_action_item(item.id, close_req)

        assert exc.value.code == 1001


class TestOptimisticLock:
    """乐观锁测试（version 列 1001）。"""

    @pytest.mark.asyncio
    async def test_version_mismatch(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-04-06: 乐观锁版本不匹配 → 1001，文案含"数据已被修改"。"""
        from app.domains.meet.schemas import (
            AttendeesSchema,
            MeetingMinutesCreateReq,
            MeetingMinutesUpdateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Content</p>",
            client_token="test-token-lock-001",
        )

        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)

        update_req1 = MeetingMinutesUpdateReq(
            title="Test Meeting Updated",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Updated by user 1</p>",
            decisions=[],
            action_items=[],
            base_version=1,
        )
        await service.update_minutes(minutes_id, update_req1)

        update_req2 = MeetingMinutesUpdateReq(
            title="Test Meeting Updated Again",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Updated by user 2</p>",
            decisions=[],
            action_items=[],
            base_version=1,
        )

        with pytest.raises(BizError) as exc:
            await service.update_minutes(minutes_id, update_req2)

        assert exc.value.code == 1001
        assert "数据已被修改" in exc.value.msg


class TestValidationTests:
    """参数校验测试（1001）。"""

    @pytest.mark.asyncio
    async def test_external_attendee_name_too_long(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-Q-D13-02: 外部参会人姓名超过 32 字 → 1001（Q-D13）。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq

        with pytest.raises(ValueError):
            MeetingMinutesCreateReq(
                title="Test Meeting",
                meeting_date=get_now(),
                attendees=AttendeesSchema(internal=[1], external=["A" * 33]),
                client_token="test-token-val-001",
            )

    @pytest.mark.asyncio
    async def test_summary_within_limit(self, db_session, meet_admin_context, sample_users_for_meet):
        """正文在 20000 字以内 → 成功。"""
        from app.domains.meet.schemas import AttendeesSchema, MeetingMinutesCreateReq
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        long_summary = "<p>" + "测" * 10000 + "</p>"

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary=long_summary,
            client_token="test-token-val-002",
        )

        result = await service.create_minutes(request)
        assert result["data"].status == "MINUTES_RECORDED"

    @pytest.mark.asyncio
    async def test_decision_content_within_limit(self, db_session, meet_admin_context, sample_users_for_meet):
        """决议内容在 512 字以内 → 成功。"""
        from app.domains.meet.schemas import (
            AttendeesSchema,
            DecisionCreateSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            decisions=[
                DecisionCreateSchema(content="D" * 512)
            ],
            client_token="test-token-val-003",
        )

        result = await service.create_minutes(request)
        assert len(result["data"].decisions) == 1

    @pytest.mark.asyncio
    async def test_evidence_url_invalid_scheme(self, db_session, meet_admin_context, sample_users_for_meet):
        """证据链接 file:// → 1001。"""
        from app.domains.meet.models import MeetingActionItem
        from app.domains.meet.schemas import (
            ActionItemCloseReq,
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Summary</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=1,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-val-004",
        )

        result = await service.create_minutes(request)

        session = get_db_session()
        item = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == int(result["data"].id),
            MeetingActionItem.deleted == 0,
        ).first()

        close_req = ActionItemCloseReq(
            close_remark="Completed",
            evidence_url="file:///etc/passwd",
        )

        with pytest.raises(BizError) as exc:
            await service.close_action_item(item.id, close_req)

        assert exc.value.code == 1001

    @pytest.mark.asyncio
    async def test_evidence_url_data_scheme(self, db_session, meet_admin_context, sample_users_for_meet):
        """证据链接 data: → 1001。"""
        from app.domains.meet.models import MeetingActionItem
        from app.domains.meet.schemas import (
            ActionItemCloseReq,
            ActionItemCreateSchema,
            AttendeesSchema,
            MeetingMinutesCreateReq,
        )
        from app.domains.meet.service import MeetingService

        service = MeetingService()

        now = get_now()
        tomorrow = (now + timedelta(days=1)).date()

        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Summary</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1",
                    assignee_user_id=1,
                    due_date=tomorrow,
                )
            ],
            client_token="test-token-val-005",
        )

        result = await service.create_minutes(request)

        session = get_db_session()
        item = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == int(result["data"].id),
            MeetingActionItem.deleted == 0,
        ).first()

        close_req = ActionItemCloseReq(
            close_remark="Completed",
            evidence_url="data:text/html,<script>alert(1)</script>",
        )

        with pytest.raises(BizError) as exc:
            await service.close_action_item(item.id, close_req)

        assert exc.value.code == 1001


class TestMeetingReminderJob:
    """ST-02: 24h/48h 提醒任务测试。"""

    @pytest.mark.asyncio
    async def test_24h_boundary_before(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-ST-02-01: 超 23h 未录纪要（边界前）→ 未发送。"""
        from app.domains.meet.jobs import meeting_reminder_job
        from app.domains.meet.models import MeetingMinutes

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        meeting_time = now - timedelta(hours=23, minutes=59)
        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101301",
            title="Test Meeting 23h",
            meeting_date=meeting_time,
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="REGISTERED",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        stats = await meeting_reminder_job()

        assert stats["reminded_24h"] == 0
        db_session.refresh(minutes)
        assert minutes.remind_24h_at is None

    @pytest.mark.asyncio
    async def test_24h_boundary_after(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-ST-02-02: 超 24h 未录纪要（边界后）→ 记录人收到消息，remind_24h_at 有值。"""
        from app.domains.meet.jobs import meeting_reminder_job
        from app.domains.meet.models import MeetingMinutes

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        meeting_time = now - timedelta(hours=24, minutes=1)
        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101302",
            title="Test Meeting 24h",
            meeting_date=meeting_time,
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="REGISTERED",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        stats = await meeting_reminder_job()

        assert stats["reminded_24h"] >= 1
        db_session.refresh(minutes)
        assert minutes.remind_24h_at is not None

    @pytest.mark.asyncio
    async def test_48h_boundary_before(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-ST-02-03: 超 47h 未归档（边界前）→ 未发送。"""
        from app.domains.meet.jobs import meeting_reminder_job
        from app.domains.meet.models import MeetingMinutes

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        meeting_time = now - timedelta(hours=47, minutes=59)
        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101303",
            title="Test Meeting 47h",
            meeting_date=meeting_time,
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        stats = await meeting_reminder_job()

        assert stats["reminded_48h"] == 0
        db_session.refresh(minutes)
        assert minutes.remind_48h_at is None

    @pytest.mark.asyncio
    async def test_48h_boundary_after(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-ST-02-04: 超 48h 未归档（边界后）→ 记录人+supervise 收到消息。"""
        from app.domains.meet.jobs import meeting_reminder_job
        from app.domains.meet.models import MeetingMinutes

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        meeting_time = now - timedelta(hours=48, minutes=1)
        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101304",
            title="Test Meeting 48h",
            meeting_date=meeting_time,
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        stats = await meeting_reminder_job()

        assert stats["reminded_48h"] >= 1
        db_session.refresh(minutes)
        assert minutes.remind_48h_at is not None

    @pytest.mark.asyncio
    async def test_idempotent_no_repeat(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-ST-02-05: 任务幂等（重入测试）→ 第二次运行不重复发送。"""
        from app.domains.meet.jobs import meeting_reminder_job
        from app.domains.meet.models import MeetingMinutes

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        meeting_time = now - timedelta(hours=25)
        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101305",
            title="Test Meeting Idempotent",
            meeting_date=meeting_time,
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="REGISTERED",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        await meeting_reminder_job()
        stats2 = await meeting_reminder_job()

        assert stats2["reminded_24h"] == 0

    @pytest.mark.asyncio
    async def test_recorder_resigned_skip(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-ST-02-06: 记录人已离职 → 不推送。"""
        from app.domains.meet.jobs import meeting_reminder_job
        from app.domains.meet.models import MeetingMinutes

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)

        meeting_time = now - timedelta(hours=25)
        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101306",
            title="Test Meeting Resigned",
            meeting_date=meeting_time,
            dept_id=1,
            recorder_user_id=4,
            attendees={"internal": [4], "external": []},
            status="REGISTERED",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        stats = await meeting_reminder_job()

        assert stats["skipped_resigned"] >= 1


class TestMeetingOverdueJob:
    """AI-03: 逾期推送与升级任务测试。"""

    @pytest.mark.asyncio
    async def test_overdue_1d_boundary_before(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-AI-03-01: 逾期刚好 1 天（边界前，get_now()）→ 未推送。"""
        from app.domains.meet.jobs import meeting_overdue_job
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes

        now = datetime(2026, 10, 13, 9, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        today = now.date()

        yesterday = today - timedelta(days=1)

        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101307",
            title="Test Overdue Meeting",
            meeting_date=now - timedelta(days=2),
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        item = MeetingActionItem(
            tenant_id=1,
            minutes_id=minutes.id,
            description="Overdue action",
            assignee_user_id=2,
            due_date=yesterday,
            status="OPEN",
        )
        db_session.add(item)
        db_session.flush()

        stats = await meeting_overdue_job()

        assert stats["marked_overdue"] >= 1
        assert stats["notified_1d"] == 0
        db_session.refresh(item)
        assert item.notified_at is None

    @pytest.mark.asyncio
    async def test_overdue_1d_boundary_after(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-AI-03-02: 逾期满 1 天（边界后）→ 责任人收到推送，数据范围外用户收不到。"""
        from app.domains.meet.jobs import meeting_overdue_job
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes

        now = datetime(2026, 10, 13, 9, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        today = now.date()

        two_days_ago = today - timedelta(days=2)

        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101308",
            title="Test Overdue Meeting 1d",
            meeting_date=now - timedelta(days=3),
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        item = MeetingActionItem(
            tenant_id=1,
            minutes_id=minutes.id,
            description="Overdue action 1d",
            assignee_user_id=2,
            due_date=two_days_ago,
            status="OPEN",
        )
        db_session.add(item)
        db_session.flush()

        stats = await meeting_overdue_job()

        assert stats["notified_1d"] >= 1
        db_session.refresh(item)
        assert item.notified_at is not None
        from app.domains.sys.models import InboxMessage
        recipients = {
            row.user_id
            for row in db_session.query(InboxMessage).filter(
                InboxMessage.title == "行动项逾期提醒",
            ).all()
        }
        assert recipients == {2}

    @pytest.mark.asyncio
    async def test_overdue_3d_boundary_before(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-AI-03-03: 逾期刚好 3 天（边界前）→ 未升级。"""
        from app.domains.meet.jobs import meeting_overdue_job
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes

        now = datetime(2026, 10, 13, 9, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        today = now.date()

        three_days_ago = today - timedelta(days=3)

        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101309",
            title="Test Overdue Meeting 3d",
            meeting_date=now - timedelta(days=5),
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        item = MeetingActionItem(
            tenant_id=1,
            minutes_id=minutes.id,
            description="Overdue action 3d boundary",
            assignee_user_id=2,
            due_date=three_days_ago,
            status="OPEN",
        )
        db_session.add(item)
        db_session.flush()

        await meeting_overdue_job()

        db_session.refresh(item)
        assert item.escalated_at is None

    @pytest.mark.asyncio
    async def test_overdue_3d_boundary_after(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-AI-03-04: 逾期满 3 天（边界后）→ supervise 用户收到升级推送，数据范围外用户收不到。"""
        from app.domains.meet.jobs import meeting_overdue_job
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes

        now = datetime(2026, 10, 13, 9, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        today = now.date()

        four_days_ago = today - timedelta(days=4)
        from app.domains.sys.models import Dept, Menu, Role, RoleMenu, User, UserRole

        child = Dept(
            id=15, tenant_id=1, parent_id=1, path="/1/15/",
            name="Child Dept", status="ENABLED", source="LOCAL",
        )
        db_session.add(child)
        for user_id, dept_id, name in ((71, 1, "allsup"), (72, 2, "outsidesup"), (73, 1, "parentsup")):
            db_session.add(User(
                id=user_id, tenant_id=1, username=name, nickname=name,
                main_dept_id=dept_id, status="ACTIVE", source="LOCAL",
            ))
        db_session.add(Menu(
            id=7701, tenant_id=1, parent_id=0, type="BUTTON", name="监督",
            perm_code="ims:meet:minutes:supervise", status="ENABLED",
        ))
        scopes = ((710, 71, "ALL"), (720, 72, "DEPT"), (730, 73, "DEPT"))
        for role_id, user_id, scope in scopes:
            db_session.add(Role(
                id=role_id, tenant_id=1, role_key=f"sup{role_id}", name=f"S{role_id}",
                source="MANUAL", status="ENABLED", data_scope=scope,
            ))
            db_session.add(RoleMenu(id=role_id * 10, tenant_id=1, role_id=role_id, menu_id=7701))
            db_session.add(UserRole(id=user_id * 10 + role_id, tenant_id=1, user_id=user_id, role_id=role_id))
        db_session.flush()

        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101310",
            title="Test Overdue Meeting 3d escalate",
            meeting_date=now - timedelta(days=6),
            dept_id=15,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        item = MeetingActionItem(
            tenant_id=1,
            minutes_id=minutes.id,
            description="Overdue action escalate",
            assignee_user_id=2,
            due_date=four_days_ago,
            status="OPEN",
        )
        db_session.add(item)
        db_session.flush()

        stats = await meeting_overdue_job()

        assert stats["escalated_3d"] >= 1
        db_session.refresh(item)
        assert item.escalated_at is not None
        from app.domains.sys.models import InboxMessage
        escalated = {
            row.user_id
            for row in db_session.query(InboxMessage).filter(
                InboxMessage.title == "行动项逾期升级",
            ).all()
        }
        assert 71 in escalated
        assert 73 in escalated
        assert 72 not in escalated

    @pytest.mark.asyncio
    async def test_overdue_idempotent(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-AI-03-05: 任务幂等（重入测试）→ 第二次运行不重复推送。"""
        from app.domains.meet.jobs import meeting_overdue_job
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes

        now = datetime(2026, 10, 13, 9, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        today = now.date()

        two_days_ago = today - timedelta(days=2)

        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101311",
            title="Test Overdue Idempotent",
            meeting_date=now - timedelta(days=4),
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        item = MeetingActionItem(
            tenant_id=1,
            minutes_id=minutes.id,
            description="Idempotent test action",
            assignee_user_id=2,
            due_date=two_days_ago,
            status="OPEN",
        )
        db_session.add(item)
        db_session.flush()

        await meeting_overdue_job()
        stats2 = await meeting_overdue_job()

        assert stats2["notified_1d"] == 0

    @pytest.mark.asyncio
    async def test_assignee_resigned_skip(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-AI-03-06: 责任人已离职 → 不推送。"""
        from app.domains.meet.jobs import meeting_overdue_job
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes

        now = datetime(2026, 10, 13, 9, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        today = now.date()

        two_days_ago = today - timedelta(days=2)

        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101312",
            title="Test Overdue Resigned",
            meeting_date=now - timedelta(days=4),
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        item = MeetingActionItem(
            tenant_id=1,
            minutes_id=minutes.id,
            description="Resigned assignee action",
            assignee_user_id=4,
            due_date=two_days_ago,
            status="OPEN",
        )
        db_session.add(item)
        db_session.flush()

        stats = await meeting_overdue_job()

        assert stats["skipped_resigned"] >= 1
        assert stats["notified_1d"] == 0
        db_session.refresh(item)
        assert item.notified_at is None

    @pytest.mark.asyncio
    async def test_resigned_assignee_still_escalates(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """离职责任人跳过 1 天推送，但仍升级给范围内的 supervise。"""
        from app.domains.meet.jobs import meeting_overdue_job
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes
        from app.domains.sys.models import InboxMessage, Menu, Role, RoleMenu, User, UserRole

        now = datetime(2026, 10, 13, 9, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        db_session.add(User(
            id=81, tenant_id=1, username="scope_sup", nickname="范围内",
            main_dept_id=1, status="ACTIVE", source="LOCAL",
        ))
        db_session.add(Menu(
            id=7702, tenant_id=1, parent_id=0, type="BUTTON", name="监督2",
            perm_code="ims:meet:minutes:supervise", status="ENABLED",
        ))
        db_session.add(Role(
            id=810, tenant_id=1, role_key="sup810", name="S810",
            source="MANUAL", status="ENABLED", data_scope="ALL",
        ))
        db_session.add(RoleMenu(id=8100, tenant_id=1, role_id=810, menu_id=7702))
        db_session.add(UserRole(id=8101, tenant_id=1, user_id=81, role_id=810))
        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101313",
            title="Resigned still escalate",
            meeting_date=now - timedelta(days=6),
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()
        item = MeetingActionItem(
            tenant_id=1,
            minutes_id=minutes.id,
            description="离职仍升级",
            assignee_user_id=4,
            due_date=now.date() - timedelta(days=4),
            status="OPEN",
        )
        db_session.add(item)
        db_session.flush()

        stats = await meeting_overdue_job()

        assert stats["skipped_resigned"] >= 1
        assert stats["escalated_3d"] >= 1
        db_session.refresh(item)
        assert item.escalated_at is not None
        recipients = {
            row.user_id
            for row in db_session.query(InboxMessage).filter(
                InboxMessage.title == "行动项逾期升级",
                InboxMessage.body.contains("离职仍升级"),
            ).all()
        }
        assert 81 in recipients
        assert 4 not in recipients

    @pytest.mark.asyncio
    async def test_48h_resigned_recorder_still_notifies_supervise(
        self, db_session, meet_admin_context, sample_users_for_meet, fixed_time,
    ):
        """Q-D9: 48h 记录人离职不推记录人，仍推范围内 supervise。"""
        from app.domains.meet.jobs import meeting_reminder_job
        from app.domains.meet.models import MeetingMinutes
        from app.domains.sys.models import InboxMessage, Menu, Role, RoleMenu, User, UserRole

        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        db_session.add(User(
            id=82, tenant_id=1, username="remind_sup", nickname="提醒监督",
            main_dept_id=1, status="ACTIVE", source="LOCAL",
        ))
        db_session.add(Menu(
            id=7703, tenant_id=1, parent_id=0, type="BUTTON", name="监督3",
            perm_code="ims:meet:minutes:supervise", status="ENABLED",
        ))
        db_session.add(Role(
            id=820, tenant_id=1, role_key="sup820", name="S820",
            source="MANUAL", status="ENABLED", data_scope="DEPT",
        ))
        db_session.add(RoleMenu(id=8200, tenant_id=1, role_id=820, menu_id=7703))
        db_session.add(UserRole(id=8201, tenant_id=1, user_id=82, role_id=820))
        minutes = MeetingMinutes(
            tenant_id=1,
            code="MM2026101314",
            title="48h resigned recorder",
            meeting_date=now - timedelta(hours=50),
            dept_id=1,
            recorder_user_id=4,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>Content</p>",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()

        stats = await meeting_reminder_job()

        assert stats["skipped_resigned"] >= 1
        assert stats["reminded_48h"] >= 1
        recipients = {
            row.user_id
            for row in db_session.query(InboxMessage).filter(
                InboxMessage.title == "会议纪要归档提醒",
            ).all()
        }
        assert 82 in recipients
        assert 4 not in recipients
