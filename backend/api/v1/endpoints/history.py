import json
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.repositories.submission_repo import SubmissionRepository

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
            "code": sub.code,
            "language": sub.language,
            "level": sub.level,
            "summary": sub.explanation.summary if sub.explanation else "",
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
    
    explanation_data = None
    if record.explanation:
        explanation_data = {
            "summary": record.explanation.summary,
            "algorithm_steps": json.loads(record.explanation.algorithm_steps) if record.explanation.algorithm_steps else [],
            "complexity": json.loads(record.explanation.complexity) if record.explanation.complexity else {},
            "hints": json.loads(record.explanation.hints) if record.explanation.hints else [],
        }

    blocks_data = [
        {
            "id": b.id,
            "title": b.title,
            "explanation": b.explanation,
            "line_start": b.line_start,
            "line_end": b.line_end,
        }
        for b in record.blocks
    ]

    concepts_data = [
        {
            "id": c.id,
            "concept": c.name,
            "definition": c.definition,
        }
        for c in record.concepts
    ]

    return {
        "id": record.id,
        "code": record.code,
        "language": record.language,
        "level": record.level,
        "created_at": record.created_at.isoformat(),
        "summary": record.explanation.summary if record.explanation else "",
        "explanation": explanation_data,
        "blocks": blocks_data,
        "concepts": concepts_data,
    }

