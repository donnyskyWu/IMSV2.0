# tests/integration/test_meeting.py - Meeting module tests (B18-M18)
"""
Meeting module integration tests.

Tests use real MySQL/Redis when available (CI), fallback to SQLite for local dev.
All tests per §6 of 会议-实现理解.md.
"""

import pytest
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from app.core.clock import set_clock, reset_clock, BEIJING_TZ
from app.core.context import RequestContext, ctx
from app.core.errors import BizError
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
    from app.domains.sys.models import User, Dept
    
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
    
    db_session.flush()
    
    return {"user1": user1, "user2": user2, "user3": user3, "resigned": resigned_user}


class TestMeetingMinutesCreate:
    """MN-02, MN-03 创建会议纪要测试。"""

    @pytest.mark.asyncio
    async def test_create_registered_success(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-01: 正常登记（正文空）→ REGISTERED。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1, 2], external=[]),
            client_token="test-token-001",
        )
        
        result = await service.create_minutes(request)
        
        assert result["data"].status == "REGISTERED"
        assert result["data"].code.startswith("MM")
        assert len(result["data"].code) >= 11
        assert not result["warnings"]

    @pytest.mark.asyncio
    async def test_create_recorded_success(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-03-01: 正常录入（正文非空+行动项）→ MINUTES_RECORDED。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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

    @pytest.mark.asyncio
    async def test_create_title_too_long(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-02: 主题 129 字 → 1001。"""
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        with pytest.raises(ValueError):
            MeetingMinutesCreateReq(
                title="A" * 129,
                meeting_date=datetime.now(BEIJING_TZ),
                attendees=AttendeesSchema(internal=[1], external=[]),
                client_token="test-token-003",
            )

    @pytest.mark.asyncio
    async def test_create_empty_attendees(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-03: 参会人为空 → 1001。"""
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        with pytest.raises(ValueError):
            MeetingMinutesCreateReq(
                title="Test Meeting",
                meeting_date=datetime.now(BEIJING_TZ),
                attendees=AttendeesSchema(internal=[], external=[]),
                client_token="test-token-004",
            )

    @pytest.mark.asyncio
    async def test_create_recorder_not_exists(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-02-05: 记录人不存在 → 1500。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=datetime.now(BEIJING_TZ),
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        request = MeetingMinutesCreateReq(
            title="Test Meeting",
            meeting_date=datetime.now(BEIJING_TZ),
            recorder_user_id=4,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="test-token-006",
        )
        
        with pytest.raises(BizError) as exc:
            await service.create_minutes(request)
        
        assert exc.value.code == 1501

    @pytest.mark.asyncio
    async def test_create_action_item_due_yesterday(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-03-02: 行动项期限为昨天 → 1001。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
    async def test_create_late_recording_warning(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """UT-B18-MN-03-03: 会后 30h 录入 → warnings 含 1116。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        
        service = MeetingService()
        
        meeting_time = now - timedelta(hours=30)
        
        request = MeetingMinutesCreateReq(
            title="Late Recording Meeting",
            meeting_date=meeting_time,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Late recording</p>",
            client_token="test-token-008",
        )
        
        result = await service.create_minutes(request)
        
        assert 1116 in result["warnings"]


class TestMeetingMinutesList:
    """MN-01 列表查询测试。"""

    @pytest.mark.asyncio
    async def test_list_no_permission(self, db_session, meet_no_perm_context, sample_users_for_meet):
        """UT-B18-MN-01-04: 无 query/query-self → 1008。"""
        from app.domains.meet.router import list_minutes
        
        with pytest.raises(BizError) as exc:
            await list_minutes()
        
        assert exc.value.code == 1008


class TestMeetingMinutesArchive:
    """MN-05 归档测试。"""

    @pytest.mark.asyncio
    async def test_archive_registered_fails(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-05-02: REGISTERED 归档 → 1001。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        """UT-B18-MN-05-03: 已归档再归档 → 1117。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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


class TestMeetingMinutesAppendix:
    """MN-06 附录测试。"""

    @pytest.mark.asyncio
    async def test_appendix_not_archived(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-06-02: 未归档追加附录 → 1117。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, AppendixCreateReq
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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

    @pytest.mark.asyncio
    async def test_appendix_success(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-06-01: 已归档追加附录 → 成功。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, AppendixCreateReq
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        """UT-B18-MN-07-02: 删除已归档 → 1117。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-07-01: 删除未归档 → 成功。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        """UT-B18-AI-02-02: 非责任人回填 → 1118。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema, ActionItemCloseReq
        from app.domains.meet.models import MeetingActionItem
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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

    @pytest.mark.asyncio
    async def test_close_invalid_url(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-AI-02-03: evidenceUrl 为 javascript:xxx → 1001。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema, ActionItemCloseReq
        from app.domains.meet.models import MeetingActionItem
        from app.core.context import RequestContext
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
