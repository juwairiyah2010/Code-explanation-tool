"""Unit tests for quiz synthesis, interactive learning material, and deterministic scoring."""

import pytest
from backend.services.quiz_service import QuizService
from backend.services.learning_service import LearningService
from backend.services.llm.mock_llm import MockLLMService
from backend.schemas.quiz import QuizRequest
from tests.fixtures import PYTHON_BASIC_MATH


@pytest.fixture
def quiz_service() -> QuizService:
    return QuizService(llm_service=MockLLMService())


@pytest.fixture
def learning_service() -> LearningService:
    return LearningService(llm_service=MockLLMService())


@pytest.mark.asyncio
async def test_generate_standard_quiz(quiz_service: QuizService):
    """Generates standard 3-question comprehension quiz with valid options and line bounds."""
    req = QuizRequest(code=PYTHON_BASIC_MATH, language="python")
    res = await quiz_service.generate_quiz(req)
    assert len(res.questions) == 3
    for q in res.questions:
        assert len(q.options) >= 2
        opt_ids = [opt.id for opt in q.options]
        assert q.correct_option_id in opt_ids


@pytest.mark.asyncio
async def test_generate_learning_material_eight_items(learning_service: LearningService):
    """Generates complete 8-item interactive learning material grounded in code."""
    res = await learning_service.generate_learning_material(
        code=PYTHON_BASIC_MATH,
        language="python",
    )
    # Check 8 core components
    assert len(res.key_concepts) >= 1
    assert len(res.beginner_explanation) > 0
    assert len(res.execution_walkthrough) >= 1
    assert len(res.common_mistakes) >= 1
    assert len(res.comprehension_questions) == 3
    assert res.debugging_question is not None
    assert res.predict_output_question is not None
    assert len(res.final_takeaway) > 0
    assert len(res.questions) == 5


def test_deterministic_scoring_and_mastery(learning_service: LearningService):
    """Grades answers deterministically and updates concept mastery percentages."""
    import uuid
    test_user_id = (uuid.uuid4().int % 900000) + 100000
    answers = {"q1": "A", "q2": "B"}
    questions = [
        {"id": "q1", "correct_answer": "A", "concept": "Functions"},
        {"id": "q2", "correct_answer": "C", "concept": "Functions"},
    ]
    eval_res = learning_service.evaluate_answers(
        answers=answers,
        questions_payload=questions,
        user_id=test_user_id,
    )
    assert eval_res.total_questions == 2
    assert eval_res.correct_count == 1
    assert eval_res.score == 50.0
    func_mastery = next((m for m in eval_res.concept_mastery if m.concept == "Functions"), None)
    assert func_mastery is not None
    assert func_mastery.mastery == 50.0
