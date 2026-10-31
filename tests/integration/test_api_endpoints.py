from fastapi.testclient import TestClient
from tests.fixtures import (
    PYTHON_BASIC_MATH,
    JAVASCRIPT_BASIC_MATH,
    PYTHON_SYNTAX_ERROR,
)


def test_health_endpoint(client: TestClient):
    """GET /api/v1/health verifies system readiness."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "python" in data["supported_languages"]


def test_ast_analysis_endpoint(client: TestClient):
    """POST /api/v1/ast/analyze processes Python and JavaScript syntax trees."""
    # Python
    py_res = client.post("/api/v1/ast/analyze", json={"code": PYTHON_BASIC_MATH, "language": "python"})
    assert py_res.status_code == 200
    assert py_res.json()["is_valid_syntax"] is True
    assert len(py_res.json()["functions"]) == 1

    # JavaScript
    js_res = client.post("/api/v1/ast/analyze", json={"code": JAVASCRIPT_BASIC_MATH, "language": "javascript"})
    assert js_res.status_code == 200
    assert js_res.json()["is_valid_syntax"] is True

    # Syntax Error
    err_res = client.post("/api/v1/ast/analyze", json={"code": PYTHON_SYNTAX_ERROR, "language": "python"})
    assert err_res.status_code == 200
    assert err_res.json()["is_valid_syntax"] is False


def test_explain_endpoint_integration(client: TestClient):
    """POST /api/v1/explain runs full pipeline with mock LLM and grounding validation."""
    payload = {
        "code": PYTHON_BASIC_MATH,
        "language": "python",
        "level": "Beginner",
        "mode": "beginner",
        "enable_trace": True,
        "enable_rag": False,
    }
    res = client.post("/api/v1/explain", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert len(data["summary"]) > 0
    assert "complexity" in data
    assert data.get("validation_result") is not None


def test_trace_endpoint_integration(client: TestClient):
    """POST /api/v1/trace executes code in subprocess and returns execution steps."""
    res = client.post("/api/v1/trace", json={"code": PYTHON_BASIC_MATH, "language": "python"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["steps"]) >= 4


def test_learning_material_and_submit_integration(client: TestClient):
    """POST /api/v1/learning/material and /api/v1/learning/submit workflow."""
    # 1. Generate learning material
    mat_res = client.post(
        "/api/v1/learning/material",
        json={"code": PYTHON_BASIC_MATH, "language": "python"},
    )
    assert mat_res.status_code == 200
    material = mat_res.json()
    assert len(material["questions"]) == 5
    assert len(material["key_concepts"]) >= 1

    # 2. Submit answers
    sub_payload = {
        "code": PYTHON_BASIC_MATH,
        "language": "python",
        "answers": {q["id"]: q["correct_answer"] for q in material["questions"]},
        "questions_payload": material["questions"],
        "user_id": 101,
    }
    submit_res = client.post("/api/v1/learning/submit", json=sub_payload)
    assert submit_res.status_code == 200
    eval_data = submit_res.json()
    assert eval_data["score"] == 100.0
    assert eval_data["correct_count"] == 5

    # 3. Retrieve progress
    prog_res = client.get("/api/v1/learning/progress?user_id=101")
    assert prog_res.status_code == 200
    assert len(prog_res.json()) >= 1


def test_auth_endpoints_integration(client: TestClient):
    """POST /api/v1/auth/signup and /api/v1/auth/login integration flow."""
    # 1. Signup
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"username": "integration_user", "password": "SecurePassword123!"},
    )
    assert signup_res.status_code == 200
    assert signup_res.json()["username"] == "integration_user"
    assert "token" in signup_res.json()
    token = signup_res.json()["token"]
    assert token is not None

    # 2. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "integration_user", "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["username"] == "integration_user"
    assert login_res.json()["token"] is not None

    # 3. Authenticated profile endpoint /me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "integration_user"

    # 4. Unauthenticated /me rejected
    assert client.get("/api/v1/auth/me").status_code == 401

    # 5. Invalid Login
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"username": "integration_user", "password": "wrongPassword"},
    )
    assert bad_login.status_code == 400



def test_rag_endpoints_integration(client: TestClient):
    """GET /api/v1/rag/stats and POST /api/v1/rag/retrieve."""
    stats_res = client.get("/api/v1/rag/stats")
    assert stats_res.status_code == 200
    assert "chunks" in stats_res.json()

    retrieve_res = client.post(
        "/api/v1/rag/retrieve",
        json={"query": "python functions", "language": "python", "top_k": 2},
    )
    assert retrieve_res.status_code == 200
    assert "results" in retrieve_res.json()
