# app/services/attendance.py - Working-day calculation (FP-H07)
"""Calendar math for expected submission days. Mock fetch makes no HTTP calls."""

from datetime import date, timedelta
from typing import Any, Optional

from app.core.errors import BizError
from app.db.ids import assign_pk
from app.db.session import get_db_session

CALENDAR_PERM = "ims:system:calendar:update"
SECRET_MASK = "******"


def mask_secret(_value: str) -> str:
    """App secrets are never returned in clear text."""
    return SECRET_MASK


def _parse(day: str) -> date:
    year, month, dd = [int(part) for part in day.split("-")]
    return date(year, month, dd)


def _is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def month_days(year: int, month: int) -> list[date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    days = []
    cursor = start
    while cursor < end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


class AttendanceService:
    """Expected-day calculator and mock leave fetch."""

    def __init__(self) -> None:
        self.http_calls: list[str] = []
        self.logs: list[str] = []

    def expected_days(
        self,
        year: int,
        month: int,
        *,
        base_weekdays: Optional[int] = None,
        enabled: bool = False,
        fetch_failed: bool = False,
        leaves: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Return expected submission days and the degraded flag."""
        from app.domains.sys.models import WorkCalendarDay

        session = get_db_session()
        holidays = set()
        extras = set()
        rows = session.query(WorkCalendarDay).filter(WorkCalendarDay.deleted == 0).all()
        for row in rows:
            parsed = _parse(row.day)
            if parsed.year == year and parsed.month == month:
                if row.kind == "HOLIDAY":
                    holidays.add(parsed)
                elif row.kind == "WORKDAY":
                    extras.add(parsed)

        if base_weekdays is None:
            base = sum(1 for day in month_days(year, month) if not _is_weekend(day))
        else:
            base = base_weekdays
        holiday_hit = sum(1 for day in holidays if not _is_weekend(day))
        makeup = len(extras)
        basic = base - holiday_hit + makeup
        if fetch_failed or not enabled:
            return {"days": basic, "degraded": bool(fetch_failed)}

        deducted = 0.0
        for leave in leaves or []:
            deducted += self._leave_days_in_month(year, month, leave, holidays, extras)
        return {"days": basic - deducted, "degraded": False}

    def _leave_days_in_month(
        self,
        year: int,
        month: int,
        leave: dict[str, Any],
        holidays: set[date],
        extras: set[date],
    ) -> float:
        start = _parse(leave["start"])
        end = _parse(leave["end"])
        portion = float(leave.get("portion", 1))
        if start == end and portion < 1:
            if start.year == year and start.month == month and self._is_workday(start, holidays, extras):
                return portion
            return 0.0
        total = 0.0
        cursor = start
        while cursor <= end:
            if cursor.year == year and cursor.month == month and self._is_workday(
                cursor, holidays, extras
            ):
                total += 1
            cursor += timedelta(days=1)
        return total

    def _is_workday(self, day: date, holidays: set[date], extras: set[date]) -> bool:
        if day in extras:
            return True
        return not (day in holidays or _is_weekend(day))

    def set_holiday(self, day: str, perm_codes: set[str]) -> None:
        """Mark a day as a holiday when the caller holds the calendar permission."""
        from app.domains.sys.models import OperateLog, WorkCalendarDay

        if CALENDAR_PERM not in perm_codes:
            raise BizError(1008)
        session = get_db_session()
        row = session.query(WorkCalendarDay).filter(
            WorkCalendarDay.day == day,
            WorkCalendarDay.deleted == 0,
        ).first()
        if row is None:
            row = WorkCalendarDay(tenant_id=1, day=day, kind="HOLIDAY")
            assign_pk(session, row)
            session.add(row)
        else:
            row.kind = "HOLIDAY"
        log = OperateLog(
            tenant_id=1,
            module="考勤",
            operation="修改工作日历",
            result="SUCCESS",
        )
        assign_pk(session, log)
        session.add(log)
        session.flush()

    def fetch_leaves(
        self,
        month: str,
        *,
        mode: str = "mock",
        timeout: bool = False,
        rows: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Pull leave rows. Mock mode does not call HTTP. A second pull is idempotent."""
        from app.domains.sys.models import LeaveRecord

        session = get_db_session()
        if mode != "mock":
            self.http_calls.append("GET /attendance")
        if timeout:
            state = self._state(session, month, "FAILED")
            self.logs.append(f"{month} 同步失败")
            session.flush()
            return {"status": state.status, "count": 0}
        incoming = rows or []
        for item in incoming:
            exists = session.query(LeaveRecord).filter(
                LeaveRecord.user_id == item["user_id"],
                LeaveRecord.start_day == item["start"],
                LeaveRecord.end_day == item["end"],
                LeaveRecord.deleted == 0,
            ).first()
            if exists is None:
                record = LeaveRecord(
                    tenant_id=1,
                    user_id=item["user_id"],
                    start_day=item["start"],
                    end_day=item["end"],
                    portion=str(item.get("portion", "1")),
                )
                assign_pk(session, record)
                session.add(record)
        state = self._state(session, month, "OK")
        session.flush()
        count = session.query(LeaveRecord).filter(LeaveRecord.deleted == 0).count()
        return {"status": state.status, "count": count, "http_calls": list(self.http_calls)}

    def _state(self, session: Any, month: str, status: str) -> Any:
        from app.domains.sys.models import AttendanceSyncState

        row = session.query(AttendanceSyncState).filter(
            AttendanceSyncState.month == month,
            AttendanceSyncState.deleted == 0,
        ).first()
        if row is None:
            row = AttendanceSyncState(tenant_id=1, month=month, status=status)
            assign_pk(session, row)
            session.add(row)
        else:
            row.status = status
        return row

    def config_snapshot(self, secret: str) -> dict[str, str]:
        return {"app_secret": mask_secret(secret), "logged": mask_secret(secret)}

