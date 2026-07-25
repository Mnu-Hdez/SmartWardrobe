from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/db/smart_wardrobe.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
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


def init_db() -> None:
    """Initialize database with default data."""
    create_db_and_tables()
    
    # Add default style rules
    from backend.models.schemas import StyleRuleCreate
    from backend.repositories.style_rule_repository import StyleRuleRepository
    
    default_rules = [
        StyleRuleCreate(
            name="color_harmony_complementary",
            description="Complementary colors score higher",
            rule_type="color_harmony",
            weight=1.5,
            parameters='{"method": "complementary", "threshold": 30}'
        ),
        StyleRuleCreate(
            name="color_harmony_analogous",
            description="Analogous colors score well",
            rule_type="color_harmony",
            weight=1.2,
            parameters='{"method": "analogous", "threshold": 15}'
        ),
        StyleRuleCreate(
            name="color_harmony_monochromatic",
            description="Monochromatic outfits are elegant",
            rule_type="color_harmony",
            weight=1.0,
            parameters='{"method": "monochromatic", "threshold": 10}'
        ),
        StyleRuleCreate(
            name="formality_match",
            description="Garments should have similar formality levels",
            rule_type="formality_match",
            weight=2.0,
            parameters='{"max_difference": 1}'
        ),
        StyleRuleCreate(
            name="pattern_balance",
            description="Avoid too many patterns in one outfit",
            rule_type="pattern_balance",
            weight=1.5,
            parameters='{"max_patterns": 2}'
        ),
        StyleRuleCreate(
            name="seasonal_appropriateness",
            description="Garments should match the season",
            rule_type="seasonal",
            weight=1.0,
            parameters='{}'
        ),
    ]
    
    with get_db_session() as session:
        repo = StyleRuleRepository(session)
        for rule in default_rules:
            existing = repo.get_by_name(rule.name)
            if not existing:
                repo.create(rule)