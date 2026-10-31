"""Quiz service encapsulating quiz generation orchestration and structure validation."""

import re
from backend.core.logging import logger
from backend.schemas.quiz import QuizRequest, QuizResponse
from backend.services.llm import get_llm_service
from backend.services.llm.base import BaseLLMService


class QuizService:
    """Coordinates code quiz synthesis with the LLM provider and validates output integrity."""

    def __init__(self, llm_service: BaseLLMService | None = None):
        self.llm = llm_service or get_llm_service()

    @staticmethod
    def validate_quiz_response(response: QuizResponse, code: str) -> None:
        """Validate question count, option consistency, and line reference bounds."""
        max_lines = max(1, len(code.splitlines()))

        for q in response.questions:
            option_ids = [opt.id for opt in q.options]
            if q.correct_option_id not in option_ids:
                raise ValueError(
                    f"Question '{q.id}' has correct_option_id '{q.correct_option_id}' which is not in options."
                )

            if q.line_reference:
                nums = re.findall(r"\d+", q.line_reference)
                for num_str in nums:
                    num = int(num_str)
                    if num > max_lines or num < 1:
                        raise ValueError(
                            f"Question '{q.id}' references invalid line {num}. Max lines: {max_lines}"
                        )

        if len(response.questions) != 3:
            raise ValueError(f"Quiz must have exactly 3 questions, got {len(response.questions)}.")

    async def generate_quiz(self, request: QuizRequest) -> QuizResponse:
        """Generate multiple choice questions based on code context and validate results."""
        logger.info(f"Generating quiz for language={request.language}, locale={request.locale}")
        response = await self.llm.generate_quiz(
            code=request.code,
            language=request.language,
            explanation_context=request.explanation_context,
            locale=request.locale,
        )
        self.validate_quiz_response(response, request.code)
        return response
