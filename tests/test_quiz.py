import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.schemas.quiz import QuizResponse, QuizQuestion, QuizOption, GlossaryTerm, CodeImprovement
from backend.services.llm.base import BaseLLMService

client = TestClient(app)

class MalformedQuizLLM(BaseLLMService):
    async def generate_explanation(self, *args, **kwargs):
        pass
    async def generate_quiz(self, code, language, explanation_context=None, locale="en"):
        raise ValueError("Malformed AI Response")

class InvalidOptionQuizLLM(BaseLLMService):
    async def generate_explanation(self, *args, **kwargs):
        pass
    async def generate_quiz(self, code, language, explanation_context=None, locale="en"):
        # Returns a question where correct_option_id is not in options
        q1 = QuizQuestion(
            id="q1", text="T?", options=[QuizOption(id="o1", text="A")], correct_option_id="o99", explanation="E", line_reference="1"
        )
        return QuizResponse(questions=[q1, q1, q1], glossary=[], common_mistakes=[])

class InvalidLineQuizLLM(BaseLLMService):
    async def generate_explanation(self, *args, **kwargs):
        pass
    async def generate_quiz(self, code, language, explanation_context=None, locale="en"):
        # Returns a line reference that exceeds the code length
        q1 = QuizQuestion(
            id="q1", text="T?", options=[QuizOption(id="o1", text="A")], correct_option_id="o1", explanation="E", line_reference="99"
        )
        return QuizResponse(questions=[q1, q1, q1], glossary=[], common_mistakes=[])

def test_quiz_success():
    # Use the default MockLLMService
    code = "def foo():\n    pass\n\n\n\n\n\n\n\n\n\n"
    response = client.post(
        "/api/v1/quiz",
        json={"code": code, "language": "python", "locale": "en"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["questions"]) == 3
    assert data["questions"][0]["text"] == "What is the purpose of this code?"
    
    # Test hindi locale
    response_hi = client.post(
        "/api/v1/quiz",
        json={"code": code, "language": "python", "locale": "hi"}
    )
    assert response_hi.status_code == 200
    data_hi = response_hi.json()
    assert "उद्देश्य" in data_hi["questions"][0]["text"]

def test_quiz_invalid_option(monkeypatch):
    import backend.api.v1.endpoints.quiz
    monkeypatch.setattr(backend.api.v1.endpoints.quiz, "get_llm_service", lambda: InvalidOptionQuizLLM())
    
    code = "x = 1"
    response = client.post(
        "/api/v1/quiz",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 422
    assert "which is not in options" in response.json()["detail"]

def test_quiz_invalid_line(monkeypatch):
    import backend.api.v1.endpoints.quiz
    monkeypatch.setattr(backend.api.v1.endpoints.quiz, "get_llm_service", lambda: InvalidLineQuizLLM())
    
    code = "x = 1"
    response = client.post(
        "/api/v1/quiz",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 422
    assert "references invalid line 99" in response.json()["detail"]

def test_quiz_malformed_response(monkeypatch):
    import backend.api.v1.endpoints.quiz
    monkeypatch.setattr(backend.api.v1.endpoints.quiz, "get_llm_service", lambda: MalformedQuizLLM())
    
    code = "x = 1"
    response = client.post(
        "/api/v1/quiz",
        json={"code": code, "language": "python"}
    )
    assert response.status_code == 422
    assert "Malformed AI Response" in response.json()["detail"]
