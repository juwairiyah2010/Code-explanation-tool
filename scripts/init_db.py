"""Reproducible database initialization and migration script.

Executes Alembic migrations to current head, ensures SQLite WAL tuning and indexes,
and bootstraps initial knowledge base documents if empty.
"""

import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from backend.config import get_settings
from backend.core.database import SessionLocal, engine, init_db
from backend.core.logging import logger
from backend.repositories.rag_repo import RAGRepository
from backend.services.rag.ingestion import KnowledgeIngestionPipeline


def run_database_initialization() -> None:
    settings = get_settings()
    logger.info(f"Initializing database for environment [{settings.ENVIRONMENT}]...")

    # 1. Ensure directory exists for SQLite
    if settings.DATABASE_URL.startswith("sqlite:///"):
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        if db_path and not db_path.startswith(":memory:"):
            db_dir = os.path.dirname(os.path.abspath(db_path))
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Ensured database directory: {db_dir}")

    # 2. Run Alembic migrations to latest head
    root_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = root_dir / "alembic.ini"

    if alembic_ini_path.exists():
        logger.info("Executing Alembic migrations (upgrade head)...")
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        try:
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations completed successfully.")
        except Exception as e:
            logger.warning(f"Alembic upgrade encountered issue, falling back to declarative create_all: {e}")
            init_db()
    else:
        logger.info("No alembic.ini found; running declarative table creation...")
        init_db()

    # 3. Verify database connectivity
    with SessionLocal() as db:
        res = db.execute(text("SELECT 1")).scalar()
        if res != 1:
            raise RuntimeError("Database connectivity check failed.")
        logger.info("Database connectivity verified (SELECT 1 -> OK).")

        # 4. Bootstrap RAG Knowledge Base if empty
        repo = RAGRepository(db)
        stats = repo.get_stats()
        if stats["chunks"] == 0:
            kb_dir = root_dir / "data" / "knowledge_base"
            if kb_dir.exists():
                logger.info(f"Bootstrapping knowledge base from {kb_dir}...")
                pipeline = KnowledgeIngestionPipeline(db)
                result = pipeline.ingest_directory(kb_dir)
                logger.info(f"Ingested {result.documents_ingested} docs, {result.chunks_created} chunks in {result.duration_seconds}s.")
        else:
            logger.info(f"Knowledge base already populated: {stats['documents']} docs, {stats['chunks']} chunks.")

    logger.info("Database initialization completed successfully.")


if __name__ == "__main__":
    run_database_initialization()
