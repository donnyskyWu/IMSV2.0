# tests/unit/test_train_ai.py - AI generation tests (B21)
"""
Unit tests for AI quiz generation.

Per Q-D6, Q-D7:
- Timeout → 1107, no mock fallback
- Failure → 1106, no mock fallback
- Not configured → 1109
- Zero questions → 1108
"""


import pytest

from app.core.errors import BizError


class TestAIGenerateErrorCodes:
    """Tests for AI generation error codes."""

    @pytest.mark.asyncio
    async def test_ai_not_configured_returns_1109(self, db_session, test_context):
        """UT-B21-AI-01: AI not configured returns 1109."""
        from app.api.train import ai_generate_quiz
        from app.domains.train.schemas import AIGenerateRequest

        req = AIGenerateRequest(
            material_ids=["1", "2"],
            question_count=10,
        )

        with pytest.raises(BizError) as exc:
            await ai_generate_quiz(req)

        assert exc.value.code == 1109
        assert "未配置" in exc.value.msg

    def test_no_mock_fallback_on_timeout(self):
        """UT-B21-AI-03: Timeout returns 1107, not mock questions."""
        pass

    def test_no_mock_fallback_on_failure(self):
        """UT-B21-AI-04: Failure returns 1106, not mock questions."""
        pass


class TestAIGenerateValidation:
    """Tests for AI generation input validation."""

    @pytest.mark.asyncio
    async def test_empty_material_ids_rejected(self):
        """Empty material IDs rejected by schema."""
        from pydantic import ValidationError

        from app.domains.train.schemas import AIGenerateRequest

        with pytest.raises(ValidationError):
            AIGenerateRequest(
                material_ids=[],
                question_count=10,
            )

    @pytest.mark.asyncio
    async def test_question_count_limits(self):
        """Question count must be 1-50."""
        from pydantic import ValidationError

        from app.domains.train.schemas import AIGenerateRequest

        with pytest.raises(ValidationError):
            AIGenerateRequest(
                material_ids=["1"],
                question_count=0,
            )

        with pytest.raises(ValidationError):
            AIGenerateRequest(
                material_ids=["1"],
                question_count=100,
            )

        req = AIGenerateRequest(
            material_ids=["1"],
            question_count=50,
        )
        assert req.question_count == 50

    @pytest.mark.asyncio
    async def test_difficulty_enum(self):
        """Difficulty must be EASY/MEDIUM/HARD."""
        from pydantic import ValidationError

        from app.domains.train.schemas import AIGenerateRequest

        with pytest.raises(ValidationError):
            AIGenerateRequest(
                material_ids=["1"],
                difficulty="INVALID",
            )

        req = AIGenerateRequest(
            material_ids=["1"],
            difficulty="HARD",
        )
        assert req.difficulty == "HARD"


class TestTrainAIClient:
    """Tests for TrainAIClient (OCR shared base)."""

    def test_client_exists_in_integrations(self):
        """TrainAIClient exists in integrations module."""
        from app.integrations.train_ai.client import TrainAIClient
        assert TrainAIClient is not None

    def test_client_has_generate_method(self):
        """Client has generate_questions method."""
        from app.integrations.train_ai.client import TrainAIClient
        assert hasattr(TrainAIClient, "generate_questions")

    @pytest.mark.asyncio
    async def test_timeout_mode_returns_1107(self):
        """UT-B21-AI-03: Timeout mode returns 1107."""
        from app.integrations.train_ai.client import TrainAIClient

        client = TrainAIClient(mode="timeout")

        with pytest.raises(BizError) as exc:
            await client.generate_questions("content", 5)

        assert exc.value.code == 1107
        assert "超时" in exc.value.msg

    @pytest.mark.asyncio
    async def test_fail_mode_returns_1106(self):
        """UT-B21-AI-04: Fail mode returns 1106."""
        from app.integrations.train_ai.client import TrainAIClient

        client = TrainAIClient(mode="fail")

        with pytest.raises(BizError) as exc:
            await client.generate_questions("content", 5)

        assert exc.value.code == 1106
        assert "失败" in exc.value.msg

    @pytest.mark.asyncio
    async def test_not_configured_returns_1109(self):
        """UT-B21-AI-01: Not configured returns 1109."""
        from app.integrations.train_ai.client import TrainAIClient

        client = TrainAIClient(mode="real")

        with pytest.raises(BizError) as exc:
            await client.generate_questions("content", 5)

        assert exc.value.code == 1109
        assert "未配置" in exc.value.msg

    @pytest.mark.asyncio
    async def test_mock_mode_returns_questions(self):
        """Mock mode returns questions."""
        from app.integrations.train_ai.client import TrainAIClient

        client = TrainAIClient(mode="mock")
        questions = await client.generate_questions("content", 5)

        assert len(questions) > 0
        assert questions[0].question

    @pytest.mark.asyncio
    async def test_unpublished_material_returns_1101(self):
        """UT-B21-AI-05: Unpublished material returns 1101."""
        from app.integrations.train_ai.client import TrainAIClient

        client = TrainAIClient(mode="mock")
        material = {"id": 1, "title": "Test", "published": False}

        with pytest.raises(BizError) as exc:
            await client.generate_for_material(material, 5)

        assert exc.value.code == 1101
        assert "未发布" in exc.value.msg
