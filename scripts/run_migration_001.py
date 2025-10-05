"""
Migration Script: Add Interactive Source Fields
Safely applies migration 001_add_interactive_source_fields.sql
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from app.database import engine as default_engine, SessionLocal as DefaultSessionLocal
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detect database type
database_url = settings.TEST_DATABASE_URL if os.getenv("TESTING") else settings.DATABASE_URL
IS_SQLITE = database_url.startswith("sqlite")
IS_POSTGRESQL = "postgresql" in database_url

logger.info(f"Database type: {'SQLite' if IS_SQLITE else 'PostgreSQL' if IS_POSTGRESQL else 'Unknown'}")


def run_migration():
    """Run migration 001: Add interactive source fields"""

    # Choose appropriate migration file based on database type
    if IS_SQLITE:
        migration_file = Path(__file__).parent.parent / "migrations" / "001_add_interactive_source_fields_sqlite.sql"
        logger.info("Using SQLite-compatible migration")
    else:
        migration_file = Path(__file__).parent.parent / "migrations" / "001_add_interactive_source_fields.sql"
        logger.info("Using PostgreSQL migration")

    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False

    logger.info(f"Reading migration file: {migration_file}")

    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    # Split into individual statements (separated by semicolons)
    statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]

    logger.info(f"Found {len(statements)} SQL statements to execute")

    # Use appropriate session based on database type
    if IS_SQLITE:
        # For SQLite, create engine without isolation_level
        from sqlalchemy.pool import StaticPool
        sqlite_engine = create_engine(
            database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        SessionLocal = sessionmaker(bind=sqlite_engine, autocommit=False, autoflush=False)
        logger.info("Using SQLite session (development mode)")
    else:
        SessionLocal = DefaultSessionLocal
        logger.info("Using PostgreSQL session (production mode)")

    db = SessionLocal()

    try:
        logger.info("Starting migration...")

        # Execute each statement
        for i, statement in enumerate(statements, 1):
            # Skip comment-only statements
            if statement.startswith('COMMENT') or statement.startswith('SELECT'):
                logger.info(f"[{i}/{len(statements)}] Executing: {statement[:50]}...")
            else:
                logger.info(f"[{i}/{len(statements)}] Executing ALTER/CREATE statement...")

            try:
                db.execute(text(statement))
                db.commit()
                logger.info(f"  ✅ Success")
            except Exception as e:
                # Check if error is benign (column already exists)
                error_msg = str(e).lower()
                if 'already exists' in error_msg or 'duplicate' in error_msg:
                    logger.warning(f"  ⚠️  Already exists (safe to ignore): {e}")
                    db.rollback()
                else:
                    logger.error(f"  ❌ Error: {e}")
                    db.rollback()
                    raise

        logger.info("✅ Migration completed successfully!")

        # Verify migration
        logger.info("\nVerifying migration...")
        verify_migration(db)

        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        return False

    finally:
        db.close()


def verify_migration(db):
    """Verify that migration was applied correctly"""

    # Check new columns exist
    check_query = text("""
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_name = 'documents'
        AND column_name IN (
            'snippet', 'citation_text', 'document_date', 'court_name',
            'case_number', 'act_chapter', 'last_verified_at', 'crawl_status',
            'freshness_score', 'legal_metadata'
        )
        ORDER BY column_name;
    """)

    result = db.execute(check_query)
    columns = result.fetchall()

    logger.info(f"\n✅ New columns added ({len(columns)}):")
    for col in columns:
        logger.info(f"  - {col[0]:25} {col[1]:20} (nullable: {col[2]})")

    # Check document counts
    stats_query = text("""
        SELECT
            COUNT(*) as total_documents,
            COUNT(snippet) as with_snippet,
            COUNT(freshness_score) as with_freshness_score,
            ROUND(AVG(freshness_score)::numeric, 2) as avg_freshness_score,
            COUNT(CASE WHEN crawl_status = 'active' THEN 1 END) as active_documents
        FROM documents;
    """)

    result = db.execute(stats_query)
    stats = result.fetchone()

    logger.info(f"\n📊 Document Statistics:")
    logger.info(f"  Total documents: {stats[0]}")
    logger.info(f"  With snippet: {stats[1]}")
    logger.info(f"  With freshness score: {stats[2]}")
    logger.info(f"  Average freshness score: {stats[3]}")
    logger.info(f"  Active documents: {stats[4]}")

    # Check indexes
    index_query = text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'documents'
        AND indexname LIKE 'idx_documents_%'
        ORDER BY indexname;
    """)

    result = db.execute(index_query)
    indexes = result.fetchall()

    logger.info(f"\n📑 Indexes created ({len(indexes)}):")
    for idx in indexes:
        logger.info(f"  - {idx[0]}")


def rollback_migration():
    """Rollback migration 001 (if needed)"""

    logger.warning("⚠️  Rolling back migration...")

    rollback_sql = """
    -- Drop new columns
    ALTER TABLE documents
    DROP COLUMN IF EXISTS snippet,
    DROP COLUMN IF EXISTS citation_text,
    DROP COLUMN IF EXISTS document_date,
    DROP COLUMN IF EXISTS court_name,
    DROP COLUMN IF EXISTS case_number,
    DROP COLUMN IF EXISTS act_chapter,
    DROP COLUMN IF EXISTS last_verified_at,
    DROP COLUMN IF EXISTS crawl_status,
    DROP COLUMN IF EXISTS freshness_score,
    DROP COLUMN IF EXISTS legal_metadata;

    -- Drop indexes
    DROP INDEX IF EXISTS idx_documents_crawl_status;
    DROP INDEX IF EXISTS idx_documents_freshness_score;
    DROP INDEX IF EXISTS idx_documents_document_date;
    DROP INDEX IF EXISTS idx_documents_court_name;
    DROP INDEX IF EXISTS idx_documents_case_number;
    DROP INDEX IF EXISTS idx_documents_legal_metadata_gin;
    """

    db = SessionLocal()

    try:
        db.execute(text(rollback_sql))
        db.commit()
        logger.info("✅ Rollback completed successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run migration 001')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration instead of applying it')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')

    args = parser.parse_args()

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
        migration_file = Path(__file__).parent.parent / "migrations" / "001_add_interactive_source_fields.sql"
        with open(migration_file, 'r', encoding='utf-8') as f:
            print(f.read())
        sys.exit(0)

    if args.rollback:
        success = rollback_migration()
    else:
        logger.info("=" * 80)
        logger.info("MIGRATION 001: Add Interactive Source Fields for Enhanced RAG")
        logger.info("=" * 80)
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Unknown'}")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info("=" * 80)

        # Confirm before running in production
        if settings.ENVIRONMENT == 'production':
            response = input("\n⚠️  Running in PRODUCTION. Continue? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Migration cancelled by user")
                sys.exit(0)

        success = run_migration()

    sys.exit(0 if success else 1)
