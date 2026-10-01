from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.repositories.submission_repo import SubmissionRepository
from typing import List, Dict, Any

router = APIRouter()

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Get submission history",
)
def get_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    repo = SubmissionRepository(db)
    submissions = repo.get_history(limit=limit, offset=offset)
    
    result = []
    for sub in submissions:
        result.append({
            "id": sub.id,
            "language": sub.language,
            "level": sub.level,
            "created_at": sub.created_at.isoformat()
        })
    return result

@router.get(
    "/{record_id}",
    status_code=status.HTTP_200_OK,
    summary="Get submission by ID",
)
def get_history_item(
    record_id: int,
    db: Session = Depends(get_db)
):
    repo = SubmissionRepository(db)
    record = repo.get_submission_by_id(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record {record_id} not found"
        )
    return {
        "id": record.id,
        "language": record.language,
        "level": record.level,
        "created_at": record.created_at.isoformat()
    }
