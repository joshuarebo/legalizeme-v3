-- Migration: Add Interactive Source Fields for Enhanced RAG Citations
-- Created: 2025-01-15
-- Description: Adds new fields to documents table to support interactive citations,
--              source verification, and rich metadata for frontend display

-- ============================================================================
-- Add new columns to documents table
-- ============================================================================

-- Interactive source preview fields
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS snippet TEXT,
ADD COLUMN IF NOT EXISTS citation_text VARCHAR(500);

-- Legal document metadata fields
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS document_date DATE,
ADD COLUMN IF NOT EXISTS court_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS case_number VARCHAR(255),
ADD COLUMN IF NOT EXISTS act_chapter VARCHAR(100);

-- Source verification and freshness tracking fields
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS crawl_status VARCHAR(50) DEFAULT 'active',
ADD COLUMN IF NOT EXISTS freshness_score FLOAT DEFAULT 1.0;

-- Rich metadata (JSONB for flexible structure)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS legal_metadata JSONB;

-- ============================================================================
-- Create indexes for better query performance
-- ============================================================================

-- Index on crawl_status for filtering active/broken sources
CREATE INDEX IF NOT EXISTS idx_documents_crawl_status ON documents(crawl_status);

-- Index on freshness_score for sorting by freshness
CREATE INDEX IF NOT EXISTS idx_documents_freshness_score ON documents(freshness_score DESC);

-- Index on document_date for temporal filtering
CREATE INDEX IF NOT EXISTS idx_documents_document_date ON documents(document_date DESC);

-- Index on court_name for filtering by court
CREATE INDEX IF NOT EXISTS idx_documents_court_name ON documents(court_name);

-- Index on case_number for quick case lookup
CREATE INDEX IF NOT EXISTS idx_documents_case_number ON documents(case_number);

-- GIN index on legal_metadata JSONB for flexible querying
CREATE INDEX IF NOT EXISTS idx_documents_legal_metadata_gin ON documents USING GIN (legal_metadata);

-- ============================================================================
-- Update existing records with default values
-- ============================================================================

-- Set snippet for existing documents (first 200 chars of content)
UPDATE documents
SET snippet = LEFT(content, 200) || CASE WHEN LENGTH(content) > 200 THEN '...' ELSE '' END
WHERE snippet IS NULL AND content IS NOT NULL;

-- Calculate and set freshness_score for existing documents
UPDATE documents
SET freshness_score = CASE
    WHEN EXTRACT(DAY FROM (NOW() - created_at)) = 0 THEN 1.0
    WHEN EXTRACT(DAY FROM (NOW() - created_at)) <= 30 THEN 0.95
    WHEN EXTRACT(DAY FROM (NOW() - created_at)) <= 90 THEN 0.85
    WHEN EXTRACT(DAY FROM (NOW() - created_at)) <= 365 THEN 0.7
    WHEN EXTRACT(DAY FROM (NOW() - created_at)) <= 1825 THEN 0.5
    ELSE 0.3
END
WHERE freshness_score IS NULL OR freshness_score = 1.0;

-- Set crawl_status to 'active' for existing documents
UPDATE documents
SET crawl_status = 'active'
WHERE crawl_status IS NULL;

-- Initialize empty legal_metadata for existing documents
UPDATE documents
SET legal_metadata = '{}'::jsonb
WHERE legal_metadata IS NULL;

-- ============================================================================
-- Add comments to new columns for documentation
-- ============================================================================

COMMENT ON COLUMN documents.snippet IS 'Short preview (200 chars) for hover tooltips';
COMMENT ON COLUMN documents.citation_text IS 'Formatted citation text (e.g., "Employment Act 2007, Section 45")';
COMMENT ON COLUMN documents.document_date IS 'Date of judgment or enactment';
COMMENT ON COLUMN documents.court_name IS 'Name of court for judgments';
COMMENT ON COLUMN documents.case_number IS 'Case number for legal cases';
COMMENT ON COLUMN documents.act_chapter IS 'Chapter number for legislation';
COMMENT ON COLUMN documents.last_verified_at IS 'Last time URL was verified as accessible';
COMMENT ON COLUMN documents.crawl_status IS 'Status: active, stale, broken, pending';
COMMENT ON COLUMN documents.freshness_score IS 'Freshness score (1.0 = today, decreases over time)';
COMMENT ON COLUMN documents.legal_metadata IS 'JSONB field for flexible legal metadata (judges, parties, sections, etc.)';

-- ============================================================================
-- Verification query
-- ============================================================================

-- Check that all columns were added successfully
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'documents'
AND column_name IN (
    'snippet', 'citation_text', 'document_date', 'court_name',
    'case_number', 'act_chapter', 'last_verified_at', 'crawl_status',
    'freshness_score', 'legal_metadata'
)
ORDER BY column_name;

-- Count of documents updated
SELECT
    COUNT(*) as total_documents,
    COUNT(snippet) as with_snippet,
    COUNT(freshness_score) as with_freshness_score,
    AVG(freshness_score) as avg_freshness_score
FROM documents;
