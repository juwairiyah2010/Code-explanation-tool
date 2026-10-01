from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.repositories.submission_repo import SubmissionRepository

router = APIRouter()

@router.get(
    "/{name}",
    status_code=status.HTTP_200_OK,
    summary="Get concept by name",
)
def get_concept(
    name: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    repo = SubmissionRepository(db)
    concepts = repo.get_concept_by_name(name=name, limit=limit, offset=offset)
    
    result = []
    for c in concepts:
        result.append({
            "id": c.id,
            "submission_id": c.submission_id,
            "name": c.name,
            "definition": c.definition
        })
    return {"items": result, "limit": limit, "offset": offset}
