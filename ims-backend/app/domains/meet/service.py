# app/domains/meet/service.py - Meeting service (B18-M18)
"""
Meeting service.

Implements:
- MN-01~MN-08: Meeting minutes CRUD
- AI-01~AI-03: Action item management
- ST-01: Archive rate statistics
"""

import html
import re
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import and_, func, literal, or_, select

from app.core.clock import get_now
from app.core.context import ctx
from app.core.errors import BizError
from app.core.pagination import PageParam, PageResult
from app.db.session import get_db_session
from app.db.transaction import transactional
from app.domains.meet.models import (
    MeetingActionItem,
    MeetingAppendix,
    MeetingClientToken,
    MeetingDecision,
    MeetingMinutes,
)
from app.domains.meet.schemas import (
    ActionItemCloseReq,
    ActionItemVO,
    AppendixCreateReq,
    AppendixVO,
    ArchiveRateResp,
    AttendeesSchema,
    DecisionVO,
    MeetingMinutesCreateReq,
    MeetingMinutesListVO,
    MeetingMinutesUpdateReq,
    MeetingMinutesVO,
    UnarchivedMinutesVO,
)

SUMMARY_ALLOWED_TAGS = {"p", "br", "strong", "em", "u", "ol", "ul", "li", "span"}


def _sanitize_html(html_str: Optional[str]) -> Optional[str]:
    """白名单净化富文本 HTML。"""
    if not html_str:
        return html_str

    tag_pattern = re.compile(r"<(/?)(\w+)([^>]*)>", re.IGNORECASE)

    def replace_tag(match: re.Match) -> str:
        closing = match.group(1)
        tag = match.group(2).lower()
        if tag in SUMMARY_ALLOWED_TAGS:
            return f"<{closing}{tag}>"
        return ""

    sanitized = tag_pattern.sub(replace_tag, html_str)
    return sanitized


def _escape_html(text: str) -> str:
    """HTML 转义。"""
    return html.escape(text)


def _validate_url(url: Optional[str]) -> None:
    """校验 URL 仅允许 http/https。"""
    if not url:
        return

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise BizError(1001, msg="证据链接仅支持 http/https")

    if len(url) > 512:
        raise BizError(1001, msg="证据链接不能超过 512 字符")


class MeetingService:
    """会议纪要服务。"""

    def _get_visible_dept_ids(self, include_children: bool = True) -> Optional[list[int]]:
        """获取当前用户可见的部门 ID 列表，ALL 范围返回 None。"""
        context = ctx.current_or_none
        if not context or not context.data_scopes:
            return []

        scope_types = set()
        for scope in context.data_scopes:
            if isinstance(scope, dict):
                scope_types.add(scope.get("scope_type"))
            else:
                scope_types.add(getattr(scope, "scope_type", None))

        if "ALL" in scope_types:
            return None

        if "DEPT" in scope_types and context.dept_ids:
            if include_children:
                from app.domains.sys.models import Dept
                session = get_db_session()
                all_dept_ids = set(context.dept_ids)

                depts = session.query(Dept).filter(
                    Dept.id.in_(context.dept_ids),
                    Dept.tenant_id == ctx.tenant_id,
                    Dept.deleted == 0,
                ).all()

                for dept in depts:
                    if dept.path:
                        child_ids = session.query(Dept.id).filter(
                            Dept.path.like(f"{dept.path}%"),
                            Dept.tenant_id == ctx.tenant_id,
                            Dept.deleted == 0,
                        ).all()
                        all_dept_ids.update(d.id for d in child_ids)

                return list(all_dept_ids)
            return list(context.dept_ids)

        return []

    def _build_scope_filter(self, session: Any, user_id: int) -> Any:
        """
        构建数据范围过滤条件。

        Q-D11: dept 范围 OR 本人相关
        本人相关：recorder_user_id = 当前用户 OR attendees.internal 包含当前用户 OR 行动项责任人 = 当前用户
        """
        dept_ids = self._get_visible_dept_ids()

        conditions = []

        if dept_ids is None:
            return None

        if dept_ids:
            conditions.append(MeetingMinutes.dept_id.in_(dept_ids))

        self_condition = or_(
            MeetingMinutes.recorder_user_id == user_id,
            func.json_contains(
                MeetingMinutes.attendees,
                literal(str(user_id)),
                literal("$.internal"),
            ),
            MeetingMinutes.id.in_(
                select(MeetingActionItem.minutes_id).where(
                    MeetingActionItem.assignee_user_id == user_id,
                    MeetingActionItem.deleted == 0,
                )
            ),
        )

        if conditions:
            return or_(and_(*conditions), self_condition)
        else:
            return self_condition

    def _check_user_exists_and_active(self, user_id: int) -> None:
        """校验用户存在且启用。"""
        from app.domains.sys.models import User
        session = get_db_session()

        user = session.query(User).filter(
            User.id == user_id,
            User.tenant_id == ctx.tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1500)

        if user.status in ("FROZEN", "RESIGNED"):
            raise BizError(1501)

    def _generate_code(self, meeting_date: datetime) -> str:
        """生成会议编号 MM + yyyyMMdd + 3 位流水。"""
        from app.core.cache import Cache

        session = get_db_session()
        date_str = meeting_date.strftime("%Y%m%d")
        prefix = f"MM{date_str}"

        cache_key = f"meet:code:{ctx.tenant_id}:{date_str}"
        seq = Cache.incr(cache_key, ttl=86400 * 2)

        code = f"{prefix}{seq:04d}" if seq > 999 else f"{prefix}{seq:03d}"

        existing = session.query(MeetingMinutes).filter(
            MeetingMinutes.tenant_id == ctx.tenant_id,
            MeetingMinutes.code == code,
            MeetingMinutes.deleted == 0,
        ).first()

        if existing:
            return self._generate_code(meeting_date)

        return code

    def _check_idempotency(self, client_token: str) -> Optional[int]:
        """检查幂等键，返回已存在的结果 ID。"""
        session = get_db_session()
        now = get_now()

        token_record = session.query(MeetingClientToken).filter(
            MeetingClientToken.tenant_id == ctx.tenant_id,
            MeetingClientToken.client_token == client_token,
            MeetingClientToken.expires_at > now,
        ).first()

        if token_record and token_record.result_id:
            return token_record.result_id

        return None

    def _save_idempotency(self, client_token: str, result_id: int) -> None:
        """保存幂等键。"""
        session = get_db_session()
        now = get_now()

        token_record = MeetingClientToken(
            tenant_id=ctx.tenant_id,
            client_token=client_token,
            result_id=result_id,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        session.add(token_record)
        session.flush()

    def _get_user_main_dept_id(self, user_id: int) -> int:
        """获取用户主部门 ID。"""
        from app.domains.sys.models import User
        session = get_db_session()

        user = session.query(User).filter(
            User.id == user_id,
            User.tenant_id == ctx.tenant_id,
            User.deleted == 0,
        ).first()

        if not user or not user.main_dept_id:
            return 0

        return user.main_dept_id

    def _get_user_name(self, user_id: int) -> Optional[str]:
        """获取用户姓名。"""
        from app.domains.sys.models import User
        session = get_db_session()

        user = session.query(User).filter(
            User.id == user_id,
            User.deleted == 0,
        ).first()

        return user.nickname if user else None

    def _get_dept_name(self, dept_id: int) -> Optional[str]:
        """获取部门名称。"""
        from app.domains.sys.models import Dept
        session = get_db_session()

        dept = session.query(Dept).filter(
            Dept.id == dept_id,
            Dept.deleted == 0,
        ).first()

        return dept.name if dept else None

    def _to_vo(self, minutes: MeetingMinutes, include_details: bool = False) -> MeetingMinutesVO:
        """转换为 VO。"""
        session = get_db_session()

        from app.domains.sys.models import User

        action_items = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == minutes.id,
            MeetingActionItem.deleted == 0,
        ).all()

        action_item_count = len(action_items)
        action_item_closed_count = sum(1 for a in action_items if a.status == "CLOSED")

        attendee_names = []
        attendees = minutes.attendees or {}
        internal_ids = attendees.get("internal", [])

        if internal_ids:
            users = session.query(User).filter(User.id.in_(internal_ids)).all()
            user_map = {u.id: u.nickname for u in users}
            attendee_names = [user_map.get(uid, str(uid)) for uid in internal_ids]

        attendee_names.extend(attendees.get("external", []))

        vo = MeetingMinutesVO(
            id=str(minutes.id),
            code=minutes.code,
            title=minutes.title,
            meeting_date=minutes.meeting_date,
            meeting_room=minutes.meeting_room,
            dept_id=str(minutes.dept_id),
            dept_name=self._get_dept_name(minutes.dept_id),
            recorder_user_id=str(minutes.recorder_user_id),
            recorder_name=self._get_user_name(minutes.recorder_user_id),
            attendees=AttendeesSchema(**attendees),
            attendee_names=attendee_names,
            summary=minutes.summary,
            status=minutes.status,
            archived_at=minutes.archived_at,
            archived_by=str(minutes.archived_by) if minutes.archived_by else None,
            archived_by_name=self._get_user_name(minutes.archived_by) if minutes.archived_by else None,
            create_time=minutes.create_time,
            update_time=minutes.update_time,
            version=minutes.version,
            action_item_count=action_item_count,
            action_item_closed_count=action_item_closed_count,
            decisions=[],
            action_items=[],
            appendices=[],
        )

        if include_details:
            decisions = session.query(MeetingDecision).filter(
                MeetingDecision.minutes_id == minutes.id,
                MeetingDecision.deleted == 0,
            ).order_by(MeetingDecision.seq).all()

            vo.decisions = [
                DecisionVO(id=str(d.id), seq=d.seq, content=d.content)
                for d in decisions
            ]

            now = get_now().date()
            vo.action_items = []
            for a in action_items:
                overdue_days = None
                if a.status != "CLOSED" and a.due_date < now:
                    overdue_days = (now - a.due_date).days

                vo.action_items.append(ActionItemVO(
                    id=str(a.id),
                    description=a.description,
                    assignee_user_id=str(a.assignee_user_id),
                    assignee_name=self._get_user_name(a.assignee_user_id),
                    due_date=a.due_date,
                    status=a.status,
                    close_remark=a.close_remark,
                    evidence_url=a.evidence_url,
                    closed_at=a.closed_at,
                    overdue_days=overdue_days,
                ))

            appendices = session.query(MeetingAppendix).filter(
                MeetingAppendix.minutes_id == minutes.id,
                MeetingAppendix.deleted == 0,
            ).order_by(MeetingAppendix.create_time.desc()).all()

            vo.appendices = [
                AppendixVO(
                    id=str(a.id),
                    content=a.content,
                    creator_name=self._get_user_name(a.creator),
                    create_time=a.create_time,
                )
                for a in appendices
            ]

        return vo

    @transactional
    async def create_minutes(self, request: MeetingMinutesCreateReq) -> dict[str, Any]:
        """
        创建会议纪要 (MN-02, MN-03).

        Returns:
            {"data": MeetingMinutesVO, "warnings": [int]}
        """
        session = get_db_session()
        warnings = []

        existing_id = self._check_idempotency(request.client_token)
        if existing_id:
            minutes = session.query(MeetingMinutes).filter(
                MeetingMinutes.id == existing_id,
                MeetingMinutes.deleted == 0,
            ).first()
            if minutes:
                return {"data": self._to_vo(minutes, include_details=True), "warnings": []}

        recorder_user_id = request.recorder_user_id or ctx.user_id
        self._check_user_exists_and_active(recorder_user_id)

        for uid in request.attendees.internal:
            self._check_user_exists_and_active(uid)

        for item in request.action_items:
            self._check_user_exists_and_active(item.assignee_user_id)

            if item.due_date < get_now().date():
                raise BizError(1001, msg="行动项截止日期不能早于今天")

        dept_id = self._get_user_main_dept_id(recorder_user_id)

        now = get_now()
        hours_since = (now - request.meeting_date).total_seconds() / 3600
        if hours_since > 24:
            warnings.append(1116)

        status = "MINUTES_RECORDED" if request.summary else "REGISTERED"

        summary = _sanitize_html(request.summary) if request.summary else None

        code = self._generate_code(request.meeting_date)

        minutes = MeetingMinutes(
            tenant_id=ctx.tenant_id,
            code=code,
            title=request.title,
            meeting_date=request.meeting_date,
            meeting_room=request.meeting_room,
            dept_id=dept_id,
            recorder_user_id=recorder_user_id,
            attendees={
                "internal": request.attendees.internal,
                "external": request.attendees.external,
            },
            summary=summary,
            status=status,
            version=1,
        )
        session.add(minutes)
        session.flush()

        for i, decision in enumerate(request.decisions, start=1):
            d = MeetingDecision(
                tenant_id=ctx.tenant_id,
                minutes_id=minutes.id,
                seq=i,
                content=_escape_html(decision.content),
            )
            session.add(d)

        for item in request.action_items:
            a = MeetingActionItem(
                tenant_id=ctx.tenant_id,
                minutes_id=minutes.id,
                description=_escape_html(item.description),
                assignee_user_id=item.assignee_user_id,
                due_date=item.due_date,
                status="OPEN",
            )
            session.add(a)
            session.flush()

        session.flush()

        self._save_idempotency(request.client_token, minutes.id)

        return {"data": self._to_vo(minutes, include_details=True), "warnings": warnings}

    async def list_minutes(
        self,
        page_param: PageParam,
        title: Optional[str] = None,
        meeting_date_start: Optional[datetime] = None,
        meeting_date_end: Optional[datetime] = None,
        status: Optional[str] = None,
    ) -> PageResult:
        """列表查询 (MN-01)。"""
        session = get_db_session()

        query = session.query(MeetingMinutes).filter(
            MeetingMinutes.tenant_id == ctx.tenant_id,
            MeetingMinutes.deleted == 0,
        )

        scope_filter = self._build_scope_filter(session, ctx.user_id)
        if scope_filter is not None:
            query = query.filter(scope_filter)

        if title:
            query = query.filter(MeetingMinutes.title.like(f"%{title}%"))

        if not meeting_date_start:
            meeting_date_start = get_now() - timedelta(days=30)
        if not meeting_date_end:
            meeting_date_end = get_now()

        query = query.filter(
            MeetingMinutes.meeting_date >= meeting_date_start,
            MeetingMinutes.meeting_date <= meeting_date_end,
        )

        if status:
            query = query.filter(MeetingMinutes.status == status)

        total = query.count()

        offset = (page_param.page_no - 1) * page_param.page_size
        minutes_list = query.order_by(MeetingMinutes.meeting_date.desc()).offset(
            offset
        ).limit(page_param.page_size).all()

        items = []
        for m in minutes_list:
            action_items = session.query(MeetingActionItem).filter(
                MeetingActionItem.minutes_id == m.id,
                MeetingActionItem.deleted == 0,
            ).all()

            attendees = m.attendees or {}
            attendee_names = []

            from app.domains.sys.models import User
            internal_ids = attendees.get("internal", [])
            if internal_ids:
                users = session.query(User).filter(User.id.in_(internal_ids)).all()
                user_map = {u.id: u.nickname for u in users}
                attendee_names = [user_map.get(uid, str(uid)) for uid in internal_ids[:3]]

            items.append(MeetingMinutesListVO(
                id=str(m.id),
                code=m.code,
                title=m.title,
                meeting_date=m.meeting_date,
                recorder_user_id=str(m.recorder_user_id),
                recorder_name=self._get_user_name(m.recorder_user_id),
                attendee_names=attendee_names,
                status=m.status,
                archived_at=m.archived_at,
                action_item_count=len(action_items),
                action_item_closed_count=sum(1 for a in action_items if a.status == "CLOSED"),
            ))

        return PageResult(
            list=[item.model_dump() for item in items],
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    async def get_minutes(self, minutes_id: int) -> MeetingMinutesVO:
        """获取详情 (MN-08)。"""
        session = get_db_session()

        minutes = session.query(MeetingMinutes).filter(
            MeetingMinutes.id == minutes_id,
            MeetingMinutes.tenant_id == ctx.tenant_id,
            MeetingMinutes.deleted == 0,
        ).first()

        if not minutes:
            raise BizError(1504)

        scope_filter = self._build_scope_filter(session, ctx.user_id)
        if scope_filter is not None:
            check_query = session.query(MeetingMinutes).filter(
                MeetingMinutes.id == minutes_id,
                scope_filter,
            ).first()
            if not check_query:
                raise BizError(1504)

        return self._to_vo(minutes, include_details=True)

    @transactional
    async def update_minutes(self, minutes_id: int, request: MeetingMinutesUpdateReq) -> dict[str, Any]:
        """编辑纪要 (MN-03, MN-04)。"""
        session = get_db_session()
        warnings = []

        minutes = session.query(MeetingMinutes).filter(
            MeetingMinutes.id == minutes_id,
            MeetingMinutes.tenant_id == ctx.tenant_id,
            MeetingMinutes.deleted == 0,
        ).first()

        if not minutes:
            raise BizError(1504)

        scope_filter = self._build_scope_filter(session, ctx.user_id)
        if scope_filter is not None:
            check_query = session.query(MeetingMinutes).filter(
                MeetingMinutes.id == minutes_id,
                scope_filter,
            ).first()
            if not check_query:
                raise BizError(1504)

        if minutes.status == "ARCHIVED":
            raise BizError(1117, msg="已归档纪要不可修改")

        if minutes.version != request.base_version:
            raise BizError(1001, msg="数据已被修改，请刷新后重试")

        recorder_user_id = request.recorder_user_id or minutes.recorder_user_id
        self._check_user_exists_and_active(recorder_user_id)

        for uid in request.attendees.internal:
            self._check_user_exists_and_active(uid)

        existing_items = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == minutes_id,
            MeetingActionItem.deleted == 0,
        ).all()

        for item in existing_items:
            if item.status == "CLOSED":
                for new_item in request.action_items:
                    if hasattr(new_item, "id") and new_item.id == item.id:
                        raise BizError(1001, msg="已闭环行动项不可修改")

        for item in request.action_items:
            self._check_user_exists_and_active(item.assignee_user_id)
            if item.due_date < get_now().date():
                raise BizError(1001, msg="行动项截止日期不能早于今天")

        now = get_now()
        hours_since = (now - request.meeting_date).total_seconds() / 3600
        if hours_since > 24:
            warnings.append(1116)

        minutes.title = request.title
        minutes.meeting_date = request.meeting_date
        minutes.meeting_room = request.meeting_room
        minutes.recorder_user_id = recorder_user_id
        minutes.attendees = {
            "internal": request.attendees.internal,
            "external": request.attendees.external,
        }
        minutes.summary = _sanitize_html(request.summary) if request.summary else None

        if minutes.summary and minutes.status == "REGISTERED":
            minutes.status = "MINUTES_RECORDED"

        minutes.version += 1
        minutes.dept_id = self._get_user_main_dept_id(recorder_user_id)

        old_decisions = session.query(MeetingDecision).filter(
            MeetingDecision.minutes_id == minutes_id,
            MeetingDecision.deleted == 0,
        ).all()
        for dec in old_decisions:
            dec.deleted = dec.id

        for i, decision in enumerate(request.decisions, start=1):
            d = MeetingDecision(
                tenant_id=ctx.tenant_id,
                minutes_id=minutes.id,
                seq=i,
                content=_escape_html(decision.content),
            )
            session.add(d)

        for item in existing_items:
            if item.status != "CLOSED":
                item.deleted = item.id

        for item in request.action_items:
            a = MeetingActionItem(
                tenant_id=ctx.tenant_id,
                minutes_id=minutes.id,
                description=_escape_html(item.description),
                assignee_user_id=item.assignee_user_id,
                due_date=item.due_date,
                status="OPEN",
            )
            session.add(a)

        session.flush()

        return {"data": self._to_vo(minutes, include_details=True), "warnings": warnings}

    @transactional
    async def archive_minutes(self, minutes_id: int) -> dict[str, Any]:
        """归档 (MN-05)。"""
        session = get_db_session()
        warnings = []

        minutes = session.query(MeetingMinutes).filter(
            MeetingMinutes.id == minutes_id,
            MeetingMinutes.tenant_id == ctx.tenant_id,
            MeetingMinutes.deleted == 0,
        ).first()

        if not minutes:
            raise BizError(1504)

        scope_filter = self._build_scope_filter(session, ctx.user_id)
        if scope_filter is not None:
            check_query = session.query(MeetingMinutes).filter(
                MeetingMinutes.id == minutes_id,
                scope_filter,
            ).first()
            if not check_query:
                raise BizError(1504)

        if minutes.status == "REGISTERED":
            raise BizError(1001, msg="请先录入纪要")

        if minutes.status == "ARCHIVED":
            raise BizError(1117, msg="已归档纪要不可重复归档")

        now = get_now()
        hours_since = (now - minutes.meeting_date).total_seconds() / 3600
        if hours_since > 48:
            warnings.append(1116)

        minutes.status = "ARCHIVED"
        minutes.archived_at = now
        minutes.archived_by = ctx.user_id

        session.flush()

        return {"data": self._to_vo(minutes, include_details=True), "warnings": warnings}

    @transactional
    async def add_appendix(self, minutes_id: int, request: AppendixCreateReq) -> MeetingMinutesVO:
        """添加附录 (MN-06)。"""
        session = get_db_session()

        minutes = session.query(MeetingMinutes).filter(
            MeetingMinutes.id == minutes_id,
            MeetingMinutes.tenant_id == ctx.tenant_id,
            MeetingMinutes.deleted == 0,
        ).first()

        if not minutes:
            raise BizError(1504)

        scope_filter = self._build_scope_filter(session, ctx.user_id)
        if scope_filter is not None:
            check_query = session.query(MeetingMinutes).filter(
                MeetingMinutes.id == minutes_id,
                scope_filter,
            ).first()
            if not check_query:
                raise BizError(1504)

        if minutes.status != "ARCHIVED":
            raise BizError(1117, msg="未归档纪要请直接编辑")

        appendix = MeetingAppendix(
            tenant_id=ctx.tenant_id,
            minutes_id=minutes_id,
            content=_escape_html(request.content),
        )
        session.add(appendix)
        session.flush()

        return self._to_vo(minutes, include_details=True)

    @transactional
    async def delete_minutes(self, minutes_id: int) -> None:
        """删除 (MN-07)。"""
        session = get_db_session()

        minutes = session.query(MeetingMinutes).filter(
            MeetingMinutes.id == minutes_id,
            MeetingMinutes.tenant_id == ctx.tenant_id,
            MeetingMinutes.deleted == 0,
        ).first()

        if not minutes:
            raise BizError(1504)

        scope_filter = self._build_scope_filter(session, ctx.user_id)
        if scope_filter is not None:
            check_query = session.query(MeetingMinutes).filter(
                MeetingMinutes.id == minutes_id,
                scope_filter,
            ).first()
            if not check_query:
                raise BizError(1504)

        if minutes.status == "ARCHIVED":
            raise BizError(1117, msg="已归档纪要不可删除")

        minutes.deleted = minutes.id

        decisions = session.query(MeetingDecision).filter(
            MeetingDecision.minutes_id == minutes_id,
            MeetingDecision.deleted == 0,
        ).all()
        for dec in decisions:
            dec.deleted = dec.id

        action_items = session.query(MeetingActionItem).filter(
            MeetingActionItem.minutes_id == minutes_id,
            MeetingActionItem.deleted == 0,
        ).all()
        for item in action_items:
            item.deleted = item.id

        appendices = session.query(MeetingAppendix).filter(
            MeetingAppendix.minutes_id == minutes_id,
            MeetingAppendix.deleted == 0,
        ).all()
        for apx in appendices:
            apx.deleted = apx.id

        session.flush()

    @transactional
    async def close_action_item(self, item_id: int, request: ActionItemCloseReq) -> ActionItemVO:
        """行动项回填 (AI-02)。"""
        session = get_db_session()

        item = session.query(MeetingActionItem).filter(
            MeetingActionItem.id == item_id,
            MeetingActionItem.tenant_id == ctx.tenant_id,
            MeetingActionItem.deleted == 0,
        ).first()

        if not item:
            raise BizError(1504)

        minutes = session.query(MeetingMinutes).filter(
            MeetingMinutes.id == item.minutes_id,
            MeetingMinutes.deleted == 0,
        ).first()

        if not minutes:
            raise BizError(1504)

        scope_filter = self._build_scope_filter(session, ctx.user_id)
        if scope_filter is not None:
            check_query = session.query(MeetingMinutes).filter(
                MeetingMinutes.id == minutes.id,
                scope_filter,
            ).first()
            if not check_query:
                raise BizError(1504)

        if item.assignee_user_id != ctx.user_id:
            raise BizError(1118, msg="非行动项责任人，无权回填")

        if item.status == "CLOSED":
            raise BizError(1001, msg="行动项已闭环")

        _validate_url(request.evidence_url)

        item.close_remark = request.close_remark
        item.evidence_url = request.evidence_url
        item.closed_at = get_now()
        item.status = "CLOSED"

        session.flush()

        return ActionItemVO(
            id=str(item.id),
            description=item.description,
            assignee_user_id=str(item.assignee_user_id),
            assignee_name=self._get_user_name(item.assignee_user_id),
            due_date=item.due_date,
            status=item.status,
            close_remark=item.close_remark,
            evidence_url=item.evidence_url,
            closed_at=item.closed_at,
            overdue_days=None,
        )

    async def get_archive_rate(
        self,
        date_range_start: Optional[datetime] = None,
        date_range_end: Optional[datetime] = None,
    ) -> ArchiveRateResp:
        """留痕率统计 (ST-01)。"""
        session = get_db_session()

        now = get_now()

        if not date_range_start:
            date_range_start = now - timedelta(days=30)
        if not date_range_end:
            date_range_end = now

        query = session.query(MeetingMinutes).filter(
            MeetingMinutes.tenant_id == ctx.tenant_id,
            MeetingMinutes.deleted == 0,
            MeetingMinutes.meeting_date >= date_range_start,
            MeetingMinutes.meeting_date <= date_range_end,
            MeetingMinutes.meeting_date < now,
        )

        scope_filter = self._build_scope_filter(session, ctx.user_id)
        if scope_filter is not None:
            query = query.filter(scope_filter)

        all_minutes = query.all()

        total = len(all_minutes)
        archived_count = sum(1 for m in all_minutes if m.status == "ARCHIVED")

        archive_rate = 100.0 if total == 0 else (archived_count / total) * 100

        unarchived = [m for m in all_minutes if m.status != "ARCHIVED"]
        unarchived.sort(key=lambda x: x.meeting_date)

        unarchived_list = []
        for m in unarchived[:100]:
            hours_since = (now - m.meeting_date).total_seconds() / 3600
            unarchived_list.append(UnarchivedMinutesVO(
                minutes_no=m.code,
                meeting_title=m.title,
                meeting_date=m.meeting_date,
                recorder_name=self._get_user_name(m.recorder_user_id) or "",
                hours_since_meeting=round(hours_since, 1),
            ))

        return ArchiveRateResp(
            total_meetings=total,
            archived_count=archived_count,
            archive_rate=round(archive_rate, 1),
            unarchived_list=unarchived_list,
        )
