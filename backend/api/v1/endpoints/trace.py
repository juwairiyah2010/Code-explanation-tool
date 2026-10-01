from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.schemas.trace import TraceRequest, TraceResponse
from backend.services.tracer_service import TracerService

router = APIRouter()

@router.post(
    "",
    response_model=TraceResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Execution Trace",
    description="Trace Python execution step-by-step in an isolated subprocess.",
)
async def create_trace(request: TraceRequest):
    tracer = TracerService()
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
