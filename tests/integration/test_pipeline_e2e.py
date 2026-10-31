"""End-to-end integration tests for ExplanationPipeline with deterministic services."""

import pytest
from sqlalchemy.orm import Session
from backend.repositories.submission_repo import SubmissionRepository
from backend.schemas.explanation import ExplainCodeRequest
from backend.services.explanation_pipeline import ExplanationPipeline
from backend.services.llm.mock_llm import MockLLMService
from tests.fixtures import PYTHON_BASIC_MATH, JAVASCRIPT_BASIC_MATH


@pytest.fixture
def pipeline(db_session: Session) -> ExplanationPipeline:
    repo = SubmissionRepository(db_session)
    pipe = ExplanationPipeline(db=db_session, repo=repo)
    pipe.llm_service = MockLLMService()
    return pipe


@pytest.mark.asyncio
async def test_pipeline_e2e_python(pipeline: ExplanationPipeline):
    """Executes full 10-stage pipeline on Python code and verifies grounding validation."""
    req = ExplainCodeRequest(
        code=PYTHON_BASIC_MATH,
        language="auto",
        level="Beginner",
        mode="beginner",
        enable_trace=True,
        enable_rag=False,
        save_history=True,
    )
    res = await pipeline.execute(req)
    assert res.language == "python"
    assert res.id is not None
    assert len(res.summary) > 0
    assert len(res.line_explanations) >= 1
    assert len(res.execution_walkthrough) >= 1
    assert res.validation_result is not None
    assert res.validation_result.valid is True


@pytest.mark.asyncio
async def test_pipeline_e2e_javascript(pipeline: ExplanationPipeline):
    """Executes pipeline on JavaScript code, skipping trace gracefully."""
    req = ExplainCodeRequest(
        code=JAVASCRIPT_BASIC_MATH,
        language="javascript",
        level="Beginner",
        mode="line-by-line",
        enable_trace=True,  # Tracing is Python-only; pipeline must handle gracefully
        enable_rag=False,
        save_history=True,
    )
    res = await pipeline.execute(req)
    assert res.language == "javascript"
    assert res.id is not None
    assert len(res.line_explanations) >= 1
    assert res.validation_result is not None
