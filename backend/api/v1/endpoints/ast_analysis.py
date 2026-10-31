"""AST and static code analysis endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.api.deps import get_code_analyzer
from backend.schemas.explanation import CodeAnalysisRequest, CodeAnalysisResponse
from backend.services.analysis.code_analyzer import CodeAnalyzer

router = APIRouter()


@router.post("/ast/analyze", response_model=CodeAnalysisResponse, tags=["AST Analysis"])
def analyze_ast(
    request: CodeAnalysisRequest,
    analyzer: CodeAnalyzer = Depends(get_code_analyzer),
) -> CodeAnalysisResponse:
    """Analyze source code syntax, extract constructs, detect language, check static rules, and calculate metrics."""
    try:
        return analyzer.analyze(
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
