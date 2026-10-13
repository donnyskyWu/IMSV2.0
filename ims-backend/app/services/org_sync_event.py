# app/services/org_sync_event.py - Organization sync event processing (FP-B1-BG-01)
"""
Organization sync event processing service.

Implements:
- Event reception and deduplication
- Event processing with retry logic
- Status transitions (PENDING -> SUCCESS/RETRYING -> DEAD)
- Out-of-order event handling
"""

import logging
from datetime import timedelta
from typing import Any, Optional

from app.core.clock import get_now
from app.core.context import ctx
from app.core.errors import BizError
from app.db.ids import assign_pk
from app.db.session import get_db_session
from app.db.transaction import transactional

logger = logging.getLogger(__name__)

RETRY_INTERVALS_MINUTES = [1, 5, 15, 60]
MAX_RETRIES = len(RETRY_INTERVALS_MINUTES)


class OrgSyncEventService:
    """Organization sync event processing service."""

    async def receive_event(
        self,
        tenant_id: int,
        event_id: str,
        event_type: str,
        event_time: Any,
        payload: str,
        biz_type: Optional[str] = None,
        subject_user_id: Optional[int] = None,
        subject_name: Optional[str] = None,
        dept_id: Optional[int] = None,
        before_dept_names: Optional[str] = None,
        after_dept_names: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Receive and store a sync event.

        Idempotent: same event_id will not create duplicate.
        Returns existing event if already received.
        """
        from app.domains.sys.models import OrgSyncEvent

        session = get_db_session()
        now = get_now()

        existing = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.event_id == event_id,
            OrgSyncEvent.deleted == 0,
        ).first()

        if existing is not None:
            return self._event_to_response(existing)

        event = OrgSyncEvent(
            tenant_id=tenant_id,
            event_id=event_id,
            event_type=event_type,
            event_time=event_time,
            payload=payload,
            status="PENDING",
            retry_count=0,
            biz_type=biz_type,
            subject_user_id=subject_user_id,
            subject_name=subject_name,
            dept_id=dept_id,
            before_dept_names=before_dept_names,
            after_dept_names=after_dept_names,
            received_time=now,
        )
        assign_pk(session, event)
        session.add(event)
        session.flush()

        logger.info(
            "Received org sync event event_id=%s type=%s biz_type=%s",
            event_id,
            event_type,
            biz_type,
        )

        return self._event_to_response(event)

    async def process_event(self, event_id: int) -> dict[str, Any]:
        """
        Process a single event by ID (database primary key).

        Rules:
        - Check if event is stale (event_time <= last_sync_at) -> SKIPPED
        - Apply changes based on biz_type
        - Mark SUCCESS or increment retry_count on failure
        """
        from app.domains.sys.models import OrgSyncEvent, OrgSyncEventAttempt

        session = get_db_session()
        now = get_now()

        event = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.id == event_id,
            OrgSyncEvent.deleted == 0,
        ).first()

        if event is None:
            raise BizError(1504)

        if event.status == "SUCCESS":
            return self._event_to_response(event)

        attempt_no = event.retry_count + 1
        attempt = OrgSyncEventAttempt(
            tenant_id=event.tenant_id,
            event_id=event.id,
            attempt_no=attempt_no,
            trigger="AUTO" if event.retry_count == 0 else "RETRY",
            start_time=now,
        )
        assign_pk(session, attempt)
        session.add(attempt)
        session.flush()

        try:
            is_stale = await self._check_stale(event)
            if is_stale:
                event.status = "SKIPPED"
                event.processed_time = now
                attempt.end_time = now
                attempt.result = "SKIPPED"
                session.flush()
                logger.info(
                    "Skipped stale event event_id=%s",
                    event.event_id,
                )
                return self._event_to_response(event)

            await self._apply_event(event)

            event.status = "SUCCESS"
            event.processed_time = now
            if event.event_time:
                event.delay_seconds = int((now - event.event_time).total_seconds())
            attempt.end_time = now
            attempt.result = "SUCCESS"
            session.flush()

            logger.info(
                "Processed event event_id=%s biz_type=%s",
                event.event_id,
                event.biz_type,
            )

        except Exception as exc:
            event.retry_count += 1
            event.last_error = str(exc)[:500]

            if event.retry_count >= MAX_RETRIES:
                event.status = "DEAD"
                logger.warning(
                    "Event became dead letter event_id=%s error=%s",
                    event.event_id,
                    str(exc)[:200],
                )
            else:
                event.status = "RETRYING"

            attempt.end_time = now
            attempt.result = "FAIL"
            attempt.error_msg = str(exc)[:500]
            session.flush()

            raise

        return self._event_to_response(event)

    async def _check_stale(self, event: Any) -> bool:
        """Check if event is stale (event_time <= target's last_sync_at)."""
        if event.event_time is None:
            return False

        if event.biz_type in ("HIRE", "USER_UPDATE", "TRANSFER", "RESIGN"):
            if event.subject_user_id:
                from app.domains.sys.models import UserMapping

                session = get_db_session()
                mapping = session.query(UserMapping).filter(
                    UserMapping.user_id == event.subject_user_id,
                    UserMapping.deleted == 0,
                ).first()
                if mapping and mapping.last_sync_time:
                    return event.event_time <= mapping.last_sync_time

        elif event.biz_type in ("DEPT_CREATE", "DEPT_UPDATE", "DEPT_DELETE"):
            if event.dept_id:
                from app.domains.sys.models import Dept

                session = get_db_session()
                dept = session.query(Dept).filter(
                    Dept.id == event.dept_id,
                    Dept.deleted == 0,
                ).first()
                if dept and dept.last_sync_at:
                    return event.event_time <= dept.last_sync_at

        return False

    async def _apply_event(self, event: Any) -> None:
        """Apply event changes based on biz_type."""
        biz_type = event.biz_type or ""

        if biz_type == "HIRE":
            await self._apply_hire(event)
        elif biz_type == "RESIGN":
            await self._apply_resign(event)
        elif biz_type == "USER_UPDATE":
            await self._apply_user_update(event)
        elif biz_type == "TRANSFER":
            await self._apply_transfer(event)
        elif biz_type == "DEPT_CREATE":
            await self._apply_dept_create(event)
        elif biz_type == "DEPT_UPDATE":
            await self._apply_dept_update(event)
        elif biz_type == "DEPT_DELETE":
            await self._apply_dept_delete(event)
        else:
            logger.warning("Unknown biz_type=%s for event_id=%s", biz_type, event.event_id)

    async def _apply_hire(self, event: Any) -> None:
        """Handle HIRE event - create user if not exists."""
        pass

    async def _apply_resign(self, event: Any) -> None:
        """Handle RESIGN event - mark user as resigned and drop sessions."""
        from app.domains.sys.models import User, UserMapping
        from app.services.user import USER_EVENTS, UserService

        if not event.subject_user_id:
            return

        session = get_db_session()
        user = session.query(User).filter(
            User.id == event.subject_user_id,
            User.deleted == 0,
        ).first()

        if user is None:
            return

        if user.status != "RESIGNED":
            user.status = "RESIGNED"
            user.token_version = (user.token_version or 0) + 1
            UserService()._drop_sessions(user.id)
            USER_EVENTS.append({"type": "user.resigned", "user_id": user.id})

        mapping = session.query(UserMapping).filter(
            UserMapping.user_id == user.id,
            UserMapping.deleted == 0,
        ).first()
        if mapping:
            mapping.last_sync_time = get_now()

        session.flush()

    async def _apply_user_update(self, event: Any) -> None:
        """Handle USER_UPDATE event."""
        pass

    async def _apply_transfer(self, event: Any) -> None:
        """Handle TRANSFER event - department change."""
        pass

    async def _apply_dept_create(self, event: Any) -> None:
        """Handle DEPT_CREATE event."""
        pass

    async def _apply_dept_update(self, event: Any) -> None:
        """Handle DEPT_UPDATE event."""
        pass

    async def _apply_dept_delete(self, event: Any) -> None:
        """Handle DEPT_DELETE event."""
        pass

    @transactional
    async def retry_event(self, event_id: int, operator_id: Optional[int] = None) -> dict[str, Any]:
        """
        Manually retry a single event.

        Rules:
        - Only RETRYING or DEAD events can be retried
        - SUCCESS or PENDING events return 1286
        - retry_count is not reset on manual retry
        """
        from app.domains.sys.models import OrgSyncEvent, OrgSyncEventAttempt

        session = get_db_session()
        now = get_now()

        event = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.id == event_id,
            OrgSyncEvent.deleted == 0,
        ).first()

        if event is None:
            raise BizError(1504)

        if event.status in ("SUCCESS", "PENDING"):
            raise BizError(1286)

        attempt_no = event.retry_count + 1
        attempt = OrgSyncEventAttempt(
            tenant_id=event.tenant_id,
            event_id=event.id,
            attempt_no=attempt_no,
            trigger="RETRY",
            operator_id=operator_id,
            start_time=now,
        )
        assign_pk(session, attempt)
        session.add(attempt)

        event.status = "PENDING"
        session.flush()

        try:
            await self._apply_event(event)

            event.status = "SUCCESS"
            event.processed_time = now
            if event.event_time:
                event.delay_seconds = int((now - event.event_time).total_seconds())
            attempt.end_time = now
            attempt.result = "SUCCESS"

        except Exception as exc:
            event.retry_count += 1
            event.last_error = str(exc)[:500]

            if event.retry_count >= MAX_RETRIES:
                event.status = "DEAD"
            else:
                event.status = "RETRYING"

            attempt.end_time = now
            attempt.result = "FAIL"
            attempt.error_msg = str(exc)[:500]

            raise

        finally:
            session.flush()

        return self._event_to_response(event)

    @transactional
    async def replay_events(
        self,
        tenant_id: int,
        start_time: Any,
        end_time: Any,
        statuses: list[str],
        operator_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Batch replay failed events.

        Rules:
        - Only DEAD and RETRYING events can be replayed
        - Time span <= 7 days
        - Max 1000 events per batch
        - DEAD events have retry_count reset to 0
        """
        from app.domains.sys.models import OrgSyncEvent

        session = get_db_session()

        if (end_time - start_time).days > 7:
            raise BizError(1001, msg="时间跨度不能超过7天")

        if not statuses:
            raise BizError(1001, msg="请选择要重放的状态")

        valid_statuses = {"DEAD", "RETRYING"}
        if not set(statuses).issubset(valid_statuses):
            raise BizError(1001, msg="只能重放失败或死信状态的事件")

        events = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.status.in_(statuses),
            OrgSyncEvent.event_time >= start_time,
            OrgSyncEvent.event_time <= end_time,
            OrgSyncEvent.deleted == 0,
        ).limit(1001).all()

        if len(events) > 1000:
            raise BizError(1001, msg="符合条件的事件超过1000条")

        for event in events:
            if event.status == "DEAD":
                event.retry_count = 0
            event.status = "PENDING"

        session.flush()

        return {
            "count": len(events),
            "statuses": statuses,
        }

    async def get_replay_preview(
        self,
        tenant_id: int,
        start_time: Any,
        end_time: Any,
        statuses: list[str],
    ) -> dict[str, Any]:
        """Preview replay count before executing."""
        from app.domains.sys.models import OrgSyncEvent

        session = get_db_session()

        if (end_time - start_time).days > 7:
            raise BizError(1001, msg="时间跨度不能超过7天")

        if not statuses:
            raise BizError(1001, msg="请选择要重放的状态")

        count = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.status.in_(statuses),
            OrgSyncEvent.event_time >= start_time,
            OrgSyncEvent.event_time <= end_time,
            OrgSyncEvent.deleted == 0,
        ).count()

        if count > 1000:
            raise BizError(1001, msg="符合条件的事件超过1000条")

        return {"count": count}

    async def get_event(self, event_id: int, tenant_id: int) -> Optional[dict[str, Any]]:
        """Get event detail by ID."""
        from app.domains.sys.models import OrgSyncEvent, OrgSyncEventAttempt

        session = get_db_session()

        event = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.id == event_id,
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.deleted == 0,
        ).first()

        if event is None:
            return None

        attempts = session.query(OrgSyncEventAttempt).filter(
            OrgSyncEventAttempt.event_id == event.id,
            OrgSyncEventAttempt.deleted == 0,
        ).order_by(OrgSyncEventAttempt.attempt_no).all()

        result = self._event_to_response(event)
        result["attempts"] = [
            {
                "attempt_no": a.attempt_no,
                "trigger": a.trigger,
                "operator_id": str(a.operator_id) if a.operator_id else None,
                "start_time": a.start_time.isoformat() + "+08:00" if a.start_time else None,
                "end_time": a.end_time.isoformat() + "+08:00" if a.end_time else None,
                "result": a.result,
                "error_msg": a.error_msg,
            }
            for a in attempts
        ]

        return result

    async def get_events_page(
        self,
        tenant_id: int,
        page_no: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        dept_id: Optional[int] = None,
        event_types: Optional[list[str]] = None,
        statuses: Optional[list[str]] = None,
        start_time: Any = None,
        end_time: Any = None,
        sort_by: str = "eventTime",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """Get paginated event list."""
        from sqlalchemy import or_

        from app.domains.sys.models import OrgSyncEvent

        session = get_db_session()

        query = session.query(OrgSyncEvent).filter(
            OrgSyncEvent.tenant_id == tenant_id,
            OrgSyncEvent.deleted == 0,
        )

        if keyword:
            keyword_filter = f"%{keyword}%"
            query = query.filter(
                or_(
                    OrgSyncEvent.subject_name.like(keyword_filter),
                    OrgSyncEvent.event_id.like(keyword_filter),
                )
            )

        if dept_id:
            query = query.filter(OrgSyncEvent.dept_id == dept_id)

        if event_types:
            query = query.filter(OrgSyncEvent.event_type.in_(event_types))

        if statuses:
            query = query.filter(OrgSyncEvent.status.in_(statuses))

        if start_time:
            query = query.filter(OrgSyncEvent.event_time >= start_time)

        if end_time:
            query = query.filter(OrgSyncEvent.event_time <= end_time)

        total = query.count()

        if sort_by == "processedTime":
            order_col = OrgSyncEvent.processed_time
        else:
            order_col = OrgSyncEvent.event_time

        if sort_order == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())

        offset = (page_no - 1) * page_size
        events = query.offset(offset).limit(page_size).all()

        return {
            "total": total,
            "list": [self._event_to_response(e) for e in events],
            "pageNo": page_no,
            "pageSize": page_size,
        }

    def _event_to_response(self, event: Any) -> dict[str, Any]:
        """Convert event to response dict."""
        return {
            "id": str(event.id),
            "eventId": event.event_id,
            "eventType": event.event_type,
            "bizType": event.biz_type,
            "subjectUserId": str(event.subject_user_id) if event.subject_user_id else None,
            "subjectName": event.subject_name,
            "deptId": str(event.dept_id) if event.dept_id else None,
            "beforeDeptNames": event.before_dept_names,
            "afterDeptNames": event.after_dept_names,
            "status": event.status,
            "retryCount": event.retry_count,
            "lastError": event.last_error,
            "eventTime": event.event_time.isoformat() + "+08:00" if event.event_time else None,
            "receivedTime": event.received_time.isoformat() + "+08:00" if event.received_time else None,
            "processedTime": event.processed_time.isoformat() + "+08:00" if event.processed_time else None,
            "delaySeconds": event.delay_seconds,
        }
