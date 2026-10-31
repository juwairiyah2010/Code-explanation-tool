"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from backend.schemas.quiz import QuizResponse


from backend.schemas.explanation import AlgorithmComplexity, BlockExplanation, ConceptTag

class LLMExplanationResult(NamedTuple):
    summary: str
    blocks: list[BlockExplanation]
    concepts: list[ConceptTag]
    algorithm_steps: list[str]
    complexity: AlgorithmComplexity
    hints: list[str]


class BaseLLMService(ABC):
    """Abstract interface for LLM generation engines."""

    async def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        json_mode: bool = True,
    ) -> str:
        """Execute chat completion and return the raw model string response."""
        raise NotImplementedError("generate_chat_completion must be implemented by provider.")


    @abstractmethod
    async def generate_explanation(
        self,
        code: str,
        language: str,
        level: str,
        ast_context: str | None = None,
        required_blocks: list | None = None,
        rag_context: str | None = None,
        rag_citations: list | None = None,
        **kwargs: Any,
    ) -> LLMExplanationResult:
        """Generate structured explanation from code and context."""
        pass

    @abstractmethod
    async def generate_quiz(
        self,
        code: str,
        language: str,
        explanation_context: str | None = None,
        locale: str = "en",
    ) -> "QuizResponse":
        """Generate a multiple-choice quiz based strictly on the code."""
        pass

