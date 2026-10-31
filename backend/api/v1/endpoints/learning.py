"""Interactive Code-Learning Workflow Endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.logging import logger
from backend.repositories.learning_repo import LearningRepository
from backend.schemas.learning import (
    ConceptMasteryItem,
    LearningEvaluationResponse,
    LearningMaterialResponse,
    SubmitAnswersRequest,
)
from backend.schemas.quiz import QuizRequest
from backend.services.learning_service import LearningService

router = APIRouter()


def get_learning_service() -> LearningService:
    return LearningService()


@router.post(
    "/material",
    response_model=LearningMaterialResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Interactive Code-Learning Workflow Material",
    description="Analyzes code deterministically and generates key concepts, beginner explanation, execution walkthrough, common mistakes, 5 grounded questions (3 comprehension, 1 debugging, 1 predict output), and final takeaway.",
)
async def generate_learning_material(
    request: QuizRequest,
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningMaterialResponse:
    try:
        return await learning_service.generate_learning_material(
            code=request.code,
            language=request.language,
            explanation_context=request.explanation_context,
            locale=request.locale,
        )
    except Exception as e:
        logger.error(f"Error generating learning material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate learning material: {str(e)}",
        )


@router.post(
    "/submit",
    response_model=LearningEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Answers and Update Learner Progress",
    description="Deterministically grades questions, calculates score, updates concept mastery, and tracks attempts.",
)
async def submit_learning_answers(
    request: SubmitAnswersRequest,
    learning_service: LearningService = Depends(get_learning_service),
    db: Session = Depends(get_db),
) -> LearningEvaluationResponse:
    try:
        repo = LearningRepository(db)

        # If questions_payload is provided, evaluate directly; otherwise regenerate deterministic questions
        questions = request.questions_payload
        if not questions:
            mat = await learning_service.generate_learning_material(
                code=request.code, language=request.language
            )
            questions = [q.model_dump() for q in mat.questions]

        return repo.evaluate_and_record_attempt(
            questions=questions,
            answers=request.answers,
            language=request.language,
            user_id=request.user_id,
        )
    except Exception as e:
        logger.error(f"Error evaluating learning answers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate answers: {str(e)}",
        )


@router.get(
    "/progress",
    response_model=list[ConceptMasteryItem],
    status_code=status.HTTP_200_OK,
    summary="Get Learner Progress Model",
    description="Returns current deterministic concept mastery percentages (e.g., Loops: 70%, Functions: 40%).",
)
def get_learner_progress(
    user_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[ConceptMasteryItem]:
    try:
        repo = LearningRepository(db)
        return repo.get_learner_progress(user_id=user_id)
    except Exception as e:
        logger.error(f"Error loading learner progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load learner progress: {str(e)}",
        )
