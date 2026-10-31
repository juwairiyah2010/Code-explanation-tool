"""Unit tests for the JavaScript AST / Tree-sitter parser."""

import pytest
from backend.services.parsers.javascript_parser import JavaScriptCodeParser
from tests.fixtures import (
    JAVASCRIPT_BASIC_MATH,
    JAVASCRIPT_EMPTY,
    JAVASCRIPT_WHITESPACE,
    JAVASCRIPT_SYNTAX_ERROR,
    JAVASCRIPT_VERY_LONG,
    JAVASCRIPT_NESTED_FUNCTIONS,
    JAVASCRIPT_RECURSION,
    JAVASCRIPT_LOOPS,
)


@pytest.fixture
def parser() -> JavaScriptCodeParser:
    return JavaScriptCodeParser()


def test_parse_valid_function(parser: JavaScriptCodeParser):
    """Verify function construct extraction in JavaScript."""
    res = parser.parse(JAVASCRIPT_BASIC_MATH)
    assert res.is_valid is True
    assert len(res.functions) >= 1
    fn = res.functions[0]
    assert fn.name == "addNumbers"
    assert "a" in fn.parameters
    assert "b" in fn.parameters


def test_parse_arrow_functions(parser: JavaScriptCodeParser):
    """Verify arrow function detection and naming."""
    code = """const multiply = (x, y) => x * y;
const greet = name => {
    return `Hello ${name}`;
};
"""
    res = parser.parse(code)
    assert res.is_valid is True
    assert len(res.functions) >= 2
    fn_names = [f.name for f in res.functions]
    assert "multiply" in fn_names
    assert "greet" in fn_names


def test_parse_class_and_methods(parser: JavaScriptCodeParser):
    """Verify class construct extraction with methods in JavaScript."""
    code = """class DataStore extends BaseStore {
    constructor(name) {
        super();
        this.name = name;
    }
    fetchItem(id) {
        return this.items[id];
    }
}
"""
    res = parser.parse(code)
    assert res.is_valid is True
    assert len(res.constructs.classes) >= 1
    cls_node = res.constructs.classes[0]
    assert cls_node.name == "DataStore"
    assert "BaseStore" in cls_node.bases
    assert "fetchItem" in cls_node.methods


def test_parse_loops(parser: JavaScriptCodeParser):
    """Verify extraction of JavaScript for-of and while loops."""
    res = parser.parse(JAVASCRIPT_LOOPS)
    assert res.is_valid is True
    assert len(res.loops) >= 2


def test_edge_case_empty_and_whitespace(parser: JavaScriptCodeParser):
    """Empty or whitespace code returns valid with zero constructs."""
    res_empty = parser.parse(JAVASCRIPT_EMPTY)
    assert res_empty.is_valid is True
    assert len(res_empty.functions) == 0

    res_ws = parser.parse(JAVASCRIPT_WHITESPACE)
    assert res_ws.is_valid is True
    assert len(res_ws.functions) == 0


def test_edge_case_syntax_error(parser: JavaScriptCodeParser):
    """Syntax errors in JavaScript must mark is_valid=False or identify syntax issues."""
    res = parser.parse(JAVASCRIPT_SYNTAX_ERROR)
    # Parser should flag the syntax anomaly gracefully
    assert res.is_valid is False or res.syntax_error is not None


def test_edge_case_very_long_code(parser: JavaScriptCodeParser):
    """Parser must handle large JavaScript files without crashing."""
    res = parser.parse(JAVASCRIPT_VERY_LONG)
    assert res.is_valid is True
    assert len(res.assignments) > 50


def test_edge_case_nested_functions(parser: JavaScriptCodeParser):
    """Nested JavaScript functions must be captured."""
    res = parser.parse(JAVASCRIPT_NESTED_FUNCTIONS)
    assert res.is_valid is True
    fn_names = [f.name for f in res.functions]
    assert "makeMultiplier" in fn_names
    assert "multiply" in fn_names


def test_edge_case_recursion(parser: JavaScriptCodeParser):
    """Recursive JavaScript function must be captured with conditional."""
    res = parser.parse(JAVASCRIPT_RECURSION)
    assert res.is_valid is True
    assert any(f.name == "factorial" for f in res.functions)
    assert len(res.conditions) >= 1
