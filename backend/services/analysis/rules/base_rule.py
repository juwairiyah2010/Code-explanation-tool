"""Base interface for static analysis rules."""

from abc import ABC, abstractmethod
from typing import Any
from backend.schemas.explanation import StaticHint


class BaseStaticRule(ABC):
    """Abstract interface for static lint / code quality analysis rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique identifier for this rule (e.g. UNUSED_VARIABLE)."""
        pass

    @abstractmethod
    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[StaticHint]:
        """Run analysis rule and yield list of StaticHints."""
        pass
