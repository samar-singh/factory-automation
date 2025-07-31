"""Database connection and session management."""

import logging
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

# Create engine
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://samarsingh@localhost:5432/factory_automation"
)
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disable connection pooling for simplicity
    echo=False,  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Session:
    """Provide a transactional scope for database operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()


def init_database():
    """Initialize database tables."""
    from factory_database.models import Base

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
