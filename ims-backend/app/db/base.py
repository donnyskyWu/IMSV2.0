# app/db/base.py - Base model classes (FP-B01-01)
"""
Base model classes with audit fields.

Rules per FP-B01-01:
- All ims_* models inherit AuditBase
- Fields: id (BIGINT auto), tenant_id (BIGINT NOT NULL), creator, create_time,
          updater, update_time, deleted (BIGINT NOT NULL DEFAULT 0)
- creator/updater from ctx.userId (Worker=0, migration=data-migration user id)
- create_time/update_time auto-filled
- Logical delete: deleted = id (not 1) - allows recreating same business code
- Business code unique key: (tenant_id, code_column, deleted)
- Test scan: any ims_* model not inheriting AuditBase -> failure
- Exception list: log tables, association tables (only need tenant_id, create_time, creator)
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Column, DateTime, String, event
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from app.core.clock import get_now
from app.core.context import ctx


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    
    type_annotation_map = {
        int: BigInteger,
    }


class AuditMixin:
    """
    Audit fields mixin.
    
    Provides standard audit fields for all business models.
    """
    
    # Primary key - BIGINT auto increment
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Tenant isolation
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    
    # Audit fields
    creator: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updater: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Logical delete: deleted = id when deleted, 0 otherwise
    # This allows recreating records with the same business code after deletion
    deleted: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class AuditBase(Base, AuditMixin):
    """
    Base class for all IMS business models.
    
    All ims_* tables should inherit from this class.
    Includes automatic audit field population.
    """
    
    __abstract__ = True
    
    # Subclasses can set this to True to enable version-based optimistic locking
    __versioned__: bool = False
    
    # Subclasses can set this to True to enable change tracking (FP-F02-01)
    __track_changes__: bool = False
    
    # Platform-level data (no tenant filtering on read)
    __platform__: bool = False
    
    # Scope fields for data range filtering (FP-C02-02)
    # e.g., {"dept": "dept_id", "ip_group": "ip_group_id", "owner": "owner_user_id"}
    __scope_fields__: dict[str, str] = {}
    
    # Shared data with publish scope (FP-C02-04)
    __shared__: bool = False
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case and add ims_ prefix
        import re
        name = re.sub(r"([A-Z])", r"_\1", cls.__name__).lower().lstrip("_")
        if not name.startswith("ims_"):
            name = f"ims_{name}"
        return name


class PlatformBase(Base, AuditMixin):
    """
    Base class for platform-level data.
    
    Platform data (menus, dicts, packages, tenants) has tenant_id fixed to 1
    and is not filtered by tenant on read.
    """
    
    __abstract__ = True
    __platform__ = True


class AssociationBase(Base):
    """
    Base class for association tables.
    
    Association tables only need: tenant_id, create_time, creator
    No id, updater, update_time, deleted.
    """
    
    __abstract__ = True
    
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    creator: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


# Event listeners for automatic audit field population

@event.listens_for(AuditBase, "before_insert", propagate=True)
def set_audit_fields_on_insert(mapper: Any, connection: Any, target: AuditBase) -> None:
    """Set audit fields before insert."""
    now = get_now()
    
    # Set create_time
    if target.create_time is None:
        target.create_time = now
    
    # Set creator from context
    if target.creator is None:
        user_id = ctx.user_id
        target.creator = user_id if user_id is not None else 0
    
    # Set tenant_id from context if not set
    if target.tenant_id is None or target.tenant_id == 0:
        tenant_id = ctx.tenant_id
        if tenant_id is not None:
            target.tenant_id = tenant_id


@event.listens_for(AuditBase, "before_update", propagate=True)
def set_audit_fields_on_update(mapper: Any, connection: Any, target: AuditBase) -> None:
    """Set audit fields before update."""
    now = get_now()
    
    # Set update_time
    target.update_time = now
    
    # Set updater from context
    user_id = ctx.user_id
    target.updater = user_id if user_id is not None else 0


@event.listens_for(AssociationBase, "before_insert", propagate=True)
def set_association_audit_on_insert(
    mapper: Any, connection: Any, target: AssociationBase
) -> None:
    """Set audit fields on association table insert."""
    now = get_now()
    
    if target.create_time is None:
        target.create_time = now
    
    if target.creator is None:
        user_id = ctx.user_id
        target.creator = user_id if user_id is not None else 0
    
    if target.tenant_id is None or target.tenant_id == 0:
        tenant_id = ctx.tenant_id
        if tenant_id is not None:
            target.tenant_id = tenant_id


def soft_delete(entity: AuditBase) -> None:
    """
    Perform soft delete on an entity.
    
    Sets deleted = id to allow recreating same business code.
    """
    entity.deleted = entity.id


def is_deleted(entity: AuditBase) -> bool:
    """Check if entity is soft deleted."""
    return entity.deleted != 0
