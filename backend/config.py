"""Configuration settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "LLM-Based Code Explanation Tool"
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Server
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 8501

    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # LLM Settings
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str | None = None

    # LLM Settings
    LLM_PROVIDER: Literal["mock", "openai", "gemini"] = "mock"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Parser / AST limits
    MAX_CODE_LENGTH: int = 10000
    ENABLE_TREE_SITTER: bool = True


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
