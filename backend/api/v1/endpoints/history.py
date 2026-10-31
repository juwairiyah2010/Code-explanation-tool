"""Submission history endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from backend.api.deps import get_history_service
from backend.schemas.history import HistorySummaryItem, HistoryDetailResponse
from backend.services.history_service import HistoryService

router = APIRouter()


@router.get(
    "",
    response_model=list[HistorySummaryItem],
    status_code=status.HTTP_200_OK,
    summary="Get submission history",
)
def get_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    history_service: HistoryService = Depends(get_history_service),
) -> list[HistorySummaryItem]:
    """Retrieve paginated submission history."""
    return history_service.list_history(limit=limit, offset=offset)


@router.get(
    "/{record_id}",
    response_model=HistoryDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get submission by ID",
)
def get_history_item(
    record_id: int,
    history_service: HistoryService = Depends(get_history_service),
) -> HistoryDetailResponse:
    """Retrieve detailed historical explanation record by ID."""
    record = history_service.get_history_detail(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {record_id} not found",
        )
    return record
