# app/domains/train/scope.py - Training data scope filters (B21)
"""
Data scope filtering for training module.

Per TK-01:
- DEPT = creator_dept_id IN dept_ids OR EXISTS(assigned user in dept_ids)
- SELF = creator == user_id OR user is assigned

Complex conditions cannot be expressed by __scope_fields__ single-field pattern.
Use explicit Repo-layer filtering or custom scope functions.

All scope functions are P0 (90% branch coverage required).
"""

from typing import Optional

from sqlalchemy import Select, or_, select

from app.core.context import DataScope, RequestContext
from app.domains.train.models import TrainTask, TrainTaskRecord


def apply_task_scope_filter(
    query: Select,
    ctx: RequestContext,
) -> Select:
    """
    Apply data scope filter to task query.

    P0 function - 90% branch coverage required.

    Scope rules (per TK-01):
    - ALL: no additional filter
    - DEPT: creator_dept_id IN dept_ids OR EXISTS(record WHERE user_dept_id IN dept_ids)
    - SELF: creator == user_id OR EXISTS(record WHERE user_id == ctx.user_id)
    """
    scope = _get_effective_scope(ctx)

    if scope == DataScope.ALL:
        return query

    if scope == DataScope.DEPT:
        dept_ids = ctx.dept_ids or []
        if not dept_ids:
            return query.where(False)

        assigned_in_dept = (
            select(TrainTaskRecord.task_id)
            .where(
                TrainTaskRecord.user_dept_id.in_(dept_ids),
                TrainTaskRecord.deleted == 0,
            )
            .distinct()
        )
        return query.where(
            or_(
                TrainTask.creator_dept_id.in_(dept_ids),
                TrainTask.id.in_(assigned_in_dept),
            )
        )

    if scope == DataScope.SELF:
        user_id = ctx.user_id
        if not user_id:
            return query.where(False)

        self_assigned = (
            select(TrainTaskRecord.task_id)
            .where(
                TrainTaskRecord.user_id == user_id,
                TrainTaskRecord.deleted == 0,
            )
            .distinct()
        )
        return query.where(
            or_(
                TrainTask.creator == user_id,
                TrainTask.id.in_(self_assigned),
            )
        )

    return query


def apply_record_scope_filter(
    query: Select,
    ctx: RequestContext,
) -> Select:
    """
    Apply data scope filter to record query.

    P0 function - 90% branch coverage required.

    Scope rules:
    - ALL: no additional filter
    - DEPT: user_dept_id IN ctx.dept_ids
    - SELF: user_id == ctx.user_id
    """
    scope = _get_effective_scope(ctx)

    if scope == DataScope.ALL:
        return query

    if scope == DataScope.DEPT:
        dept_ids = ctx.dept_ids or []
        if not dept_ids:
            return query.where(False)
        return query.where(TrainTaskRecord.user_dept_id.in_(dept_ids))

    if scope == DataScope.SELF:
        user_id = ctx.user_id
        if not user_id:
            return query.where(False)
        return query.where(TrainTaskRecord.user_id == user_id)

    return query


def get_stat_visible_depts(
    ctx: RequestContext,
    request_dept_id: Optional[int],
) -> tuple[Optional[list[int]], bool]:
    """
    Get visible departments for statistics queries.

    P0 function - 90% branch coverage required.

    Returns:
        (visible_dept_ids, is_self_only)
        - (None, False): all departments visible
        - ([dept_ids], False): limited to specific departments
        - (None, True): self only (ignore departments)
        - ([], False): no data (intersection empty)

    E2E-B21-38: DEPT user passing other dept's ID -> empty result (intersection)
    """
    scope = _get_effective_scope(ctx)

    if scope == DataScope.SELF:
        return None, True

    if scope == DataScope.ALL:
        if request_dept_id:
            return [request_dept_id], False
        return None, False

    if scope == DataScope.DEPT:
        user_depts = ctx.dept_ids or []
        if not user_depts:
            return [], False

        if request_dept_id:
            if request_dept_id in user_depts:
                return [request_dept_id], False
            return [], False

        return list(user_depts), False

    return None, False


def check_task_in_scope(
    ctx: RequestContext,
    task: TrainTask,
    assigned_user_dept_ids: list[int],
) -> bool:
    """
    Check if a task is within the user's data scope.

    P0 function - 90% branch coverage required.

    Args:
        ctx: Request context
        task: The task to check
        assigned_user_dept_ids: Department IDs of users assigned to this task

    Returns:
        True if task is visible to the user
    """
    scope = _get_effective_scope(ctx)

    if scope == DataScope.ALL:
        return True

    if scope == DataScope.DEPT:
        user_depts = set(ctx.dept_ids or [])
        if task.creator_dept_id in user_depts:
            return True
        return bool(user_depts.intersection(assigned_user_dept_ids))

    if scope == DataScope.SELF:
        return task.creator == ctx.user_id

    return False


def _get_effective_scope(ctx: RequestContext) -> DataScope:
    """Get the effective data scope from context."""
    if ctx.data_scopes:
        for ds in ctx.data_scopes:
            scope_type = ds.get("scope_type")
            if scope_type:
                try:
                    return DataScope(scope_type)
                except ValueError:
                    pass
    return DataScope.SELF


def get_user_perm_key(user_id: int) -> str:
    """Get Redis key for user permission version."""
    return f"ims:perm_ver:u:{user_id}"


def get_tenant_perm_key(tenant_id: int) -> str:
    """Get Redis key for tenant permission version."""
    return f"ims:perm_ver:t:{tenant_id}"
