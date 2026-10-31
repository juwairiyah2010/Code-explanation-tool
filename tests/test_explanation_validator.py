"""Comprehensive Unit Tests for the Deterministic Explanation Validation Layer."""

import pytest
from backend.schemas.explanation import (
    ExplanationValidationResult,
    IssueItem,
    LineExplanationItem,
    StructuredExplanationOutput,
    ExplainCodeRequest,
)
from backend.services.analysis.analysis_service import AnalysisService
from backend.services.explanation_pipeline import ExplanationPipeline
from backend.services.explanation_validator import ExplanationValidator


@pytest.fixture
def validator():
    return ExplanationValidator()


@pytest.fixture
def sample_code():
    return (
        "import math\n"            # Line 1
        "def compute(n):\n"        # Line 2
        "    if n < 0:\n"          # Line 3
        "        return 0\n"       # Line 4
        "    total = 0\n"          # Line 5
        "    for i in range(n):\n" # Line 6
        "        total += i\n"     # Line 7
        "    return total\n"       # Line 8
    )


@pytest.fixture
def sample_ast(sample_code):
    analyzer = AnalysisService()
    return analyzer.analyze(sample_code, language="python")


# ── 1. Source-Line & Referenced-Line Validation ──────────────────────────────

def test_source_and_referenced_line_validation_valid(validator, sample_code, sample_ast):
    structured = StructuredExplanationOutput(
        summary="A mathematical computation function.",
        line_explanations=[
            LineExplanationItem(line_number=1, explanation="Imports math module."),
            LineExplanationItem(line_number=2, explanation="Defines function compute."),
            LineExplanationItem(line_number=3, explanation="Checks if n is negative."),
            LineExplanationItem(line_number=6, explanation="Loop over range n."),
        ],
        concepts=[],
        issues=[],
        execution_walkthrough=["Starts at line 1, defines compute at line 2"],
        key_takeaways=[],
        suggested_improvements=[],
        uncertainty_notes=[],
    )

    result = validator.validate_grounding(structured, sample_code, sample_ast)
    assert isinstance(result, ExplanationValidationResult)
    assert result.valid is True
    assert result.invalid_references == []
    assert 1 in result.referenced_lines
    assert 2 in result.referenced_lines
    assert 3 in result.referenced_lines
    assert 6 in result.referenced_lines


def test_referenced_line_validation_invalid_out_of_bounds(validator, sample_code, sample_ast):
    structured = StructuredExplanationOutput(
        summary="Explains lines including an invalid line 99 and line 0.",
        line_explanations=[
            LineExplanationItem(line_number=2, explanation="Defines function compute."),
            LineExplanationItem(line_number=99, explanation="Non-existent line outside file bounds."),
        ],
        concepts=[],
        issues=[
            IssueItem(category="bug", severity="low", description="Fake bug", line_number=15)
        ],
        execution_walkthrough=["References non-existent Line 42 in text walkthrough."],
        key_takeaways=[],
        suggested_improvements=[],
        uncertainty_notes=[],
    )

    result = validator.validate_grounding(structured, sample_code, sample_ast)
    assert result.valid is False
    assert 99 in result.invalid_references
    assert 15 in result.invalid_references
    assert 42 in result.invalid_references


# ── 2. AST Construct Validation ──────────────────────────────────────────────

def test_ast_construct_validation_loop_on_correct_line(validator, sample_code, sample_ast):
    # Line 6 is "for i in range(n):" which is a valid loop
    structured = StructuredExplanationOutput(
        summary="Loop explanation",
        line_explanations=[
            LineExplanationItem(line_number=6, explanation="Line 6 contains a for loop iterating over range(n)."),
        ],
        concepts=[],
        issues=[],
        execution_walkthrough=[],
        key_takeaways=[],
        suggested_improvements=[],
        uncertainty_notes=[],
    )

    result = validator.validate_grounding(structured, sample_code, sample_ast)
    assert not any("Line 6 is claimed to contain a loop" in claim for claim in result.unsupported_claims)


def test_ast_construct_validation_loop_claimed_on_non_loop_line(validator, sample_code, sample_ast):
    # Line 7 is "total += i" which is an assignment, not a loop header/construct
    # Line 3 is "if n < 0:" which is a conditional, not a loop
    structured = StructuredExplanationOutput(
        summary="Code summary with false claim that Line 3 contains a loop.",
        line_explanations=[
            LineExplanationItem(line_number=3, explanation="Line 3 contains a loop over values."),
        ],
        concepts=[],
        issues=[],
        execution_walkthrough=["Line 3 contains a loop."],
        key_takeaways=[],
        suggested_improvements=[],
        uncertainty_notes=[],
    )

    result = validator.validate_grounding(structured, sample_code, sample_ast)
    assert result.valid is False
    assert any(
        "Line 3 is claimed to contain a loop" in claim or "Text claims Line 3 contains a loop" in claim
        for claim in result.unsupported_claims
    )


def test_ast_construct_validation_function_def_claim(validator, sample_code, sample_ast):
    # Line 5 is "total = 0", not a function definition
    structured = StructuredExplanationOutput(
        summary="Summary",
        line_explanations=[
            LineExplanationItem(line_number=5, explanation="Defines a function calculate."),
        ],
        concepts=[],
        issues=[],
        execution_walkthrough=[],
        key_takeaways=[],
        suggested_improvements=[],
        uncertainty_notes=[],
    )

    result = validator.validate_grounding(structured, sample_code, sample_ast)
    assert result.valid is False
    assert any("Line 5 is claimed to define a function" in claim for claim in result.unsupported_claims)


# ── 3. Static Finding Consistency Checking ───────────────────────────────────

def test_static_finding_consistency_warning(validator, sample_code, sample_ast):
    # If the LLM generates an issue on a line where deterministic static analysis did not find an issue
    structured = StructuredExplanationOutput(
        summary="Summary",
        line_explanations=[
            LineExplanationItem(line_number=2, explanation="Defines compute."),
        ],
        concepts=[],
        issues=[
            IssueItem(category="security", severity="high", description="Fake SQL injection vulnerability", line_number=4)
        ],
        execution_walkthrough=[],
        key_takeaways=[],
        suggested_improvements=[],
        uncertainty_notes=[],
    )

    result = validator.validate_grounding(structured, sample_code, sample_ast)
    assert any("Issue reported at line 4" in w and "not present in deterministic static analysis" in w for w in result.warnings)


# ── 4. Explanation Coverage Calculation ──────────────────────────────────────

def test_explanation_coverage_calculation(validator, sample_code, sample_ast):
    # sample_code has 8 significant lines (lines 1 to 8, all non-empty code)
    structured_low = StructuredExplanationOutput(
        summary="Very sparse explanation",
        line_explanations=[
            LineExplanationItem(line_number=1, explanation="Import math"),
        ],
        concepts=[],
        issues=[],
        execution_walkthrough=[],
        key_takeaways=[],
        suggested_improvements=[],
        uncertainty_notes=[],
    )

    res_low = validator.validate_grounding(structured_low, sample_code, sample_ast)
    assert res_low.coverage_score <= 0.25
    assert any("Low code coverage" in w for w in res_low.warnings)

    # Now explain all lines 1 through 8
    structured_full = StructuredExplanationOutput(
        summary="Complete coverage",
        line_explanations=[
            LineExplanationItem(line_number=i, explanation=f"Explains line {i}")
            for i in range(1, 9)
        ],
        concepts=[],
        issues=[],
        execution_walkthrough=[],
        key_takeaways=[],
        suggested_improvements=[],
        uncertainty_notes=[],
    )

    res_full = validator.validate_grounding(structured_full, sample_code, sample_ast)
    assert res_full.coverage_score == 1.0
    assert not any("Low code coverage" in w for w in res_full.warnings)


# ── 5. Deterministic Repair ──────────────────────────────────────────────────

def test_deterministic_repair_removes_invalids_and_fixes_unsupported_claims(validator, sample_code, sample_ast):
    structured = StructuredExplanationOutput(
        summary="Code summary",
        line_explanations=[
            LineExplanationItem(line_number=3, explanation="Line 3 contains a loop"),  # unsupported claim (it's an if)
            LineExplanationItem(line_number=99, explanation="Invented line 99"),        # invalid reference
        ],
        concepts=[],
        issues=[
            IssueItem(category="bug", severity="low", description="Fake bug", line_number=100)
        ],
        execution_walkthrough=["Text mentioning Line 50"],
        key_takeaways=[],
        suggested_improvements=[],
        uncertainty_notes=[],
    )

    initial_val = validator.validate_grounding(structured, sample_code, sample_ast)
    assert initial_val.valid is False

    repaired_struct = validator.repair_explanation(
        structured=structured,
        validation=initial_val,
        code=sample_code,
        ast_result=sample_ast,
    )

    # Line 99 must be removed
    line_nums = [item.line_number for item in repaired_struct.line_explanations]
    assert 99 not in line_nums

    # Line 3 explanation must be repaired using deterministic syntax info
    line_3 = next(item for item in repaired_struct.line_explanations if item.line_number == 3)
    assert "loop" not in line_3.explanation.lower()
    assert "conditional" in line_3.explanation.lower() or "if" in line_3.explanation.lower()

    # Re-evaluating validation on repaired output
    repaired_val = validator.validate_grounding(repaired_struct, sample_code, sample_ast)
    assert len(repaired_val.invalid_references) == 0
    assert len(repaired_val.unsupported_claims) == 0


# ── 6. End-to-End Pipeline Integration with Validation Result ─────────────────

@pytest.mark.asyncio
async def test_pipeline_includes_validation_result_and_indicator():
    pipeline = ExplanationPipeline(db=None)

    req = ExplainCodeRequest(
        code="def hello():\n    print('Hello World')\nhello()",
        language="python",
        mode="beginner",
        include_ast_analysis=True,
        enable_trace=True,
        enable_rag=False,
        save_history=False,
    )

    response = await pipeline.execute(req)

    assert response.validation_result is not None
    assert isinstance(response.validation_result, ExplanationValidationResult)
    assert response.validation_result.valid is True
    assert response.validation_result.coverage_score > 0.0
    assert response.validation_result.grounding_level in ["High", "Moderate"]
    assert response.validation_result.referenced_lines == [1, 2, 3]
