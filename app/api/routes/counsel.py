from fastapi import APIRouter, Depends, HTTPException, status, Query as FastAPIQuery
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from app.services.ai_service import AIService
from app.services.mcp_service import MCPService
from app.services.vector_service import VectorService
from app.services.llm_manager import llm_manager
from app.database import get_db
from app.models.user import User
from app.models.query import Query
from app.core.security import get_current_user
from app.config import settings
from app.crawlers.kenya_law_crawler import KenyaLawCrawler
from app.crawlers.parliament_crawler import ParliamentCrawler

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class LegalQueryRequest(BaseModel):
    query: str = Field(..., max_length=settings.MAX_QUERY_LENGTH)
    context: Optional[Dict[str, Any]] = None
    query_type: str = Field(default="legal_query")

class LegalQueryResponse(BaseModel):
    query_id: str
    answer: str
    relevant_documents: List[Dict[str, Any]]
    confidence: float
    model_used: str
    processing_time: float
    timestamp: datetime

class DocumentGenerationRequest(BaseModel):
    document_type: str = Field(..., description="Type of document to generate")
    parameters: Dict[str, Any] = Field(..., description="Parameters for document generation")

class DocumentGenerationResponse(BaseModel):
    document_type: str
    content: str
    parameters: Dict[str, Any]
    timestamp: datetime

class LegalResearchRequest(BaseModel):
    query: str = Field(..., max_length=settings.MAX_QUERY_LENGTH)
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

class DirectQueryRequest(BaseModel):
    query: str = Field(..., max_length=settings.MAX_QUERY_LENGTH)
    model_preference: Optional[str] = Field(default=None, description="Preferred model: claude-sonnet, claude-haiku, or mistral-7b")

class DirectQueryResponse(BaseModel):
    response_text: str
    model_used: str
    model_id: str
    latency_ms: float
    success: bool
    timestamp: datetime

# Initialize services
ai_service = AIService()
mcp_service = MCPService()
vector_service = VectorService()

@router.post("/query", response_model=LegalQueryResponse)
async def ask_legal_question(
    request: LegalQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ask a legal question and get AI-powered response"""
    start_time = datetime.utcnow()
    
    try:
        # Create query record
        query_record = Query(
            user_id=current_user.id,
            query_text=request.query,
            query_type=request.query_type,
            context=request.context,
            status="processing"
        )
        
        db.add(query_record)
        db.commit()
        db.refresh(query_record)
        
        # Process query using AI service
        response = await ai_service.answer_legal_query(request.query, request.context)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Update query record
        query_record.response_text = response['answer']
        query_record.response_metadata = response
        query_record.confidence_score = response.get('confidence', 0.0)
        query_record.processing_time = processing_time
        query_record.status = "completed"
        query_record.completed_at = datetime.utcnow()
        query_record.ai_model = response.get('model_used', 'unknown')
        
        db.commit()
        
        return LegalQueryResponse(
            query_id=str(query_record.uuid),
            answer=response['answer'],
            relevant_documents=response.get('relevant_documents', []),
            confidence=response.get('confidence', 0.0),
            model_used=response.get('model_used', 'unknown'),
            processing_time=processing_time,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error processing legal query: {e}")
        
        # Update query record with error
        if 'query_record' in locals():
            query_record.status = "failed"
            query_record.error_message = str(e)
            db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

@router.post("/query-direct", response_model=DirectQueryResponse)
async def direct_llm_query(
    request: DirectQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """Direct query to LLM manager with fallback logic - Production endpoint"""
    try:
        # Use LLM manager directly for production queries
        result = await llm_manager.invoke_model(
            prompt=request.query,
            model_preference=request.model_preference
        )

        return DirectQueryResponse(
            response_text=result['response_text'],
            model_used=result['model_used'],
            model_id=result['model_id'],
            latency_ms=result['latency_ms'],
            success=result['success'],
            timestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Error in direct LLM query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing direct query: {str(e)}"
        )

@router.post("/generate-document", response_model=DocumentGenerationResponse)
async def generate_legal_document(
    request: DocumentGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate legal documents"""
    try:
        # Validate document type
        valid_types = ['contract', 'agreement', 'notice', 'petition', 'affidavit', 'memorandum']
        if request.document_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Generate document using AI service
        document_content = await ai_service.generate_legal_document(
            request.document_type, 
            request.parameters
        )
        
        # Log the generation
        logger.info(f"Document generated for user {current_user.username}: {request.document_type}")
        
        return DocumentGenerationResponse(
            document_type=request.document_type,
            content=document_content,
            parameters=request.parameters,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating document: {str(e)}"
        )

@router.post("/research", response_model=LegalResearchResponse)
async def conduct_legal_research(
    request: LegalResearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Conduct comprehensive legal research"""
    try:
        # Use MCP service for comprehensive research
        research_request = {
            'type': 'legal_research',
            'query': request.query,
            'max_results': request.max_results,
            'sources': request.sources
        }
        
        response = await mcp_service.process_legal_request(research_request)
        
        if not response.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.get('error', 'Research failed')
            )
        
        return LegalResearchResponse(
            query=response['query'],
            summary=response['summary'],
            relevant_documents=response['relevant_documents'],
            total_results=response['total_results'],
            timestamp=datetime.fromisoformat(response['timestamp'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error conducting legal research: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error conducting research: {str(e)}"
        )

@router.post("/feedback")
async def submit_query_feedback(
    feedback: QueryFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback for a query"""
    try:
        # Find the query
        query = db.query(Query).filter(
            Query.uuid == feedback.query_id,
            Query.user_id == current_user.id
        ).first()
        
        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        
        # Update feedback
        query.user_rating = feedback.rating
        query.user_feedback = feedback.feedback
        
        db.commit()
        
        return {"message": "Feedback submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error submitting feedback"
        )

@router.get("/fetch-law")
async def fetch_legal_resources(
    query: str = FastAPIQuery(..., description="Search query for legal resources"),
    source: str = FastAPIQuery("all", description="Source to search: kenya_law, parliament, or all"),
    limit: int = FastAPIQuery(10, ge=1, le=50, description="Maximum number of results"),
    current_user: User = Depends(get_current_user)
):
    """Fetch legal resources from Kenya Law and Parliament websites"""
    try:
        results = []
        
        # Initialize crawlers based on source
        if source in ["kenya_law", "all"]:
            kenya_crawler = KenyaLawCrawler()
            kenya_results = await kenya_crawler.search_documents(query, limit=limit)
            results.extend(kenya_results)
            await kenya_crawler.close()
            
        if source in ["parliament", "all"]:
            parliament_crawler = ParliamentCrawler()
            parliament_results = await parliament_crawler.search_documents(query, limit=limit)
            results.extend(parliament_results)
            await parliament_crawler.close()
        
        # Sort by relevance if available
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Limit to requested number
        results = results[:limit]
        
        return {
            "query": query,
            "source": source,
            "total_results": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error fetching legal resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching legal resources: {str(e)}"
        )

@router.get("/history")
async def get_query_history(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's query history"""
    try:
        queries = db.query(Query).filter(
            Query.user_id == current_user.id
        ).order_by(Query.created_at.desc()).offset(offset).limit(limit).all()
        
        query_history = []
        for query in queries:
            query_history.append({
                'query_id': str(query.uuid),
                'query_text': query.query_text,
                'query_type': query.query_type,
                'response_text': query.response_text,
                'confidence_score': query.confidence_score,
                'processing_time': query.processing_time,
                'status': query.status,
                'user_rating': query.user_rating,
                'created_at': query.created_at,
                'completed_at': query.completed_at
            })
        
        return {
            'queries': query_history,
            'total': len(query_history),
            'offset': offset,
            'limit': limit
        }
        
    except Exception as e:
        logger.error(f"Error getting query history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving query history"
        )

@router.get("/suggest")
async def get_query_suggestions(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """Get query suggestions based on partial input"""
    try:
        # Search for similar documents to provide context
        similar_docs = await vector_service.search_similar_documents(query, limit=3)
        
        # Generate suggestions based on document titles and content
        suggestions = []
        for doc in similar_docs:
            # Extract key phrases from document titles
            title_words = doc.title.lower().split()
            for i, word in enumerate(title_words):
                if query.lower() in word:
                    # Create suggestion based on context
                    suggestion = f"What are the legal implications of {' '.join(title_words[max(0, i-2):i+3])}?"
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
        
        # Add some general suggestions
        general_suggestions = [
            "What are the requirements for contract formation in Kenya?",
            "How do I file a case in the High Court of Kenya?",
            "What are the employment laws in Kenya?",
            "How do I register a business in Kenya?",
            "What are the property rights in Kenya?"
        ]
        
        # Filter general suggestions based on query
        filtered_general = [s for s in general_suggestions if any(word in s.lower() for word in query.lower().split())]
        
        suggestions.extend(filtered_general)
        
        return {
            'suggestions': suggestions[:5],  # Return top 5 suggestions
            'query': query
        }
        
    except Exception as e:
        logger.error(f"Error getting query suggestions: {e}")
        return {
            'suggestions': [],
            'query': query,
            'error': str(e)
        }
