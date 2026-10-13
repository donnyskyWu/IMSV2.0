# 待办最小实现（B5，B3 未合入时使用）。版本 v1.0 · 2026-10-13
"""todo.create / complete / cancel 落在 ims_sys_todo。"""

from __future__ import annotations

from app.db.session import get_db_session
from app.domains.sys.models import TodoItem
from app.services.corp_support import add_row, base_stmt


class TodoService:
    """同一事件只保留一条未关闭待办。"""

    def create(self, assignee_user_id: int, title: str, type: str, source_type: str, source_id: int) -> TodoItem:
        event_id = f"{source_type}:{source_id}"
        session = get_db_session()
        existing = session.execute(
            base_stmt(TodoItem).where(
                TodoItem.event_id == event_id,
                TodoItem.assignee_user_id == int(assignee_user_id),
                TodoItem.status == "OPEN",
            )
        ).scalars().first()
        if existing is not None:
            return existing
        row = TodoItem(
            assignee_user_id=int(assignee_user_id),
            title=title,
            event_id=event_id,
            status="OPEN",
        )
        # type 是调用约定里的「预警」，标题已带级别，表上没有 type 列。
        _ = type
        return add_row(session, row)

    def complete(self, source_type: str, source_id: int) -> int:
        return self._close(source_type, source_id, "DONE")

    def cancel(self, source_type: str, source_id: int) -> int:
        return self._close(source_type, source_id, "CANCELLED")

    def _close(self, source_type: str, source_id: int, status: str) -> int:
        session = get_db_session()
        event_id = f"{source_type}:{source_id}"
        rows = session.execute(
            base_stmt(TodoItem).where(TodoItem.event_id == event_id, TodoItem.status == "OPEN")
        ).scalars().all()
        for row in rows:
            row.status = status
        session.flush()
        return len(rows)


todo = TodoService()
