import pytest
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

