from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON, Boolean, Date
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import TypeDecorator
from app.database import Base, IS_SQLITE
import uuid


# Create a flexible JSON type that works with both SQLite and PostgreSQL
class FlexibleJSON(TypeDecorator):
    """JSON type that uses JSON for SQLite and JSONB for PostgreSQL"""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    url = Column(String(1000), nullable=True)
    source = Column(String(100), nullable=False)  # kenya_law, parliament, etc.
    document_type = Column(String(100), nullable=False)  # judgment, legislation, etc.
    
    # Metadata
    jurisdiction = Column(String(100), default="kenya")
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)
    
    # Content analysis
    language = Column(String(10), default="en")
    word_count = Column(Integer, nullable=True)
    readability_score = Column(Float, nullable=True)
    
    # Vector embeddings
    embedding = Column(JSON, nullable=True)  # Store as JSON array
    embedding_model = Column(String(100), nullable=True)
    
    # Status and metadata
    is_processed = Column(Boolean, default=False)
    is_indexed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_indexed = Column(DateTime(timezone=True), nullable=True)

    # Relevance scoring (for search results)
    relevance_score = Column(Float, nullable=True)

    # ============================================================================
    # NEW FIELDS FOR INTERACTIVE SOURCES (Phase 2.5 Enhancement)
    # ============================================================================

    # Interactive source preview
    snippet = Column(Text, nullable=True)  # 200-char preview for hover tooltips
    citation_text = Column(String(500), nullable=True)  # e.g., "Employment Act 2007, Section 45"

    # Legal document metadata
    document_date = Column(Date, nullable=True)  # Date of judgment/enactment
    court_name = Column(String(255), nullable=True)  # For judgments (e.g., "High Court of Kenya")
    case_number = Column(String(255), nullable=True)  # For case law (e.g., "Petition No. 123 of 2024")
    act_chapter = Column(String(100), nullable=True)  # For legislation (e.g., "Cap. 49")

    # Source verification and freshness tracking
    last_verified_at = Column(DateTime(timezone=True), nullable=True)  # Last time URL was verified
    crawl_status = Column(String(50), default="active")  # 'active', 'stale', 'broken', 'pending'
    freshness_score = Column(Float, default=1.0)  # 1.0 = today, decreases over time

    # Rich metadata (JSONB for flexible structure)
    # Stores: judges, parties, legal_issues, amendments, sections, etc.
    legal_metadata = Column(FlexibleJSON, nullable=True)
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"

    def calculate_freshness_score(self) -> float:
        """
        Calculate freshness score based on creation date and last verification
        Returns: float between 0.0 and 1.0
        - 1.0: Document from today
        - 0.95: Within last 30 days
        - 0.85: Within last 90 days
        - 0.7: Within last year
        - 0.5: Within 5 years
        - 0.3: Older than 5 years
        """
        from datetime import datetime

        # Use last_verified_at if available, otherwise created_at
        reference_date = self.last_verified_at or self.created_at

        if not reference_date:
            return 0.5  # Default for unknown age

        days_old = (datetime.utcnow() - reference_date.replace(tzinfo=None)).days

        if days_old == 0:
            return 1.0
        elif days_old <= 30:
            return 0.95
        elif days_old <= 90:
            return 0.85
        elif days_old <= 365:
            return 0.7
        elif days_old <= 1825:  # 5 years
            return 0.5
        else:
            return 0.3

    def generate_snippet(self, max_length: int = 200) -> str:
        """
        Generate a snippet from content for preview
        Args:
            max_length: Maximum length of snippet
        Returns: Truncated content with ellipsis
        """
        if not self.content:
            return ""

        # Use existing snippet if available
        if self.snippet:
            return self.snippet

        # Generate from content
        clean_content = self.content.strip()
        if len(clean_content) <= max_length:
            return clean_content

        # Truncate at last complete word before max_length
        truncated = clean_content[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]

        return truncated + "..."

    def to_dict(self, include_content: bool = False) -> dict:
        """
        Convert document to dictionary for API responses
        Args:
            include_content: Whether to include full content
        Returns: Dictionary representation
        """
        data = {
            "id": str(self.uuid),
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "document_type": self.document_type,
            "snippet": self.snippet or self.generate_snippet(),
            "citation_text": self.citation_text,
            "document_date": self.document_date.isoformat() if self.document_date else None,
            "court_name": self.court_name,
            "case_number": self.case_number,
            "act_chapter": self.act_chapter,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "crawl_status": self.crawl_status,
            "freshness_score": self.freshness_score or self.calculate_freshness_score(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "legal_metadata": self.legal_metadata or {}
        }

        if include_content:
            data["content"] = self.content
            data["summary"] = self.summary

        return data
