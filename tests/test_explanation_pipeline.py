"""Unit and integration tests for the redesigned 10-stage Explanation Pipeline."""

import pytest
from backend.schemas.explanation import (
    ExplainCodeRequest,
    StructuredExplanationOutput,
)

from backend.services.analysis.analysis_service import AnalysisService
from backend.services.detector.language_detector import LanguageDetector
from backend.services.explanation_pipeline import ExplanationPipeline
from backend.services.explanation_validator import ExplanationValidator
from backend.services.llm.base import BaseLLMService
from backend.services.llm.gemini_llm import GeminiLLMService
from backend.services.llm.mock_llm import MockLLMService
from backend.services.llm.openai_llm import OpenAILLMService
from backend.services.prompt_builder import PromptBuilder
from backend.services.rag.retrieval_service import RetrievalService
from backend.services.tracer_service import TraceService


SAMPLE_PYTHON_CODE = """def calculate_total(prices: list[float], tax_rate: float) -> float:
    subtotal = sum(prices)
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative")
    total = subtotal * (1 + tax_rate)
    return round(total, 2)

result = calculate_total([10.0, 20.0, 30.0], 0.05)
print(f"Total: {result}")
"""

SAMPLE_JS_CODE = """function formatGreeting(name, age) {
    if (!name) {
        throw new Error("Name is required");
    }
    return `Hello ${name}, you are ${age} years old.`;
}

console.log(formatGreeting("Alice", 25));
"""


# ── 1. Individual Service Unit Tests ─────────────────────────────────────────

def test_language_detector_service():
    detector = LanguageDetector()
    res_py = detector.detect(SAMPLE_PYTHON_CODE)
    assert res_py.language == "python"
    assert res_py.confidence > 0.5

    res_js = detector.detect(SAMPLE_JS_CODE)
    assert res_js.language == "javascript"
    assert res_js.confidence > 0.5

    res_file = detector.detect("let x = 1;", filename="test.js")
    assert res_file.language == "javascript"
    assert res_file.method == "filename"


def test_analysis_service():
    service = AnalysisService()
    res = service.analyze(SAMPLE_PYTHON_CODE, language="python")
    assert res.is_valid_syntax is True
    assert res.complexity_score >= 1
    assert res.function_count == 1
    assert "calculate_total" in [f.name for f in res.constructs.functions]
    assert len(res.blocks) > 0


@pytest.mark.asyncio
async def test_trace_service_applicable_and_not_applicable():
    trace_service = TraceService()

    # Applicable for valid Python
    trace_py = await trace_service.trace_if_applicable(
        "a = 5\nb = 10\nc = a + b", language="python"
    )
    assert trace_py is not None
    assert trace_py.success is True
    assert len(trace_py.steps or []) >= 3

    # Not applicable for JavaScript
    trace_js = await trace_service.trace_if_applicable(
        "console.log('hi')", language="javascript"
    )
    assert trace_js is None


def test_retrieval_service_query_extraction():
    service = RetrievalService(db=None)
    analyzer = AnalysisService()
    ast_res = analyzer.analyze(SAMPLE_PYTHON_CODE, language="python")

    query = service.extract_search_query(SAMPLE_PYTHON_CODE, ast_result=ast_res)
    assert "functions" in query or "calculate_total" in query or "prices" in query


def test_prompt_builder_all_eight_modes():
    builder = PromptBuilder()
    modes = [
        "absolute beginner",
        "beginner",
        "intermediate",
        "expert",
        "line-by-line",
        "debugging",
        "security",
        "performance",
    ]

    for mode in modes:
        sys_p, usr_p = builder.build_prompts(
            code=SAMPLE_PYTHON_CODE,
            language="python",
            mode=mode,
        )
        assert "Core Code Explanation Engine" in sys_p
        assert f"Requested Mode**: {mode}" in usr_p
        assert "SOURCE CODE" in usr_p
        assert "DETERMINISTIC AST & STATIC ANALYSIS FINDINGS" in usr_p
        assert "RUNTIME EXECUTION TRACE" in usr_p


def test_explanation_validator_line_reference_integrity():
    validator = ExplanationValidator()
    code = "x = 1\ny = 2\nz = x + y"

    raw_json = """{
      "summary": "Valid test snippet",
      "line_explanations": [
        {"line_number": 1, "code": "x = 1", "explanation": "Assigns x.", "uncertainty_note": null},
        {"line_number": 2, "code": "y = 2", "explanation": "Assigns y.", "uncertainty_note": null},
        {"line_number": 99, "code": "fake()", "explanation": "Invented line outside source range.", "uncertainty_note": null}
      ],
      "concepts": [],
      "issues": [],
      "execution_walkthrough": [],
      "key_takeaways": [],
      "suggested_improvements": [],
      "uncertainty_notes": []
    }"""


    output, err = validator.validate_and_sanitize(raw_json, code)
    assert err is None
    assert output is not None

    # Line 99 should have been safely discarded
    line_nums = [item.line_number for item in output.line_explanations]
    assert line_nums == [1, 2]
    assert 99 not in line_nums
    assert any("Discarded" in note and "99" in note for note in output.uncertainty_notes)


def test_explanation_validator_safe_fallback_on_invalid_json():
    validator = ExplanationValidator()
    code = "def add(a, b):\n    return a + b"
    invalid_raw = "This is not JSON at all! Just raw plain text."

    output, err = validator.validate_and_sanitize(invalid_raw, code)
    assert output is None
    assert "JSON parse error" in err

    fallback = validator.synthesize_fallback(
        code=code,
        language="python",
        mode="beginner",
        failure_reason=err,
    )
    assert isinstance(fallback, StructuredExplanationOutput)
    assert len(fallback.line_explanations) == 2
    assert fallback.line_explanations[0].line_number == 1
    assert fallback.line_explanations[1].line_number == 2
    assert any("Notice:" in note for note in fallback.uncertainty_notes)


def test_provider_interface_conformance():
    mock_svc = MockLLMService()
    openai_svc = OpenAILLMService(api_key="sk-fake", model="gpt-4o-mini")
    gemini_svc = GeminiLLMService(api_key="gm-fake", model="gemini-1.5-flash")

    assert isinstance(mock_svc, BaseLLMService)
    assert isinstance(openai_svc, BaseLLMService)
    assert isinstance(gemini_svc, BaseLLMService)

    assert hasattr(mock_svc, "generate_chat_completion")
    assert hasattr(openai_svc, "generate_chat_completion")
    assert hasattr(gemini_svc, "generate_chat_completion")


# ── 2. Full End-to-End Pipeline Execution Tests ─────────────────────────────

@pytest.mark.asyncio
async def test_explanation_pipeline_end_to_end_python():
    pipeline = ExplanationPipeline(db=None)

    req = ExplainCodeRequest(
        code=SAMPLE_PYTHON_CODE,
        language="python",
        level="Intermediate",
        mode="debugging",
        include_ast_analysis=True,
        enable_trace=True,
        enable_rag=False,
        save_history=False,
    )

    res = await pipeline.execute(req)

    # Structure assertions
    assert res.language == "python"
    assert res.explanation_mode == "debugging"
    assert res.summary is not None
    assert len(res.summary) > 10

    # Structured output fields
    assert res.structured_output is not None
    assert len(res.line_explanations) > 0
    assert len(res.execution_walkthrough) > 0
    assert len(res.key_takeaways) > 0
    assert len(res.suggested_improvements) > 0

    # Line-by-line verification
    total_lines = len(SAMPLE_PYTHON_CODE.splitlines())
    for item in res.line_explanations:
        assert 1 <= item.line_number <= total_lines
        assert item.code is not None

    # Execution trace attached
    assert res.execution_trace is not None
    assert res.execution_trace.success is True


@pytest.mark.asyncio
async def test_explanation_pipeline_end_to_end_javascript():
    pipeline = ExplanationPipeline(db=None)

    req = ExplainCodeRequest(
        code=SAMPLE_JS_CODE,
        language="javascript",
        level="Beginner",
        mode="absolute beginner",
        include_ast_analysis=True,
        enable_trace=True,  # Should gracefully skip trace for JS
        enable_rag=False,
        save_history=False,
    )

    res = await pipeline.execute(req)
    assert res.language == "javascript"
    assert res.explanation_mode == "absolute beginner"
    assert res.structured_output is not None
    assert res.execution_trace is None  # Not traced in Python sandbox


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode",
    [
        "absolute beginner",
        "beginner",
        "intermediate",
        "expert",
        "line-by-line",
        "debugging",
        "security",
        "performance",
    ],
)
async def test_pipeline_supports_all_eight_modes(mode: str):
    pipeline = ExplanationPipeline(db=None)
    req = ExplainCodeRequest(
        code="n = 10\nresult = [i ** 2 for i in range(n)]\nprint(result)",
        language="python",
        mode=mode,
        save_history=False,
    )
    res = await pipeline.execute(req)
    assert res.explanation_mode == mode
    assert res.structured_output is not None
    assert len(res.line_explanations) == 3


@pytest.mark.asyncio
async def test_pipeline_safe_fallback_when_llm_fails_json():
    # Use mock with failure flag enabled
    failing_llm = MockLLMService()
    failing_llm.should_fail_json = True

    pipeline = ExplanationPipeline(db=None, llm_service=failing_llm)

    req = ExplainCodeRequest(
        code="def greet(name):\n    return f'Hello, {name}'\n\ngreet('World')",
        language="python",
        mode="security",
        save_history=False,
    )

    res = await pipeline.execute(req)
    # The pipeline must not crash; it safely synthesizes deterministic fallback
    assert res.structured_output is not None
    assert len(res.line_explanations) > 0
    assert any("Notice:" in note for note in res.uncertainty_notes)


@pytest.mark.asyncio
async def test_pipeline_discards_hallucinated_lines_and_notes_uncertainty():
    hallucinating_llm = MockLLMService()
    hallucinating_llm.simulate_hallucinated_lines = True

    pipeline = ExplanationPipeline(db=None, llm_service=hallucinating_llm)

    code = "val = 42\nprint(val)"
    req = ExplainCodeRequest(
        code=code,
        language="python",
        mode="beginner",
        save_history=False,
    )

    res = await pipeline.execute(req)
    total_lines = len(code.splitlines())  # 2 lines

    for item in res.line_explanations:
        assert 1 <= item.line_number <= total_lines

    # Should note that hallucinated lines were discarded
    assert any("Discarded" in note for note in res.uncertainty_notes)
