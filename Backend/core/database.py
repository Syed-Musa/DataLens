"""Database connection and session management for target PostgreSQL."""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from core.config import get_settings

logger = logging.getLogger(__name__)


def get_engine(connection_url: str | None = None) -> Engine:
    """Create SQLAlchemy engine for the target database."""
    settings = get_settings()
    url = connection_url or settings.database_url

    engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    return engine


# Default engine (uses settings at import time - call refresh if URL changes)
_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_session_factory(connection_url: str | None = None) -> sessionmaker:
    """Get or create session factory for the target database."""
    global _engine, _SessionLocal
    url = connection_url or get_settings().database_url

    if _SessionLocal is None or (_engine and str(_engine.url) != url):
        _engine = get_engine(url)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        logger.info("Database session factory initialized")

    return _SessionLocal


def reset_connection(url: str | None = None) -> None:
    """Reset engine and session (e.g., after connection string change)."""
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    get_session_factory(url)


@contextmanager
def get_db_session(connection_url: str | None = None) -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    factory = get_session_factory(connection_url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection(connection_url: str | None = None) -> tuple[bool, str]:
    """Test database connectivity."""
    try:
        engine = get_engine(connection_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Connected successfully."
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        error_msg = str(e)
        if "password authentication failed" in error_msg:
            return False, "Authentication failed. Check username/password."
        if "connection to server at" in error_msg and "failed" in error_msg:
            return False, "Connection refused. Check host and port."
        if "database" in error_msg and "does not exist" in error_msg:
             return False, "Database does not exist."
        return False, error_msg
