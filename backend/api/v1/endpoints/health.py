"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.config import Settings, get_settings
from backend.core.database import get_db
from backend.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Check API server, database connectivity, and environment status."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    status = "healthy" if db_status == "connected" else "degraded"

    return HealthResponse(
        status=status,
        version="0.1.0",
        database=db_status,
        environment=settings.ENVIRONMENT,
        supported_languages=["python", "javascript"],
    )
