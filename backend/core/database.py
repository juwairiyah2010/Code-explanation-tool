"""Database engine and session management for SQLite."""

from collections.abc import Generator
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import get_settings

settings = get_settings()

# SQLite specific connect args for thread safety
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG and settings.ENVIRONMENT == "development",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables, ensuring target directory exists."""
    import backend.models.persistence  # Register all models with Base.metadata
    _ = backend.models.persistence
    if settings.DATABASE_URL.startswith("sqlite:///"):
        db_file = settings.DATABASE_URL.replace("sqlite:///", "")
        if db_file and not db_file.startswith(":memory:"):
            db_dir = os.path.dirname(db_file)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    # Ensure backward-compatible schema additions in SQLite
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            res = conn.execute(text("PRAGMA table_info(knowledge_chunks)")).fetchall()
            cols = [r[1] for r in res]
            if cols and "section" not in cols:
                conn.execute(text("ALTER TABLE knowledge_chunks ADD COLUMN section TEXT DEFAULT ''"))
                conn.commit()
    except Exception:
        pass
