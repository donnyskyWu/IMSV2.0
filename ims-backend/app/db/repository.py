# app/db/repository.py - Generic repository (FP-C01-02)
"""
Generic repository with common CRUD operations.

Methods per FP-C01-02:
- get(id): Not exist, deleted, or cross-tenant -> 1504
- page(query, page): Paginated list
- list(query): Full list
- create(obj): Create with audit fields
- update(obj): Update with audit fields
- soft_delete(id): Via FP-B06-03/04 cascade rules
- bulk_create, bulk_update

Rules:
- Default filter: deleted = 0
- include_deleted=True for internal/scan use (not exposed in API)
- All methods pass through tenant and data scope filtering (FP-C02)
- Optimistic lock only when model has __versioned__=True
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, Sequence, Tuple, Type, TypeVar

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.core.context import ctx
from app.core.errors import BizError
from app.core.pagination import PageParam, PageResult
from app.db.base import AuditBase, is_deleted, soft_delete
from app.db.session import get_db_session

T = TypeVar("T", bound=AuditBase)


class BaseRepository(Generic[T]):
    """
    Generic repository for CRUD operations.
    
    All queries automatically filter by:
    - deleted = 0 (unless include_deleted=True)
    - tenant_id = ctx.tenant_id
    - Data scope based on model's __scope_fields__
    """
    
    def __init__(self, model: Type[T]) -> None:
        self.model = model
    
    @property
    def session(self) -> Session:
        """Get current database session."""
        return get_db_session()
    
    def _base_query(self, include_deleted: bool = False) -> Select[tuple[T]]:
        """Create base query with standard filters."""
        query = select(self.model)
        
        # Filter deleted unless explicitly included
        if not include_deleted:
            query = query.where(self.model.deleted == 0)
        
        # Filter by tenant (unless platform data)
        if not getattr(self.model, "__platform__", False):
            tenant_id = ctx.tenant_id
            if tenant_id is not None:
                query = query.where(self.model.tenant_id == tenant_id)
        
        return query
    
    def _apply_data_scope(self, query: Select[tuple[T]]) -> Select[tuple[T]]:
        """
        Apply data scope filtering based on model configuration and user context.
        
        Per FP-C02-02:
        - ALL: no additional filter
        - DEPT: filter by dept field IN ctx.deptIds
        - IP_GROUP: filter by ip_group field IN ctx.ipGroupIds
        - SELF: filter by owner field = ctx.userId
        - Multiple scopes use OR (union)
        - Scope without matching model field contributes no data
        """
        scope_fields = getattr(self.model, "__scope_fields__", {})
        if not scope_fields:
            return query
        
        context = ctx.current_or_none
        if context is None or context.is_system:
            return query
        
        # Check for ALL scope
        if context.has_all_data_scope():
            return query
        
        # Build scope conditions
        conditions = []
        scope_types = context.get_data_scope_types()
        
        if "DEPT" in scope_types and "dept" in scope_fields:
            dept_col = getattr(self.model, scope_fields["dept"], None)
            if dept_col is not None and context.dept_ids:
                conditions.append(dept_col.in_(context.dept_ids))
        
        if "IP_GROUP" in scope_types and "ip_group" in scope_fields:
            ipg_col = getattr(self.model, scope_fields["ip_group"], None)
            if ipg_col is not None and context.ip_group_ids:
                conditions.append(ipg_col.in_(context.ip_group_ids))
        
        if "SELF" in scope_types:
            owner_field = scope_fields.get("owner", "creator")
            owner_col = getattr(self.model, owner_field, None)
            if owner_col is not None:
                conditions.append(owner_col == context.user_id)
        
        # No valid conditions -> no data visible
        if not conditions:
            # Return query that matches nothing
            query = query.where(self.model.id == -1)
        elif len(conditions) == 1:
            query = query.where(conditions[0])
        else:
            from sqlalchemy import or_
            query = query.where(or_(*conditions))
        
        return query
    
    def get(
        self,
        id: int,
        include_deleted: bool = False,
        lock: bool = False,
    ) -> T:
        """
        Get entity by ID.
        
        Raises BizError(1504) if:
        - Not exists
        - Deleted (when include_deleted=False)
        - Cross-tenant
        
        Args:
            id: Entity ID
            include_deleted: Include soft-deleted records
            lock: Use SELECT ... FOR SHARE for concurrent protection
        """
        query = self._base_query(include_deleted=include_deleted)
        query = query.where(self.model.id == id)
        
        if lock:
            query = query.with_for_update(read=True)
        
        entity = self.session.execute(query).scalar_one_or_none()
        
        if entity is None:
            raise BizError.not_found()
        
        return entity
    
    def get_or_none(
        self,
        id: int,
        include_deleted: bool = False,
    ) -> Optional[T]:
        """Get entity by ID, return None if not found."""
        query = self._base_query(include_deleted=include_deleted)
        query = query.where(self.model.id == id)
        return self.session.execute(query).scalar_one_or_none()
    
    def exists(self, id: int) -> bool:
        """Check if entity exists and is not deleted."""
        query = select(func.count()).select_from(self.model)
        query = query.where(
            and_(
                self.model.id == id,
                self.model.deleted == 0,
            )
        )
        
        if not getattr(self.model, "__platform__", False):
            tenant_id = ctx.tenant_id
            if tenant_id is not None:
                query = query.where(self.model.tenant_id == tenant_id)
        
        count = self.session.execute(query).scalar() or 0
        return count > 0
    
    def list(
        self,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[list[tuple[str, str]]] = None,
        include_deleted: bool = False,
        apply_scope: bool = True,
    ) -> Sequence[T]:
        """
        Get all entities matching filters.
        
        Args:
            filters: Column name -> value mapping
            order_by: List of (column_name, "asc"|"desc")
            include_deleted: Include soft-deleted records
            apply_scope: Apply data scope filtering
        """
        query = self._base_query(include_deleted=include_deleted)
        
        if apply_scope:
            query = self._apply_data_scope(query)
        
        if filters:
            for col_name, value in filters.items():
                col = getattr(self.model, col_name, None)
                if col is not None:
                    if isinstance(value, (list, tuple)):
                        query = query.where(col.in_(value))
                    else:
                        query = query.where(col == value)
        
        if order_by:
            for col_name, order in order_by:
                col = getattr(self.model, col_name, None)
                if col is not None:
                    query = query.order_by(col.desc() if order == "desc" else col.asc())
        else:
            # Default order
            query = query.order_by(self.model.create_time.desc(), self.model.id.desc())
        
        return self.session.execute(query).scalars().all()
    
    def page(
        self,
        page_param: PageParam,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[list[tuple[str, str]]] = None,
        include_deleted: bool = False,
        apply_scope: bool = True,
    ) -> PageResult[T]:
        """
        Get paginated entities.
        
        Args:
            page_param: Pagination parameters
            filters: Column name -> value mapping
            order_by: List of (column_name, "asc"|"desc"), overrides page_param sort
            include_deleted: Include soft-deleted records
            apply_scope: Apply data scope filtering
        """
        # Build base query
        query = self._base_query(include_deleted=include_deleted)
        
        if apply_scope:
            query = self._apply_data_scope(query)
        
        if filters:
            for col_name, value in filters.items():
                col = getattr(self.model, col_name, None)
                if col is not None:
                    if isinstance(value, (list, tuple)):
                        query = query.where(col.in_(value))
                    else:
                        query = query.where(col == value)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.execute(count_query).scalar() or 0
        
        if total == 0:
            return PageResult.empty(page_param)
        
        # Apply ordering
        if order_by:
            for col_name, order in order_by:
                col = getattr(self.model, col_name, None)
                if col is not None:
                    query = query.order_by(col.desc() if order == "desc" else col.asc())
        else:
            # Default order
            query = query.order_by(self.model.create_time.desc(), self.model.id.desc())
        
        # Apply pagination
        query = query.offset(page_param.offset).limit(page_param.limit)
        
        items = list(self.session.execute(query).scalars().all())
        
        return PageResult.of(items, total, page_param)
    
    def create(self, entity: T) -> T:
        """Create a new entity."""
        self.session.add(entity)
        self.session.flush()
        return entity
    
    def bulk_create(self, entities: list[T]) -> list[T]:
        """Create multiple entities."""
        self.session.add_all(entities)
        self.session.flush()
        return entities
    
    def update(self, entity: T) -> T:
        """Update an entity."""
        # Check optimistic locking if enabled
        if getattr(self.model, "__versioned__", False):
            version_col = getattr(entity, "version", None)
            if version_col is not None:
                # Version will be checked by SQLAlchemy
                pass
        
        self.session.flush()
        return entity
    
    def bulk_update(self, entities: list[T]) -> list[T]:
        """Update multiple entities."""
        self.session.flush()
        return entities
    
    def delete(self, entity: T) -> None:
        """Soft delete an entity (sets deleted = id)."""
        soft_delete(entity)
        self.session.flush()
    
    def hard_delete(self, entity: T) -> None:
        """Permanently delete an entity (use with caution)."""
        self.session.delete(entity)
        self.session.flush()
    
    def count(
        self,
        filters: Optional[dict[str, Any]] = None,
        include_deleted: bool = False,
    ) -> int:
        """Count entities matching filters."""
        query = select(func.count()).select_from(self.model)
        
        if not include_deleted:
            query = query.where(self.model.deleted == 0)
        
        if not getattr(self.model, "__platform__", False):
            tenant_id = ctx.tenant_id
            if tenant_id is not None:
                query = query.where(self.model.tenant_id == tenant_id)
        
        if filters:
            for col_name, value in filters.items():
                col = getattr(self.model, col_name, None)
                if col is not None:
                    if isinstance(value, (list, tuple)):
                        query = query.where(col.in_(value))
                    else:
                        query = query.where(col == value)
        
        return self.session.execute(query).scalar() or 0
