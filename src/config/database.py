"""Database configuration and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator
from src.models.base import Base
from src.config.settings import settings

# Database URL from settings (which properly loads .env)
DATABASE_URL = settings.DATABASE_URL

# Create engine
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Use NullPool for development
    echo=settings.SQL_ECHO,  # Log SQL queries
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session for FastAPI dependency injection.

    Yields:
        Database session

    Example:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.

    Creates all tables defined in models if they don't exist.
    For production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all database tables.

    WARNING: This will delete all data!
    Only use in development/testing.
    """
    Base.metadata.drop_all(bind=engine)
