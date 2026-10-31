"""Unit and integration tests for the Interactive Code-Learning Workflow and Learner Progress Model."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.learning_service import LearningService
from backend.schemas.learning import LearningMaterialResponse

from backend.core.database import init_db

init_db()
client = TestClient(app)

SAMPLE_CODE = """def count_positive(numbers: list[int]) -> int:
    total = 0
    for n in numbers:
        if n > 0:
            total += 1
    return total

res = count_positive([1, -2, 3, -4, 5])
print(res)
"""


@pytest.mark.asyncio
async def test_learning_material_generation_eight_items():
    service = LearningService()
    mat = await service.generate_learning_material(code=SAMPLE_CODE, language="python")

    assert isinstance(mat, LearningMaterialResponse)

    # 1. Key Concepts
    assert len(mat.key_concepts) >= 1
    concept_names = [kc.name for kc in mat.key_concepts]
    assert any(c in ["Functions", "Loops", "Conditionals"] for c in concept_names)
    for kc in mat.key_concepts:
        assert kc.description is not None
        assert len(kc.referenced_lines) > 0

    # 2. Beginner Explanation
    assert mat.beginner_explanation is not None
    assert len(mat.beginner_explanation) > 10

    # 3. Execution Walkthrough
    assert len(mat.execution_walkthrough) >= 2
    assert any("Step" in s for s in mat.execution_walkthrough)

    # 4. Common Mistakes
    assert len(mat.common_mistakes) >= 2

    # 5. Three Comprehension Questions
    assert len(mat.comprehension_questions) == 3
    for q in mat.comprehension_questions:
        assert q.question_type == "comprehension"
        assert len(q.options) >= 2
        assert q.correct_answer in [opt.id for opt in q.options]
        assert q.explanation is not None
        assert len(q.referenced_lines) > 0
        assert q.concept is not None
        assert q.difficulty in ["Beginner", "Intermediate", "Advanced"]

    # 6. One Debugging Question
    assert mat.debugging_question is not None
    assert mat.debugging_question.question_type == "debugging"
    assert len(mat.debugging_question.options) >= 2
    assert mat.debugging_question.correct_answer in [opt.id for opt in mat.debugging_question.options]

    # 7. One Predict the Output Question
    assert mat.predict_output_question is not None
    assert mat.predict_output_question.question_type == "predict_output"
    assert len(mat.predict_output_question.options) >= 2
    assert mat.predict_output_question.correct_answer in [opt.id for opt in mat.predict_output_question.options]

    # 8. Final Takeaway
    assert mat.final_takeaway is not None
    assert len(mat.final_takeaway) > 10

    # Aggregated Questions count is 5
    assert len(mat.questions) == 5


def test_question_line_grounding_integrity():
    service = LearningService()
    total_lines = len(SAMPLE_CODE.splitlines())
    mat = service.synthesize_deterministic_material(code=SAMPLE_CODE, language="python", ast_result=None)

    for q in mat.questions:
        for line_num in q.referenced_lines:
            assert 1 <= line_num <= total_lines


def test_learning_material_api_endpoint():
    res = client.post(
        "/api/v1/learning/material",
        json={"code": SAMPLE_CODE, "language": "python", "locale": "en"},
    )
    assert res.status_code == 200
    data = res.json()

    assert "key_concepts" in data
    assert "beginner_explanation" in data
    assert "execution_walkthrough" in data
    assert "common_mistakes" in data
    assert "comprehension_questions" in data
    assert "debugging_question" in data
    assert "predict_output_question" in data
    assert "final_takeaway" in data
    assert len(data["questions"]) == 5


def test_deterministic_scoring_and_progress_tracking():
    # 1. Fetch material to obtain question IDs and correct answers
    mat_res = client.post(
        "/api/v1/learning/material",
        json={"code": SAMPLE_CODE, "language": "python", "locale": "en"},
    )
    assert mat_res.status_code == 200
    questions = mat_res.json()["questions"]
    assert len(questions) == 5

    # 2. Submit partial answers: 3 correct, 2 incorrect
    answers = {}
    for i, q in enumerate(questions):
        correct_id = q["correct_answer"]
        if i < 3:
            answers[q["id"]] = correct_id  # Correct
        else:
            # Pick a wrong option
            wrong_opt = next(opt["id"] for opt in q["options"] if opt["id"] != correct_id)
            answers[q["id"]] = wrong_opt

    sub_res = client.post(
        "/api/v1/learning/submit",
        json={
            "code": SAMPLE_CODE,
            "language": "python",
            "answers": answers,
            "questions_payload": questions,
        },
    )
    assert sub_res.status_code == 200
    eval_data = sub_res.json()

    # Track: score, attempts, incorrect concepts, completion status
    assert eval_data["total_questions"] == 5
    assert eval_data["correct_count"] == 3
    assert eval_data["score"] == 60.0  # 3/5 = 60.0%
    assert eval_data["attempts"] >= 1
    assert eval_data["completion_status"] == "completed"
    assert len(eval_data["incorrect_concepts"]) >= 1

    # Check Learner Progress Model (Concept Mastery)
    progress = eval_data["concept_mastery"]
    assert len(progress) > 0
    for p in progress:
        assert "concept" in p
        assert "mastery" in p
        assert 0.0 <= p["mastery"] <= 100.0


def test_learner_progress_endpoint():
    res = client.get("/api/v1/learning/progress")
    assert res.status_code == 200
    progress = res.json()
    assert isinstance(progress, list)


def test_quiz_endpoint_backward_compatibility():
    # Existing standard quiz endpoint must continue working with 3 questions
    res = client.post(
        "/api/v1/quiz",
        json={"code": SAMPLE_CODE, "language": "python", "locale": "en", "workflow": "standard"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["questions"]) == 3
    assert "key_concepts" in data
    assert "beginner_explanation" in data
    assert "final_takeaway" in data
