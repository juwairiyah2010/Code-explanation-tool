"""Unit tests for the deterministic explanation grounding validation layer."""

import pytest
from backend.services.explanation_validator import ExplanationValidator
from backend.schemas.explanation import (
    LineExplanationItem,
    StructuredExplanationOutput,
    AlgorithmComplexity,
)
from backend.services.analysis.code_analyzer import CodeAnalyzer
from tests.fixtures import PYTHON_BASIC_MATH


@pytest.fixture
def validator() -> ExplanationValidator:
    return ExplanationValidator()


@pytest.fixture
def analyzer() -> CodeAnalyzer:
    return CodeAnalyzer()


def test_grounding_valid_explanation(validator: ExplanationValidator, analyzer: CodeAnalyzer):
    """Accurate explanations pass grounding validation with High rating."""
    analysis = analyzer.analyze(PYTHON_BASIC_MATH, language="python")
    output = StructuredExplanationOutput(
        summary="Adds two integers.",
        complexity=AlgorithmComplexity(time="O(1)", space="O(1)"),
        line_explanations=[
            LineExplanationItem(line=1, explanation="Defines add_numbers function.", ast_node="FunctionDef"),
            LineExplanationItem(line=3, explanation="Computes sum.", ast_node="Assign"),
            LineExplanationItem(line=4, explanation="Returns sum.", ast_node="Return"),
        ],
        hints=[],
        key_takeaways=["Simple function."],
    )
    res = validator.validate(code=PYTHON_BASIC_MATH, explanation=output, analysis=analysis)
    assert res.valid is True
    assert len(res.invalid_references) == 0
    assert res.coverage_score > 0.4


def test_grounding_invalid_line_reference(validator: ExplanationValidator, analyzer: CodeAnalyzer):
    """Detects references to non-existent source lines."""
    analysis = analyzer.analyze(PYTHON_BASIC_MATH, language="python")
    output = StructuredExplanationOutput(
        summary="Broken line reference.",
        complexity=AlgorithmComplexity(time="O(1)", space="O(1)"),
        line_explanations=[
            LineExplanationItem(line=999, explanation="Non-existent line.", ast_node="FunctionDef"),
        ],
        hints=[],
        key_takeaways=[],
    )
    res = validator.validate(code=PYTHON_BASIC_MATH, explanation=output, analysis=analysis)
    assert res.valid is False
    assert 999 in res.invalid_references


def test_grounding_unsupported_ast_claim(validator: ExplanationValidator, analyzer: CodeAnalyzer):
    """Detects false claims about AST constructs on non-loop lines."""
    analysis = analyzer.analyze(PYTHON_BASIC_MATH, language="python")
    output = StructuredExplanationOutput(
        summary="Contains loop claim.",
        complexity=AlgorithmComplexity(time="O(1)", space="O(1)"),
        line_explanations=[
            LineExplanationItem(line=3, explanation="Line 3 contains a while loop iterating items.", ast_node="While"),
        ],
        hints=[],
        key_takeaways=[],
    )
    res = validator.validate(code=PYTHON_BASIC_MATH, explanation=output, analysis=analysis)
    assert res.valid is False
    assert any("loop" in c.lower() for c in res.unsupported_claims)
