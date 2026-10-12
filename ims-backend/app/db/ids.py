# app/db/ids.py - Explicit primary keys for association and SQLite inserts
"""Assign primary keys when the dialect will not fill BIGINT ids."""

from sqlalchemy import event
from sqlalchemy.orm import Session, object_mapper


def assign_pk(session: Session, obj: object) -> None:
    """Set ``obj.id`` to max(id)+1 when it is missing.

    Unflushed rows in the same session are included so a loop of inserts
    does not reuse one id.
    """
    if getattr(obj, "id", None):
        return
    try:
        columns = object_mapper(obj).columns
    except Exception:
        return
    if "id" not in columns:
        return
    model = type(obj)
    remembered = session.info.setdefault("pk_max", {})
    with session.no_autoflush:
        last = session.query(model.id).order_by(model.id.desc()).limit(1).scalar() or 0
    pending = [
        int(item.id)
        for item in session.new
        if isinstance(item, model) and getattr(item, "id", None)
    ]
    top = max([int(last), int(remembered.get(model, 0)), *pending])
    obj.id = top + 1
    remembered[model] = obj.id


@event.listens_for(Session, "before_flush")
def _fill_sqlite_primary_keys(session: Session, _flush_context: object, _instances: object) -> None:
    """SQLite does not auto-fill BIGINT primary keys. MySQL does."""
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "sqlite":
        return
    for obj in list(session.new):
        assign_pk(session, obj)
