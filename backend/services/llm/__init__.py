from backend.config import get_settings
from backend.services.llm.base import BaseLLMService, LLMExplanationResult
from backend.services.llm.mock_llm import MockLLMService
from backend.services.llm.openai_llm import OpenAILLMService
from backend.services.llm.gemini_llm import GeminiLLMService
from backend.services.llm.prompts import build_explanation_prompt, SYSTEM_PROMPT


def get_llm_service(provider: str | None = None) -> BaseLLMService:
    """Factory returning configured LLM service instance behind the unified provider interface."""
    settings = get_settings()
    selected_provider = (provider or settings.LLM_PROVIDER or "mock").lower()

    if selected_provider == "openai":
        return OpenAILLMService()
    elif selected_provider == "gemini":
        return GeminiLLMService()
    return MockLLMService()


__all__ = [
    "BaseLLMService",
    "LLMExplanationResult",
    "MockLLMService",
    "OpenAILLMService",
    "GeminiLLMService",
    "get_llm_service",
    "build_explanation_prompt",
    "SYSTEM_PROMPT",
]
