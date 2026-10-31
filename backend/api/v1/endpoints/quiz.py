from fastapi import APIRouter, Depends, HTTPException, status
from backend.core.logging import logger
from backend.core.security import rate_limit_expensive, sanitize_internal_error
from backend.schemas.quiz import QuizRequest, QuizResponse
from backend.services.llm import get_llm_service
from backend.services.quiz_service import QuizService

router = APIRouter()


def get_current_quiz_service() -> QuizService:
    """Dependency provider resolving QuizService with current LLM service."""
    return QuizService(llm_service=get_llm_service())


@router.post(
    "",
    response_model=QuizResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Code Quiz",
    description="Generate a multiple-choice quiz based on code and explanation.",
    dependencies=[Depends(rate_limit_expensive)],
)
async def generate_quiz(
    request: QuizRequest,
    quiz_service: QuizService = Depends(get_current_quiz_service),
) -> QuizResponse:
    """Generate and validate a 3-question multiple choice quiz for code comprehension."""
    try:
        return await quiz_service.generate_quiz(request)
    except ValueError as e:
        logger.error(f"Quiz validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Generated quiz failed validation: {str(e)}",
        )
    except Exception as e:
        detail = sanitize_internal_error(e, context_msg="Internal error generating quiz")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
