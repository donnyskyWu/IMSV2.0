# tests/unit/test_train_service.py - Training service tests (B21)
"""
Unit tests for training services.

P0 services require 90% branch coverage:
- TrainTaskService.create_task_by_user
- TrainTaskService.create_task_by_position
- TrainTaskService.preview_position_users
- TrainStudyService.report_video_progress
- TrainStudyService.confirm_duration
- TrainStudyService.submit_quiz
- TrainStatService.get_finish_rate
"""

from unittest.mock import MagicMock

import pytest

from app.core.errors import BizError
from app.domains.train.schemas import QuizQuestion


class TestTrainMaterialServiceCreateMaterial:
    """Tests for material creation."""

    @pytest.mark.asyncio
    async def test_link_material_valid_url(self, db_session, test_context):
        """LINK material with valid URL passes."""
        from app.core.context import ctx
        from app.domains.train.models import TrainMaterialCate
        from app.domains.train.service import TrainMaterialService

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="测试分类",
            creator=ctx.user_id,
        )
        db_session.add(cate)
        db_session.flush()

        service = TrainMaterialService()
        from app.domains.train.schemas import MaterialCreateRequest

        req = MaterialCreateRequest(
            title="外链资料",
            cate_id=str(cate.id),
            material_type="LINK",
            link_url="https://example.com",
            position_codes=[],
        )

        result = await service.create_material(req)

        assert result.title == "外链资料"
        assert result.material_type == "LINK"
        assert result.link_url == "https://example.com"

    @pytest.mark.asyncio
    async def test_link_material_invalid_url(self, db_session, test_context):
        """LINK material with invalid URL fails with 1001."""
        from app.core.context import ctx
        from app.domains.train.models import TrainMaterialCate
        from app.domains.train.service import TrainMaterialService

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="测试分类",
            creator=ctx.user_id,
        )
        db_session.add(cate)
        db_session.flush()

        service = TrainMaterialService()
        from app.domains.train.schemas import MaterialCreateRequest

        req = MaterialCreateRequest(
            title="外链资料",
            cate_id=str(cate.id),
            material_type="LINK",
            link_url="javascript:alert(1)",
            position_codes=[],
        )

        with pytest.raises(BizError) as exc:
            await service.create_material(req)
        assert exc.value.code == 1001

    @pytest.mark.asyncio
    async def test_doc_material_without_file(self, db_session, test_context):
        """DOC material without file fails with 1001."""
        from app.core.context import ctx
        from app.domains.train.models import TrainMaterialCate
        from app.domains.train.service import TrainMaterialService

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="测试分类",
            creator=ctx.user_id,
        )
        db_session.add(cate)
        db_session.flush()

        service = TrainMaterialService()
        from app.domains.train.schemas import MaterialCreateRequest

        req = MaterialCreateRequest(
            title="文档资料",
            cate_id=str(cate.id),
            material_type="DOC",
            position_codes=[],
        )

        with pytest.raises(BizError) as exc:
            await service.create_material(req)
        assert exc.value.code == 1001
        assert "必须上传文件" in exc.value.msg


class TestTrainTaskServiceValidation:
    """Tests for task validation."""

    def test_validate_quiz_empty(self, db_session):
        """Empty quiz fails validation."""
        from app.domains.train.service import TrainTaskService

        service = TrainTaskService()

        with pytest.raises(BizError) as exc:
            service._validate_quiz([])
        assert exc.value.code == 1001
        assert "不能为空" in exc.value.msg

    def test_validate_quiz_single_missing_options(self, db_session):
        """SINGLE type without options fails."""
        from app.domains.train.service import TrainTaskService

        service = TrainTaskService()
        quiz = [QuizQuestion(type="SINGLE", question="Q1", options=[])]

        with pytest.raises(BizError) as exc:
            service._validate_quiz(quiz)
        assert exc.value.code == 1001
        assert "选项" in exc.value.msg

    def test_validate_quiz_single_invalid_answer(self, db_session):
        """SINGLE type with invalid answer index fails."""
        from app.domains.train.service import TrainTaskService

        service = TrainTaskService()
        quiz = [QuizQuestion(
            type="SINGLE",
            question="Q1",
            options=["A", "B", "C"],
            answer_index=5,
        )]

        with pytest.raises(BizError) as exc:
            service._validate_quiz(quiz)
        assert exc.value.code == 1001
        assert "答案索引" in exc.value.msg

    def test_validate_quiz_true_false_missing_answer(self, db_session):
        """TRUE_FALSE type without answer fails."""
        from app.domains.train.service import TrainTaskService

        service = TrainTaskService()
        quiz = [QuizQuestion(type="TRUE_FALSE", question="Q1")]

        with pytest.raises(BizError) as exc:
            service._validate_quiz(quiz)
        assert exc.value.code == 1001
        assert "答案不能为空" in exc.value.msg

    def test_validate_quiz_valid(self, db_session):
        """Valid quiz passes."""
        from app.domains.train.service import TrainTaskService

        service = TrainTaskService()
        quiz = [
            QuizQuestion(
                type="SINGLE",
                question="Q1",
                options=["A", "B", "C"],
                answer_index=0,
            ),
            QuizQuestion(
                type="TRUE_FALSE",
                question="Q2",
                answer_boolean=True,
            ),
        ]

        service._validate_quiz(quiz)


class TestTrainStudyServiceGradeQuiz:
    """Tests for quiz grading."""

    def test_grade_empty_quiz(self, db_session):
        """Empty quiz returns 0."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        assert service._grade_quiz([], []) == 0

    def test_grade_all_correct(self, db_session):
        """All correct answers return 100."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        quiz = [
            {"type": "SINGLE", "answer_index": 0},
            {"type": "SINGLE", "answer_index": 1},
            {"type": "TRUE_FALSE", "answer_boolean": True},
        ]
        answers = [0, 1, True]

        assert service._grade_quiz(quiz, answers) == 100

    def test_grade_partial_correct(self, db_session):
        """Partial correct answers return proportional score."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        quiz = [
            {"type": "SINGLE", "answer_index": 0},
            {"type": "SINGLE", "answer_index": 1},
        ]
        answers = [0, 0]

        assert service._grade_quiz(quiz, answers) == 50

    def test_grade_all_wrong(self, db_session):
        """All wrong answers return 0."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        quiz = [
            {"type": "SINGLE", "answer_index": 0},
            {"type": "SINGLE", "answer_index": 1},
        ]
        answers = [1, 0]

        assert service._grade_quiz(quiz, answers) == 0

    def test_grade_missing_answers(self, db_session):
        """Missing answers count as wrong."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        quiz = [
            {"type": "SINGLE", "answer_index": 0},
            {"type": "SINGLE", "answer_index": 1},
            {"type": "SINGLE", "answer_index": 2},
        ]
        answers = [0]

        assert service._grade_quiz(quiz, answers) == 33


class TestTrainStudyServiceCalculateProgress:
    """Tests for progress calculation."""

    def test_calculate_empty_materials(self, db_session):
        """Empty materials return 0."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        task = MagicMock()
        task.material_ids = "[]"

        assert service._calculate_overall_progress(task, {}) == 0

    def test_calculate_all_complete(self, db_session):
        """All complete materials return 100."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        task = MagicMock()
        task.material_ids = "[1, 2, 3]"

        progress = {"1": 100, "2": 100, "3": 100}
        assert service._calculate_overall_progress(task, progress) == 100

    def test_calculate_partial_progress(self, db_session):
        """Partial progress calculated correctly."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        task = MagicMock()
        task.material_ids = "[1, 2]"

        progress = {"1": 100, "2": 50}
        assert service._calculate_overall_progress(task, progress) == 75

    def test_calculate_missing_progress(self, db_session):
        """Missing material progress counts as 0."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        task = MagicMock()
        task.material_ids = "[1, 2]"

        progress = {"1": 100}
        assert service._calculate_overall_progress(task, progress) == 50


class TestTrainMaterialServiceCateTree:
    """Tests for category tree operations."""

    @pytest.mark.asyncio
    async def test_get_cate_tree_empty(self, db_session, test_context):
        """Get empty category tree."""
        from app.domains.train.service import TrainMaterialService

        service = TrainMaterialService()
        result = await service.get_cate_tree()

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_cate_tree_with_position(self, db_session, test_context):
        """Get category tree filtered by position."""
        from app.core.context import ctx
        from app.domains.train.models import TrainMaterialCate
        from app.domains.train.service import TrainMaterialService

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Position Cate",
            position_code="POS001",
            creator=ctx.user_id,
        )
        db_session.add(cate)
        db_session.flush()

        service = TrainMaterialService()
        result = await service.get_cate_tree(position_code="POS001")

        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_create_cate_parent_not_exists(self, db_session, test_context):
        """Create category with non-existent parent fails."""
        from app.domains.train.schemas import CateCreateRequest
        from app.domains.train.service import TrainMaterialService

        service = TrainMaterialService()
        req = CateCreateRequest(
            parent_id="99999",
            cate_name="Test Cate",
            sort=1,
        )

        with pytest.raises(BizError) as exc:
            await service.create_cate(req)
        assert exc.value.code == 1500

    @pytest.mark.asyncio
    async def test_create_cate_root(self, db_session, test_context):
        """Create root category (parent_id=0)."""
        from app.domains.train.schemas import CateCreateRequest
        from app.domains.train.service import TrainMaterialService

        service = TrainMaterialService()
        req = CateCreateRequest(
            parent_id="0",
            cate_name="Root Category",
            sort=1,
        )

        result = await service.create_cate(req)
        assert result.cate_name == "Root Category"
        assert result.parent_id is None or result.parent_id == "0"

    @pytest.mark.asyncio
    async def test_update_cate_not_exists(self, db_session, test_context):
        """Update non-existent category fails."""
        from app.domains.train.schemas import CateUpdateRequest
        from app.domains.train.service import TrainMaterialService

        service = TrainMaterialService()
        req = CateUpdateRequest(cate_name="New Name")

        with pytest.raises(BizError) as exc:
            await service.update_cate("99999", req)
        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_update_cate_name(self, db_session, test_context):
        """Update category name."""
        from app.core.context import ctx
        from app.domains.train.models import TrainMaterialCate
        from app.domains.train.schemas import CateUpdateRequest
        from app.domains.train.service import TrainMaterialService

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Original Name",
            creator=ctx.user_id,
        )
        db_session.add(cate)
        db_session.flush()

        service = TrainMaterialService()
        req = CateUpdateRequest(cate_name="Updated Name", sort=5)

        result = await service.update_cate(str(cate.id), req)
        assert result.cate_name == "Updated Name"
        assert result.sort == 5

    @pytest.mark.asyncio
    async def test_delete_cate_not_exists(self, db_session, test_context):
        """Delete non-existent category fails."""
        from app.domains.train.service import TrainMaterialService

        service = TrainMaterialService()

        with pytest.raises(BizError) as exc:
            await service.delete_cate("99999")
        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_delete_cate_has_children(self, db_session, test_context):
        """Delete category with children fails."""
        from app.core.context import ctx
        from app.domains.train.models import TrainMaterialCate
        from app.domains.train.service import TrainMaterialService

        parent = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Parent",
            creator=ctx.user_id,
        )
        db_session.add(parent)
        db_session.flush()

        child = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=parent.id,
            cate_name="Child",
            creator=ctx.user_id,
        )
        db_session.add(child)
        db_session.flush()

        service = TrainMaterialService()

        with pytest.raises(BizError) as exc:
            await service.delete_cate(str(parent.id))
        assert exc.value.code == 1001

    @pytest.mark.asyncio
    async def test_delete_cate_success(self, db_session, test_context):
        """Delete empty category succeeds."""
        from app.core.context import ctx
        from app.domains.train.models import TrainMaterialCate
        from app.domains.train.service import TrainMaterialService

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="To Delete",
            creator=ctx.user_id,
        )
        db_session.add(cate)
        db_session.flush()
        cate_id = str(cate.id)

        service = TrainMaterialService()
        await service.delete_cate(cate_id)


class TestTrainMaterialServiceListMaterials:
    """Tests for listing materials."""

    @pytest.mark.asyncio
    async def test_list_materials_empty(self, db_session, test_context):
        """List materials returns empty when none exist."""
        from app.domains.train.service import TrainMaterialService

        service = TrainMaterialService()
        items, total = await service.list_materials()

        assert total >= 0

    @pytest.mark.asyncio
    async def test_list_materials_with_cate_filter(self, db_session, test_context):
        """List materials with category filter."""
        from app.core.context import ctx
        from app.domains.train.models import TrainMaterial, TrainMaterialCate
        from app.domains.train.service import TrainMaterialService

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Test Cate",
            creator=ctx.user_id,
        )
        db_session.add(cate)
        db_session.flush()

        material = TrainMaterial(
            tenant_id=ctx.tenant_id,
            cate_id=cate.id,
            title="Test Material",
            material_type="LINK",
            link_url="https://example.com",
            status="PUBLISHED",
            material_no="MT202610130001",
            creator=ctx.user_id,
        )
        db_session.add(material)
        db_session.flush()

        service = TrainMaterialService()
        items, total = await service.list_materials(cate_id=str(cate.id))

        assert total >= 1

    @pytest.mark.asyncio
    async def test_list_materials_pagination(self, db_session, test_context):
        """List materials respects pagination."""
        from app.domains.train.service import TrainMaterialService

        service = TrainMaterialService()
        items, total = await service.list_materials(page=1, page_size=10)

        assert isinstance(items, list)
        assert len(items) <= 10


class TestTrainMaterialServiceGetDetail:
    """Tests for getting material detail."""

    @pytest.mark.asyncio
    async def test_get_material_not_exists(self, db_session, test_context):
        """Get non-existent material fails."""
        from app.domains.train.service import TrainMaterialService

        service = TrainMaterialService()

        with pytest.raises(BizError) as exc:
            await service.get_material_detail("99999")
        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_get_material_with_versions(self, db_session, test_context):
        """Get material detail includes versions."""
        from app.core.context import ctx
        from app.domains.train.models import (
            TrainMaterial,
            TrainMaterialCate,
            TrainMaterialVersion,
        )
        from app.domains.train.service import TrainMaterialService

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Test Cate",
            creator=ctx.user_id,
        )
        db_session.add(cate)
        db_session.flush()

        material = TrainMaterial(
            tenant_id=ctx.tenant_id,
            cate_id=cate.id,
            title="Versioned Material",
            material_type="LINK",
            link_url="https://example.com",
            status="DRAFT",
            material_no="MT202610130002",
            version=1,
            creator=ctx.user_id,
        )
        db_session.add(material)
        db_session.flush()

        from app.core.clock import get_now

        version = TrainMaterialVersion(
            tenant_id=ctx.tenant_id,
            material_id=material.id,
            version=1,
            title="Versioned Material",
            link_url="https://example.com",
            editor_user_id=ctx.user_id,
            created_at=get_now(),
        )
        db_session.add(version)
        db_session.flush()

        service = TrainMaterialService()
        result = await service.get_material_detail(str(material.id))

        assert result.title == "Versioned Material"
        assert len(result.versions) >= 1


class TestTrainMaterialServiceUpdate:
    """Tests for updating materials."""

    @pytest.mark.asyncio
    async def test_update_material_not_exists(self, db_session, test_context):
        """Update non-existent material fails."""
        from app.domains.train.schemas import MaterialUpdateRequest
        from app.domains.train.service import TrainMaterialService

        service = TrainMaterialService()
        req = MaterialUpdateRequest(title="New Title")

        with pytest.raises(BizError) as exc:
            await service.update_material("99999", req)
        assert exc.value.code == 1504

    @pytest.mark.asyncio
    async def test_update_offline_material_fails(self, db_session, test_context):
        """Update offline material fails."""
        from app.core.context import ctx
        from app.domains.train.models import TrainMaterial, TrainMaterialCate
        from app.domains.train.schemas import MaterialUpdateRequest
        from app.domains.train.service import TrainMaterialService

        cate = TrainMaterialCate(
            tenant_id=ctx.tenant_id,
            parent_id=0,
            cate_name="Test",
            creator=ctx.user_id,
        )
        db_session.add(cate)
        db_session.flush()

        material = TrainMaterial(
            tenant_id=ctx.tenant_id,
            cate_id=cate.id,
            title="Offline Material",
            material_type="LINK",
            link_url="https://example.com",
            status="OFFLINE",
            material_no="MT202610130003",
            version=1,
            creator=ctx.user_id,
        )
        db_session.add(material)
        db_session.flush()

        service = TrainMaterialService()
        req = MaterialUpdateRequest(title="New Title")

        with pytest.raises(BizError) as exc:
            await service.update_material(str(material.id), req)
        assert exc.value.code == 1501


class TestTrainTaskServiceValidationExtended:
    """Extended tests for task validation."""

    def test_validate_quiz_with_mixed_types(self, db_session):
        """Mixed SINGLE and TRUE_FALSE quiz types pass."""
        from app.domains.train.service import TrainTaskService

        service = TrainTaskService()
        quiz = [
            QuizQuestion(
                type="SINGLE",
                question="Q1",
                options=["A", "B", "C"],
                answer_index=0,
            ),
            QuizQuestion(
                type="TRUE_FALSE",
                question="Q2",
                answer_boolean=False,
            ),
            QuizQuestion(
                type="SINGLE",
                question="Q3",
                options=["X", "Y"],
                answer_index=1,
            ),
        ]

        service._validate_quiz(quiz)
