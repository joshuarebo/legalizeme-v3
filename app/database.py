from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
# Redis removed - using PostgreSQL-only architecture
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)

# Determine if we're in testing mode
IS_TESTING = os.getenv("TESTING", "false").lower() == "true" or "pytest" in os.getenv("_", "")

# Database setup - use test database for testing
database_url = settings.TEST_DATABASE_URL if IS_TESTING else settings.DATABASE_URL

# Detect database type from URL
IS_SQLITE = database_url.startswith("sqlite")
IS_POSTGRESQL = "postgresql" in database_url or "postgres" in database_url

# Database-specific configuration
if IS_SQLITE:
    # SQLite configuration for development/testing
    engine_kwargs = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
        "pool_recycle": -1,
        "echo": True if settings.ENVIRONMENT == "development" else False
    }
    logger.info("Using SQLite database configuration")
elif IS_POSTGRESQL:
    # PostgreSQL production configuration - fixes session management issues
    engine_kwargs = {
        "poolclass": QueuePool,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # 1 hour instead of 5 minutes
        "pool_timeout": 30,
        "echo": False,  # Disable echo in production for performance
        "isolation_level": "READ_COMMITTED"  # PostgreSQL-specific isolation level
    }
    logger.info("Using PostgreSQL database configuration")
else:
    # Default configuration
    engine_kwargs = {
        "echo": True if settings.ENVIRONMENT == "development" else False
    }
    logger.warning(f"Unknown database type, using default configuration: {database_url[:20]}...")

engine = create_engine(database_url, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent session expiration issues
)

Base = declarative_base()

# Redis completely removed - using PostgreSQL-only architecture
redis_client = None
logger.info("Redis removed - using PostgreSQL-only architecture")

def get_db():
    """Database dependency with improved error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def get_redis():
    """Redis dependency"""
    return redis_client

# Database initialization
def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
