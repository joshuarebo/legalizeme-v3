#!/usr/bin/env python3
"""
Migration script to make user_id nullable in queries table
This script handles the database schema change for removing authentication
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_user_id_nullable():
    """
    Make user_id column nullable in queries table
    """
    try:
        # Create engine
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if the table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'queries'
                );
            """))
            
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info("Queries table does not exist yet. No migration needed.")
                return True
            
            # Check current column definition
            result = conn.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'queries' 
                AND column_name = 'user_id'
                AND table_schema = 'public';
            """))
            
            current_nullable = result.scalar()
            
            if current_nullable == 'YES':
                logger.info("user_id column is already nullable. No migration needed.")
                return True
            
            logger.info("Making user_id column nullable...")
            
            # Make the column nullable
            conn.execute(text("""
                ALTER TABLE queries 
                ALTER COLUMN user_id DROP NOT NULL;
            """))
            
            # Commit the transaction
            conn.commit()
            
            logger.info("Successfully made user_id column nullable in queries table")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Database migration failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Migration failed with unexpected error: {e}")
        return False

def verify_migration():
    """
    Verify that the migration was successful
    """
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check column definition
            result = conn.execute(text("""
                SELECT is_nullable, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'queries' 
                AND column_name = 'user_id'
                AND table_schema = 'public';
            """))
            
            row = result.fetchone()
            if row:
                is_nullable, data_type = row
                logger.info(f"user_id column: type={data_type}, nullable={is_nullable}")
                return is_nullable == 'YES'
            else:
                logger.error("user_id column not found")
                return False
                
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting database migration: Make user_id nullable")
    
    # Run migration
    success = migrate_user_id_nullable()
    
    if success:
        # Verify migration
        if verify_migration():
            logger.info("Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("Migration verification failed!")
            sys.exit(1)
    else:
        logger.error("Migration failed!")
        sys.exit(1)
