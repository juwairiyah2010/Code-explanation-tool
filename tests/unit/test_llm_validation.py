"""Unit tests for LLM response validation, MockLLM, and malformed JSON recovery."""

import pytest
from backend.services.llm.mock_llm import MockLLMService
from backend.schemas.explanation import StructuredExplanationOutput
from tests.fixtures import (
    PYTHON_BASIC_MATH,
    MALFORMED_LLM_NOT_JSON,
)


@pytest.fixture
def mock_llm() -> MockLLMService:
    return MockLLMService()


@pytest.mark.asyncio
async def test_mock_llm_deterministic_output(mock_llm: MockLLMService):
    """Verify MockLLM returns fully populated and valid StructuredExplanationOutput."""
    res = await mock_llm.generate_structured_explanation(
        code=PYTHON_BASIC_MATH,
        language="python",
        mode="beginner",
    )
    assert isinstance(res, StructuredExplanationOutput)
    assert len(res.summary) > 0
    assert len(res.line_explanations) >= 1
    assert len(res.key_takeaways) >= 1


@pytest.mark.asyncio
async def test_mock_llm_all_modes_conformance(mock_llm: MockLLMService):
    """Verify MockLLM supports all eight explanation modes without errors."""
    modes = [
        "absolute beginner", "beginner", "intermediate", "expert",
        "line-by-line", "debugging", "security", "performance",
    ]
    for mode in modes:
        res = await mock_llm.generate_structured_explanation(
            code=PYTHON_BASIC_MATH,
            language="python",
            mode=mode,
        )
        assert res.summary is not None
        if res.complexity:
            assert res.complexity.time_complexity is not None


def test_pydantic_validation_on_malformed_json():
    """Verify raw malformed strings fail Pydantic model validation cleanly."""
    with pytest.raises(Exception):
        StructuredExplanationOutput.model_validate_json(MALFORMED_LLM_NOT_JSON)

    with pytest.raises(Exception):
        StructuredExplanationOutput.model_validate_json('{"line_explanations": "invalid_not_a_list"}')
