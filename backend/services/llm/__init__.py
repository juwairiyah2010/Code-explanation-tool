from backend.config import get_settings
from backend.services.llm.base import BaseLLMService, LLMExplanationResult
from backend.services.llm.mock_llm import MockLLMService
from backend.services.llm.prompts import build_explanation_prompt, SYSTEM_PROMPT


def get_llm_service() -> BaseLLMService:
    """Factory returning configured LLM service instance."""
    settings = get_settings()
    # In future or when keys are provided, we can branch to OpenAILLMService or GeminiLLMService
    return MockLLMService()


__all__ = [
    "BaseLLMService",
    "LLMExplanationResult",
    "MockLLMService",
    "get_llm_service",
    "build_explanation_prompt",
    "SYSTEM_PROMPT",
]
