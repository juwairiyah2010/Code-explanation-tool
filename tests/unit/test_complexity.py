"""Unit tests for complexity metrics and AST nesting depth calculation."""

import pytest
from backend.services.analysis.code_analyzer import CodeAnalyzer
from tests.fixtures import PYTHON_EMPTY


@pytest.fixture
def analyzer() -> CodeAnalyzer:
    return CodeAnalyzer()


def test_linear_code_complexity(analyzer: CodeAnalyzer):
    """Linear code without branches has Cyclomatic Complexity = 1 and Nesting Depth = 1 or 0."""
    code = """x = 10
y = 20
z = x + y
print(z)
"""
    res = analyzer.analyze(code, language="python")
    assert res.cyclomatic_complexity == 1
    assert res.max_nesting_depth in (0, 1)


def test_single_branch_complexity(analyzer: CodeAnalyzer):
    """Single conditional branch raises Cyclomatic Complexity to 2."""
    code = """def check_val(x):
    if x > 0:
        return True
    return False
"""
    res = analyzer.analyze(code, language="python")
    assert res.cyclomatic_complexity >= 2
    assert len(res.constructs.conditions) >= 1


def test_deeply_nested_complexity_and_depth(analyzer: CodeAnalyzer):
    """Deeply nested loops and conditions calculate high nesting depth and complexity."""
    code = """def deeply_nested(data):
    for a in data:
        for b in a:
            if b > 0:
                while b < 10:
                    b += 1
    return data
"""
    res = analyzer.analyze(code, language="python")
    assert res.cyclomatic_complexity >= 4
    assert res.max_nesting_depth >= 4
    assert len(res.constructs.loops) >= 3


def test_empty_code_complexity(analyzer: CodeAnalyzer):
    """Empty code should safely return baseline complexity metrics without crashing."""
    res = analyzer.analyze(PYTHON_EMPTY, language="python")
    assert res.cyclomatic_complexity in (0, 1)
    assert res.max_nesting_depth == 0
