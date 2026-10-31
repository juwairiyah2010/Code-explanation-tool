"""Health check endpoint providing comprehensive liveness, readiness, and subsystem status."""

from datetime import datetime, timezone
import time
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.core.database import get_db
from backend.models.persistence import KnowledgeChunk
from backend.schemas.health import HealthResponse

router = APIRouter()

_START_TIME = time.time()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(
    http_response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Check API server liveness, SQLite database connectivity, and RAG knowledge store readiness."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    rag_status = "ready"
    try:
        chunk_count = db.execute(select(func.count(KnowledgeChunk.id))).scalar_one() or 0
        if chunk_count == 0:
            rag_status = "empty"
        else:
            rag_status = f"ready ({chunk_count} chunks)"
    except Exception as e:
        rag_status = f"unreachable: {str(e)}"

    if db_status != "connected":
        overall_status = "unhealthy"
        http_response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif rag_status.startswith("unreachable"):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    now_iso = datetime.now(timezone.utc).isoformat()
    uptime = round(time.time() - _START_TIME, 2)

    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        database=db_status,
        environment=settings.ENVIRONMENT,
        supported_languages=["python", "javascript"],
        rag_store=rag_status,
        timestamp=now_iso,
        uptime_seconds=uptime,
    )
