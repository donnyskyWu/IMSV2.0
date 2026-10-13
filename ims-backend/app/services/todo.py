# app/services/todo.py - 待办生成与关闭 (FP-G02-01)
"""待办服务。业务模块通过 create / complete / cancel 接入，不直接写表。"""

from datetime import datetime
from typing import Optional

from app.db.ids import assign_pk
from app.db.session import get_db_session


class TodoService:
    """FP-G02-01。同一来源同一类型只保留一条待处理待办。"""

    def create(
        self,
        *,
        type: str,
        source_module: str,
        source_type: str,
        source_id: str,
        title: str,
        route: str,
        assignee_user_ids: list[int],
        due_time: Optional[datetime] = None,
        tenant_id: Optional[int] = None,
    ):
        from app.core.context import ctx
        from app.domains.sys.models import TodoItem

        session = get_db_session()
        tenant = tenant_id if tenant_id is not None else ctx.tenant_id
        existing = session.query(TodoItem).filter(
            TodoItem.tenant_id == tenant,
            TodoItem.source_type == source_type,
            TodoItem.source_id == str(source_id),
            TodoItem.todo_type == type,
            TodoItem.status == "PENDING",
            TodoItem.deleted == 0,
        ).first()
        if existing is not None:
            return existing

        assignee = assignee_user_ids[0] if assignee_user_ids else 0
        row = TodoItem(
            tenant_id=tenant,
            assignee_user_id=assignee,
            title=title[:200],
            status="PENDING",
            todo_type=type,
            source_module=source_module,
            source_type=source_type,
            source_id=str(source_id),
            route=route,
            due_time=due_time,
        )
        assign_pk(session, row)
        session.add(row)
        session.flush()
        return row

    def complete(self, source_type: str, source_id: str, by_user: int) -> None:
        self._set_status(source_type, source_id, "DONE", by_user)

    def cancel(self, source_type: str, source_id: str, reason: str) -> None:
        self._set_status(source_type, source_id, "CANCELLED", None, reason)

    def _set_status(
        self,
        source_type: str,
        source_id: str,
        status: str,
        by_user: Optional[int],
        reason: Optional[str] = None,
    ) -> None:
        from app.core.context import ctx
        from app.domains.sys.models import TodoItem

        session = get_db_session()
        rows = session.query(TodoItem).filter(
            TodoItem.tenant_id == ctx.tenant_id,
            TodoItem.source_type == source_type,
            TodoItem.source_id == str(source_id),
            TodoItem.status == "PENDING",
            TodoItem.deleted == 0,
        ).all()
        for row in rows:
            row.status = status
            if by_user:
                row.updater = by_user
            if reason:
                row.event_id = reason[:64]
        session.flush()
