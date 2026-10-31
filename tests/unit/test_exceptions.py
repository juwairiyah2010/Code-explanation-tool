from backend.services.tracer_runner import run_trace
from tests.fixtures import (
    PYTHON_ZERO_DIVISION,
    PYTHON_INDEX_ERROR,
    PYTHON_CUSTOM_EXCEPTION,
    PYTHON_SYNTAX_ERROR,
)


def test_capture_zero_division_exception():
    """Verify runtime ZeroDivisionError is captured with line and description."""
    res = run_trace(PYTHON_ZERO_DIVISION)
    assert res["success"] is False
    assert "ZeroDivisionError" in (res["error"] or "")
    exception_steps = [s for s in res["steps"] if s.get("event_type") == "exception"]
    assert len(exception_steps) >= 1
    assert "ZeroDivisionError" in str(exception_steps[0].get("exception"))


def test_capture_index_error_exception():
    """Verify runtime IndexError is captured cleanly."""
    res = run_trace(PYTHON_INDEX_ERROR)
    assert res["success"] is False
    assert "IndexError" in (res["error"] or "")


def test_capture_custom_exception():
    """Verify user-defined custom exceptions are caught and reported without crashing host."""
    res = run_trace(PYTHON_CUSTOM_EXCEPTION)
    assert res["success"] is False
    assert "InvalidAgeError" in (res["error"] or "")


def test_capture_syntax_error():
    """Verify syntax error is caught at compile time before execution starts."""
    res = run_trace(PYTHON_SYNTAX_ERROR)
    assert res["success"] is False
    assert "SyntaxError" in (res["error"] or "")
    assert len(res["steps"]) == 0
