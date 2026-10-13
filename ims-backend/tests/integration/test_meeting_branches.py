# tests/integration/test_meeting_branches.py
"""补齐会议服务和定时任务的分支，供 P0 门禁统计。"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.cache import Cache
from app.core.clock import BEIJING_TZ, get_now
from app.core.context import RequestContext, ctx
from app.core.errors import BizError
from app.core.pagination import PageParam
from app.domains.meet.jobs import _get_supervise_users_for_minutes
from app.domains.meet.service import MeetingService, _sanitize_html, _validate_url


def _user(session, user_id, dept_id, status="ACTIVE"):
    from app.domains.sys.models import User

    row = User(
        id=user_id,
        tenant_id=1,
        username=f"u{user_id}",
        nickname=f"U{user_id}",
        main_dept_id=dept_id,
        status=status,
        source="LOCAL",
    )
    session.add(row)
    return row


def _dept(session, dept_id, path):
    from app.domains.sys.models import Dept

    row = Dept(
        id=dept_id,
        tenant_id=1,
        parent_id=0,
        path=path,
        name=f"D{dept_id}",
        status="ENABLED",
        source="LOCAL",
    )
    session.add(row)
    return row


def _role(session, role_id, scope, status="ENABLED"):
    from app.domains.sys.models import Role

    row = Role(
        id=role_id,
        tenant_id=1,
        role_key=f"r{role_id}",
        name=f"R{role_id}",
        source="MANUAL",
        status=status,
        data_scope=scope,
    )
    session.add(row)
    return row


_bind_seq = 88000


def _bind(session, role_id, user_id, menu_id):
    from app.domains.sys.models import RoleMenu, UserRole

    global _bind_seq
    session.flush()
    exists = session.query(RoleMenu).filter(
        RoleMenu.role_id == role_id,
        RoleMenu.menu_id == menu_id,
    ).first()
    if exists is None:
        _bind_seq += 1
        session.add(RoleMenu(id=_bind_seq, tenant_id=1, role_id=role_id, menu_id=menu_id))
    _bind_seq += 1
    session.add(UserRole(id=_bind_seq, tenant_id=1, user_id=user_id, role_id=role_id))


@pytest.fixture
def admin_ctx():
    context = RequestContext(
        trace_id="branch",
        user_id=1,
        tenant_id=1,
        perm_codes={"ims:meet:minutes:query", "ims:meet:minutes:supervise"},
        data_scopes=[{"scope_type": "ALL"}],
        dept_ids=[1],
        client_ip="127.0.0.1",
    )
    ctx.set(context)
    yield context
    ctx.reset()


class TestSuperviseRecipients:
    def test_each_scope_and_empty_paths(self, db_session, admin_ctx):
        from app.domains.sys.models import Menu

        minutes = SimpleNamespace(
            tenant_id=1,
            dept_id=2,
            recorder_user_id=11,
            attendees={"internal": [12], "external": []},
        )
        assert _get_supervise_users_for_minutes(db_session, minutes) == []

        menu = Menu(
            id=8801,
            tenant_id=1,
            parent_id=0,
            type="BUTTON",
            name="监督",
            perm_code="ims:meet:minutes:supervise",
            status="ENABLED",
        )
        db_session.add(menu)
        db_session.flush()
        assert _get_supervise_users_for_minutes(db_session, minutes) == []

        disabled = _role(db_session, 881, "ALL", status="DISABLED")
        _bind(db_session, disabled.id, 21, menu.id)
        db_session.flush()
        assert _get_supervise_users_for_minutes(db_session, minutes) == []

        _dept(db_session, 1, "/1/")
        _dept(db_session, 2, "/1/2/")
        _dept(db_session, 9, "")
        all_role = _role(db_session, 882, "ALL")
        dept_role = _role(db_session, 883, "DEPT")
        self_role = _role(db_session, 884, "SELF")
        other_role = _role(db_session, 885, "IP_GROUP")
        empty_path_role = _role(db_session, 886, "DEPT")
        _user(db_session, 31, 1)
        _user(db_session, 32, 2)
        _user(db_session, 33, 1)
        _user(db_session, 34, None, status="RESIGNED")
        _user(db_session, 11, 9)
        _user(db_session, 12, 9)
        _user(db_session, 35, None)
        _user(db_session, 36, 9)
        _user(db_session, 37, 9)
        db_session.flush()
        assert _get_supervise_users_for_minutes(db_session, minutes) == []

        _bind(db_session, all_role.id, 31, menu.id)
        _bind(db_session, dept_role.id, 32, menu.id)
        _bind(db_session, dept_role.id, 33, menu.id)
        _bind(db_session, self_role.id, 11, menu.id)
        _bind(db_session, self_role.id, 12, menu.id)
        _bind(db_session, other_role.id, 35, menu.id)
        _bind(db_session, dept_role.id, 34, menu.id)
        _bind(db_session, empty_path_role.id, 36, menu.id)
        _bind(db_session, self_role.id, 37, menu.id)
        db_session.flush()

        found = set(_get_supervise_users_for_minutes(db_session, minutes))
        assert {31, 32, 33, 11, 12} <= found
        assert 34 not in found
        assert 35 not in found

        orphan = SimpleNamespace(
            tenant_id=1,
            dept_id=404,
            recorder_user_id=99,
            attendees=None,
        )
        missed = _get_supervise_users_for_minutes(db_session, orphan)
        assert 32 not in missed
        assert 31 in missed


class TestJobEdges:
    @pytest.mark.asyncio
    async def test_locks_and_missing_minutes(self, db_session, admin_ctx):
        from app.domains.meet.jobs import meeting_overdue_job, meeting_reminder_job
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes

        now = datetime(2026, 10, 13, 9, 0, tzinfo=BEIJING_TZ)
        _dept(db_session, 1, "/1/")
        _user(db_session, 1, 1)
        _user(db_session, 4, 1, status="RESIGNED")
        minutes = MeetingMinutes(
            tenant_id=1,
            code="MMLOCK001",
            title="Locked",
            meeting_date=now - timedelta(hours=30),
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="REGISTERED",
            version=1,
        )
        db_session.add(minutes)
        db_session.flush()
        Cache.setnx(f"meet:reminder:{minutes.id}:24h", "1", ttl=86400)
        stats = await meeting_reminder_job()
        assert stats["reminded_24h"] == 0

        item = MeetingActionItem(
            tenant_id=1,
            minutes_id=999999,
            description="gone",
            assignee_user_id=1,
            due_date=now.date() - timedelta(days=5),
            status="OPEN",
        )
        db_session.add(item)
        db_session.flush()
        Cache.setnx(f"meet:overdue:{item.id}:1d", "1", ttl=86400)
        overdue = await meeting_overdue_job()
        assert overdue["notified_1d"] == 0


class TestServiceBranches:
    @pytest.mark.asyncio
    async def test_list_update_archive_and_helpers(self, db_session, admin_ctx):
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes
        from app.domains.meet.schemas import (
            ActionItemCloseReq,
            ActionItemCreateSchema,
            AttendeesSchema,
            DecisionCreateSchema,
            MeetingMinutesCreateReq,
            MeetingMinutesUpdateReq,
        )

        _dept(db_session, 1, "/1/")
        _dept(db_session, 3, "/1/3/")
        _user(db_session, 1, 1)
        _user(db_session, 2, 1)
        db_session.flush()

        assert _sanitize_html(None) is None
        assert "<script>" not in (_sanitize_html("<p>ok</p><script>x</script>") or "")
        _validate_url(None)
        with pytest.raises(BizError) as exc:
            _validate_url("https://example.com/" + ("a" * 500))
        assert exc.value.code == 1001

        service = MeetingService()
        now = get_now()
        request = MeetingMinutesCreateReq(
            title="Branch Meeting",
            meeting_date=now - timedelta(hours=2),
            attendees=AttendeesSchema(internal=[1], external=["外"]),
            summary="<p>正文</p>",
            decisions=[DecisionCreateSchema(content="决议<b>")],
            action_items=[
                ActionItemCreateSchema(
                    description="待办",
                    assignee_user_id=1,
                    due_date=(now + timedelta(days=2)).date(),
                )
            ],
            client_token="branch-token-1",
        )
        created = await service.create_minutes(request)
        again = await service.create_minutes(request)
        assert again["data"].id == created["data"].id

        dup = MeetingMinutes(
            tenant_id=1,
            code=created["data"].code[:-3] + f"{int(created['data'].code[-3:]) + 1:03d}",
            title="占号",
            meeting_date=now,
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="REGISTERED",
            version=1,
        )
        db_session.add(dup)
        db_session.flush()
        await service.create_minutes(MeetingMinutesCreateReq(
            title="Next code",
            meeting_date=now,
            attendees=AttendeesSchema(internal=[1], external=[]),
            client_token="branch-token-2",
        ))

        listed = await service.list_minutes(
            PageParam(page_no=1, page_size=10),
            title="Branch",
            status="MINUTES_RECORDED",
            meeting_date_start=now - timedelta(days=2),
            meeting_date_end=now + timedelta(days=1),
        )
        assert listed.total >= 1

        row = db_session.query(MeetingMinutes).filter(
            MeetingMinutes.id == int(created["data"].id),
        ).one()
        row.attendees = {"internal": [1, 99], "external": ["外"]}
        item_row = db_session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == row.id,
            MeetingActionItem.deleted == 0,
        ).one()
        item_row.due_date = (now - timedelta(days=2)).date()
        db_session.flush()

        detail = await service.get_minutes(int(created["data"].id))
        assert detail.action_items[0].overdue_days is not None
        assert "99" in detail.attendee_names

        updated = await service.update_minutes(
            int(created["data"].id),
            MeetingMinutesUpdateReq(
                title="Branch Meeting",
                meeting_date=now - timedelta(hours=30),
                attendees=AttendeesSchema(internal=[1], external=[]),
                summary="<p>改</p>",
                decisions=[DecisionCreateSchema(content="新决议")],
                action_items=[
                    ActionItemCreateSchema(
                        description="新待办",
                        assignee_user_id=2,
                        due_date=(now + timedelta(days=2)).date(),
                    )
                ],
                base_version=detail.version,
            ),
        )
        assert 1116 in updated["warnings"]

        ctx.set(RequestContext(
            trace_id="dept",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            data_scopes=[{"scope_type": "DEPT"}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        ))
        visible = service._get_visible_dept_ids(include_children=True)
        assert 3 in visible
        assert service._get_visible_dept_ids(include_children=False) == [1]

        ctx.set(RequestContext(
            trace_id="obj",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            data_scopes=[SimpleNamespace(scope_type="DEPT")],
            dept_ids=[1],
            client_ip="127.0.0.1",
        ))
        assert service._get_visible_dept_ids(include_children=False) == [1]

        ctx.set(RequestContext(
            trace_id="empty",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            data_scopes=[],
            dept_ids=[],
            client_ip="127.0.0.1",
        ))
        assert service._get_visible_dept_ids() == []
        assert service._build_scope_filter(db_session, 1) is not None

        ctx.set(admin_ctx)
        rate = await service.get_archive_rate(
            date_range_start=now - timedelta(days=3),
            date_range_end=now + timedelta(hours=1),
        )
        assert rate.total_meetings >= 1

        closed = db_session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == int(created["data"].id),
            MeetingActionItem.deleted == 0,
            MeetingActionItem.assignee_user_id == 1,
        ).first()
        if closed is not None:
            await service.close_action_item(
                closed.id,
                ActionItemCloseReq(close_remark="完成", evidence_url="https://example.com/a"),
            )

        await service.delete_minutes(int(created["data"].id))


class TestRemainingBranches:
    @pytest.mark.asyncio
    async def test_scope_edges(self, db_session, admin_ctx):
        from app.domains.meet.models import MeetingActionItem, MeetingAppendix, MeetingMinutes
        from app.domains.meet.schemas import (
            ActionItemCloseReq,
            ActionItemCreateSchema,
            AppendixCreateReq,
            AttendeesSchema,
            MeetingMinutesCreateReq,
            MeetingMinutesUpdateReq,
        )

        _dept(db_session, 1, "/1/")
        _dept(db_session, 9, "")
        _user(db_session, 1, 1)
        _user(db_session, 40, None)
        db_session.flush()

        service = MeetingService()
        _validate_url("https://example.com/ok")
        assert service._get_user_main_dept_id(40) == 0

        ctx.set(RequestContext(
            trace_id="self",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            data_scopes=[{"scope_type": "SELF"}],
            dept_ids=[],
            client_ip="127.0.0.1",
        ))
        assert service._get_visible_dept_ids() == []

        ctx.set(RequestContext(
            trace_id="empty-path",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            data_scopes=[{"scope_type": "DEPT"}],
            dept_ids=[9],
            client_ip="127.0.0.1",
        ))
        assert 9 in service._get_visible_dept_ids(include_children=True)

        ctx.set(admin_ctx)
        now = get_now()
        external = AttendeesSchema(internal=[], external=["外宾"])
        created = await service.create_minutes(MeetingMinutesCreateReq(
            title="External only",
            meeting_date=now - timedelta(hours=1),
            attendees=external,
            client_token="branch-ext-1",
        ))
        minutes_id = int(created["data"].id)
        row = db_session.query(MeetingMinutes).filter(MeetingMinutes.id == minutes_id).one()
        brief = service._to_vo(row, include_details=False)
        assert brief.decisions == []
        assert brief.attendee_names == ["外宾"]

        ctx.set(RequestContext(
            trace_id="dept",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            data_scopes=[{"scope_type": "DEPT"}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        ))
        listed = await service.list_minutes(PageParam(page_no=1, page_size=10))
        assert listed.total >= 1

        detail = await service.get_minutes(minutes_id)
        updated = await service.update_minutes(
            minutes_id,
            MeetingMinutesUpdateReq(
                title="External only",
                meeting_date=now - timedelta(hours=1),
                attendees=external,
                summary="<p>记</p>",
                base_version=detail.version,
            ),
        )
        assert updated["data"].status == "MINUTES_RECORDED"

        with_item = await service.create_minutes(MeetingMinutesCreateReq(
            title="With item",
            meeting_date=now - timedelta(hours=2),
            attendees=AttendeesSchema(internal=[1], external=[]),
            summary="<p>已录</p>",
            action_items=[
                ActionItemCreateSchema(
                    description="待办",
                    assignee_user_id=1,
                    due_date=(now + timedelta(days=1)).date(),
                )
            ],
            client_token="branch-item-1",
        ))
        item_minutes_id = int(with_item["data"].id)
        open_item = db_session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == item_minutes_id,
            MeetingActionItem.deleted == 0,
        ).one()
        await service.close_action_item(
            open_item.id,
            ActionItemCloseReq(close_remark="完成"),
        )
        await service.update_minutes(
            item_minutes_id,
            MeetingMinutesUpdateReq(
                title="With item",
                meeting_date=now - timedelta(hours=2),
                attendees=AttendeesSchema(internal=[1], external=[]),
                summary="<p>已录</p>",
                action_items=[
                    ActionItemCreateSchema(
                        description="新待办",
                        assignee_user_id=1,
                        due_date=(now + timedelta(days=3)).date(),
                    )
                ],
                base_version=with_item["data"].version,
            ),
        )
        with pytest.raises(BizError) as past_due:
            await service.update_minutes(
                item_minutes_id,
                MeetingMinutesUpdateReq(
                    title="With item",
                    meeting_date=now - timedelta(hours=2),
                    attendees=AttendeesSchema(internal=[1], external=[]),
                    summary="<p>已录</p>",
                    action_items=[
                        ActionItemCreateSchema(
                            description="过期",
                            assignee_user_id=1,
                            due_date=(now - timedelta(days=1)).date(),
                        )
                    ],
                    base_version=with_item["data"].version + 1,
                ),
            )
        assert past_due.value.code == 1001

        other = await service.create_minutes(MeetingMinutesCreateReq(
            title="Other assignee",
            meeting_date=now - timedelta(hours=3),
            attendees=AttendeesSchema(internal=[1], external=[]),
            action_items=[
                ActionItemCreateSchema(
                    description="别人的",
                    assignee_user_id=1,
                    due_date=(now + timedelta(days=1)).date(),
                )
            ],
            client_token="branch-item-2",
        ))
        other_id = int(other["data"].id)
        other_item = db_session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == other_id,
            MeetingActionItem.deleted == 0,
        ).one()
        ctx.set(RequestContext(
            trace_id="not-owner",
            user_id=2,
            tenant_id=1,
            perm_codes=set(),
            data_scopes=[{"scope_type": "DEPT"}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        ))
        with pytest.raises(BizError) as denied:
            await service.close_action_item(
                other_item.id,
                ActionItemCloseReq(close_remark="不行"),
            )
        assert denied.value.code == 1118

        ctx.set(RequestContext(
            trace_id="dept-again",
            user_id=1,
            tenant_id=1,
            perm_codes=set(),
            data_scopes=[{"scope_type": "DEPT"}],
            dept_ids=[1],
            client_ip="127.0.0.1",
        ))
        db_session.add(MeetingAppendix(
            tenant_id=1,
            minutes_id=other_id,
            content="手工附录",
        ))
        db_session.flush()
        await service.delete_minutes(other_id)

        archived = await service.archive_minutes(minutes_id)
        assert archived["data"].status == "ARCHIVED"
        with pytest.raises(BizError) as locked:
            await service.update_minutes(
                minutes_id,
                MeetingMinutesUpdateReq(
                    title="External only",
                    meeting_date=now - timedelta(hours=1),
                    attendees=external,
                    summary="<p>记</p>",
                    base_version=detail.version,
                ),
            )
        assert locked.value.code == 1117
        appendix = await service.add_appendix(minutes_id, AppendixCreateReq(content="补充"))
        assert appendix.appendices

        rate = await service.get_archive_rate()
        assert rate.total_meetings >= 1

    @pytest.mark.asyncio
    async def test_job_locks_and_empty_recipients(self, db_session, admin_ctx, fixed_time):
        from app.domains.meet.jobs import meeting_overdue_job, meeting_reminder_job
        from app.domains.meet.models import MeetingActionItem, MeetingMinutes
        from app.domains.sys.models import Menu, RoleMenu, UserRole

        now = datetime(2026, 10, 13, 9, 0, tzinfo=BEIJING_TZ)
        fixed_time(now)
        _dept(db_session, 1, "/1/")
        _user(db_session, 1, 1)
        _user(db_session, 4, 1, status="RESIGNED")
        _user(db_session, 31, 1)
        _user(db_session, 34, 1, status="RESIGNED")
        menu = Menu(
            id=8901,
            tenant_id=1,
            parent_id=0,
            type="BUTTON",
            name="监督",
            perm_code="ims:meet:minutes:supervise",
            status="ENABLED",
        )
        db_session.add(menu)
        role = _role(db_session, 891, "ALL")
        db_session.flush()
        db_session.add(RoleMenu(id=89101, tenant_id=1, role_id=role.id, menu_id=menu.id))
        db_session.flush()
        sample = SimpleNamespace(
            tenant_id=1,
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [], "external": []},
        )
        assert _get_supervise_users_for_minutes(db_session, sample) == []

        db_session.add(UserRole(id=89102, tenant_id=1, user_id=34, role_id=role.id))
        db_session.flush()
        assert _get_supervise_users_for_minutes(db_session, sample) == []

        db_session.add(UserRole(id=89103, tenant_id=1, user_id=31, role_id=role.id))
        resigned = MeetingMinutes(
            tenant_id=1,
            code="MMLOCK48R",
            title="离职记录人",
            meeting_date=now - timedelta(hours=50),
            dept_id=1,
            recorder_user_id=4,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>x</p>",
            version=1,
        )
        locked = MeetingMinutes(
            tenant_id=1,
            code="MMLOCK48L",
            title="48h 已锁",
            meeting_date=now - timedelta(hours=50),
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>x</p>",
            version=1,
        )
        host = MeetingMinutes(
            tenant_id=1,
            code="MMOVERDUE",
            title="逾期宿主",
            meeting_date=now - timedelta(hours=1),
            dept_id=1,
            recorder_user_id=1,
            attendees={"internal": [1], "external": []},
            status="MINUTES_RECORDED",
            summary="<p>x</p>",
            version=1,
        )
        db_session.add_all([resigned, locked, host])
        db_session.flush()
        Cache.setnx(f"meet:reminder:{locked.id}:48h", "1", ttl=86400)

        locked_item = MeetingActionItem(
            tenant_id=1,
            minutes_id=host.id,
            description="1d locked",
            assignee_user_id=1,
            due_date=now.date() - timedelta(days=2),
            status="OPEN",
        )
        escalate_locked = MeetingActionItem(
            tenant_id=1,
            minutes_id=host.id,
            description="3d locked",
            assignee_user_id=1,
            due_date=now.date() - timedelta(days=4),
            status="OVERDUE",
            notified_at=now,
        )
        escalate = MeetingActionItem(
            tenant_id=1,
            minutes_id=host.id,
            description="3d send",
            assignee_user_id=1,
            due_date=now.date() - timedelta(days=4),
            status="OPEN",
        )
        db_session.add_all([locked_item, escalate_locked, escalate])
        db_session.flush()
        Cache.setnx(f"meet:overdue:{locked_item.id}:1d", "1", ttl=86400)
        Cache.setnx(f"meet:overdue:{escalate_locked.id}:3d", "1", ttl=86400)

        reminder = await meeting_reminder_job()
        assert reminder["skipped_resigned"] >= 1
        assert reminder["reminded_48h"] == 0

        overdue = await meeting_overdue_job()
        assert overdue["escalated_3d"] >= 1
        assert overdue["messages_sent"] >= 1
