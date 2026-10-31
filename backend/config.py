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
        "http://localhost:5001",
        "http://127.0.0.1:5001",
        "http://localhost:3000",
    ]
    RATE_LIMITING_ENABLED: bool = True

    # Parser / AST limits
    MAX_CODE_LENGTH: int = 50000
    ENABLE_TREE_SITTER: bool = True


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
