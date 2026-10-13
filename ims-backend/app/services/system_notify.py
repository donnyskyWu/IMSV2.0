# app/services/system_notify.py - Notification service (B2-M02)
"""
Notification service.

Implements N-01 to N-02 from the B2 system management module:
- Notification record list
- Notification resend
"""

from typing import Any, Optional

from app.core.context import ctx
from app.core.errors import BizError
from app.core.pagination import PageParam, PageResult
from app.db.session import get_db_session
from app.db.transaction import transactional


class SystemNotifyService:
    """Notification service for B2 system management."""

    async def get_notify_record_page(
        self,
        page_param: PageParam,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> PageResult:
        """Get paginated notification record list (N-01)."""
        from app.domains.sys.models import OutboxEvent

        session = get_db_session()
        tenant_id = ctx.tenant_id

        query = session.query(OutboxEvent).filter(
            OutboxEvent.tenant_id == tenant_id,
            OutboxEvent.deleted == 0,
        )

        if status:
            query = query.filter(OutboxEvent.status == status)

        if event_type:
            query = query.filter(OutboxEvent.event_type == event_type)

        total = query.count()

        offset = (page_param.page_no - 1) * page_param.page_size
        records = query.order_by(OutboxEvent.create_time.desc()).offset(offset).limit(
            page_param.page_size
        ).all()

        items = []
        for record in records:
            items.append({
                "id": str(record.id),
                "event_type": record.event_type,
                "status": record.status,
                "synced_at": record.synced_at.isoformat() if record.synced_at else None,
                "create_time": record.create_time.isoformat() if record.create_time else None,
            })

        return PageResult(
            list=items,
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    @transactional
    async def resend_notification(self, record_id: str) -> dict[str, Any]:
        """Resend a failed notification (N-02)."""
        from app.domains.sys.models import OutboxEvent

        session = get_db_session()
        tenant_id = ctx.tenant_id
        record_id_int = int(record_id)

        record = session.query(OutboxEvent).filter(
            OutboxEvent.id == record_id_int,
            OutboxEvent.tenant_id == tenant_id,
            OutboxEvent.deleted == 0,
        ).first()

        if not record:
            raise BizError(1504)

        # Reset status to trigger resend
        record.status = "PENDING"
        session.flush()

        return {
            "id": str(record.id),
            "status": record.status,
        }
