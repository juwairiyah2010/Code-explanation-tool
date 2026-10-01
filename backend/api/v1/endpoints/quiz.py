from fastapi import APIRouter, HTTPException, status
from backend.schemas.quiz import QuizRequest, QuizResponse
from backend.services.llm import get_llm_service
from backend.core.logging import logger
import re

router = APIRouter()

def validate_quiz_response(response: QuizResponse, code: str):
    max_lines = len(code.splitlines())
    
    for q in response.questions:
        # Check that correct option exists
        option_ids = [opt.id for opt in q.options]
        if q.correct_option_id not in option_ids:
            raise ValueError(f"Question '{q.id}' has correct_option_id '{q.correct_option_id}' which is not in options.")
            
        # Check line references if provided
        if q.line_reference:
            # We can extract numbers and ensure they are <= max_lines
            nums = re.findall(r'\d+', q.line_reference)
            for num_str in nums:
                num = int(num_str)
                if num > max_lines or num < 1:
                    raise ValueError(f"Question '{q.id}' references invalid line {num}. Max lines: {max_lines}")
                    
    # Also ensure exactly 3 questions
    if len(response.questions) != 3:
        raise ValueError(f"Quiz must have exactly 3 questions, got {len(response.questions)}.")

@router.post(
    "",
    response_model=QuizResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Code Quiz",
    description="Generate a multiple-choice quiz based on code and explanation.",
)
async def generate_quiz(request: QuizRequest):
    llm = get_llm_service()
    
    try:
        response = await llm.generate_quiz(
            code=request.code,
            language=request.language,
            explanation_context=request.explanation_context,
            locale=request.locale,
        )
        
        # Validate the generated quiz
        validate_quiz_response(response, request.code)
        return response
        
    except ValueError as e:
        logger.error(f"Quiz validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Generated quiz failed validation: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error generating quiz: {str(e)}"
        )
