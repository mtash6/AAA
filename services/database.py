"""
AAA ADVANCE AMERICAN AGENCY — Enterprise Database Infrastructure & Connection Management
Supports SQLite (local dev with WAL & busy timeout) and PostgreSQL (production with connection pooling).
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# --- ENVIRONMENT & CONNECTION STRINGS ---
DEFAULT_DB_URL = "sqlite:///./aaa_agency.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
DEBUG_SQL = os.getenv("SQL_ECHO", "false").lower() in ("true", "1", "yes")

# Handle Heroku / Railway legacy PostgreSQL connection strings
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = DATABASE_URL.startswith("sqlite")
is_memory_sqlite = DATABASE_URL in ("sqlite://", "sqlite:///:memory:")

# --- ENGINE CONFIGURATION & CONNECTION POOLING ---
engine_kwargs = {
    "echo": DEBUG_SQL,
    "pool_pre_ping": True,  # Verifies connection viability prior to checkout
}

if is_sqlite:
    # 'timeout': 30 prevents 'sqlite3.OperationalError: database is locked' during concurrent writes
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": int(os.getenv("DB_BUSY_TIMEOUT", "30")),
    }
    
    # In-memory SQLite requires StaticPool so threads share the single in-memory instance
    if is_memory_sqlite:
        engine_kwargs["poolclass"] = StaticPool
else:
    # Production connection pool settings (PostgreSQL / MySQL)
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),  # Recycle connection every 30 mins
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)

# --- SQLITE PERFORMANCE & SAFETY PRAGMAS ---
if is_sqlite and not is_memory_sqlite:
    @event.listens_for(engine, "connect")
    def configure_sqlite_connection(dbapi_connection, connection_record):
        """
        Enforces Foreign Keys, enables Write-Ahead Logging (WAL) for concurrency, 
        and configures synchronous=NORMAL for optimal write throughput.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative Base class for ORM Models (SQLAlchemy 2.0+)."""
    pass


# --- DATABASE SESSION UTILITIES & LIFECYCLE ---

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Request Dependency. Yields an isolated DB session 
    and guarantees closure after HTTP response delivery.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for background tasks, CLI tools, or non-HTTP scripts.
    Handles auto-commit on success and rollback on exceptions.
    
    Usage:
        with get_db_context() as db:
            db.add(my_model)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction rolled back due to error: {e}", exc_info=True)
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Pings the database to verify active connectivity.
    Useful for healthcheck endpoints or startup validation.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.critical(f"Database health check failed: {e}")
        return False


def init_db() -> None:
    """
    Initializes database tables and triggers schema synchronization.
    Called during application startup.
    """
    try:
        import models  # Lazy import to prevent circular dependency
        
        Base.metadata.create_all(bind=engine)
        
        # Execute schema migration helper from models.py if available
        if hasattr(models, "sync_database_schema"):
            models.sync_database_schema(engine)
            
        logger.info("Database initialized and schema synchronized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


def close_db() -> None:
    """Disposes of the database engine pool during application shutdown."""
    engine.dispose()
    logger.info("Database engine pool closed.")
