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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, MeetingMinutesUpdateReq, AttendeesSchema
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, AppendixCreateReq
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema, ActionItemCloseReq
        from app.domains.meet.models import MeetingActionItem
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, MeetingMinutesUpdateReq, AttendeesSchema
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema, ActionItemCloseReq
        from app.domains.meet.models import MeetingActionItem
        
        ctx.set(meet_admin_context)
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
    """安全测试：1216 冻结/离职用户。"""

    @pytest.fixture
    def frozen_user_context(self):
        """冻结用户上下文。"""
        context = RequestContext(
            trace_id="frozen-user-trace",
            user_id=4,
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
    async def test_resigned_user_as_recorder(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-SEC-12: 离职用户作为记录人 → 1501。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
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
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, AppendixCreateReq
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
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
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
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema, ActionItemCloseReq
        from app.domains.meet.models import MeetingActionItem
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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

    @pytest.mark.asyncio
    async def test_edit_closed_action_item(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-04-05: 修改已闭环行动项 → 1001。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, MeetingMinutesUpdateReq, AttendeesSchema, ActionItemCreateSchema, ActionItemCloseReq
        from app.domains.meet.models import MeetingActionItem
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
            client_token="test-token-closed-002",
        )
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)
        
        session = get_db_session()
        item = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == minutes_id,
            MeetingActionItem.deleted == 0,
        ).first()
        
        close_req = ActionItemCloseReq(close_remark="Completed")
        await service.close_action_item(item.id, close_req)
        
        update_req = MeetingMinutesUpdateReq(
            title="Test Meeting Updated",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Updated content</p>",
            decisions=[],
            action_items=[
                ActionItemCreateSchema(
                    description="Action 1 Modified",
                    assignee_user_id=2,
                    due_date=tomorrow,
                )
            ],
            base_version=1,
        )
        
        pass


class TestArchiveWarnings:
    """归档警告测试。"""

    @pytest.mark.asyncio
    async def test_archive_over_48h_warning(self, db_session, meet_admin_context, sample_users_for_meet, fixed_time):
        """超 48h 归档 → warnings 含 1116。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        now = datetime(2026, 10, 13, 10, 0, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        
        service = MeetingService()
        
        meeting_time = now - timedelta(hours=50)
        
        request = MeetingMinutesCreateReq(
            title="Late Archive Meeting",
            meeting_date=meeting_time,
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>Late recording</p>",
            client_token="test-token-archive-warn-001",
        )
        
        result = await service.create_minutes(request)
        minutes_id = int(result["data"].id)
        
        archive_result = await service.archive_minutes(minutes_id)
        
        assert 1116 in archive_result["warnings"]


class TestValidationTests:
    """参数校验测试（1001）。"""

    @pytest.mark.asyncio
    async def test_external_attendee_name_too_long(self, db_session, meet_admin_context, sample_users_for_meet):
        """外部参会人姓名超过 32 字 → 1001。"""
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        with pytest.raises(ValueError):
            MeetingMinutesCreateReq(
                title="Test Meeting",
                meeting_date=datetime.now(BEIJING_TZ),
                attendees=AttendeesSchema(internal=[1], external=["A" * 33]),
                client_token="test-token-val-001",
            )

    @pytest.mark.asyncio
    async def test_summary_within_limit(self, db_session, meet_admin_context, sample_users_for_meet):
        """正文在 20000 字以内 → 成功。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, DecisionCreateSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
        
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema, ActionItemCloseReq
        from app.domains.meet.models import MeetingActionItem
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, AttendeesSchema, ActionItemCreateSchema, ActionItemCloseReq
        from app.domains.meet.models import MeetingActionItem
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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


class TestOptimisticLock:
    """乐观锁测试（version 列 1001）。"""

    @pytest.mark.asyncio
    async def test_version_mismatch(self, db_session, meet_admin_context, sample_users_for_meet):
        """UT-B18-MN-04-06: 乐观锁版本不匹配 → 1001。"""
        from app.domains.meet.service import MeetingService
        from app.domains.meet.schemas import MeetingMinutesCreateReq, MeetingMinutesUpdateReq, AttendeesSchema
        
        service = MeetingService()
        
        now = datetime.now(BEIJING_TZ)
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
