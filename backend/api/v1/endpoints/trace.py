"""Execution tracing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.api.deps import get_tracer_service
from backend.core.security import rate_limit_expensive, sanitize_internal_error
from backend.schemas.trace import TraceRequest, TraceResponse
from backend.services.tracer_service import TracerService

router = APIRouter()


@router.post(
    "",
    response_model=TraceResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Execution Trace",
    description="Trace Python execution step-by-step in an isolated subprocess.",
    dependencies=[Depends(rate_limit_expensive)],
)
async def create_trace(
    request: TraceRequest,
    tracer: TracerService = Depends(get_tracer_service),
) -> TraceResponse:
    """Trace code execution and capture variable frames."""
    try:
        response = await tracer.trace_code(request)
        if not response.success:
            if "Timeout" in str(response.error) or "timed out" in str(response.error):
                raise HTTPException(status_code=408, detail=response.error)
            raise HTTPException(status_code=400, detail=response.error)
        return response
    except HTTPException:
        raise
    except Exception as e:
        detail = sanitize_internal_error(e, context_msg="Execution trace failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
