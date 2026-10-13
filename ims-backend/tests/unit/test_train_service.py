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

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from app.core.errors import BizError
from app.domains.train.schemas import QuizQuestion, TaskCreateRequest


class TestTrainMaterialServiceCreateMaterial:
    """Tests for material creation."""

    @pytest.mark.asyncio
    async def test_link_material_valid_url(self, db_session, test_context):
        """LINK material with valid URL passes."""
        from app.domains.train.service import TrainMaterialService
        from app.domains.train.models import TrainMaterialCate
        from app.core.context import ctx

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
        from app.domains.train.service import TrainMaterialService
        from app.domains.train.models import TrainMaterialCate
        from app.core.context import ctx

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
        from app.domains.train.service import TrainMaterialService
        from app.domains.train.models import TrainMaterialCate
        from app.core.context import ctx

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

    def test_validate_quiz_empty(self):
        """Empty quiz fails validation."""
        from app.domains.train.service import TrainTaskService

        service = TrainTaskService()

        with pytest.raises(BizError) as exc:
            service._validate_quiz([])
        assert exc.value.code == 1001
        assert "不能为空" in exc.value.msg

    def test_validate_quiz_single_missing_options(self):
        """SINGLE type without options fails."""
        from app.domains.train.service import TrainTaskService

        service = TrainTaskService()
        quiz = [QuizQuestion(type="SINGLE", question="Q1", options=[])]

        with pytest.raises(BizError) as exc:
            service._validate_quiz(quiz)
        assert exc.value.code == 1001
        assert "选项" in exc.value.msg

    def test_validate_quiz_single_invalid_answer(self):
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

    def test_validate_quiz_true_false_missing_answer(self):
        """TRUE_FALSE type without answer fails."""
        from app.domains.train.service import TrainTaskService

        service = TrainTaskService()
        quiz = [QuizQuestion(type="TRUE_FALSE", question="Q1")]

        with pytest.raises(BizError) as exc:
            service._validate_quiz(quiz)
        assert exc.value.code == 1001
        assert "答案不能为空" in exc.value.msg

    def test_validate_quiz_valid(self):
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

    def test_grade_empty_quiz(self):
        """Empty quiz returns 0."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        assert service._grade_quiz([], []) == 0

    def test_grade_all_correct(self):
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

    def test_grade_partial_correct(self):
        """Partial correct answers return proportional score."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        quiz = [
            {"type": "SINGLE", "answer_index": 0},
            {"type": "SINGLE", "answer_index": 1},
        ]
        answers = [0, 0]

        assert service._grade_quiz(quiz, answers) == 50

    def test_grade_all_wrong(self):
        """All wrong answers return 0."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        quiz = [
            {"type": "SINGLE", "answer_index": 0},
            {"type": "SINGLE", "answer_index": 1},
        ]
        answers = [1, 0]

        assert service._grade_quiz(quiz, answers) == 0

    def test_grade_missing_answers(self):
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

    def test_calculate_empty_materials(self):
        """Empty materials return 0."""
        from app.domains.train.service import TrainStudyService
        from unittest.mock import MagicMock

        service = TrainStudyService()
        task = MagicMock()
        task.material_ids = "[]"

        assert service._calculate_overall_progress(task, {}) == 0

    def test_calculate_all_complete(self):
        """All complete materials return 100."""
        from app.domains.train.service import TrainStudyService
        from unittest.mock import MagicMock

        service = TrainStudyService()
        task = MagicMock()
        task.material_ids = "[1, 2, 3]"

        progress = {"1": 100, "2": 100, "3": 100}
        assert service._calculate_overall_progress(task, progress) == 100

    def test_calculate_partial_progress(self):
        """Partial progress calculated correctly."""
        from app.domains.train.service import TrainStudyService
        from unittest.mock import MagicMock

        service = TrainStudyService()
        task = MagicMock()
        task.material_ids = "[1, 2]"

        progress = {"1": 100, "2": 50}
        assert service._calculate_overall_progress(task, progress) == 75

    def test_calculate_missing_progress(self):
        """Missing material progress counts as 0."""
        from app.domains.train.service import TrainStudyService
        from unittest.mock import MagicMock

        service = TrainStudyService()
        task = MagicMock()
        task.material_ids = "[1, 2]"

        progress = {"1": 100}
        assert service._calculate_overall_progress(task, progress) == 50
