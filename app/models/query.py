from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid

class Query(Base):
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Query details
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), nullable=False)  # legal_query, document_search, etc.
    context = Column(JSON, nullable=True)
    
    # Response
    response_text = Column(Text, nullable=True)
    response_metadata = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # AI model used
    ai_model = Column(String(100), nullable=True)
    model_parameters = Column(JSON, nullable=True)
    
    # Processing
    processing_time = Column(Float, nullable=True)  # in seconds
    status = Column(String(50), default="pending")  # pending, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    user_feedback = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="queries")
    
    def __repr__(self):
        return f"<Query(id={self.id}, user_id={self.user_id}, type='{self.query_type}')>"
