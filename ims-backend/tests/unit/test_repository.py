# tests/unit/test_repository.py - Generic repository tests (FP-C01-02)
"""
Unit tests for app/db/repository.py.

Tests cover:
- UT-C01-02-01: get() retrieves entity by ID
- UT-C01-02-02: get() raises 1504 for not found
- UT-C01-02-03: get() raises 1504 for deleted
- UT-C01-02-04: get_or_none() returns None for not found
- UT-C01-02-05: exists() checks entity existence
- UT-C01-02-06: list() with filters
- UT-C01-02-07: list() with order_by
- UT-C01-02-08: page() returns paginated result
- UT-C01-02-09: create() adds entity
- UT-C01-02-10: bulk_create() adds multiple entities
- UT-C01-02-11: update() modifies entity
- UT-C01-02-12: delete() soft-deletes entity
- UT-C01-02-13: hard_delete() permanently removes entity
- UT-C01-02-14: count() counts entities
- UT-C01-02-15: _apply_data_scope() with DEPT scope
- UT-C01-02-16: _apply_data_scope() with SELF scope
- UT-C01-02-17: _apply_data_scope() with ALL scope
- UT-C01-02-18: _apply_data_scope() with IP_GROUP scope
- UT-C01-02-19: _base_query() filters deleted records
- UT-C01-02-20: _base_query() filters by tenant_id
- UT-C01-02-21: list() with include_deleted=True
- UT-C01-02-22: page() empty result
- UT-C01-02-23: list() with list filter values (IN clause)
- UT-C01-02-24: get() with lock=True
"""

import os

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")

from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import BizError
from app.core.pagination import PageParam
from app.db.base import AuditBase, Base
from app.db.repository import BaseRepository


class TestEntity(AuditBase):
    """Test entity for repository tests."""
    __tablename__ = "test_entity"
    __scope_fields__ = {"dept": "dept_id", "owner": "creator"}
    
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="ACTIVE")
    dept_id = Column(Integer, nullable=True)


class PlatformEntity(AuditBase):
    """Test platform entity (no tenant filtering)."""
    __tablename__ = "platform_entity"
    __platform__ = True
    
    name = Column(String(100), nullable=False)


class ScopedEntity(AuditBase):
    """Entity with IP_GROUP scope."""
    __tablename__ = "scoped_entity"
    __scope_fields__ = {"ip_group": "ip_group_id", "owner": "creator"}
    
    name = Column(String(100), nullable=False)
    ip_group_id = Column(Integer, nullable=True)


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_context():
    """Create a mock context."""
    context = MagicMock()
    context.tenant_id = 1
    context.user_id = 100
    context.dept_ids = [10, 20]
    context.ip_group_ids = [1, 2]
    context.is_system = False
    context.has_all_data_scope = MagicMock(return_value=False)
    context.get_data_scope_types = MagicMock(return_value=["DEPT", "SELF"])
    return context


@pytest.fixture
def sample_entities(db_session):
    """Create sample test entities."""
    now = datetime.now()
    entities = []
    for i in range(5):
        entity = TestEntity(
            id=i + 1,
            name=f"Entity {i + 1}",
            status="ACTIVE" if i % 2 == 0 else "INACTIVE",
            dept_id=10 if i < 3 else 20,
            tenant_id=1,
            deleted=0,
            creator=100 if i < 2 else 200,
            create_time=now,
            update_time=now,
        )
        db_session.add(entity)
        entities.append(entity)
    
    # Add a deleted entity
    deleted_entity = TestEntity(
        id=10,
        name="Deleted Entity",
        status="DELETED",
        dept_id=10,
        tenant_id=1,
        deleted=10,  # Soft-deleted (deleted = id)
        creator=100,
        create_time=now,
        update_time=now,
    )
    db_session.add(deleted_entity)
    
    # Add entity for different tenant
    other_tenant = TestEntity(
        id=20,
        name="Other Tenant Entity",
        status="ACTIVE",
        dept_id=10,
        tenant_id=2,
        deleted=0,
        creator=100,
        create_time=now,
        update_time=now,
    )
    db_session.add(other_tenant)
    
    db_session.commit()
    return entities


class TestRepositoryGet:
    """Tests for repository.get() method."""

    def test_get_entity_by_id(self, db_session, sample_entities):
        """UT-C01-02-01: get() retrieves entity by ID."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                entity = repo.get(1)
                
                assert entity is not None
                assert entity.id == 1
                assert entity.name == "Entity 1"

    def test_get_not_found_raises_1504(self, db_session, sample_entities):
        """UT-C01-02-02: get() raises 1504 for not found."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                with pytest.raises(BizError) as exc_info:
                    repo.get(999)
                
                assert exc_info.value.code == 1504

    def test_get_deleted_raises_1504(self, db_session, sample_entities):
        """UT-C01-02-03: get() raises 1504 for deleted entity."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                with pytest.raises(BizError) as exc_info:
                    repo.get(10)
                
                assert exc_info.value.code == 1504

    def test_get_deleted_with_include_deleted(self, db_session, sample_entities):
        """UT-C01-02-03b: get() with include_deleted=True retrieves deleted."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                entity = repo.get(10, include_deleted=True)
                
                assert entity is not None
                assert entity.id == 10
                assert entity.deleted == 10

    def test_get_cross_tenant_raises_1504(self, db_session, sample_entities):
        """UT-C01-02-03c: get() raises 1504 for cross-tenant access."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                # Entity 20 belongs to tenant 2
                with pytest.raises(BizError) as exc_info:
                    repo.get(20)
                
                assert exc_info.value.code == 1504


class TestRepositoryGetOrNone:
    """Tests for repository.get_or_none() method."""

    def test_get_or_none_found(self, db_session, sample_entities):
        """UT-C01-02-04a: get_or_none() returns entity when found."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                entity = repo.get_or_none(1)
                
                assert entity is not None
                assert entity.id == 1

    def test_get_or_none_not_found(self, db_session, sample_entities):
        """UT-C01-02-04: get_or_none() returns None for not found."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                entity = repo.get_or_none(999)
                
                assert entity is None


class TestRepositoryExists:
    """Tests for repository.exists() method."""

    def test_exists_returns_true(self, db_session, sample_entities):
        """UT-C01-02-05a: exists() returns True for existing entity."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                result = repo.exists(1)
                
                assert result is True

    def test_exists_returns_false_not_found(self, db_session, sample_entities):
        """UT-C01-02-05: exists() returns False for non-existent entity."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                result = repo.exists(999)
                
                assert result is False

    def test_exists_returns_false_for_deleted(self, db_session, sample_entities):
        """UT-C01-02-05b: exists() returns False for deleted entity."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                result = repo.exists(10)
                
                assert result is False


class TestRepositoryList:
    """Tests for repository.list() method."""

    def test_list_all(self, db_session, sample_entities, mock_context):
        """UT-C01-02-06a: list() returns all entities."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None  # No scope filtering
                
                entities = repo.list(apply_scope=False)
                
                assert len(entities) == 5  # Excludes deleted and other tenant

    def test_list_with_filters(self, db_session, sample_entities, mock_context):
        """UT-C01-02-06: list() with filters."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entities = repo.list(filters={"status": "ACTIVE"}, apply_scope=False)
                
                assert len(entities) == 3
                for e in entities:
                    assert e.status == "ACTIVE"

    def test_list_with_order_by(self, db_session, sample_entities, mock_context):
        """UT-C01-02-07: list() with order_by."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entities = repo.list(order_by=[("name", "asc")], apply_scope=False)
                
                assert len(entities) == 5
                assert entities[0].name == "Entity 1"
                assert entities[-1].name == "Entity 5"

    def test_list_with_order_by_desc(self, db_session, sample_entities, mock_context):
        """UT-C01-02-07b: list() with descending order."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entities = repo.list(order_by=[("name", "desc")], apply_scope=False)
                
                assert len(entities) == 5
                assert entities[0].name == "Entity 5"

    def test_list_with_include_deleted(self, db_session, sample_entities, mock_context):
        """UT-C01-02-21: list() with include_deleted=True."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entities = repo.list(include_deleted=True, apply_scope=False)
                
                assert len(entities) == 6  # Includes deleted

    def test_list_with_list_filter(self, db_session, sample_entities, mock_context):
        """UT-C01-02-23: list() with list filter values (IN clause)."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entities = repo.list(filters={"dept_id": [10, 20]}, apply_scope=False)
                
                assert len(entities) == 5


class TestRepositoryPage:
    """Tests for repository.page() method."""

    def test_page_returns_paginated_result(self, db_session, sample_entities, mock_context):
        """UT-C01-02-08: page() returns paginated result."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                page_param = PageParam(page_no=1, page_size=2)
                result = repo.page(page_param, apply_scope=False)
                
                assert result.total == 5
                assert len(result.list) == 2
                assert result.page_no == 1
                assert result.page_size == 2
                assert result.has_more is True

    def test_page_second_page(self, db_session, sample_entities, mock_context):
        """UT-C01-02-08b: page() returns second page."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                page_param = PageParam(page_no=2, page_size=2)
                result = repo.page(page_param, apply_scope=False)
                
                assert result.total == 5
                assert len(result.list) == 2
                assert result.page_no == 2

    def test_page_with_filters(self, db_session, sample_entities, mock_context):
        """UT-C01-02-08c: page() with filters."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                page_param = PageParam(page_no=1, page_size=10)
                result = repo.page(page_param, filters={"status": "ACTIVE"}, apply_scope=False)
                
                assert result.total == 3
                assert len(result.list) == 3

    def test_page_empty_result(self, db_session, sample_entities, mock_context):
        """UT-C01-02-22: page() empty result."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                page_param = PageParam(page_no=1, page_size=10)
                result = repo.page(page_param, filters={"status": "NONEXISTENT"}, apply_scope=False)
                
                assert result.total == 0
                assert len(result.list) == 0
                assert result.has_more is False

    def test_page_with_order_by(self, db_session, sample_entities, mock_context):
        """UT-C01-02-08d: page() with custom order."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                page_param = PageParam(page_no=1, page_size=10)
                result = repo.page(page_param, order_by=[("name", "asc")], apply_scope=False)
                
                assert result.list[0].name == "Entity 1"


class TestRepositoryCreate:
    """Tests for repository.create() method."""

    def test_create_adds_entity(self, db_session, sample_entities):
        """UT-C01-02-09: create() adds entity."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.user_id = 100
                mock_ctx.current_or_none = None
                
                now = datetime.now()
                entity = TestEntity(
                    id=100,  # Explicit ID for SQLite
                    name="New Entity",
                    status="ACTIVE",
                    dept_id=10,
                    tenant_id=1,
                    deleted=0,
                    creator=100,
                    create_time=now,
                    update_time=now,
                )
                
                result = repo.create(entity)
                
                assert result.id is not None
                assert result.name == "New Entity"
                
                # Verify in database
                found = db_session.get(TestEntity, result.id)
                assert found is not None
                assert found.name == "New Entity"


class TestRepositoryBulkCreate:
    """Tests for repository.bulk_create() method."""

    def test_bulk_create_adds_multiple(self, db_session, sample_entities):
        """UT-C01-02-10: bulk_create() adds multiple entities."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.user_id = 100
                mock_ctx.current_or_none = None
                
                now = datetime.now()
                entities = [
                    TestEntity(
                        id=100 + i,  # Explicit IDs for SQLite
                        name=f"Bulk Entity {i}",
                        status="ACTIVE",
                        dept_id=10,
                        tenant_id=1,
                        deleted=0,
                        creator=100,
                        create_time=now,
                        update_time=now,
                    )
                    for i in range(3)
                ]
                
                results = repo.bulk_create(entities)
                
                assert len(results) == 3
                for r in results:
                    assert r.id is not None


class TestRepositoryUpdate:
    """Tests for repository.update() method."""

    def test_update_modifies_entity(self, db_session, sample_entities):
        """UT-C01-02-11: update() modifies entity."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entity = sample_entities[0]
                entity.name = "Updated Name"
                
                result = repo.update(entity)
                
                assert result.name == "Updated Name"
                
                # Verify in database
                found = db_session.get(TestEntity, 1)
                assert found.name == "Updated Name"


class TestRepositoryBulkUpdate:
    """Tests for repository.bulk_update() method."""

    def test_bulk_update_modifies_multiple(self, db_session, sample_entities):
        """UT-C01-02-11b: bulk_update() modifies multiple entities."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                sample_entities[0].name = "Bulk Updated 1"
                sample_entities[1].name = "Bulk Updated 2"
                
                results = repo.bulk_update([sample_entities[0], sample_entities[1]])
                
                assert len(results) == 2


class TestRepositoryDelete:
    """Tests for repository.delete() method."""

    def test_delete_soft_deletes(self, db_session, sample_entities):
        """UT-C01-02-12: delete() soft-deletes entity."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entity = sample_entities[0]
                entity_id = entity.id
                
                repo.delete(entity)
                
                # Verify soft-deleted (deleted = id)
                found = db_session.get(TestEntity, entity_id)
                assert found.deleted == entity_id


class TestRepositoryHardDelete:
    """Tests for repository.hard_delete() method."""

    def test_hard_delete_removes_permanently(self, db_session, sample_entities):
        """UT-C01-02-13: hard_delete() permanently removes entity."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entity = sample_entities[0]
                entity_id = entity.id
                
                repo.hard_delete(entity)
                
                # Verify permanently deleted
                found = db_session.get(TestEntity, entity_id)
                assert found is None


class TestRepositoryCount:
    """Tests for repository.count() method."""

    def test_count_all(self, db_session, sample_entities):
        """UT-C01-02-14a: count() returns total count."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                count = repo.count()
                
                assert count == 5

    def test_count_with_filters(self, db_session, sample_entities):
        """UT-C01-02-14: count() with filters."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                count = repo.count(filters={"status": "ACTIVE"})
                
                assert count == 3

    def test_count_with_list_filter(self, db_session, sample_entities):
        """UT-C01-02-14b: count() with list filter (IN clause)."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                count = repo.count(filters={"dept_id": [10]})
                
                assert count == 3

    def test_count_with_include_deleted(self, db_session, sample_entities):
        """UT-C01-02-14c: count() with include_deleted."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                count = repo.count(include_deleted=True)
                
                assert count == 6


class TestRepositoryDataScope:
    """Tests for repository data scope filtering."""

    def test_apply_data_scope_with_dept(self, db_session, sample_entities, mock_context):
        """UT-C01-02-15: _apply_data_scope() with DEPT scope."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_context.get_data_scope_types.return_value = ["DEPT"]
                mock_ctx.current_or_none = mock_context
                
                entities = repo.list(apply_scope=True)
                
                # Should only return entities with dept_id in [10, 20]
                assert all(e.dept_id in [10, 20] for e in entities)

    def test_apply_data_scope_with_self(self, db_session, sample_entities, mock_context):
        """UT-C01-02-16: _apply_data_scope() with SELF scope."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_context.get_data_scope_types.return_value = ["SELF"]
                mock_context.dept_ids = []  # No dept access
                mock_ctx.current_or_none = mock_context
                
                entities = repo.list(apply_scope=True)
                
                # Should only return entities created by user 100
                assert all(e.creator == 100 for e in entities)

    def test_apply_data_scope_with_all(self, db_session, sample_entities, mock_context):
        """UT-C01-02-17: _apply_data_scope() with ALL scope."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_context.has_all_data_scope.return_value = True
                mock_ctx.current_or_none = mock_context
                
                entities = repo.list(apply_scope=True)
                
                # Should return all entities (no scope filtering)
                assert len(entities) == 5

    def test_apply_data_scope_system_context(self, db_session, sample_entities, mock_context):
        """UT-C01-02-17b: _apply_data_scope() with system context."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_context.is_system = True
                mock_ctx.current_or_none = mock_context
                
                entities = repo.list(apply_scope=True)
                
                # System context should bypass scope
                assert len(entities) == 5

    def test_apply_data_scope_no_valid_conditions(self, db_session, sample_entities, mock_context):
        """UT-C01-02-18b: _apply_data_scope() with no valid conditions returns nothing."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_context.get_data_scope_types.return_value = ["DEPT"]
                mock_context.dept_ids = []  # No dept access
                mock_context.has_all_data_scope.return_value = False
                mock_ctx.current_or_none = mock_context
                
                entities = repo.list(apply_scope=True)
                
                # No valid conditions -> no data visible
                assert len(entities) == 0


class TestRepositoryBaseQuery:
    """Tests for repository._base_query() method."""

    def test_base_query_filters_deleted(self, db_session, sample_entities):
        """UT-C01-02-19: _base_query() filters deleted records."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entities = repo.list(include_deleted=False, apply_scope=False)
                
                assert all(e.deleted == 0 for e in entities)

    def test_base_query_filters_tenant(self, db_session, sample_entities):
        """UT-C01-02-20: _base_query() filters by tenant_id."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.current_or_none = None
                
                entities = repo.list(apply_scope=False)
                
                assert all(e.tenant_id == 1 for e in entities)


class TestRepositoryPlatformEntity:
    """Tests for platform entities (no tenant filtering)."""

    def test_platform_entity_no_tenant_filter(self, engine, db_session):
        """UT-C01-02-20b: Platform entity has no tenant filtering."""
        repo = BaseRepository(PlatformEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = None
                mock_ctx.user_id = 100
                mock_ctx.current_or_none = None
                
                now = datetime.now()
                entity = PlatformEntity(
                    id=1,
                    name="Platform Entity",
                    tenant_id=1,
                    deleted=0,
                    creator=100,
                    create_time=now,
                    update_time=now,
                )
                db_session.add(entity)
                db_session.commit()
                
                entities = repo.list(apply_scope=False)
                
                assert len(entities) == 1
                assert entities[0].name == "Platform Entity"


class TestRepositoryLock:
    """Tests for repository locking."""

    @pytest.mark.skipif(
        "sqlite" in os.environ.get("IMS_DB_URL", "sqlite"),
        reason="SQLite doesn't support FOR UPDATE - run with MySQL"
    )
    def test_get_with_lock(self, db_session, sample_entities):
        """UT-C01-02-24: get() with lock=True uses SELECT FOR SHARE."""
        repo = BaseRepository(TestEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                
                entity = repo.get(1, lock=True)
                
                assert entity is not None
                assert entity.id == 1


class TestRepositoryIpGroupScope:
    """Tests for IP_GROUP scope."""

    def test_apply_data_scope_with_ip_group(self, engine, db_session, mock_context):
        """UT-C01-02-18: _apply_data_scope() with IP_GROUP scope."""
        repo = BaseRepository(ScopedEntity)
        
        with patch('app.db.repository.get_db_session', return_value=db_session):
            with patch('app.db.repository.ctx') as mock_ctx:
                mock_ctx.tenant_id = 1
                mock_ctx.user_id = 100
                mock_context.get_data_scope_types.return_value = ["IP_GROUP"]
                mock_context.dept_ids = []
                mock_ctx.current_or_none = mock_context
                
                now = datetime.now()
                for i in range(3):
                    entity = ScopedEntity(
                        id=i + 1,
                        name=f"Scoped Entity {i}",
                        ip_group_id=1 if i < 2 else 3,  # 2 in group 1, 1 in group 3
                        tenant_id=1,
                        deleted=0,
                        creator=100,
                        create_time=now,
                        update_time=now,
                    )
                    db_session.add(entity)
                db_session.commit()
                
                entities = repo.list(apply_scope=True)
                
                # Should only return entities with ip_group_id in [1, 2]
                assert len(entities) == 2
                assert all(e.ip_group_id in [1, 2] for e in entities)
