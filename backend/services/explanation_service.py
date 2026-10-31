"""Orchestration service coordinating language detection, AST parsing, LLM prompt synthesis, and repository storage."""

from sqlalchemy.orm import Session
from backend.repositories.submission_repo import SubmissionRepository
from backend.schemas.explanation import (
    CodeAnalysisResponse,
    ExplainCodeRequest,
    ExplainCodeResponse,
)
from backend.services.analysis.analysis_service import AnalysisService
from backend.services.explanation_pipeline import ExplanationPipeline
from backend.services.llm import BaseLLMService




class ExplanationService:
    """Service that processes code analysis and explanations using the ExplanationPipeline."""

    def __init__(self, db: Session | None = None, pipeline: ExplanationPipeline | None = None):
        self.db = db
        self.repo = SubmissionRepository(db) if db is not None else None
        self.analysis_service = AnalysisService()
        self.pipeline = pipeline or ExplanationPipeline(db=db, repo=self.repo)

    @property
    def llm(self) -> BaseLLMService:
        return self.pipeline.llm_service

    @llm.setter
    def llm(self, value: BaseLLMService) -> None:
        self.pipeline.llm_service = value


    def analyze_code_ast(
        self,
        code: str,
        language: str = "auto",
        filename: str | None = None,
    ) -> CodeAnalysisResponse:
        """Analyze code with CodeAnalyzer returning normalized findings and metrics."""
        return self.analysis_service.analyze(code, language=language, filename=filename)

    async def explain_code(self, request: ExplainCodeRequest) -> ExplainCodeResponse:
        """Execute the structured 10-stage explanation pipeline."""
        return await self.pipeline.execute(request)
