"""Tests for Python AST and JavaScript parsers."""

from backend.services.parsers import get_parser, PythonCodeParser, JavaScriptCodeParser


def test_python_parser_valid_code() -> None:
    code = """
import math

class Calculator:
    def add(self, a: int, b: int) -> int:
        \"\"\"Add two numbers.\"\"\"
        if a > 0 and b > 0:
            return a + b
        return 0
"""
    parser = get_parser("python")
    assert isinstance(parser, PythonCodeParser)
    result = parser.parse(code)

    assert result.is_valid_syntax is True
    assert result.syntax_error is None
    assert len(result.classes) == 1
    assert result.classes[0].name == "Calculator"
    assert len(result.functions) == 1
    assert result.functions[0].name == "add"
    assert "math" in result.imports
    assert result.complexity_score >= 2  # Has `if` and `and`


def test_python_parser_syntax_error() -> None:
    broken_code = "def broken_func(:\n    pass"
    parser = get_parser("python")
    result = parser.parse(broken_code)

    assert result.is_valid_syntax is False
    assert result.syntax_error is not None


def test_javascript_parser_valid_code() -> None:
    js_code = """
import { useState } from 'react';

class UserProfile {
    constructor(name) {
        this.name = name;
    }
}

function computeScore(user, multiplier) {
    if (multiplier > 1) {
        return 100 * multiplier;
    }
    return 100;
}
"""
    parser = get_parser("javascript")
    assert isinstance(parser, JavaScriptCodeParser)
    result = parser.parse(js_code)

    assert result.is_valid_syntax is True
    assert len(result.classes) >= 1
    assert result.classes[0].name == "UserProfile"
    assert len(result.functions) >= 1
    assert any(f.name == "computeScore" for f in result.functions)
    assert result.complexity_score >= 2


def test_python_parser_async_function() -> None:
    code = """
async def fetch_user(user_id: int):
    \"\"\"Asynchronous user lookup.\"\"\"
    return {"id": user_id}
"""
    parser = get_parser("python")
    result = parser.parse(code)
    assert result.is_valid_syntax is True
    assert len(result.functions) == 1
    assert result.functions[0].name == "fetch_user"
    assert result.functions[0].node_type == "AsyncFunctionDef"
    assert result.functions[0].docstring == "Asynchronous user lookup."


def test_javascript_parser_arrow_functions() -> None:
    code = """
const multiply = (a, b) => a * b;
const calculateTotal = (items) => {
    return items.reduce((acc, item) => acc + item.price, 0);
};
"""
    parser = get_parser("javascript")
    result = parser.parse(code)
    assert result.is_valid_syntax is True
    assert len(result.functions) >= 1
    names = [f.name for f in result.functions]
    assert "multiply" in names or "calculateTotal" in names

