"""Code explanation and history endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.schemas.explanation import (
    ExplainCodeRequest,
    ExplainCodeResponse,
)
from backend.services.explanation_service import ExplanationService

router = APIRouter()


@router.post("/explain", response_model=ExplainCodeResponse, tags=["Code Explanation"])
async def explain_code(
    request: ExplainCodeRequest,
    db: Session = Depends(get_db),
) -> ExplainCodeResponse:
    """Generate structured AI explanation for Python or JavaScript code snippets."""
    try:
        service = ExplanationService(db)
        return await service.explain_code(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation generation failed: {str(e)}",
        )
