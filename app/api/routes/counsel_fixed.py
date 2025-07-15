from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from app.services.ai_service import AIService
from app.services.llm_manager import llm_manager
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class LegalQueryRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    context: Optional[Dict[str, Any]] = None
    query_type: str = Field(default="legal_query")
    use_enhanced_rag: bool = Field(default=True)
    agent_mode: bool = Field(default=False)
    user_context: Optional[Dict[str, Any]] = Field(default=None)
    conversation_id: Optional[str] = Field(default=None)
    message_history: Optional[List[Dict[str, str]]] = Field(default=None)

class LegalQueryResponse(BaseModel):
    query_id: str
    answer: str
    relevant_documents: List[Dict[str, Any]]
    confidence: float
    model_used: str
    processing_time: float
    timestamp: datetime
    enhanced: bool = Field(default=False)
    sources: Optional[List[Dict[str, Any]]] = Field(default=None)
    retrieval_strategy: Optional[str] = Field(default=None)
    agent_mode: bool = Field(default=False)
    research_strategy: Optional[str] = Field(default=None)
    reasoning_chain: Optional[List[str]] = Field(default=None)
    follow_up_suggestions: Optional[List[str]] = Field(default=None)
    related_queries: Optional[List[str]] = Field(default=None)

class DirectQueryRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    model_preference: Optional[str] = Field(None)

class DirectQueryResponse(BaseModel):
    response_text: str
    model_used: str
    model_id: str
    latency_ms: float
    success: bool
    timestamp: datetime

class DocumentGenerationRequest(BaseModel):
    document_type: str = Field(...)
    parameters: Dict[str, Any] = Field(...)

class DocumentGenerationResponse(BaseModel):
    document_type: str
    content: str
    parameters: Dict[str, Any]
    timestamp: datetime

class LegalResearchRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    max_results: int = Field(default=10, ge=1, le=50)
    sources: List[str] = Field(default=["kenya_law", "parliament"])

class LegalResearchResponse(BaseModel):
    query: str
    summary: str
    relevant_documents: List[Dict[str, Any]]
    total_results: int
    timestamp: datetime

class QueryFeedback(BaseModel):
    query_id: str
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None

# Initialize services
ai_service = AIService()

@router.post("/query", response_model=LegalQueryResponse)
async def ask_legal_question(request: LegalQueryRequest):
    """Ask a legal question and get AI-powered response"""
    start_time = datetime.utcnow()
    
    try:
        # Simple implementation without complex dependencies
        query_id = f"query_{int(start_time.timestamp())}"
        
        # Use LLM manager for direct query
        response_data = await llm_manager.invoke_model(
            prompt=request.query,
            model_preference="claude-sonnet-4"
        )
        response_text = response_data.get("response_text", "")

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return LegalQueryResponse(
            query_id=query_id,
            answer=response_text or "I apologize, but I'm unable to process your query at the moment.",
            relevant_documents=[],
            confidence=0.7,  # Default confidence since we don't have this from LLM
            model_used=response_data.get("model_used", "claude-sonnet-4"),
            processing_time=processing_time,
            timestamp=datetime.utcnow(),
            enhanced=request.use_enhanced_rag,
            agent_mode=request.agent_mode
        )
        
    except Exception as e:
        logger.error(f"Error processing legal query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing legal query"
        )

@router.post("/query-direct", response_model=DirectQueryResponse)
async def direct_llm_query(request: DirectQueryRequest):
    """Direct query to LLM manager with fallback logic"""
    try:
        start_time = datetime.utcnow()
        
        response_data = await llm_manager.invoke_model(
            prompt=request.query,
            model_preference=request.model_preference or "claude-sonnet-4"
        )
        response_text = response_data.get("response_text", "")

        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return DirectQueryResponse(
            response_text=response_text or "Unable to process query",
            model_used=response_data.get("model_used", "claude-sonnet-4"),
            model_id=response_data.get("model_id", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
            latency_ms=latency_ms,
            success=response_data.get("success", True),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error in direct LLM query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing direct query"
        )

@router.post("/generate-document", response_model=DocumentGenerationResponse)
async def generate_legal_document(request: DocumentGenerationRequest):
    """Generate legal documents"""
    try:
        # Simple document generation
        content = f"Generated {request.document_type} document with parameters: {request.parameters}"
        
        return DocumentGenerationResponse(
            document_type=request.document_type,
            content=content,
            parameters=request.parameters,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating document"
        )

@router.post("/research", response_model=LegalResearchResponse)
async def conduct_legal_research(request: LegalResearchRequest):
    """Conduct comprehensive legal research"""
    try:
        # Simple research implementation
        summary = f"Research summary for: {request.query}"
        
        return LegalResearchResponse(
            query=request.query,
            summary=summary,
            relevant_documents=[],
            total_results=0,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error conducting research: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error conducting research"
        )

@router.post("/feedback")
async def submit_query_feedback(feedback: QueryFeedback):
    """Submit feedback for a query"""
    try:
        logger.info(f"Feedback received for query {feedback.query_id}: {feedback.rating}/5")
        return {"message": "Feedback submitted successfully", "query_id": feedback.query_id}
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error submitting feedback"
        )

@router.get("/suggest")
async def get_query_suggestions(query: str):
    """Get query suggestions based on partial input"""
    try:
        # Simple suggestions
        suggestions = [
            f"{query} in Kenya",
            f"{query} legal requirements",
            f"{query} procedures",
            f"{query} rights and obligations"
        ]
        
        return {
            "suggestions": suggestions[:4],
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return {
            "suggestions": [],
            "query": query,
            "error": str(e)
        }
