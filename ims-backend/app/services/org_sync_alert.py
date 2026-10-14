# app/services/org_sync_alert.py - Organization sync alert service (FP-B1-BG-05)
"""
Organization sync alert service.

Implements:
- Dead letter alerts (hourly merge)
- Delay alerts (hourly throttle)
- Reconcile failure P1 alerts
"""

import logging
from datetime import timedelta
from typing import Any

from app.core.cache import Cache
from app.core.clock import get_now
from app.db.ids import assign_pk
from app.db.session import get_db_session

logger = logging.getLogger(__name__)

DEAD_LETTER_ALERT_KEY = "ims:alert:dead_letter:{tenant_id}:{hour}"
DELAY_ALERT_KEY = "ims:alert:delay:{tenant_id}:{hour}"
ALERT_KEY_TTL = 7200


class OrgSyncAlertService:
    """Organization sync alert service."""

    async def check_dead_letter(self, tenant_id: int, event_id: int) -> None:
        """
        Check and send dead letter alert.

        Rules:
        - Merge by hour: all dead letters in the same hour combine into one notification
        - Recipients: users with ims:system:org-sync:run permission
        """
        now = get_now()
        hour_key = now.strftime("%Y%m%d%H")
        cache_key = DEAD_LETTER_ALERT_KEY.format(tenant_id=tenant_id, hour=hour_key)

        existing = Cache.get(cache_key)
        if existing:
            count = int(existing) + 1
            Cache.set(cache_key, str(count), ttl=ALERT_KEY_TTL)
            logger.info(
                "Dead letter event added to hourly batch tenant=%s hour=%s count=%s",
                tenant_id,
                hour_key,
                count,
            )
            return

        Cache.set(cache_key, "1", ttl=ALERT_KEY_TTL)

        await self._send_dead_letter_notification(tenant_id, hour_key)

    async def _send_dead_letter_notification(self, tenant_id: int, hour_key: str) -> None:
        """Send dead letter notification to relevant users."""
        recipients = await self._get_alert_recipients(tenant_id, "ims:system:org-sync:run")

        if not recipients:
            logger.warning("No recipients for dead letter alert tenant=%s", tenant_id)
            return

        from app.domains.sys.models import InboxMessage

        session = get_db_session()

        for user_id in recipients:
            message = InboxMessage(
                tenant_id=tenant_id,
                user_id=user_id,
                title=f"组织同步死信告警 ({hour_key})",
                body="有同步事件进入死信状态，请及时处理",
            )
            assign_pk(session, message)
            session.add(message)

        session.flush()
        logger.info(
            "Sent dead letter notification tenant=%s hour=%s recipients=%s",
            tenant_id,
            hour_key,
            len(recipients),
        )

    async def check_delay_alert(
        self,
        tenant_id: int,
        event_id: int,
        delay_seconds: int,
        threshold_minutes: int = 5,
    ) -> None:
        """
        Check and send delay alert.

        Rules:
        - Trigger when delay > threshold (default 5 minutes)
        - Throttle: max one alert per hour
        """
        if delay_seconds < threshold_minutes * 60:
            return

        now = get_now()
        hour_key = now.strftime("%Y%m%d%H")
        cache_key = DELAY_ALERT_KEY.format(tenant_id=tenant_id, hour=hour_key)

        if Cache.get(cache_key):
            logger.debug(
                "Delay alert throttled for this hour tenant=%s hour=%s",
                tenant_id,
                hour_key,
            )
            return

        Cache.set(cache_key, "1", ttl=ALERT_KEY_TTL)

        await self._send_delay_notification(tenant_id, delay_seconds)

    async def _send_delay_notification(self, tenant_id: int, delay_seconds: int) -> None:
        """Send delay notification to relevant users."""
        recipients = await self._get_alert_recipients(tenant_id, "ims:system:org-sync:run")

        if not recipients:
            logger.warning("No recipients for delay alert tenant=%s", tenant_id)
            return

        from app.domains.sys.models import InboxMessage

        session = get_db_session()
        delay_minutes = delay_seconds // 60

        for user_id in recipients:
            message = InboxMessage(
                tenant_id=tenant_id,
                user_id=user_id,
                title="组织同步延迟告警",
                body=f"同步事件处理延迟 {delay_minutes} 分钟，请检查同步状态",
            )
            assign_pk(session, message)
            session.add(message)

        session.flush()
        logger.info(
            "Sent delay notification tenant=%s delay_minutes=%s recipients=%s",
            tenant_id,
            delay_minutes,
            len(recipients),
        )

    async def check_reconcile_failure(self, tenant_id: int, batch_id: int) -> None:
        """
        Check if reconcile has failed twice consecutively.

        Rules:
        - Send P1 notification if last two batches both failed
        - Show red banner on page
        """
        from app.domains.sys.models import OrgSyncBatch

        session = get_db_session()

        recent_batches = session.query(OrgSyncBatch).filter(
            OrgSyncBatch.tenant_id == tenant_id,
            OrgSyncBatch.deleted == 0,
            OrgSyncBatch.status.in_(["SUCCESS", "FAILED"]),
        ).order_by(OrgSyncBatch.id.desc()).limit(2).all()

        if len(recent_batches) < 2:
            return

        if all(b.status == "FAILED" for b in recent_batches):
            await self._send_reconcile_failure_p1(tenant_id)

    async def _send_reconcile_failure_p1(self, tenant_id: int) -> None:
        """Send P1 notification for consecutive reconcile failures."""
        recipients = await self._get_alert_recipients(tenant_id, "ims:system:org-sync:run")

        if not recipients:
            logger.warning("No recipients for reconcile failure P1 tenant=%s", tenant_id)
            return

        from app.domains.sys.models import InboxMessage

        session = get_db_session()

        for user_id in recipients:
            message = InboxMessage(
                tenant_id=tenant_id,
                user_id=user_id,
                title="【P1】组织对账连续失败",
                body="组织对账已连续两次失败，请立即检查钉钉连接状态",
            )
            assign_pk(session, message)
            session.add(message)

        session.flush()
        logger.warning(
            "Sent reconcile failure P1 notification tenant=%s recipients=%s",
            tenant_id,
            len(recipients),
        )

    async def _get_alert_recipients(self, tenant_id: int, perm_code: str) -> list[int]:
        """Get users with the specified permission code who are active."""
        from app.domains.sys.models import Menu, RoleMenu, User, UserRole

        session = get_db_session()

        menu = session.query(Menu).filter(
            Menu.perm_code == perm_code,
            Menu.deleted == 0,
        ).first()

        if menu is None:
            return []

        role_ids = [
            r.role_id
            for r in session.query(RoleMenu).filter(
                RoleMenu.menu_id == menu.id
            ).all()
        ]

        if not role_ids:
            return []

        user_ids = [
            ur.user_id
            for ur in session.query(UserRole).filter(
                UserRole.role_id.in_(role_ids)
            ).all()
        ]

        if not user_ids:
            return []

        active_users = session.query(User.id).filter(
            User.id.in_(user_ids),
            User.tenant_id == tenant_id,
            User.status == "ACTIVE",
            User.deleted == 0,
        ).all()

        return [u.id for u in active_users]

    async def get_sync_metrics(self, tenant_id: int) -> dict[str, Any]:
        """
        Get sync metrics for dashboard.

        Returns:
        - userTotal: ACTIVE or FROZEN users
        - yesterdayEventCount: events from yesterday
        - pendingEventCount: PENDING events
        - deadEventCount: DEAD events
        - avgDelayMinutes: average delay in last 24h
        - p95DelayMinutes: 95th percentile delay
        - successRate24h: success rate in last 24h
        - dingtalkUnavailable: timeout in last 10 minutes
        - reconcileFailedTwice: last two batches failed
        """

        from app.domains.sys.models import OrgSyncBatch, OrgSyncEvent, User

        session = get_db_session()
        now = get_now()
        yesterday_start = (now - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        last_24h = now - timedelta(hours=24)
        last_10min = now - timedelta(minutes=10)

        user_total = session.query(User).filter(
            User.tenant_id == tenant_id,
            User.status.in_(["ACTIVE", "FROZEN"]),
            User.deleted == 0,
        ).count()

        yesterday_count = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.event_time >= yesterday_start,
            OrgSyncEvent.event_time < yesterday_end,
            OrgSyncEvent.deleted == 0,
        ).count()

        pending_count = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.status == "PENDING",
            OrgSyncEvent.deleted == 0,
        ).count()

        dead_count = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.status == "DEAD",
            OrgSyncEvent.deleted == 0,
        ).count()

        success_events = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.status == "SUCCESS",
            OrgSyncEvent.processed_time >= last_24h,
            OrgSyncEvent.delay_seconds.isnot(None),
            OrgSyncEvent.deleted == 0,
        ).all()

        if success_events:
            delays = [e.delay_seconds for e in success_events if e.delay_seconds]
            avg_delay = sum(delays) / len(delays) / 60 if delays else 0
            sorted_delays = sorted(delays)
            p95_idx = int(len(sorted_delays) * 0.95)
            p95_delay = sorted_delays[p95_idx] / 60 if sorted_delays else 0
        else:
            avg_delay = 0
            p95_delay = 0

        total_24h = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.processed_time >= last_24h,
            OrgSyncEvent.status.in_(["SUCCESS", "DEAD"]),
            OrgSyncEvent.deleted == 0,
        ).count()

        success_24h = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.processed_time >= last_24h,
            OrgSyncEvent.status == "SUCCESS",
            OrgSyncEvent.deleted == 0,
        ).count()

        success_rate = success_24h / total_24h if total_24h > 0 else 1.0

        timeout_events = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.last_error.like("%5003%"),
            OrgSyncEvent.processed_time >= last_10min,
            OrgSyncEvent.deleted == 0,
        ).count()

        dingtalk_unavailable = timeout_events > 0

        recent_batches = session.query(OrgSyncBatch).filter(
            OrgSyncBatch.tenant_id == tenant_id,
            OrgSyncBatch.deleted == 0,
            OrgSyncBatch.status.in_(["SUCCESS", "FAILED"]),
        ).order_by(OrgSyncBatch.id.desc()).limit(2).all()

        reconcile_failed_twice = (
            len(recent_batches) >= 2
            and all(b.status == "FAILED" for b in recent_batches)
        )

        return {
            "userTotal": user_total,
            "yesterdayEventCount": yesterday_count,
            "pendingEventCount": pending_count,
            "deadEventCount": dead_count,
            "avgDelayMinutes": round(avg_delay, 1),
            "p95DelayMinutes": round(p95_delay, 1),
            "successRate24h": round(success_rate, 2),
            "dingtalkUnavailable": dingtalk_unavailable,
            "reconcileFailedTwice": reconcile_failed_twice,
        }

    async def send_todo_for_pending_assign(
        self,
        tenant_id: int,
        dept_name: str,
        user_count: int,
    ) -> None:
        """Send todo to users with ims:system:user:update permission."""
        recipients = await self._get_alert_recipients(tenant_id, "ims:system:user:update")

        if not recipients:
            logger.warning("No recipients for pending assign todo tenant=%s", tenant_id)
            return

        from app.domains.sys.models import TodoItem

        session = get_db_session()

        for user_id in recipients:
            todo = TodoItem(
                tenant_id=tenant_id,
                assignee_user_id=user_id,
                title=f"部门「{dept_name}」已删除，有 {user_count} 人移入待分配",
                status="OPEN",
            )
            assign_pk(session, todo)
            session.add(todo)

        session.flush()
        logger.info(
            "Sent pending assign todo tenant=%s dept=%s users=%s recipients=%s",
            tenant_id,
            dept_name,
            user_count,
            len(recipients),
        )

    async def send_todo_for_local_orphan(
        self,
        tenant_id: int,
        dept_name: str,
    ) -> None:
        """Send todo for local orphan department confirmation."""
        recipients = await self._get_alert_recipients(tenant_id, "ims:system:user:update")

        if not recipients:
            return

        from app.domains.sys.models import TodoItem

        session = get_db_session()

        for user_id in recipients:
            todo = TodoItem(
                tenant_id=tenant_id,
                assignee_user_id=user_id,
                title=f"本地部门「{dept_name}」的父部门已删除，请确认新位置",
                status="OPEN",
            )
            assign_pk(session, todo)
            session.add(todo)

        session.flush()
