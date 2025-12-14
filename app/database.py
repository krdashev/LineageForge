"""Database connection and session management."""

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)


def init_db() -> None:
    """Create all tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get database session."""
    with Session(engine) as session:
        yield session
