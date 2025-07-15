from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.ai_service import AIService
from app.services.llm_manager import llm_manager
from app.services.conversation_service import ConversationService
from app.database import get_db
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

# Enhanced RAG models
class EnhancedRAGRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    context: Optional[str] = Field(default="")
    max_tokens: int = Field(default=4000)

class EnhancedRAGResponse(BaseModel):
    success: bool
    response: str
    model_used: str
    retrieved_documents: int
    context_tokens: int
    total_tokens: int
    cost_estimate: Dict[str, Any]
    sources: List[str]
    similarities: List[float]
    latency_ms: int

# Conversation models
class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None)
    agent_mode: bool = Field(default=False)
    use_enhanced_rag: bool = Field(default=True)
    initial_context: Optional[Dict[str, Any]] = Field(default=None)

class ConversationResponse(BaseModel):
    id: str
    title: str
    agent_mode: bool
    use_enhanced_rag: bool
    context: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None)
    agent_mode: Optional[bool] = Field(default=None)
    use_enhanced_rag: Optional[bool] = Field(default=None)

class ConversationMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    created_at: datetime

# Services will be initialized on-demand to avoid startup crashes
# ai_service = AIService()

# Global conversation service instance (lazy-initialized)
_conversation_service = None

def get_conversation_service():
    """Get conversation service instance with lazy initialization"""
    global _conversation_service
    if _conversation_service is None:
        try:
            _conversation_service = ConversationService()
            logger.info("✅ ConversationService lazy-initialized successfully")
        except Exception as e:
            logger.error(f"❌ ConversationService lazy initialization failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Conversation service unavailable: {e}"
            )
    return _conversation_service

@router.post("/init-db")
async def initialize_database(db: Session = Depends(get_db)):
    """Initialize conversation database tables (admin endpoint)"""
    try:
        from app.models.conversation import Conversation, ConversationMessage
        from app.database import Base, engine

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Test table creation by checking if tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        conversation_tables = [table for table in tables if 'conversation' in table.lower()]

        return {
            "success": True,
            "message": "Database tables initialized successfully",
            "conversation_tables": conversation_tables,
            "total_tables": len(tables)
        }

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database initialization failed: {str(e)}"
        )

@router.get("/debug-conversation-service")
async def debug_conversation_service():
    """Debug conversation service status"""
    try:
        # Check if ConversationService can be imported
        from app.services.conversation_service import ConversationService
        import_success = True
        import_error = None
    except Exception as e:
        import_success = False
        import_error = str(e)

    # Check global variable
    global _conversation_service
    service_status = "initialized" if _conversation_service is not None else "not_initialized"

    # Try to initialize
    init_success = False
    init_error = None
    try:
        test_service = get_conversation_service()
        init_success = True
    except Exception as e:
        init_error = str(e)

    return {
        "import_success": import_success,
        "import_error": import_error,
        "service_status": service_status,
        "init_success": init_success,
        "init_error": init_error,
        "function_exists": callable(get_conversation_service)
    }

@router.post("/query", response_model=LegalQueryResponse)
async def ask_legal_question(request: LegalQueryRequest):
    """Ask a legal question and get AI-powered response"""
    start_time = datetime.utcnow()
    
    try:
        # Simple implementation without complex dependencies
        query_id = f"query_{int(start_time.timestamp())}"
        
        # Use LLM manager for direct query
        response = await llm_manager.invoke_model(
            prompt=request.query,
            model_preference="claude-sonnet-4"
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return LegalQueryResponse(
            query_id=query_id,
            answer=response.get("response_text", "I apologize, but I'm unable to process your query at the moment."),
            relevant_documents=[],
            confidence=0.8 if response.get("success") else 0.3,
            model_used=response.get("model_used", "claude-sonnet-4"),
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
        
        response = await llm_manager.invoke_model(
            prompt=request.query,
            model_preference=request.model_preference or "claude-sonnet-4"
        )
        
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return DirectQueryResponse(
            response_text=response.get("response_text", "Unable to process query"),
            model_used=response.get("model_used", "claude-sonnet-4"),
            model_id=response.get("model_id", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
            latency_ms=latency_ms,
            success=response.get("success", True),
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
async def get_query_suggestions(
    query: str,
    args: Optional[str] = None,
    kwargs: Optional[str] = None
):
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

# Conversation Management Endpoints

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    try:
        conversation = get_conversation_service().create_conversation(
            db=db,
            user_id=None,  # No user authentication in public service layer
            title=request.title,
            agent_mode=request.agent_mode,
            use_enhanced_rag=request.use_enhanced_rag,
            initial_context=request.initial_context
        )

        return ConversationResponse(
            id=str(conversation.uuid),
            title=conversation.title,
            agent_mode=conversation.agent_mode,
            use_enhanced_rag=conversation.use_enhanced_rag,
            context=conversation.context or {},
            created_at=conversation.created_at,
            updated_at=conversation.updated_at or conversation.created_at
        )

    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating conversation: {str(e)}"
        )

@router.get("/conversations")
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    args: Optional[str] = None,
    kwargs: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List conversations"""
    try:
        conversations = get_conversation_service().get_user_conversations(
            db=db,
            user_id=None,  # No user authentication in public service layer
            limit=limit,
            offset=offset
        )

        return {
            "conversations": [
                ConversationResponse(
                    id=str(conv.uuid),
                    title=conv.title,
                    agent_mode=conv.agent_mode,
                    use_enhanced_rag=conv.use_enhanced_rag,
                    context=conv.context or {},
                    created_at=conv.created_at,
                    updated_at=conv.updated_at or conv.created_at
                )
                for conv in conversations
            ],
            "total": len(conversations),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing conversations: {str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    args: Optional[str] = None,
    kwargs: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get a specific conversation"""
    try:
        conversation = get_conversation_service().get_conversation(db, conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return ConversationResponse(
            id=str(conversation.uuid),
            title=conversation.title,
            agent_mode=conversation.agent_mode,
            use_enhanced_rag=conversation.use_enhanced_rag,
            context=conversation.context or {},
            created_at=conversation.created_at,
            updated_at=conversation.updated_at or conversation.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting conversation: {str(e)}"
        )

@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update a conversation"""
    try:
        conversation = get_conversation_service().update_conversation(
            db=db,
            conversation_id=conversation_id,
            title=request.title,
            agent_mode=request.agent_mode,
            use_enhanced_rag=request.use_enhanced_rag
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return ConversationResponse(
            id=str(conversation.uuid),
            title=conversation.title,
            agent_mode=conversation.agent_mode,
            use_enhanced_rag=conversation.use_enhanced_rag,
            context=conversation.context or {},
            created_at=conversation.created_at,
            updated_at=conversation.updated_at or conversation.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating conversation: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Delete a conversation"""
    try:
        success = get_conversation_service().delete_conversation(db, conversation_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return {"message": "Conversation deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting conversation: {str(e)}"
        )

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    args: Optional[str] = None,
    kwargs: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get messages for a conversation"""
    try:
        messages = get_conversation_service().get_conversation_messages(
            db=db,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )

        return {
            "messages": [
                ConversationMessageResponse(
                    id=str(msg.id),
                    conversation_id=str(msg.conversation_id),
                    role=msg.role,
                    content=msg.content,
                    metadata=msg.metadata or {},
                    created_at=msg.created_at
                )
                for msg in messages
            ],
            "total": len(messages),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting conversation messages: {str(e)}"
        )



@router.post("/query-enhanced-rag", response_model=EnhancedRAGResponse)
async def enhanced_rag_query(request: EnhancedRAGRequest):
    """Enhanced RAG query with AWS-native services (simplified implementation)"""
    start_time = datetime.utcnow()

    try:
        # Simplified implementation using existing working services
        # Use LLM manager directly for now to avoid initialization issues

        # Create enhanced prompt with context
        enhanced_prompt = f"""
        Context: {request.context}

        Legal Query: {request.query}

        Please provide a comprehensive legal response based on Kenyan law, including:
        1. Direct answer to the query
        2. Relevant legal provisions
        3. Practical guidance
        4. Any important considerations
        """

        # Use LLM manager for response generation
        response = await llm_manager.invoke_model(
            prompt=enhanced_prompt,
            model_preference="claude-sonnet-4"
        )

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Create response in expected format
        return EnhancedRAGResponse(
            success=response.get("success", True),
            response=response.get("response_text", "Unable to process query at this time."),
            model_used=response.get("model_used", "claude-sonnet-4"),
            retrieved_documents=0,  # Simplified - no actual retrieval yet
            context_tokens=len(enhanced_prompt.split()),
            total_tokens=len(enhanced_prompt.split()) + len(response.get("response_text", "").split()),
            cost_estimate={"total_cost": 0.01, "input_cost": 0.005, "output_cost": 0.005},
            sources=["AWS Bedrock Claude Sonnet 4"],
            similarities=[0.8],
            latency_ms=int(processing_time)
        )

    except Exception as e:
        logger.error(f"Error in enhanced RAG query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing enhanced RAG query: {str(e)}"
        )
