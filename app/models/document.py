from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid

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
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"
