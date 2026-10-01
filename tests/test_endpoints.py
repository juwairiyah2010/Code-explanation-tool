"""Tests for API v1 AST analysis, explanation, and history endpoints."""

from fastapi.testclient import TestClient


def test_ast_analyze_endpoint(client: TestClient) -> None:
    code = "def greet(name: str):\n    return f'Hello, {name}'"
    response = client.post(
        "/api/v1/ast/analyze",
        json={"code": code, "language": "python"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "python"
    assert data["is_valid_syntax"] is True
    assert len(data["functions"]) == 1
    assert data["functions"][0]["name"] == "greet"


def test_explain_endpoint(client: TestClient) -> None:
    code = "def is_even(n: int) -> bool:\n    return n % 2 == 0"
    response = client.post(
        "/api/v1/explain",
        json={
            "code": code,
            "language": "python",
            "level": "Beginner",
            "include_ast_analysis": True,
            "save_history": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["language"] == "python"
    assert data["level"] == "Beginner"
    assert "summary" in data
    assert "blocks" in data
    assert "concepts" in data
    assert "algorithm_steps" in data
    assert "complexity" in data
    assert "hints" in data
    assert data["ast_analysis"] is not None


def test_history_endpoints(client: TestClient) -> None:
    # First create an explanation
    client.post(
        "/api/v1/explain",
        json={
            "code": "const x = 42;",
            "language": "javascript",
            "level": "Intermediate",
            "save_history": True,
        },
    )

    # List history
    history_res = client.get("/api/v1/history")
    assert history_res.status_code == 200
    items = history_res.json()
    assert len(items) >= 1

    item_id = items[0]["id"]
    # Get by ID
    item_res = client.get(f"/api/v1/history/{item_id}")
    assert item_res.status_code == 200
    assert item_res.json()["id"] == item_id


def test_history_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/history/999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_explain_empty_code_validation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/explain",
        json={"code": "   \n\t  ", "language": "python", "level": "Intermediate"},
    )
    assert response.status_code == 422


def test_explain_invalid_language(client: TestClient) -> None:
    response = client.post(
        "/api/v1/explain",
        json={"code": "print(1)", "language": "ruby", "level": "Intermediate"},
    )
    assert response.status_code == 422

