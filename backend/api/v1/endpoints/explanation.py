"""Code explanation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.api.deps import get_explanation_service
from backend.core.security import rate_limit_expensive, sanitize_internal_error
from backend.schemas.explanation import ExplainCodeRequest, ExplainCodeResponse
from backend.services.explanation_service import ExplanationService

router = APIRouter()


@router.post(
    "/explain",
    response_model=ExplainCodeResponse,
    tags=["Code Explanation"],
    dependencies=[Depends(rate_limit_expensive)],
)
async def explain_code(
    request: ExplainCodeRequest,
    service: ExplanationService = Depends(get_explanation_service),
) -> ExplainCodeResponse:
    """Generate structured AI explanation for Python or JavaScript code snippets."""
    try:
        return await service.explain_code(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        detail = sanitize_internal_error(e, context_msg="Explanation generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
