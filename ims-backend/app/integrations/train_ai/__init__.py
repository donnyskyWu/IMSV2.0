# app/integrations/train_ai - Training AI adapter (FW-H08)
"""
Training AI integration for question generation.

Per FP-H08-01:
- Uses DashScope OpenAI-compatible API
- Configuration in B10 AI Resource Center (not system params)
- Error codes: 1106 (call failed), 1107 (timeout), 1108 (zero questions), 1109 (not configured)

Note: Default mock mode, real connection config from B10 in production.
"""

from app.integrations.train_ai.client import TrainAIClient

__all__ = ["TrainAIClient"]
