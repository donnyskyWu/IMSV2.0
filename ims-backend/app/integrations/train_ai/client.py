# app/integrations/train_ai/client.py - Training AI client (FP-H08-01)
"""
Training AI client for question generation.

Per FP-H08-01 and D-09:
- Uses DashScope OpenAI-compatible API
- Default base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
- Default model: qwen3.8-max
- Configuration from B10 AI Resource Center
"""

from typing import Any, Optional
from dataclasses import dataclass

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
        
        if self.mode == "mock":
            questions = self._mock_questions[:question_count]
            if not questions:
                raise BizError(1108, msg="生成的题目数量为0")
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
            raise BizError(1106, msg=f"培训AI调用失败: {e}")
    
    def set_mock_questions(self, questions: list[GeneratedQuestion]) -> None:
        """Set mock questions for testing."""
        self._mock_questions = questions
