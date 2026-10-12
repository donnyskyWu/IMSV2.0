# app/db/guard.py - Fail-closed data scope and platform writes (FP-C02)
"""Missing context and scope calculation errors become 1008."""

from typing import Any, Callable

from app.core.context import ctx
from app.core.errors import BizError

SCOPE_LOGS: list[str] = []


def guarded_call(fn: Callable[[], Any]) -> Any:
    """Reject a missing user and hide scope calculation failures."""
    context = ctx.current_or_none
    if context is None or context.user_id is None:
        raise BizError(1008)
    try:
        return fn()
    except BizError:
        raise
    except Exception:
        SCOPE_LOGS.append("scope")
        raise BizError(1008) from None


def create_in_scope(repo: Any, entity: Any) -> Any:
    """An empty data scope cannot create a scoped row."""
    fields = getattr(repo.model, "__scope_fields__", None)
    context = ctx.current_or_none
    if fields and (context is None or not context.data_scopes):
        raise BizError(1008)
    return repo.create(entity)


def read_in_scope(repo: Any, entity_id: int) -> Any:
    """Read only rows the current scope can list. Anything else is 1504."""
    for row in repo.list():
        if row.id == entity_id:
            return row
    raise BizError(1504)


def rename_platform_menu(menu_id: int, name: str) -> None:
    """Platform menus can only be edited from the platform tenant."""
    from app.db.session import get_db_session
    from app.domains.sys.models import Menu

    if ctx.tenant_id != 1:
        raise BizError(1008)
    session = get_db_session()
    menu = session.query(Menu).filter(Menu.id == menu_id, Menu.deleted == 0).first()
    if menu is None:
        raise BizError(1504)
    menu.name = name
    session.flush()
