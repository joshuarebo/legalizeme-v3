from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Float
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid

class LegalCase(Base):
    __tablename__ = "legal_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Case identification
    case_number = Column(String(100), nullable=False, index=True)
    case_title = Column(String(500), nullable=False)
    case_citation = Column(String(200), nullable=True)
    
    # Court information
    court_name = Column(String(200), nullable=False)
    court_level = Column(String(50), nullable=True)  # high_court, court_of_appeal, supreme_court
    judge_names = Column(JSON, nullable=True)  # Array of judge names
    
    # Case details
    case_type = Column(String(100), nullable=True)  # civil, criminal, constitutional
    case_category = Column(String(100), nullable=True)
    case_status = Column(String(50), nullable=True)  # pending, decided, appealed
    
    # Dates
    filing_date = Column(DateTime(timezone=True), nullable=True)
    hearing_date = Column(DateTime(timezone=True), nullable=True)
    judgment_date = Column(DateTime(timezone=True), nullable=True)
    
    # Parties
    plaintiff = Column(String(300), nullable=True)
    defendant = Column(String(300), nullable=True)
    parties_json = Column(JSON, nullable=True)  # More detailed party information
    
    # Legal content
    case_summary = Column(Text, nullable=True)
    legal_issues = Column(JSON, nullable=True)  # Array of legal issues
    judgment_text = Column(Text, nullable=True)
    legal_precedents = Column(JSON, nullable=True)  # Referenced cases
    
    # Legislation references
    statutes_cited = Column(JSON, nullable=True)
    regulations_cited = Column(JSON, nullable=True)
    
    # Metadata
    keywords = Column(JSON, nullable=True)
    practice_areas = Column(JSON, nullable=True)
    outcome = Column(String(100), nullable=True)
    
    # Source information
    source_url = Column(String(1000), nullable=True)
    pdf_url = Column(String(1000), nullable=True)
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<LegalCase(id={self.id}, case_number='{self.case_number}', title='{self.case_title[:50]}...')>"
