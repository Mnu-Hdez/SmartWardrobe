from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.core.config import settings

# Single engine for the whole app. Previously this module and backend/api/main.py
# each created their own engine from different config sources (this one read
# DATABASE_URL straight from os.getenv, main.py used settings.DATABASE_URL) -
# if they ever diverged (e.g. DATABASE_URL only set via .env, not a real env
# var) requests would silently hit a different database file than the one
# migrations/startup initialized.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in settings.DATABASE_URL else None,
)


def create_db_and_tables() -> None:
    """Create database and tables."""
    SQLModel.metadata.create_all(engine)
    _ensure_outfit_daily_columns()


def _ensure_outfit_daily_columns() -> None:
    """Lightweight migration for SQLite DBs created before the
    is_daily/for_date columns existed on Outfit - no alembic migrations are
    wired up in this project yet, so this just adds the columns if a table
    from before this feature is missing them. No-op on a fresh DB (created_all
    already includes them) or on non-SQLite backends."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    with engine.connect() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(outfit)")}
        if "is_daily" not in columns:
            conn.exec_driver_sql("ALTER TABLE outfit ADD COLUMN is_daily BOOLEAN NOT NULL DEFAULT 0")
        if "for_date" not in columns:
            conn.exec_driver_sql("ALTER TABLE outfit ADD COLUMN for_date VARCHAR(10)")
        conn.commit()


def get_session() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get DB session."""
    with Session(engine) as session:
        yield session


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions outside of FastAPI."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
