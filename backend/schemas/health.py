"""Health check schemas."""

from typing import Literal
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    database: str = Field(..., description="Database connection status")
    environment: str = Field(..., description="Current deployment environment")
    supported_languages: list[str] = Field(..., description="Supported programming languages")
    rag_store: str = Field("ready", description="RAG knowledge chunks store status")
    timestamp: str | None = Field(None, description="ISO timestamp of health check")
    uptime_seconds: float | None = Field(None, description="Application process uptime in seconds")
