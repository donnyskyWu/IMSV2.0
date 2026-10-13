# app/domains/meet/jobs.py - Meeting scheduled jobs (B18-M18)
"""
Meeting scheduled jobs.

Implements:
- ST-02: 24h/48h reminders (meeting_reminder_job)
- AI-03: Overdue push and escalation (meeting_overdue_job)
"""

from datetime import timedelta
from typing import Any

from sqlalchemy import text

from app.core.cache import Cache
from app.core.clock import get_now
from app.db.session import get_db_session


async def meeting_reminder_job() -> dict[str, Any]:
    """
    24h/48h 提醒任务 (ST-02).
    
    每小时执行一次：
    - 会后超 24h 仍 REGISTERED → 给记录人发消息
    - 会后超 48h 未归档 → 给记录人 + supervise 用户发消息
    
    幂等：remind_24h_at / remind_48h_at 非空时跳过
    """
    from app.domains.meet.models import MeetingMinutes
    from app.domains.sys.models import User
    
    session = get_db_session()
    now = get_now()
    
    stats = {
        "reminded_24h": 0,
        "reminded_48h": 0,
        "skipped_resigned": 0,
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
            stats["reminded_24h"] += 1
    
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
        
        if not recorder or recorder.status == "RESIGNED":
            stats["skipped_resigned"] += 1
            continue
        
        result = session.execute(
            text("""
            UPDATE ims_meeting_minutes 
            SET remind_48h_at = :now 
            WHERE id = :id AND remind_48h_at IS NULL
            """),
            {"now": now, "id": m.id}
        )
        
        if result.rowcount > 0:
            stats["reminded_48h"] += 1
    
    session.commit()
    
    return stats


async def meeting_overdue_job() -> dict[str, Any]:
    """
    逾期推送与升级任务 (AI-03).
    
    每日 09:00 执行：
    - 扫描 due_date < 今天 且 status != CLOSED 的行动项
    - 标记 status = OVERDUE
    - 逾期满 1 天（due_date + 1 < 今天）→ 推送责任人
    - 逾期满 3 天（due_date + 3 < 今天）→ 推送 supervise 用户
    
    幂等：notified_at / escalated_at 非空时跳过
    """
    from app.domains.meet.models import MeetingMinutes, MeetingActionItem
    from app.domains.sys.models import User
    
    session = get_db_session()
    now = get_now()
    today = now.date()
    
    stats = {
        "marked_overdue": 0,
        "notified_1d": 0,
        "escalated_3d": 0,
        "skipped_resigned": 0,
    }
    
    overdue_items = session.query(MeetingActionItem).filter(
        MeetingActionItem.deleted == 0,
        MeetingActionItem.due_date < today,
        MeetingActionItem.status != "CLOSED",
    ).all()
    
    for item in overdue_items:
        if item.status == "OPEN":
            item.status = "OVERDUE"
            stats["marked_overdue"] += 1
        
        days_overdue = (today - item.due_date).days
        
        if days_overdue >= 1 and item.notified_at is None:
            lock_key = f"meet:overdue:{item.id}:1d"
            if not Cache.setnx(lock_key, "1", ttl=86400 * 7):
                continue
            
            assignee = session.query(User).filter(
                User.id == item.assignee_user_id,
                User.deleted == 0,
            ).first()
            
            if not assignee or assignee.status == "RESIGNED":
                stats["skipped_resigned"] += 1
                continue
            
            result = session.execute(
                text("""
                UPDATE ims_meeting_action_item 
                SET notified_at = :now 
                WHERE id = :id AND notified_at IS NULL
                """),
                {"now": now, "id": item.id}
            )
            
            if result.rowcount > 0:
                stats["notified_1d"] += 1
        
        if days_overdue >= 3 and item.escalated_at is None:
            lock_key = f"meet:overdue:{item.id}:3d"
            if not Cache.setnx(lock_key, "1", ttl=86400 * 7):
                continue
            
            result = session.execute(
                text("""
                UPDATE ims_meeting_action_item 
                SET escalated_at = :now 
                WHERE id = :id AND escalated_at IS NULL
                """),
                {"now": now, "id": item.id}
            )
            
            if result.rowcount > 0:
                stats["escalated_3d"] += 1
    
    session.commit()
    
    return stats
