"""AnalysisService coordinating AST parsing, structural metrics, and educational rule findings."""

from backend.schemas.explanation import CodeAnalysisResponse
from backend.services.analysis.code_analyzer import CodeAnalyzer
from backend.services.analysis.static_analyzer import StaticAnalyzer


class AnalysisService:
    """Service encapsulating multi-language AST parsing and deterministic static analysis."""

    def __init__(self, code_analyzer: CodeAnalyzer | None = None, static_analyzer: StaticAnalyzer | None = None):
        self.analyzer = code_analyzer or CodeAnalyzer(static_analyzer=static_analyzer)

    def analyze(
        self,
        code: str,
        language: str = "auto",
        filename: str | None = None,
    ) -> CodeAnalysisResponse:
        """Run complete AST parsing, syntax validation, metric calculation, and rule evaluation."""
        return self.analyzer.analyze(code=code, language=language, filename=filename)
