"""Concept definitions lookup endpoint."""

from fastapi import APIRouter, Depends, Query, status
from backend.api.deps import get_history_service
from backend.schemas.history import ConceptLookupResponse
from backend.services.history_service import HistoryService

router = APIRouter()


@router.get(
    "/{name}",
    response_model=ConceptLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get concept by name",
)
def get_concept(
    name: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    history_service: HistoryService = Depends(get_history_service),
) -> ConceptLookupResponse:
    """Retrieve historical concept definitions matching a name."""
    return history_service.lookup_concepts(name=name, limit=limit, offset=offset)
