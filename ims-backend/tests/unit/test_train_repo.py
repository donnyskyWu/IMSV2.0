# tests/unit/test_train_repo.py - Training repository tests (B21)
"""
Unit tests for training repository layer.
Additional tests to improve code coverage.
"""


from app.domains.train.models import TrainMaterialCate


class TestTrainCateRepo:
    """Tests for TrainCateRepo."""

    def test_get_tree_all(self, db_session, test_context):
        """Get all categories for tenant."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainCateRepo

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Test Category",
            sort=1,
        )
        db_session.add(cate)
        db_session.flush()

        repo = TrainCateRepo(db_session)
        result = repo.get_tree(ctx.tenant_id)

        assert len(result) >= 1
        assert result[0].cate_name == "Test Category"

    def test_get_tree_with_position(self, db_session, test_context):
        """Get categories filtered by position."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainCateRepo

        cate1 = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Position Category",
            position_code="POS001",
            sort=1,
        )
        cate2 = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Global Category",
            position_code=None,
            sort=2,
        )
        db_session.add_all([cate1, cate2])
        db_session.flush()

        repo = TrainCateRepo(db_session)
        result = repo.get_tree(ctx.tenant_id, position_code="POS001")

        assert len(result) >= 2

    def test_get_by_id_exists(self, db_session, test_context):
        """Get category by ID that exists."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainCateRepo

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Lookup Test",
        )
        db_session.add(cate)
        db_session.flush()

        repo = TrainCateRepo(db_session)
        result = repo.get_by_id(cate.id, ctx.tenant_id)

        assert result is not None
        assert result.cate_name == "Lookup Test"

    def test_get_by_id_not_found(self, db_session, test_context):
        """Get category by ID returns None when not found."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainCateRepo

        repo = TrainCateRepo(db_session)
        result = repo.get_by_id(99999, ctx.tenant_id)

        assert result is None

    def test_create_category(self, db_session, test_context):
        """Create a new category."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainCateRepo

        repo = TrainCateRepo(db_session)
        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="New Category",
        )
        result = repo.create(cate)

        assert result.id is not None
        assert result.cate_name == "New Category"

    def test_has_children_true(self, db_session, test_context):
        """Check category has children returns true."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainCateRepo

        parent = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Parent",
        )
        db_session.add(parent)
        db_session.flush()

        child = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=parent.id,
            cate_name="Child",
        )
        db_session.add(child)
        db_session.flush()

        repo = TrainCateRepo(db_session)
        result = repo.has_children(parent.id, ctx.tenant_id)

        assert result is True

    def test_has_children_false(self, db_session, test_context):
        """Check category has children returns false."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainCateRepo

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Leaf Category",
        )
        db_session.add(cate)
        db_session.flush()

        repo = TrainCateRepo(db_session)
        result = repo.has_children(cate.id, ctx.tenant_id)

        assert result is False


class TestTrainMaterialRepo:
    """Tests for TrainMaterialRepo."""

    def test_generate_material_no(self, db_session, test_context):
        """Generate material number follows pattern."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainMaterialRepo

        repo = TrainMaterialRepo(db_session)
        no = repo.generate_material_no(ctx.tenant_id)

        assert no.startswith("MT")
        assert len(no) == 14  # MT + 8 digits + 4 seq

    def test_get_by_id_not_found(self, db_session, test_context):
        """Get material by ID returns None when not found."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainMaterialRepo

        repo = TrainMaterialRepo(db_session)
        result = repo.get_by_id(99999, ctx.tenant_id)

        assert result is None


class TestTrainTaskRepo:
    """Tests for TrainTaskRepo."""

    def test_generate_task_no(self, db_session, test_context):
        """Generate task number follows pattern."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainTaskRepo

        repo = TrainTaskRepo(db_session)
        no = repo.generate_task_no(ctx.tenant_id)

        assert no.startswith("TT")
        assert len(no) == 14  # TT + 8 digits + 4 seq

    def test_get_by_id_not_found(self, db_session, test_context):
        """Get task by ID returns None when not found."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainTaskRepo

        repo = TrainTaskRepo(db_session)
        result = repo.get_by_id(99999, ctx.tenant_id)

        assert result is None


class TestTrainRecordRepo:
    """Tests for TrainRecordRepo."""

    def test_get_by_user_task_not_found(self, db_session, test_context):
        """Get record by task and user returns None when not found."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainRecordRepo

        repo = TrainRecordRepo(db_session)
        result = repo.get_by_user_task(99999, ctx.user_id, ctx.tenant_id)

        assert result is None

    def test_get_by_task_empty(self, db_session, test_context):
        """Get records by task returns empty list when none exist."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainRecordRepo

        repo = TrainRecordRepo(db_session)
        result = repo.get_by_task(99999, ctx.tenant_id)

        assert result == []

    def test_is_user_assigned_false(self, db_session, test_context):
        """Is user assigned returns false when not assigned."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainRecordRepo

        repo = TrainRecordRepo(db_session)
        result = repo.is_user_assigned(99999, ctx.user_id, ctx.tenant_id)

        assert result is False

    def test_get_assigned_dept_ids_empty(self, db_session, test_context):
        """Get assigned dept IDs returns empty when no records."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainRecordRepo

        repo = TrainRecordRepo(db_session)
        result = repo.get_assigned_dept_ids(99999, ctx.tenant_id)

        assert result == []

    def test_count_by_task_zero(self, db_session, test_context):
        """Count by task returns zeros when no records."""
        from app.core.context import ctx
        from app.domains.train.repo import TrainRecordRepo

        repo = TrainRecordRepo(db_session)
        result = repo.count_by_task(99999, ctx.tenant_id)

        assert result["total"] == 0
        assert result["confirmed"] == 0
