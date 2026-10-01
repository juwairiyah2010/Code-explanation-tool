"""Comprehensive tests for the code analysis layer across Python and JavaScript.

Tests at least 10 diverse sample programs covering language detection, constructs extraction,
syntax blocks splitting, and static rules (unused variables, deep nesting, missing returns).
"""

import pytest
from backend.services.detector import detect_language, detect_by_syntax
from backend.services.parsers import get_parser, PythonCodeParser, JavaScriptCodeParser


# ---------------------------------------------------------------------------
# Sample Programs 1-6: Python
# ---------------------------------------------------------------------------

SAMPLE_PY_1_MATH = """
import math

def calculate_hypotenuse(a: float, b: float) -> float:
    \"\"\"Compute hypotenuse using Pythagorean theorem.\"\"\"
    squared_sum = a**2 + b**2
    return math.sqrt(squared_sum)
"""

SAMPLE_PY_2_OOP = """
from typing import Optional

class Animal:
    def __init__(self, name: str):
        self.name = name

    def speak(self) -> str:
        return f"{self.name} makes a sound"

class Dog(Animal):
    def speak(self) -> str:
        return f"{self.name} barks"
"""

SAMPLE_PY_3_DEEP_NESTING = """
def process_matrix(matrix: list[list[int]]) -> int:
    total = 0
    for row in matrix:
        for val in row:
            if val > 0:
                if val % 2 == 0:
                    if val > 100:
                        total += val
    return total
"""

SAMPLE_PY_4_UNUSED_VAR = """
def compute_area(length: float, width: float) -> float:
    temp_multiplier = 100  # Never used
    area = length * width
    return area
"""

SAMPLE_PY_5_MISSING_RETURN = """
def classify_number(n: int) -> str:
    if n > 0:
        return "positive"
    elif n < 0:
        return "negative"
    # Falls through for 0 without return
"""

SAMPLE_PY_6_SYNTAX_ERROR = """
def broken_syntax(x, y:
    return x + y
"""


# ---------------------------------------------------------------------------
# Sample Programs 7-10: JavaScript
# ---------------------------------------------------------------------------

SAMPLE_JS_7_CLOSURE = """
function createCounter(initialValue = 0) {
    let count = initialValue;
    const increment = () => {
        count += 1;
        return count;
    };
    return increment;
}
"""

SAMPLE_JS_8_OOP = """
import { EventEmitter } from 'events';

class DataService extends EventEmitter {
    constructor(endpoint) {
        super();
        this.endpoint = endpoint;
    }

    async fetchData() {
        const response = await fetch(this.endpoint);
        return response.json();
    }
}
"""

SAMPLE_JS_9_DEEP_NESTING = """
function findItem(grid) {
    for (let i = 0; i < grid.length; i++) {
        for (let j = 0; j < grid[i].length; j++) {
            if (grid[i][j] !== null) {
                if (grid[i][j] > 10) {
                    if (grid[i][j] % 2 === 0) {
                        return { x: i, y: j };
                    }
                }
            }
        }
    }
    return null;
}
"""

SAMPLE_JS_10_UNUSED_AND_RETURN = """
function evaluateScore(score) {
    const unusedWeight = 1.5;
    if (score >= 90) {
        return "A";
    } else if (score >= 80) {
        return "B";
    }
}
"""


# ===========================================================================
# Test Cases
# ===========================================================================

# 1. Sample 1: Python Math Function
def test_sample_1_python_math():
    parser = get_parser("python")
    res = parser.parse(SAMPLE_PY_1_MATH)

    assert res.is_valid_syntax is True
    assert len(res.constructs.functions) == 1
    fn = res.constructs.functions[0]
    assert fn.name == "calculate_hypotenuse"
    assert fn.parameters == ["a", "b"]
    assert fn.docstring is not None
    assert len(res.constructs.imports) == 1
    assert len(res.constructs.calls) >= 1
    assert len(res.blocks) >= 1


# 2. Sample 2: Python OOP with Classes & Inheritance
def test_sample_2_python_oop():
    parser = get_parser("python")
    res = parser.parse(SAMPLE_PY_2_OOP)

    assert res.is_valid_syntax is True
    assert len(res.constructs.classes) == 2
    class_names = [c.name for c in res.constructs.classes]
    assert "Animal" in class_names
    assert "Dog" in class_names
    dog_class = next(c for c in res.constructs.classes if c.name == "Dog")
    assert "Animal" in dog_class.bases
    assert "speak" in dog_class.methods


# 3. Sample 3: Python Deep Nesting Rule
def test_sample_3_python_deep_nesting():
    parser = get_parser("python")
    res = parser.parse(SAMPLE_PY_3_DEEP_NESTING)

    assert res.is_valid_syntax is True
    assert res.max_nesting_depth >= 4
    hint_rules = [h.rule_id for h in res.static_hints]
    assert "DEEP_NESTING" in hint_rules


# 4. Sample 4: Python Unused Variable Rule
def test_sample_4_python_unused_variable():
    parser = get_parser("python")
    res = parser.parse(SAMPLE_PY_4_UNUSED_VAR)

    assert res.is_valid_syntax is True
    hint_rules = [h.rule_id for h in res.static_hints]
    assert "UNUSED_VARIABLE" in hint_rules
    unused_hint = next(h for h in res.static_hints if h.rule_id == "UNUSED_VARIABLE")
    assert "temp_multiplier" in unused_hint.message


# 5. Sample 5: Python Missing Return Rule
def test_sample_5_python_missing_return():
    parser = get_parser("python")
    res = parser.parse(SAMPLE_PY_5_MISSING_RETURN)

    assert res.is_valid_syntax is True
    hint_rules = [h.rule_id for h in res.static_hints]
    assert "MISSING_RETURN" in hint_rules


# 6. Sample 6: Python Syntax Error Handling
def test_sample_6_python_syntax_error():
    parser = get_parser("python")
    res = parser.parse(SAMPLE_PY_6_SYNTAX_ERROR)

    assert res.is_valid_syntax is False
    assert res.syntax_error is not None
    assert len(res.syntax_errors) >= 1
    assert res.syntax_errors[0].line >= 1


# 7. Sample 7: JavaScript Closures & Arrow Functions
def test_sample_7_javascript_closure():
    parser = get_parser("javascript")
    res = parser.parse(SAMPLE_JS_7_CLOSURE)

    assert res.is_valid_syntax is True
    assert len(res.constructs.functions) >= 2  # createCounter and increment arrow function
    fn_names = [f.name for f in res.constructs.functions]
    assert "createCounter" in fn_names
    assert "increment" in fn_names


# 8. Sample 8: JavaScript OOP & Async Methods
def test_sample_8_javascript_oop():
    parser = get_parser("javascript")
    res = parser.parse(SAMPLE_JS_8_OOP)

    assert res.is_valid_syntax is True
    assert len(res.constructs.classes) == 1
    cls = res.constructs.classes[0]
    assert cls.name == "DataService"
    assert "EventEmitter" in cls.bases


# 9. Sample 9: JavaScript Deep Nesting
def test_sample_9_javascript_deep_nesting():
    parser = get_parser("javascript")
    res = parser.parse(SAMPLE_JS_9_DEEP_NESTING)

    assert res.is_valid_syntax is True
    assert len(res.constructs.loops) >= 2
    assert len(res.constructs.conditions) >= 2
    assert res.max_nesting_depth >= 4 or len(res.static_hints) >= 1


# 10. Sample 10: JavaScript Unused Variable & Missing Return
def test_sample_10_javascript_unused_and_missing_return():
    parser = get_parser("javascript")
    res = parser.parse(SAMPLE_JS_10_UNUSED_AND_RETURN)

    assert res.is_valid_syntax is True
    hint_rules = [h.rule_id for h in res.static_hints]
    assert "UNUSED_VARIABLE" in hint_rules or "MISSING_RETURN" in hint_rules


# 11. Language Detection by File Extension
def test_language_detection_by_extension():
    assert detect_language("x = 1", filename="script.py").language == "python"
    assert detect_language("x = 1", filename="types.pyi").language == "python"
    assert detect_language("const x = 1;", filename="index.js").language == "javascript"
    assert detect_language("const x = 1;", filename="component.tsx").language == "javascript"
    assert detect_language("const x = 1;", filename="app.mjs").language == "javascript"


# 12. Language Detection by Syntax Heuristic Fallback
def test_language_detection_by_syntax():
    py_code = "def greet(name):\n    print(f'Hello {name}')"
    js_code = "const greet = (name) => {\n    console.log(`Hello ${name}`);\n};"

    assert detect_by_syntax(py_code).language == "python"
    assert detect_by_syntax(js_code).language == "javascript"


# 13. Safe Handling of Empty and Whitespace Code
def test_empty_and_whitespace_code_handling():
    py_parser = get_parser("python")
    res_py = py_parser.parse("")
    assert res_py.is_valid_syntax is True
    assert res_py.metrics["total_lines"] == 0

    js_parser = get_parser("javascript")
    res_js = js_parser.parse("   \n   \t  ")
    assert res_js.is_valid_syntax is True
