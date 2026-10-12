# app/db - Database layer
"""
Database components:
- Session management and transaction handling
- Base models (AuditBase)
- Repository pattern
- Reference registry
- Tenant and data scope filtering
"""

from app.db.session import (
    get_db,
    get_db_session,
    engine,
    SessionLocal,
)
from app.db.base import (
    Base,
    AuditBase,
    PlatformBase,
    AssociationBase,
)
from app.db.repository import BaseRepository
from app.db.transaction import transactional

__all__ = [
    "get_db",
    "get_db_session",
    "engine",
    "SessionLocal",
    "Base",
    "AuditBase",
    "PlatformBase",
    "AssociationBase",
    "BaseRepository",
    "transactional",
]
