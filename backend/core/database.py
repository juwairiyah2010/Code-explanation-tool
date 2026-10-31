"""Database engine and session management for SQLite with pooling and WAL performance tuning."""

from collections.abc import Generator
import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import get_settings

settings = get_settings()

is_sqlite = "sqlite" in settings.DATABASE_URL
is_memory = ":memory:" in settings.DATABASE_URL

# SQLite specific connect args for thread safety and busy timeout
connect_args = {"check_same_thread": False, "timeout": 20.0} if is_sqlite else {}

engine_kwargs = {
    "connect_args": connect_args,
    "echo": settings.DEBUG and settings.ENVIRONMENT == "development",
}

if is_sqlite and not is_memory:
    from sqlalchemy.pool import QueuePool
    engine_kwargs.update({
        "poolclass": QueuePool,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable high-performance SQLite PRAGMAs: WAL journal, 64MB cache, memory temp store."""
    if is_sqlite:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB in-memory page cache
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
            cursor.execute("PRAGMA busy_timeout=5000")
        except Exception:
            pass
        finally:
            cursor.close()


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
    """Initialize database tables, ensuring target directory exists and indexes are built."""
    import backend.models.persistence  # Register all models with Base.metadata
    _ = backend.models.persistence
    if settings.DATABASE_URL.startswith("sqlite:///"):
        db_file = settings.DATABASE_URL.replace("sqlite:///", "")
        if db_file and not db_file.startswith(":memory:"):
            db_dir = os.path.dirname(db_file)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

    Base.metadata.create_all(bind=engine)

    # Ensure schema migrations and indexes exist on existing tables
    try:
        with engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(knowledge_chunks)")).fetchall()
            cols = [r[1] for r in res]
            if cols and "section" not in cols:
                conn.execute(text("ALTER TABLE knowledge_chunks ADD COLUMN section TEXT DEFAULT ''"))

            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_lang_topic ON knowledge_chunks(language, topic)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_learner_progress_user_concept ON learner_progress(user_id, concept)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_submissions_user_lang ON submissions(user_id, language)"))
            conn.commit()
    except Exception:
        pass
