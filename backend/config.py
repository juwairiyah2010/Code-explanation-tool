"""Configuration settings supporting development, testing, and production environments."""

from functools import lru_cache
import os
from typing import Literal, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Code Lore - Code Explanation Engine"
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Server Network Binding (configurable, zero hardcoded localhost)
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 8501
    WORKERS: int = 2
    BACKEND_URL: str | None = None  # Optional explicit backend URL for frontends

    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["text", "json"] = "text"

    # LLM Provider Configuration
    LLM_PROVIDER: Literal["mock", "openai", "gemini"] = "mock"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # RAG & Embeddings
    EMBEDDING_PROVIDER: str = "fastembed"

    # Security & CORS
    SECRET_KEY: str = "code_lore_default_secret_key"
    CORS_ORIGINS: list[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
    ]
    RATE_LIMITING_ENABLED: bool = True

    # Parser / AST limits
    MAX_CODE_LENGTH: int = 50000
    ENABLE_TREE_SITTER: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        """Support comma-separated string from env (e.g. 'https://app.com,https://api.com') or list."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @model_validator(mode="after")
    def apply_environment_defaults(self) -> "Settings":
        """Apply environment-specific defaults for production, testing, and development."""
        if self.ENVIRONMENT == "production":
            # In production, debug is disabled unless explicitly overridden
            if "DEBUG" not in self.model_fields_set:
                self.DEBUG = False
            # In production, structured JSON logging is default
            if "LOG_FORMAT" not in self.model_fields_set:
                self.LOG_FORMAT = "json"
        elif self.ENVIRONMENT == "testing":
            if "DATABASE_URL" not in self.model_fields_set:
                self.DATABASE_URL = "sqlite:///:memory:"
            self.DEBUG = False
        return self


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
