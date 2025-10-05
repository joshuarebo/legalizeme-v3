-- Migration: Add Interactive Source Fields for Enhanced RAG Citations (SQLite)
-- Created: 2025-01-15
-- Description: SQLite version - Adds new fields to documents table to support interactive citations

-- Note: SQLite doesn't support ADD COLUMN IF NOT EXISTS before version 3.35
-- We'll handle this gracefully in the Python script

-- ============================================================================
-- Add new columns to documents table (SQLite syntax)
-- ============================================================================

-- Interactive source preview fields
ALTER TABLE documents ADD COLUMN snippet TEXT;
ALTER TABLE documents ADD COLUMN citation_text VARCHAR(500);

-- Legal document metadata fields
ALTER TABLE documents ADD COLUMN document_date DATE;
ALTER TABLE documents ADD COLUMN court_name VARCHAR(255);
ALTER TABLE documents ADD COLUMN case_number VARCHAR(255);
ALTER TABLE documents ADD COLUMN act_chapter VARCHAR(100);

-- Source verification and freshness tracking fields
ALTER TABLE documents ADD COLUMN last_verified_at DATETIME;
ALTER TABLE documents ADD COLUMN crawl_status VARCHAR(50) DEFAULT 'active';
ALTER TABLE documents ADD COLUMN freshness_score REAL DEFAULT 1.0;

-- Rich metadata (JSON for SQLite, JSONB for PostgreSQL)
ALTER TABLE documents ADD COLUMN legal_metadata TEXT;

-- ============================================================================
-- Create indexes for better query performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_documents_crawl_status ON documents(crawl_status);
CREATE INDEX IF NOT EXISTS idx_documents_freshness_score ON documents(freshness_score DESC);
CREATE INDEX IF NOT EXISTS idx_documents_document_date ON documents(document_date DESC);
CREATE INDEX IF NOT EXISTS idx_documents_court_name ON documents(court_name);
CREATE INDEX IF NOT EXISTS idx_documents_case_number ON documents(case_number);

-- ============================================================================
-- Update existing records with default values
-- ============================================================================

-- Set snippet for existing documents (first 200 chars of content)
UPDATE documents
SET snippet = SUBSTR(content, 1, 200) || CASE WHEN LENGTH(content) > 200 THEN '...' ELSE '' END
WHERE snippet IS NULL AND content IS NOT NULL;

-- Calculate and set freshness_score for existing documents
UPDATE documents
SET freshness_score = CASE
    WHEN CAST((julianday('now') - julianday(created_at)) AS INTEGER) = 0 THEN 1.0
    WHEN CAST((julianday('now') - julianday(created_at)) AS INTEGER) <= 30 THEN 0.95
    WHEN CAST((julianday('now') - julianday(created_at)) AS INTEGER) <= 90 THEN 0.85
    WHEN CAST((julianday('now') - julianday(created_at)) AS INTEGER) <= 365 THEN 0.7
    WHEN CAST((julianday('now') - julianday(created_at)) AS INTEGER) <= 1825 THEN 0.5
    ELSE 0.3
END
WHERE freshness_score IS NULL OR freshness_score = 1.0;

-- Set crawl_status to 'active' for existing documents
UPDATE documents
SET crawl_status = 'active'
WHERE crawl_status IS NULL;

-- Initialize empty legal_metadata for existing documents
UPDATE documents
SET legal_metadata = '{}'
WHERE legal_metadata IS NULL;
