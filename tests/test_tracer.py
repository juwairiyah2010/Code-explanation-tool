from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_trace_simple_python():
    code = """
x = 5
y = 10
print("Hello")
z = x + y
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["language"] == "python"
    
    steps = data["steps"]
    assert len(steps) >= 4
    
    # First step should assign x
    
    # x will be populated in subsequent steps after it's assigned
    x_found = any(s.get("variables", {}).get("x") == "5" for s in steps)
    assert x_found, "x = 5 not found in any step's variables"
    
    # The step executing print should capture "Hello\n"
    # Wait, the output might appear in the print step or the step after it.
    output_found = any(s.get("output") == "Hello\n" for s in steps)
    assert output_found, f"Output not found in steps: {steps}"

def test_trace_loop():
    code = """
for i in range(3):
    pass
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    steps = data["steps"]
    # range(3) loop will execute `for` line 4 times and `pass` 3 times
    assert len(steps) >= 6

def test_trace_timeout():
    code = """
while True:
    pass
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    # the endpoint should catch timeout and return 400 or 408
    assert response.status_code in (400, 408)
    data = response.json()
    assert "Execution failed" in data["detail"] or "timed out" in data["detail"].lower()

def test_trace_syntax_error():
    code = """
def invalid syntax
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    # A syntax error in trace code should return 400 with the error message
    assert response.status_code == 400
    data = response.json()
    assert "SyntaxError" in data["detail"]

def test_trace_runtime_error():
    code = """
x = 1 / 0
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    # The trace runner should capture runtime exception and return it in the trace response
    # wait, the API returns 400 on trace failure right now.
    assert response.status_code == 400
    data = response.json()
    assert "ZeroDivisionError" in data["detail"]

def test_trace_with_input():
    code = """
name = input()
print("Hello", name)
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python", "input_data": "Alice\\n"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    output_found = any("Hello Alice" in (s.get("output") or "") for s in data["steps"])
    assert output_found

def test_trace_unsupported_language():
    code = "let x = 1;"
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "javascript"}
    )
    assert response.status_code == 400
    assert "only supported for Python" in response.json()["detail"]

def test_generate_flowchart():
    code = """
if True:
    x = 1
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python", "generate_flowchart": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["flowchart"] is not None
    assert "graph TD" in data["flowchart"]

def test_trace_sandbox_blocks_file_access():
    code = "f = open('.env', 'r')\ncontent = f.read()"
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 400
    assert "NameError" in response.json()["detail"] or "open" in response.json()["detail"]

def test_trace_sandbox_blocks_import():
    code = "import os\nos.system('echo test')"
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 400
    assert "ImportError" in response.json()["detail"] or "__import__" in response.json()["detail"]


def test_trace_variable_updates():
    code = """
a = 10
a = 20
a = a + 5
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Check changed_variables across steps
    diffs = [s.get("changed_variables", {}) for s in data["steps"]]
    assert any(d.get("a") == "10" for d in diffs)
    assert any(d.get("a") == "20" for d in diffs)
    assert any(d.get("a") == "25" for d in diffs)


def test_trace_nested_functions():
    code = """
def outer(x):
    def inner(y):
        return y * 2
    return inner(x) + 1

res = outer(3)
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    steps = data["steps"]
    # Check that call_depth reached at least 2
    max_depth = max(s.get("call_depth", 0) for s in steps)
    assert max_depth >= 2

    # Check function names captured
    funcs = {s.get("function_name") for s in steps}
    assert "outer" in funcs
    assert "inner" in funcs

    # Final state should include res = 7
    assert data["final_state"].get("res") == "7"


def test_trace_recursion():
    code = """
def fact(n):
    if n <= 1:
        return 1
    return n * fact(n - 1)

r = fact(3)
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    steps = data["steps"]
    fact_calls = [s for s in steps if s.get("event_type") == "call" and s.get("function_name") == "fact"]
    assert len(fact_calls) == 3

    # Call depths for recursive calls should increase
    depths = [c.get("call_depth", 0) for c in fact_calls]
    assert depths == [1, 2, 3]

    assert data["final_state"].get("r") == "6"


def test_trace_conditionals():
    code = """
x = 10
if x > 5:
    branch = "greater"
else:
    branch = "lesser"
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # "greater" should be recorded in final state, not "lesser"
    assert data["final_state"].get("branch") == "'greater'"


def test_trace_exceptions_captured():
    code = """
try:
    int("not_a_number")
except ValueError as e:
    handled = True
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Check that exception event was captured
    exc_steps = [s for s in data["steps"] if s.get("event_type") == "exception"]
    assert len(exc_steps) >= 1
    assert "ValueError" in (exc_steps[0].get("exception") or "")
    assert data["final_state"].get("handled") == "True"


def test_trace_print_statements():
    code = """
print("Alpha")
print("Beta")
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Alpha\n" in data["output"]
    assert "Beta\n" in data["output"]


def test_trace_step_limit_protection():
    code = """
for i in range(1200):
    x = i
"""
    response = client.post(
        "/api/v1/trace",
        json={"code": code, "language": "python"}
    )
    # Exceeding step limit marks trace as failed and returns 400
    assert response.status_code == 400
    assert "step limit exceeded" in response.json()["detail"].lower()


