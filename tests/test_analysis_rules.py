"""Comprehensive unit tests for each static analysis rule, category, and metric."""

import pytest
from backend.services.analysis.code_analyzer import CodeAnalyzer
from backend.schemas.explanation import AnalysisFinding


@pytest.fixture
def analyzer() -> CodeAnalyzer:
    return CodeAnalyzer()


def assert_normalized_finding(finding: AnalysisFinding, expected_category: str | None = None) -> None:
    """Validate that every finding conforms to the normalized model specification."""
    assert finding.rule_id, "Finding must have a non-empty rule_id"
    assert finding.language in ("python", "javascript"), f"Unexpected language: {finding.language}"
    assert finding.severity in ("info", "warning", "error"), f"Unexpected severity: {finding.severity}"
    assert isinstance(finding.line_number, int) and finding.line_number >= 1, "line_number must be >= 1"
    assert finding.category, "Category must not be empty"
    if expected_category:
        assert finding.category == expected_category, f"Expected category {expected_category}, got {finding.category}"
    assert finding.title, "Title must not be empty"
    assert finding.technical_description, "technical_description must not be empty"
    assert finding.beginner_explanation, "beginner_explanation must not be empty"
    assert finding.suggested_fix, "suggested_fix must not be empty"


# 1. Syntax Rule Category
def test_rule_syntax_python_error(analyzer: CodeAnalyzer) -> None:
    code = "def broken(\n    return 42"
    result = analyzer.analyze(code, language="python")

    assert result.is_valid_syntax is False
    assert len(result.findings) >= 1
    syntax_findings = [f for f in result.findings if f.category == "syntax"]
    assert len(syntax_findings) >= 1
    f = syntax_findings[0]
    assert_normalized_finding(f, "syntax")
    assert f.severity == "error"
    assert "parenthesis" in f.beginner_explanation.lower() or "closed" in f.beginner_explanation.lower()


# 2. Unused Code Category
def test_rule_unused_variable(analyzer: CodeAnalyzer) -> None:
    code = """
def compute():
    unused_var = 100
    used_var = 50
    return used_var * 2
"""
    result = analyzer.analyze(code, language="python")
    unused_findings = [f for f in result.findings if f.category == "unused code"]
    assert len(unused_findings) >= 1
    f = unused_findings[0]
    assert_normalized_finding(f, "unused code")
    assert "unused_var" in f.title or "unused_var" in f.technical_description


def test_rule_unused_import(analyzer: CodeAnalyzer) -> None:
    code = """
import math
import os

def get_cwd():
    return os.getcwd()
"""
    result = analyzer.analyze(code, language="python")
    unused_imports = [f for f in result.findings if f.category == "unused code" and "math" in f.title]
    assert len(unused_imports) >= 1
    assert_normalized_finding(unused_imports[0], "unused code")


# 3. Complexity Category
def test_rule_deep_nesting(analyzer: CodeAnalyzer) -> None:
    code = """
def deep_nested(x, y, z, w):
    if x > 0:
        for i in range(y):
            while z > 0:
                if w:
                    print("Too deep!")
"""
    result = analyzer.analyze(code, language="python")
    complexity_findings = [f for f in result.findings if f.category == "complexity"]
    assert len(complexity_findings) >= 1
    f = complexity_findings[0]
    assert_normalized_finding(f, "complexity")
    assert result.maximum_nesting_depth >= 4


# 4. Control Flow Category
def test_rule_infinite_loop(analyzer: CodeAnalyzer) -> None:
    code = """
def loop_forever():
    while True:
        print("running...")
"""
    result = analyzer.analyze(code, language="python")
    cf_findings = [f for f in result.findings if f.rule_id == "INFINITE_LOOP"]
    assert len(cf_findings) >= 1
    f = cf_findings[0]
    assert_normalized_finding(f, "control flow")
    assert "forever" in f.beginner_explanation.lower() or "infinite" in f.title.lower()


def test_rule_unreachable_code(analyzer: CodeAnalyzer) -> None:
    code = """
def check_val(x):
    if x > 0:
        return True
        print("This will never print!")
    return False
"""
    result = analyzer.analyze(code, language="python")
    unreachable = [f for f in result.findings if f.rule_id == "UNREACHABLE_CODE"]
    assert len(unreachable) >= 1
    f = unreachable[0]
    assert_normalized_finding(f, "control flow")
    assert "never be executed" in f.beginner_explanation.lower()


def test_rule_duplicate_branch(analyzer: CodeAnalyzer) -> None:
    code = """
def same_actions(val):
    if val > 10:
        do_work()
    else:
        do_work()
"""
    result = analyzer.analyze(code, language="python")
    dup_branches = [f for f in result.findings if f.rule_id == "DUPLICATE_BRANCH"]
    assert len(dup_branches) >= 1
    assert_normalized_finding(dup_branches[0], "control flow")


# 5. Return Behavior Category
def test_rule_missing_returns(analyzer: CodeAnalyzer) -> None:
    code = """
def find_item(flag, items):
    if flag:
        return items[0]
    # missing else return
"""
    result = analyzer.analyze(code, language="python")
    ret_findings = [f for f in result.findings if f.category == "return behavior"]
    assert len(ret_findings) >= 1
    f = ret_findings[0]
    assert_normalized_finding(f, "return behavior")
    assert "None" in f.beginner_explanation


# 6. Variable Usage Category
def test_rule_shadowed_builtin(analyzer: CodeAnalyzer) -> None:
    code = """
def process(list):
    str = "hello"
    return str + " world"
"""
    result = analyzer.analyze(code, language="python")
    shadowed = [f for f in result.findings if f.rule_id == "SHADOWED_BUILTIN"]
    assert len(shadowed) >= 1
    f = shadowed[0]
    assert_normalized_finding(f, "variable usage")
    assert "built-in" in f.beginner_explanation.lower()


def test_rule_self_assignment(analyzer: CodeAnalyzer) -> None:
    code = """
def refresh():
    total = 10
    total = total
    return total
"""
    result = analyzer.analyze(code, language="python")
    self_assigns = [f for f in result.findings if f.rule_id == "SELF_ASSIGNMENT"]
    assert len(self_assigns) >= 1
    assert_normalized_finding(self_assigns[0], "variable usage")


def test_rule_undefined_variable(analyzer: CodeAnalyzer) -> None:
    code = """
def do_calc():
    return undefined_val * 2
"""
    result = analyzer.analyze(code, language="python")
    undef = [f for f in result.findings if f.rule_id == "UNDEFINED_VARIABLE"]
    assert len(undef) >= 1
    f = undef[0]
    assert_normalized_finding(f, "variable usage")
    assert "never heard of" in f.beginner_explanation.lower()


# 7. Imports Category
def test_rule_wildcard_and_duplicate_import(analyzer: CodeAnalyzer) -> None:
    code = """
from math import *
import json
import json

def parse(d):
    return json.loads(d)
"""
    result = analyzer.analyze(code, language="python")
    wildcards = [f for f in result.findings if f.rule_id == "WILDCARD_IMPORT"]
    duplicates = [f for f in result.findings if f.rule_id == "DUPLICATE_IMPORT"]

    assert len(wildcards) >= 1
    assert_normalized_finding(wildcards[0], "imports")

    assert len(duplicates) >= 1
    assert_normalized_finding(duplicates[0], "imports")


# 8. Exception Handling Category
def test_rule_bare_and_silent_except(analyzer: CodeAnalyzer) -> None:
    code = """
def load_data():
    try:
        data = int("abc")
    except:
        pass
"""
    result = analyzer.analyze(code, language="python")
    bare_findings = [f for f in result.findings if f.rule_id == "BARE_EXCEPT"]
    silent_findings = [f for f in result.findings if f.rule_id == "SILENT_EXCEPTION"]

    assert len(bare_findings) >= 1
    assert_normalized_finding(bare_findings[0], "exception handling")
    assert "ctrl+c" in bare_findings[0].beginner_explanation.lower()

    assert len(silent_findings) >= 1
    assert_normalized_finding(silent_findings[0], "exception handling")
    assert "quietly" in silent_findings[0].beginner_explanation.lower() or "swallows" in silent_findings[0].beginner_explanation.lower()


# 9. Code Quality Category
def test_rule_mutable_default_arg_and_bool_compare(analyzer: CodeAnalyzer) -> None:
    code = """
def append_item(val, items=[]):
    if (val > 0) == True:
        items.append(val)
    return items
"""
    result = analyzer.analyze(code, language="python")
    mutable_args = [f for f in result.findings if f.rule_id == "MUTABLE_DEFAULT_ARG"]
    redundant_bools = [f for f in result.findings if f.rule_id == "REDUNDANT_BOOLEAN_COMPARISON"]

    assert len(mutable_args) >= 1
    assert_normalized_finding(mutable_args[0], "code quality")
    assert "persist" in mutable_args[0].beginner_explanation.lower()

    assert len(redundant_bools) >= 1
    assert_normalized_finding(redundant_bools[0], "code quality")
    assert "redundant" in redundant_bools[0].beginner_explanation.lower()


# 10. Security Category
def test_rule_eval_and_insecure_assert(analyzer: CodeAnalyzer) -> None:
    code = """
def dangerous(user_input):
    assert user_input != "", "Cannot be empty"
    api_key = "sk_live_supersecretpassword999"
    return eval(user_input)
"""
    result = analyzer.analyze(code, language="python")
    eval_findings = [f for f in result.findings if f.rule_id == "DANGEROUS_EVAL"]
    assert_findings = [f for f in result.findings if f.rule_id == "INSECURE_ASSERT"]
    secret_findings = [f for f in result.findings if f.rule_id == "HARDCODED_SECRET"]

    assert len(eval_findings) >= 1
    assert_normalized_finding(eval_findings[0], "security")
    assert eval_findings[0].severity == "error"

    assert len(assert_findings) >= 1
    assert_normalized_finding(assert_findings[0], "security")

    assert len(secret_findings) >= 1
    assert_normalized_finding(secret_findings[0], "security")


# 11. Performance Category
def test_rule_string_concat_in_loop(analyzer: CodeAnalyzer) -> None:
    code = """
def assemble_text(items):
    out_str = ""
    for item in items:
        out_str += str(item)
    return out_str
"""
    result = analyzer.analyze(code, language="python")
    concat_findings = [f for f in result.findings if f.rule_id == "INEFFICIENT_STRING_CONCAT"]
    assert len(concat_findings) >= 1
    f = concat_findings[0]
    assert_normalized_finding(f, "performance")
    assert "join" in f.suggested_fix.lower()


# Metrics & Structural Verification
def test_metrics_calculation(analyzer: CodeAnalyzer) -> None:
    code = """
# This is a sample module
import os
import sys

class DataStore:
    def __init__(self):
        self.data = []

    def add(self, x):
        if x > 0:
            self.data.append(x)
        return len(self.data)

def helper():
    return 42
"""
    result = analyzer.analyze(code, language="python")

    # Metrics validation
    assert result.cyclomatic_complexity >= 2
    assert result.function_count == 3  # __init__, add, helper
    assert result.class_count == 1
    assert result.import_count == 2
    assert result.maximum_nesting_depth >= 1

    loc = result.lines_of_code
    assert loc["total"] >= 15
    assert loc["code"] > 0
    assert loc["blank"] > 0
    assert loc["comment"] >= 1


def test_duplicate_patterns_detection(analyzer: CodeAnalyzer) -> None:
    code = """
def process():
    print("Exact duplicate step")
    print("Exact duplicate step")
    print("Exact duplicate step")
"""
    result = analyzer.analyze(code, language="python")
    assert len(result.duplicate_patterns) >= 1
    dup = result.duplicate_patterns[0]
    assert "duplicate" in dup["description"].lower() or "repeated" in dup["description"].lower()


def test_javascript_analysis_preserved(analyzer: CodeAnalyzer) -> None:
    js_code = """
function calculateDiscount(price, isMember) {
    if (price > 100) {
        return price * 0.9;
    }
}
"""
    result = analyzer.analyze(js_code, language="javascript")
    assert result.language == "javascript"
    assert result.is_valid_syntax is True
    assert result.function_count >= 1
    assert len(result.findings) >= 1
    assert any(f.category == "return behavior" for f in result.findings)
