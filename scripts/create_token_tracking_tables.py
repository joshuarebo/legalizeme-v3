#!/usr/bin/env python3
"""
Create Token Tracking Tables for CounselAI
Creates user_tokens and token_usage_history tables
"""

import sys
import os
import logging

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import engine, Base
from app.models.token_tracking import UserTokens, TokenUsageHistory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_token_tracking_tables():
    """Create token tracking tables"""
    try:
        logger.info("Creating token tracking tables...")

        # Create all tables defined in the models
        Base.metadata.create_all(bind=engine, tables=[
            UserTokens.__table__,
            TokenUsageHistory.__table__
        ])

        logger.info("✅ Token tracking tables created successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error creating token tracking tables: {e}")
        return False

def main():
    """Main function to create token tracking tables"""
    logger.info("🚀 Starting token tracking table creation...")

    # Create tables
    if not create_token_tracking_tables():
        logger.error("❌ Failed to create token tracking tables")
        sys.exit(1)

    logger.info("🎉 Token tracking system setup completed successfully!")
    logger.info("📋 Available endpoints:")
    logger.info("  - GET /api/v1/tokens/status/{userId}")
    logger.info("  - POST /api/v1/tokens/check")
    logger.info("  - POST /api/v1/tokens/track")
    logger.info("  - GET /api/v1/tokens/history/{userId}")

if __name__ == "__main__":
    main()
