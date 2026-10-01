"""AST and static code analysis endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.schemas.explanation import CodeAnalysisRequest, CodeAnalysisResponse
from backend.services.explanation_service import ExplanationService

router = APIRouter()


@router.post("/ast/analyze", response_model=CodeAnalysisResponse, tags=["AST Analysis"])
def analyze_ast(
    request: CodeAnalysisRequest,
    db: Session = Depends(get_db),
) -> CodeAnalysisResponse:
    """Analyze source code syntax, extract constructs, detect language, check static rules, and split blocks."""
    try:
        service = ExplanationService(db)
        return service.analyze_code_ast(
            code=request.code,
            language=request.language,
            filename=request.filename,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AST Analysis failed: {str(e)}",
        )
