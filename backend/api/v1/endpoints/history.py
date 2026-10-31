"""Submission history endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.api.deps import get_current_user, get_history_service
from backend.models.persistence import User
from backend.schemas.history import HistoryDetailResponse, HistorySummaryItem
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
    current_user: User = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> list[HistorySummaryItem]:
    """Retrieve paginated submission history for the authenticated user."""
    return history_service.list_history(limit=limit, offset=offset, user_id=current_user.id)


@router.get(
    "/{record_id}",
    response_model=HistoryDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get submission by ID",
)
def get_history_item(
    record_id: int,
    current_user: User = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service),
) -> HistoryDetailResponse:
    """Retrieve detailed historical explanation record by ID for the authenticated user."""
    record = history_service.get_history_detail(record_id, user_id=current_user.id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {record_id} not found",
        )
    return record

