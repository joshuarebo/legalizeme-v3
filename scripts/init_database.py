"""
Initialize Database Script
Creates all tables based on SQLAlchemy models
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Base and engine
from app.database import Base, engine, database_url

# Import ALL models so they're registered with Base
from app.models.document import Document
from app.models.legal_case import LegalCase
from app.models.query import Query
from app.models.user import User

# Import any other models
try:
    from app.models.conversation import Conversation, ConversationMessage
    logger.info("Imported conversation models")
except ImportError:
    logger.warning("Conversation models not found")

try:
    from app.models.token_usage import UserToken, TokenUsageHistory
    logger.info("Imported token usage models")
except ImportError:
    logger.warning("Token usage models not found")


def init_database():
    """Initialize all database tables"""
    logger.info("=" * 80)
    logger.info("INITIALIZING DATABASE")
    logger.info("=" * 80)
    logger.info(f"Database URL: {database_url}")
    logger.info(f"Tables to create: {len(Base.metadata.tables)}")

    for table_name in Base.metadata.tables.keys():
        logger.info(f"  - {table_name}")

    logger.info("=" * 80)

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully!")

        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        logger.info(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            columns = inspector.get_columns(table)
            logger.info(f"  ✓ {table} ({len(columns)} columns)")

        return True

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
