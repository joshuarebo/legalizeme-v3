#!/usr/bin/env python3
"""
Database migration script to create conversation tables
Run this script to add conversation management to the existing database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.config import settings
from app.models.conversation import Conversation, ConversationMessage
from app.database import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_conversation_tables():
    """Create conversation tables in the database"""
    try:
        # Use production database URL
        db_url = "postgresql://counseladmin:CounselAI2025SecurePass!@counsel-db-v2.cns8kokico8n.us-east-1.rds.amazonaws.com:5432/postgres"
        engine = create_engine(db_url)
        
        # Create tables
        logger.info("Creating conversation tables...")
        
        # Create only the new tables
        Conversation.__table__.create(engine, checkfirst=True)
        ConversationMessage.__table__.create(engine, checkfirst=True)
        
        logger.info("✅ Conversation tables created successfully!")
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('conversations', 'conversation_messages')
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            logger.info(f"✅ Verified tables exist: {tables}")
            
            if len(tables) == 2:
                logger.info("🎉 Migration completed successfully!")
                return True
            else:
                logger.error(f"❌ Expected 2 tables, found {len(tables)}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

def rollback_conversation_tables():
    """Rollback conversation tables (for testing)"""
    try:
        # Use production database URL
        db_url = "postgresql://counseladmin:CounselAI2025SecurePass!@counsel-db-v2.cns8kokico8n.us-east-1.rds.amazonaws.com:5432/postgres"
        engine = create_engine(db_url)
        
        logger.info("Rolling back conversation tables...")
        
        # Drop tables in reverse order (due to foreign keys)
        ConversationMessage.__table__.drop(engine, checkfirst=True)
        Conversation.__table__.drop(engine, checkfirst=True)
        
        logger.info("✅ Conversation tables rolled back successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Conversation tables migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_conversation_tables()
    else:
        success = create_conversation_tables()
    
    sys.exit(0 if success else 1)
