# app/services/system_calendar.py - Work calendar service (B2-M02)
"""
Work calendar service (Q4).

Implements:
- Calendar list (holidays and extra workdays)
- Calendar update
"""

from typing import Any, Optional

from app.core.context import ctx
from app.db.session import get_db_session
from app.db.transaction import transactional


class SystemCalendarService:
    """Work calendar service for B2 system management."""

    async def get_calendar_list(
        self,
        year: int,
        month: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Get calendar list (Q4)."""
        from app.domains.sys.models import WorkCalendarDay
        
        session = get_db_session()
        tenant_id = ctx.tenant_id

        query = session.query(WorkCalendarDay).filter(
            WorkCalendarDay.tenant_id == tenant_id,
            WorkCalendarDay.deleted == 0,
        )

        # Filter by year
        if month:
            prefix = f"{year}-{month:02d}"
        else:
            prefix = f"{year}-"

        query = query.filter(WorkCalendarDay.day.like(f"{prefix}%"))

        days = query.order_by(WorkCalendarDay.day).all()

        return [
            {
                "id": str(d.id),
                "day": d.day,
                "kind": d.kind,
            }
            for d in days
        ]

    @transactional
    async def update_calendar(
        self,
        day: str,
        kind: str,
    ) -> dict[str, Any]:
        """Update calendar day (Q4)."""
        from app.domains.sys.models import WorkCalendarDay
        from app.db.ids import assign_pk
        
        session = get_db_session()
        tenant_id = ctx.tenant_id

        # Upsert
        existing = session.query(WorkCalendarDay).filter(
            WorkCalendarDay.tenant_id == tenant_id,
            WorkCalendarDay.day == day,
            WorkCalendarDay.deleted == 0,
        ).first()

        if existing:
            if kind == "NORMAL":
                # Delete entry to reset to normal
                existing.deleted = existing.id
            else:
                existing.kind = kind
        else:
            if kind != "NORMAL":
                new_day = WorkCalendarDay(
                    tenant_id=tenant_id,
                    day=day,
                    kind=kind,
                )
                assign_pk(session, new_day)
                session.add(new_day)

        session.flush()

        return {
            "day": day,
            "kind": kind,
        }
