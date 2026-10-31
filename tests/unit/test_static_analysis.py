"""Unit tests for static analysis engine and rule checkers."""

import pytest
from backend.services.analysis.code_analyzer import CodeAnalyzer
from tests.fixtures import PYTHON_BASIC_MATH, PYTHON_EMPTY, PYTHON_SYNTAX_ERROR


@pytest.fixture
def analyzer() -> CodeAnalyzer:
    return CodeAnalyzer()


def test_clean_code_static_analysis(analyzer: CodeAnalyzer):
    """Clean code should produce high maintainability index and no critical errors."""
    res = analyzer.analyze(PYTHON_BASIC_MATH, language="python")
    assert res.is_valid is True
    assert res.complexity >= 1
    assert res.metrics.maintainability_index > 60


def test_broad_exception_rule_violation(analyzer: CodeAnalyzer):
    """Detects bare or broad exception handling without logging or re-raise."""
    code = """def unsafe_reader():
    try:
        val = 1 / 0
    except Exception:
        pass
"""
    res = analyzer.analyze(code, language="python")
    rule_ids = [h.rule_id for h in res.hints]
    assert any("exception" in rid.lower() or "broad" in rid.lower() or "error" in rid.lower() for rid in rule_ids)


def test_shadowing_builtin_rule(analyzer: CodeAnalyzer):
    """Detects shadowing of Python built-in names."""
    code = """def process_items(list, id):
    return list[0]
"""
    res = analyzer.analyze(code, language="python")
    messages = [h.message.lower() for h in res.hints]
    assert any("shadow" in m or "builtin" in m or "name" in m for m in messages)


def test_edge_case_empty_code_analysis(analyzer: CodeAnalyzer):
    """Empty code produces 0 functions, 0 complexity or baseline complexity 1."""
    res = analyzer.analyze(PYTHON_EMPTY, language="python")
    assert res.is_valid is True
    assert len(res.functions) == 0
    assert len(res.classes) == 0


def test_edge_case_syntax_error_analysis(analyzer: CodeAnalyzer):
    """Code with syntax error must return is_valid=False and descriptive error hint."""
    res = analyzer.analyze(PYTHON_SYNTAX_ERROR, language="python")
    assert res.is_valid is False
    assert res.syntax_error is not None
    assert any(h.severity == "error" for h in res.hints)
