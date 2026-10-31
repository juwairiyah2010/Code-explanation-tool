"""Base interface for static code analysis rules."""

from abc import ABC, abstractmethod
from typing import Any
from backend.schemas.explanation import AnalysisFinding


class BaseStaticRule(ABC):
    """Abstract interface for static lint / code quality analysis rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique identifier for this rule (e.g. UNUSED_VARIABLE)."""
        pass

    @property
    def category(self) -> str:
        """Category: syntax, unused code, complexity, control flow, return behavior, variable usage, imports, exception handling, code quality, security, performance."""
        return "code quality"

    @abstractmethod
    def analyze(
        self, code: str, language: str, ast_tree: Any, raw_constructs: Any
    ) -> list[AnalysisFinding]:
        """Run analysis rule and return normalized findings."""
        pass
