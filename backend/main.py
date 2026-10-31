"""FastAPI Main Application Entrypoint."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.v1.api_router import api_router
from backend.config import get_settings
from backend.core.database import init_db
from backend.core.logging import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    logger.info("Initializing SQLite database tables...")
    init_db()

    # Verify or initialize RAG knowledge base
    try:
        from pathlib import Path
        from backend.core.database import SessionLocal
        from backend.repositories.rag_repo import RAGRepository
        from backend.services.rag.ingestion import KnowledgeIngestionPipeline

        db = SessionLocal()
        try:
            repo = RAGRepository(db)
            stats = repo.get_stats()
            if stats["chunks"] == 0:
                logger.info("Knowledge base is empty. Triggering initial ingestion...")
                pipeline = KnowledgeIngestionPipeline(db)
                kb_path = Path("data/knowledge_base")
                if kb_path.exists():
                    pipeline.ingest_directory(kb_path)
            else:
                logger.info(f"Knowledge base ready: {stats['documents']} documents, {stats['chunks']} chunks.")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Knowledge base auto-ingestion skipped: {e}")

    logger.info(f"Starting {settings.APP_NAME} in [{settings.ENVIRONMENT}] mode.")
    yield
    logger.info("Shutting down application...")



from fastapi import Request
from fastapi.responses import JSONResponse
from backend.core.security import RequestSizeLimitMiddleware, sanitize_internal_error


def create_app() -> FastAPI:
    """FastAPI Application Factory with hardened security and error sanitization."""
    docs_url = "/docs" if settings.ENVIRONMENT != "production" else None
    redoc_url = "/redoc" if settings.ENVIRONMENT != "production" else None

    app = FastAPI(
        title=settings.APP_NAME,
        description="Modular REST API for AST-powered and LLM-assisted multi-language code explanation.",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        lifespan=lifespan,
    )

    # Request size limiting middleware (2 MB maximum payload)
    app.add_middleware(RequestSizeLimitMiddleware, max_content_length=2 * 1024 * 1024)

    # CORS configuration
    cors_origins = settings.CORS_ORIGINS if settings.ENVIRONMENT == "production" else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Root-level health check endpoint for standard container orchestrators
    from backend.api.v1.endpoints.health import health_check
    app.add_api_route("/health", health_check, methods=["GET"], tags=["Health"])

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Sanitize unhandled internal exceptions to prevent information leakage in production."""
        detail = sanitize_internal_error(exc, context_msg="Unhandled server exception")
        return JSONResponse(
            status_code=500,
            content={"detail": detail},
        )

    @app.get("/", tags=["Root"])
    def root() -> dict[str, str]:
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "docs": "/docs",
            "health": f"{settings.API_V1_STR}/health",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
    )
