# app/domains/meet/jobs.py - Meeting scheduled jobs (B18-M18)
"""
Meeting scheduled jobs.

Implements:
- ST-02: 24h/48h reminders (meeting_reminder_job)
- AI-03: Overdue push and escalation (meeting_overdue_job)

Registered via @job decorator in worker.py.
"""

from datetime import timedelta
from typing import Any, List

from sqlalchemy import text

from app.core.cache import Cache
from app.core.clock import get_now
from app.db.session import get_db_session
from app.worker import job

PERM_SUPERVISE = "ims:meet:minutes:supervise"


def _dept_covers_meeting(session: Any, user_dept_id: int, minutes_dept_id: int) -> bool:
    """DEPT 范围覆盖本部门和下级（Q-D7）。路径缺失时沿 parent_id 向上找。"""
    from app.domains.sys.models import Dept

    if user_dept_id == minutes_dept_id:
        return True

    user_dept = session.query(Dept).filter(
        Dept.id == user_dept_id,
        Dept.deleted == 0,
    ).first()
    minutes_dept = session.query(Dept).filter(
        Dept.id == minutes_dept_id,
        Dept.deleted == 0,
    ).first()
    if user_dept is None or minutes_dept is None:
        return False

    if user_dept.path and minutes_dept.path:
        prefix = user_dept.path if user_dept.path.endswith("/") else f"{user_dept.path}/"
        if minutes_dept.path.startswith(prefix):
            return True

    current = minutes_dept
    seen: set[int] = set()
    while current is not None and current.parent_id and current.id not in seen:
        seen.add(current.id)
        if current.parent_id == user_dept_id:
            return True
        current = session.query(Dept).filter(
            Dept.id == current.parent_id,
            Dept.deleted == 0,
        ).first()
    return False


def _user_dept_ids(session: Any, user: Any) -> List[int]:
    from app.domains.sys.models import UserDept

    dept_ids: List[int] = []
    if user.main_dept_id:
        dept_ids.append(user.main_dept_id)
    linked = session.query(UserDept.dept_id).filter(UserDept.user_id == user.id).all()
    for (dept_id,) in linked:
        if dept_id not in dept_ids:
            dept_ids.append(dept_id)
    return dept_ids


def _get_supervise_users_for_minutes(session: Any, minutes: Any) -> List[int]:
    """
    获取有 supervise 权限且数据范围覆盖该会议的用户列表。

    Q-D7/Q-D9: supervise 接收人按权限码 + 数据范围，不按角色名。
    数据范围覆盖条件：ALL 或 dept_id 在用户可见部门内 或 本人相关。
    """
    from app.domains.sys.models import Menu, Role, RoleMenu, User, UserRole

    supervise_menu = session.query(Menu).filter(
        Menu.perm_code == PERM_SUPERVISE,
        Menu.deleted == 0,
    ).first()

    if not supervise_menu:
        return []

    role_ids_with_perm = session.query(RoleMenu.role_id).filter(
        RoleMenu.menu_id == supervise_menu.id,
    ).distinct().all()
    role_ids_with_perm = [r[0] for r in role_ids_with_perm]

    if not role_ids_with_perm:
        return []

    roles = session.query(Role).filter(
        Role.id.in_(role_ids_with_perm),
        Role.tenant_id == minutes.tenant_id,
        Role.status == "ENABLED",
        Role.deleted == 0,
    ).all()

    if not roles:
        return []

    valid_role_ids = [r.id for r in roles]

    user_roles = session.query(UserRole).filter(
        UserRole.role_id.in_(valid_role_ids),
    ).all()

    user_ids = list({ur.user_id for ur in user_roles})
    if not user_ids:
        return []

    users = session.query(User).filter(
        User.id.in_(user_ids),
        User.tenant_id == minutes.tenant_id,
        User.deleted == 0,
        User.status.notin_(["FROZEN", "RESIGNED"]),
    ).all()

    if not users:
        return []

    result_user_ids = []

    for user in users:
        user_role_ids = [ur.role_id for ur in user_roles if ur.user_id == user.id]
        user_roles_obj = [r for r in roles if r.id in user_role_ids]

        can_see = False

        for role in user_roles_obj:
            if role.data_scope == "ALL":
                can_see = True
                break
            if role.data_scope == "DEPT":
                for dept_id in _user_dept_ids(session, user):
                    if _dept_covers_meeting(session, dept_id, minutes.dept_id):
                        can_see = True
                        break
                if can_see:
                    break
            if role.data_scope == "SELF":
                if user.id == minutes.recorder_user_id:
                    can_see = True
                    break
                attendees = minutes.attendees or {}
                internal_ids = attendees.get("internal", [])
                if user.id in internal_ids:
                    can_see = True
                    break

        if can_see:
            result_user_ids.append(user.id)

    return result_user_ids


@job
async def meeting_reminder_job() -> dict[str, Any]:
    """
    24h/48h 提醒任务 (ST-02).

    每小时执行一次：
    - 会后超 24h 仍 REGISTERED → 给记录人发消息
    - 会后超 48h 未归档 → 给记录人 + supervise 用户（有权限且数据范围覆盖）发消息

    幂等：remind_24h_at / remind_48h_at 非空时跳过
    """
    from app.domains.meet.models import MeetingMinutes
    from app.domains.sys.models import User
    from app.services.notify import NotifyService

    session = get_db_session()
    now = get_now()
    notify_service = NotifyService()

    stats = {
        "reminded_24h": 0,
        "reminded_48h": 0,
        "reminded_48h_supervise": 0,
        "skipped_resigned": 0,
        "messages_sent": 0,
    }

    threshold_24h = now - timedelta(hours=24)
    threshold_48h = now - timedelta(hours=48)

    minutes_24h = session.query(MeetingMinutes).filter(
        MeetingMinutes.deleted == 0,
        MeetingMinutes.status == "REGISTERED",
        MeetingMinutes.meeting_date < threshold_24h,
        MeetingMinutes.remind_24h_at.is_(None),
    ).all()

    for m in minutes_24h:
        lock_key = f"meet:reminder:{m.id}:24h"
        if not Cache.setnx(lock_key, "1", ttl=86400):
            continue

        recorder = session.query(User).filter(
            User.id == m.recorder_user_id,
            User.deleted == 0,
        ).first()

        if not recorder or recorder.status == "RESIGNED":
            stats["skipped_resigned"] += 1
            continue

        result = session.execute(
            text("""
            UPDATE ims_meeting_minutes
            SET remind_24h_at = :now
            WHERE id = :id AND remind_24h_at IS NULL
            """),
            {"now": now, "id": m.id}
        )

        if result.rowcount > 0:
            await notify_service.send(
                user_ids=[m.recorder_user_id],
                tenant_id=m.tenant_id,
                title="会议纪要录入提醒",
                content=f"会议「{m.title}」已超过 24 小时未录入纪要，请尽快录入。",
                biz_type="MEETING_REMINDER_24H",
                biz_id=str(m.id),
            )
            stats["reminded_24h"] += 1
            stats["messages_sent"] += 1

    minutes_48h = session.query(MeetingMinutes).filter(
        MeetingMinutes.deleted == 0,
        MeetingMinutes.status != "ARCHIVED",
        MeetingMinutes.meeting_date < threshold_48h,
        MeetingMinutes.remind_48h_at.is_(None),
    ).all()

    for m in minutes_48h:
        lock_key = f"meet:reminder:{m.id}:48h"
        if not Cache.setnx(lock_key, "1", ttl=86400):
            continue

        recorder = session.query(User).filter(
            User.id == m.recorder_user_id,
            User.deleted == 0,
        ).first()

        recorder_active = recorder is not None and recorder.status != "RESIGNED"
        if not recorder_active:
            stats["skipped_resigned"] += 1

        supervise_user_ids = _get_supervise_users_for_minutes(session, m)
        stats["reminded_48h_supervise"] += len(supervise_user_ids)
        recipients = list(supervise_user_ids)
        if recorder_active:
            recipients.append(m.recorder_user_id)
        recipients = list(dict.fromkeys(recipients))

        result = session.execute(
            text("""
            UPDATE ims_meeting_minutes
            SET remind_48h_at = :now
            WHERE id = :id AND remind_48h_at IS NULL
            """),
            {"now": now, "id": m.id}
        )

        if result.rowcount > 0 and recipients:
            await notify_service.send(
                user_ids=recipients,
                tenant_id=m.tenant_id,
                title="会议纪要归档提醒",
                content=f"会议「{m.title}」已超过 48 小时未归档，请尽快处理。",
                biz_type="MEETING_REMINDER_48H",
                biz_id=str(m.id),
            )
            stats["reminded_48h"] += 1
            stats["messages_sent"] += len(recipients)

    session.commit()

    return stats


@job
async def meeting_overdue_job() -> dict[str, Any]:
    """
    逾期推送与升级任务 (AI-03).

    每日 09:00 执行：
    - 扫描 due_date < 今天 且 status != CLOSED 的行动项
    - 标记 status = OVERDUE
    - 逾期满 1 天（due_date + 1 < 今天）→ 推送责任人
    - 逾期满 3 天（due_date + 3 < 今天）→ 推送 supervise 用户（有权限且数据范围覆盖）

    幂等：notified_at / escalated_at 非空时跳过
    """
    from app.domains.meet.models import MeetingActionItem, MeetingMinutes
    from app.domains.sys.models import User
    from app.services.notify import NotifyService

    session = get_db_session()
    now = get_now()
    today = now.date()
    notify_service = NotifyService()

    stats = {
        "marked_overdue": 0,
        "notified_1d": 0,
        "escalated_3d": 0,
        "escalated_3d_supervise_count": 0,
        "skipped_resigned": 0,
        "messages_sent": 0,
    }

    overdue_items = session.query(MeetingActionItem).filter(
        MeetingActionItem.deleted == 0,
        MeetingActionItem.due_date < today,
        MeetingActionItem.status != "CLOSED",
    ).all()

    for item in overdue_items:
        minutes = session.query(MeetingMinutes).filter(
            MeetingMinutes.id == item.minutes_id,
            MeetingMinutes.deleted == 0,
        ).first()

        if not minutes:
            continue

        if item.status == "OPEN":
            item.status = "OVERDUE"
            stats["marked_overdue"] += 1

        days_overdue = (today - item.due_date).days

        if days_overdue > 1 and item.notified_at is None:
            lock_key = f"meet:overdue:{item.id}:1d"
            if Cache.setnx(lock_key, "1", ttl=86400 * 7):
                assignee = session.query(User).filter(
                    User.id == item.assignee_user_id,
                    User.deleted == 0,
                ).first()

                if not assignee or assignee.status == "RESIGNED":
                    stats["skipped_resigned"] += 1
                else:
                    result = session.execute(
                        text("""
                        UPDATE ims_meeting_action_item
                        SET notified_at = :now
                        WHERE id = :id AND notified_at IS NULL
                        """),
                        {"now": now, "id": item.id}
                    )

                    if result.rowcount > 0:
                        await notify_service.send(
                            user_ids=[item.assignee_user_id],
                            tenant_id=item.tenant_id,
                            title="行动项逾期提醒",
                            content=f"行动项「{item.description}」已逾期 {days_overdue} 天，请尽快处理。",
                            biz_type="MEETING_ACTION_OVERDUE_1D",
                            biz_id=str(item.id),
                        )
                        stats["notified_1d"] += 1
                        stats["messages_sent"] += 1

        if days_overdue > 3 and item.escalated_at is None:
            lock_key = f"meet:overdue:{item.id}:3d"
            if not Cache.setnx(lock_key, "1", ttl=86400 * 7):
                continue

            supervise_user_ids = _get_supervise_users_for_minutes(session, minutes)
            stats["escalated_3d_supervise_count"] += len(supervise_user_ids)

            result = session.execute(
                text("""
                UPDATE ims_meeting_action_item
                SET escalated_at = :now
                WHERE id = :id AND escalated_at IS NULL
                """),
                {"now": now, "id": item.id}
            )

            if result.rowcount > 0:
                if supervise_user_ids:
                    await notify_service.send(
                        user_ids=supervise_user_ids,
                        tenant_id=minutes.tenant_id,
                        title="行动项逾期升级",
                        content=f"会议「{minutes.title}」的行动项「{item.description}」已逾期 {days_overdue} 天，请关注跟进。",
                        biz_type="MEETING_ACTION_ESCALATE_3D",
                        biz_id=str(item.id),
                    )
                    stats["messages_sent"] += len(supervise_user_ids)
                stats["escalated_3d"] += 1

    session.commit()

    return stats
