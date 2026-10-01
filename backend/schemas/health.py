"""Health check schemas."""

from typing import Literal
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    database: str = Field(..., description="Database connection status")
    environment: str = Field(..., description="Current deployment environment")
    supported_languages: list[str] = Field(..., description="Supported programming languages")
