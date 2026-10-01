"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import NamedTuple


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

    @abstractmethod
    async def generate_explanation(
        self,
        code: str,
        language: str,
        level: str,
        ast_context: str | None = None,
        required_blocks: list | None = None,
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
