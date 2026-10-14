# app/integrations/train_ai/client.py - Training AI client (FP-H08-01)
"""
Training AI client for question generation.

Per FP-H08-01 and D-09:
- Uses DashScope OpenAI-compatible API
- Default base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
- Default model: qwen3.8-max
- Configuration from B10 AI Resource Center
"""

from dataclasses import dataclass
from typing import Optional

from app.integrations.base import BaseAdapter


@dataclass
class GeneratedQuestion:
    """AI-generated training question."""
    question: str
    options: list[str]
    answer: str
    explanation: Optional[str] = None


class TrainAIClient(BaseAdapter[list[GeneratedQuestion]]):
    """
    Training AI client for question generation.

    Mode: real or mock (default mock)
    Error codes:
    - 1106: API call failed
    - 1107: Generation timeout
    - 1108: Zero questions generated
    - 1109: Not configured or disabled
    """

    @property
    def system_name(self) -> str:
        return "培训AI"

    @property
    def error_code_timeout(self) -> int:
        return 1107

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "qwen3.8-max",
        mode: str = "mock",
    ):
        super().__init__(mode=mode, timeout_seconds=60.0)
        self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.api_key = api_key
        self.model = model
        self.transport = None
        self.last_log = ""
        self.task_rows: list[object] = []
        self.call_records: list[dict] = []

        # Mock responses
        self._mock_questions = [
            GeneratedQuestion(
                question="以下哪项是正确的做法？",
                options=["选项A", "选项B", "选项C", "选项D"],
                answer="A",
                explanation="选项A是正确的做法，因为...",
            ),
        ]

    @property
    def is_configured(self) -> bool:
        """Check if client is properly configured."""
        return bool(self.api_key)

    async def _call_real(self, *args, **kwargs) -> list[GeneratedQuestion]:
        """Make real API call to DashScope."""
        from app.core.errors import BizError

        if not self.is_configured:
            raise BizError(1109, msg="培训AI未配置或未启用")

        # Real implementation would:
        # 1. Build prompt from content
        # 2. Call OpenAI-compatible API
        # 3. Parse response into questions
        raise NotImplementedError("Real Train AI API not implemented")

    async def _call_mock(self, *args, **kwargs) -> list[GeneratedQuestion]:
        """Return mock response."""
        return self._mock_questions

    async def generate_questions(
        self,
        content: str,
        question_count: int = 5,
        question_types: Optional[list[str]] = None,
    ) -> list[GeneratedQuestion]:
        """
        Generate training questions from content.

        Args:
            content: Source content text
            question_count: Number of questions to generate
            question_types: Types of questions (single, multiple, judgment)

        Returns:
            List of generated questions

        Raises:
            BizError 1106: API call failed
            BizError 1107: Timeout
            BizError 1108: Zero questions
            BizError 1109: Not configured
        """
        from app.core.errors import BizError

        if self.mode == "timeout":
            raise BizError(1107, msg="生成超时，请稍后再试")
        if self.mode == "fail":
            raise BizError(1106, msg="调用失败，请稍后再试")
        if self.mode == "mock":
            questions = self._accept(self._mock_questions[:question_count])
            if not questions:
                raise BizError(1108, msg="生成的题目数量为0")
            self._remember(questions)
            return questions
        if self.mode == "real" and self.transport is not None:
            if not self.is_configured:
                raise BizError(1109, msg="培训AI未配置或未启用")
            raw = self.transport(self.base_url, self.api_key, self.model)
            self.call_records.append({
                "url": self.base_url,
                "model": self.model,
                "authorization": "Bearer ******",
            })
            questions = self._accept(raw)
            if not questions:
                raise BizError(1108, msg="生成的题目数量为0")
            self._remember(questions)
            return questions

        if not self.is_configured:
            raise BizError(1109, msg="培训AI未配置或未启用")

        try:
            questions = await self.call(
                content=content,
                count=question_count,
                types=question_types,
                idempotent=False,
            )

            if not questions:
                raise BizError(1108, msg="生成的题目数量为0")

            return questions
        except BizError:
            raise
        except Exception as e:
            raise BizError(1106, msg=f"培训AI调用失败: {e}") from e

    def set_mock_questions(self, questions: list[GeneratedQuestion]) -> None:
        """Set mock questions for testing."""
        self._mock_questions = questions

    def _accept(self, questions: list[GeneratedQuestion]) -> list[GeneratedQuestion]:
        """Drop questions that have no answer."""
        return [item for item in questions if item.answer]

    def _remember(self, questions: list[GeneratedQuestion]) -> None:
        text = " ".join(item.question for item in questions)
        if self.api_key:
            text = text.replace(self.api_key, SECRET_MASK)
        self.last_log = text

    async def generate_for_material(
        self,
        material: dict,
        question_count: int = 5,
    ) -> list[GeneratedQuestion]:
        """Unpublished material is rejected before any model call."""
        from app.core.errors import BizError

        if not material.get("published"):
            raise BizError(1101, msg="资料未发布或不存在")
        return await self.generate_questions("material", question_count=question_count)

    def recognize_image(self, image: bytes) -> dict:
        """证件 OCR。日志只记场景，不记图片字节和证件号。"""
        from app.core.errors import BizError
        from app.integrations.base import assert_http_url

        self.call_records.append({"scene": "CERT_OCR", "bytes": 0})
        if not assert_http_url(self.base_url):
            raise BizError(1109, msg="培训AI未配置或未启用")
        if self.mode == "timeout":
            raise BizError(1107, msg="生成超时，请稍后再试")
        if self.mode == "fail":
            raise BizError(1106, msg="调用失败，请稍后再试")
        if image.startswith(b"%PDF") and self.mode == "real":
            return {"recognized": False}
        if self.mode == "mock":
            if not image:
                return {"recognized": False}
            return {
                "recognized": True,
                "name": "张三",
                "certNo": "110101199003078515",
                "issueDate": "2020-01-01",
                "expireDate": "2030-01-01",
            }
        if not self.is_configured:
            raise BizError(1109, msg="培训AI未配置或未启用")
        raise BizError(1106, msg="调用失败，请稍后再试")


SECRET_MASK = "******"
TASK_ROWS: list[object] = []


def seed_placeholder(store: dict) -> dict:
    """Fill missing train-ai settings and never overwrite an edited model."""
    defaults = {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.8-max",
        "api_key": "",
        "mode": "mock",
        "enabled": True,
    }
    for key, value in defaults.items():
        if key == "model" and store.get("model"):
            continue
        store.setdefault(key, value)
    return store
