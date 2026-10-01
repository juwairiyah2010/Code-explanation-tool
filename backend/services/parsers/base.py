"""Base parser interface for code syntax and AST analysis."""

from abc import ABC, abstractmethod
from backend.schemas.explanation import CodeAnalysisResponse


class BaseCodeParser(ABC):
    """Abstract Base Class for language-specific AST parsers."""

    @abstractmethod
    def parse(self, code: str, detection_method: str = "explicit") -> CodeAnalysisResponse:
        """Parse source code string and extract AST information, syntax checks, and metrics."""
        pass
