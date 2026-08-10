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
