from backend.services.tracer_runner import run_trace
from tests.fixtures import (
    PYTHON_BASIC_MATH,
    PYTHON_NESTED_FUNCTIONS,
    PYTHON_RECURSION,
)


def test_trace_variable_assignments():
    """Verify trace steps capture line execution and changed variable diffs."""
    res = run_trace(PYTHON_BASIC_MATH)
    assert res["success"] is True
    assert len(res["steps"]) >= 4
    all_assigned_vars = set()
    for s in res["steps"]:
        all_assigned_vars.update(s.get("changed_variables", {}).keys())
    assert "total" in all_assigned_vars
    assert "Total: 12" in res["output"]


def test_trace_nested_functions():
    """Verify trace captures call depth and frame entries for nested functions."""
    res = run_trace(PYTHON_NESTED_FUNCTIONS)
    assert res["success"] is True
    call_steps = [s for s in res["steps"] if s["event_type"] == "call"]
    assert len(call_steps) >= 2  # make_multiplier and multiply calls
    func_names = [s["function_name"] for s in call_steps]
    assert "multiply" in func_names


def test_trace_recursion():
    """Verify recursive calls increase call depth and record return values."""
    res = run_trace(PYTHON_RECURSION)
    assert res["success"] is True
    max_call_depth = max(s.get("call_depth", 0) for s in res["steps"])
    assert max_call_depth >= 3
    assert "Factorial 4 is 24" in res["output"]


def test_trace_step_limit():
    """Verify runaway loops are cut off at MAX_STEPS with a helpful error."""
    code = """count = 0
while True:
    count += 1
"""
    res = run_trace(code)
    assert res["success"] is False
    assert "step limit" in res["error"].lower()
