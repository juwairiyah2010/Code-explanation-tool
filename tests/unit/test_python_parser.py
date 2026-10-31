"""Unit tests for the Python AST parser and construct extractor."""

import pytest
from backend.services.parsers.python_parser import PythonCodeParser
from tests.fixtures import (
    PYTHON_BASIC_MATH,
    PYTHON_EMPTY,
    PYTHON_WHITESPACE,
    PYTHON_SYNTAX_ERROR,
    PYTHON_VERY_LONG,
    PYTHON_NESTED_FUNCTIONS,
    PYTHON_RECURSION,
    PYTHON_LOOPS,
)


@pytest.fixture
def parser() -> PythonCodeParser:
    return PythonCodeParser()


def test_parse_valid_function(parser: PythonCodeParser):
    """Verify function construct extraction with parameters, return type, and docstring."""
    res = parser.parse(PYTHON_BASIC_MATH)
    assert res.is_valid is True
    assert len(res.constructs.functions) == 1
    fn = res.constructs.functions[0]
    assert fn.name == "add_numbers"
    assert fn.parameters == ["a", "b"]
    assert fn.return_type == "int"
    assert "Add two numbers" in (fn.docstring or "")
    assert fn.line_start == 1
    assert fn.line_end == 4


def test_parse_class_construct(parser: PythonCodeParser):
    """Verify class extraction with bases, methods, and line bounds."""
    code = """class Calculator(BaseEngine):
    \"\"\"Perform numerical operations.\"\"\"
    def multiply(self, x, y):
        return x * y
"""
    res = parser.parse(code)
    assert res.is_valid is True
    assert len(res.constructs.classes) == 1
    cls_node = res.constructs.classes[0]
    assert cls_node.name == "Calculator"
    assert cls_node.bases == ["BaseEngine"]
    assert "multiply" in cls_node.methods
    assert "Perform numerical" in (cls_node.docstring or "")


def test_parse_async_function(parser: PythonCodeParser):
    """Verify async function extraction correctly sets is_async=True."""
    code = """async def fetch_data(url: str):
    return await client.get(url)
"""
    res = parser.parse(code)
    assert res.is_valid is True
    assert len(res.constructs.functions) == 1
    assert res.constructs.functions[0].is_async is True


def test_parse_loops(parser: PythonCodeParser):
    """Verify extraction of nested for loops and while loops."""
    res = parser.parse(PYTHON_LOOPS)
    assert res.is_valid is True
    assert len(res.loops) >= 3
    loop_types = [l.loop_type for l in res.loops]
    assert "for" in loop_types
    assert "while" in loop_types


def test_edge_case_empty_code(parser: PythonCodeParser):
    """Empty or whitespace code should return valid with empty construct lists."""
    res_empty = parser.parse(PYTHON_EMPTY)
    assert res_empty.is_valid is True
    assert len(res_empty.functions) == 0
    assert len(res_empty.classes) == 0

    res_ws = parser.parse(PYTHON_WHITESPACE)
    assert res_ws.is_valid is True
    assert len(res_ws.functions) == 0


def test_edge_case_syntax_error(parser: PythonCodeParser):
    """Syntax error must mark is_valid=False and populate syntax_error details."""
    res = parser.parse(PYTHON_SYNTAX_ERROR)
    assert res.is_valid is False
    assert res.syntax_error is not None
    assert "line" in res.syntax_error.lower() or "syntax" in res.syntax_error.lower()


def test_edge_case_very_long_code(parser: PythonCodeParser):
    """Parser must handle large multi-line code files without degradation."""
    res = parser.parse(PYTHON_VERY_LONG)
    assert res.is_valid is True
    assert len(res.assignments) > 50


def test_edge_case_nested_functions(parser: PythonCodeParser):
    """Parser must detect both outer and inner nested functions."""
    res = parser.parse(PYTHON_NESTED_FUNCTIONS)
    assert res.is_valid is True
    fn_names = [f.name for f in res.constructs.functions]
    assert "make_multiplier" in fn_names
    assert "multiply" in fn_names


def test_edge_case_recursion(parser: PythonCodeParser):
    """Parser must capture recursive function definitions and conditionals."""
    res = parser.parse(PYTHON_RECURSION)
    assert res.is_valid is True
    assert len(res.constructs.functions) == 1
    assert res.constructs.functions[0].name == "factorial"
    assert len(res.conditions) >= 1
