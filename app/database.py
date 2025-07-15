from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
# Redis removed - using PostgreSQL-only architecture
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)

# Determine if we're in testing mode
IS_TESTING = os.getenv("TESTING", "false").lower() == "true" or "pytest" in os.getenv("_", "")

# Database setup - use test database for testing
database_url = settings.TEST_DATABASE_URL if IS_TESTING else settings.DATABASE_URL

engine_kwargs = {
    "poolclass": StaticPool,
    "pool_pre_ping": True,
    "echo": True if settings.ENVIRONMENT == "development" else False
}

# SQLite specific configuration for testing
if IS_TESTING and database_url.startswith("sqlite"):
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "pool_recycle": -1
    })
else:
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(database_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Redis completely removed - using PostgreSQL-only architecture
redis_client = None
logger.info("Redis removed - using PostgreSQL-only architecture")

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
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
