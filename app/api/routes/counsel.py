from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.ai_service import AIService
from app.services.llm_manager import llm_manager
from app.services.conversation_service import ConversationService
from app.services.intelligent_cache_service import intelligent_cache_service
from app.services.kenyan_legal_prompt_optimizer import kenyan_legal_prompt_optimizer
from app.services.aws_embedding_service import aws_embedding_service
from app.services.streaming_agent_service import streaming_agent_service
from app.services.streaming_rag_service import streaming_rag_service
from app.services.production_monitoring_service import production_monitoring_service
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
    """
    OPTIMIZED LEGAL QUERY ENDPOINT
    =============================
    Enhanced with intelligent caching, prompt optimization, and AWS-native RAG
    """
    start_time = datetime.utcnow()

    try:
        # Initialize services if needed
        if not intelligent_cache_service._initialized:
            await intelligent_cache_service.initialize()
        if not kenyan_legal_prompt_optimizer._initialized:
            await kenyan_legal_prompt_optimizer.initialize()

        query_id = f"query_{int(start_time.timestamp())}"

        # Step 1: Check intelligent cache first (always check, even for agent mode)
        query_embedding = await aws_embedding_service.generate_embeddings(request.query)
        cached_response = await intelligent_cache_service.get_cached_response(
            request.query,
            query_embedding
        )

        if cached_response:
            logger.info(f"Cache HIT for query: {request.query[:50]}...")
            cached_response["query_id"] = query_id
            cached_response["processing_time"] = (datetime.utcnow() - start_time).total_seconds()
            cached_response["timestamp"] = datetime.utcnow()
            cached_response["enhanced"] = request.use_enhanced_rag
            cached_response["agent_mode"] = request.agent_mode
            cached_response["cached"] = True

            return LegalQueryResponse(**cached_response)

        # Step 2: Enhanced RAG processing for complex queries
        if request.use_enhanced_rag and not request.agent_mode:
            response = await _process_enhanced_rag_query(request, query_embedding)
        # Step 3: Agent mode processing
        elif request.agent_mode:
            response = await _process_agent_mode_query(request)
        # Step 4: Direct optimized query
        else:
            response = await _process_direct_optimized_query(request)

        processing_time = (datetime.utcnow() - start_time).total_seconds()
        processing_time_ms = processing_time * 1000

        # Step 5: Record monitoring metrics
        await production_monitoring_service.record_api_request(
            endpoint="/api/v1/counsel/query",
            response_time_ms=processing_time_ms,
            model_used=response.get("model_used", "unknown"),
            success=response.get("success", False),
            cache_hit=cached_response is not None,
            confidence=response.get("confidence", 0.0),
            legal_area=response.get("legal_area", "general"),
            error_type=None if response.get("success") else "processing_error"
        )

        # Step 6: Cache successful responses
        if response.get("success") and response.get("confidence", 0) > 0.6:  # Lowered threshold
            await intelligent_cache_service.cache_response(
                query=request.query,
                response={
                    "answer": response.get("response_text", ""),
                    "confidence": response.get("confidence", 0.8),
                    "model_used": response.get("model_used", "unknown"),
                    "processing_time": processing_time_ms,
                    "relevant_documents": [],
                    "sources": response.get("sources", []),
                    "success": True
                },
                query_embedding=query_embedding,
                force_cache=response.get("confidence", 0) > 0.8  # Force cache high confidence responses
            )

        return LegalQueryResponse(
            query_id=query_id,
            answer=response.get("response_text", "I apologize, but I'm unable to process your query at the moment."),
            relevant_documents=response.get("relevant_documents", []),
            confidence=response.get("confidence", 0.8 if response.get("success") else 0.3),
            model_used=response.get("model_used", "claude-sonnet-4"),
            processing_time=processing_time,
            timestamp=datetime.utcnow(),
            enhanced=request.use_enhanced_rag,
            agent_mode=request.agent_mode,
            sources=response.get("sources", []),
            retrieval_strategy=response.get("retrieval_strategy"),
            reasoning_chain=response.get("reasoning_chain", []),
            follow_up_suggestions=response.get("follow_up_suggestions", [])
        )

    except Exception as e:
        logger.error(f"Error processing legal query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing legal query"
        )

async def _process_direct_optimized_query(request: LegalQueryRequest) -> Dict[str, Any]:
    """Process direct query with optimized prompts"""
    try:
        # Optimize prompt for Kenyan legal context
        optimized_prompt = kenyan_legal_prompt_optimizer.optimize_for_speed(request.query)

        # Use intelligent model selection with speed mode
        response = await llm_manager.invoke_model(
            prompt=optimized_prompt,
            model_preference="claude-sonnet-4",
            speed_mode=True
        )

        return response

    except Exception as e:
        logger.error(f"Error in direct optimized query: {e}")
        return {"success": False, "response_text": "Error processing query", "error": str(e)}

async def _process_enhanced_rag_query(request: LegalQueryRequest, query_embedding: Optional[List[float]]) -> Dict[str, Any]:
    """Process query with enhanced AWS-native RAG"""
    try:
        # Use AWS-native RAG service (will implement next)
        from app.services.aws_rag_service import aws_rag_service

        rag_response = await aws_rag_service.query_with_context(
            query=request.query,
            context=request.context or {},
            max_sources=5,
            query_embedding=query_embedding
        )

        return {
            "success": True,
            "response_text": rag_response.get("answer", ""),
            "confidence": rag_response.get("confidence", 0.8),
            "model_used": rag_response.get("model_used", "claude-sonnet-4"),
            "relevant_documents": rag_response.get("documents", []),
            "sources": rag_response.get("sources", []),
            "retrieval_strategy": "aws_native_rag"
        }

    except ImportError:
        # Fallback to direct query if RAG service not available
        logger.warning("AWS RAG service not available, falling back to direct query")
        return await _process_direct_optimized_query(request)
    except Exception as e:
        logger.error(f"Error in enhanced RAG query: {e}")
        return await _process_direct_optimized_query(request)

async def _process_agent_mode_query(request: LegalQueryRequest) -> Dict[str, Any]:
    """Process query with agent mode (chain-of-thought reasoning)"""
    try:
        # Build context-engineered prompt for agent reasoning
        agent_prompt = kenyan_legal_prompt_optimizer.optimize_prompt(
            query=request.query,
            query_type="agent_research",
            context=request.context
        )

        # Add chain-of-thought reasoning structure
        reasoning_prompt = f"""{agent_prompt}

CHAIN-OF-THOUGHT REASONING:
Please think through this step by step:

1. LEGAL ISSUE IDENTIFICATION:
   - What is the core legal question?
   - Which area of Kenyan law applies?

2. LEGAL FRAMEWORK ANALYSIS:
   - What are the relevant statutes and regulations?
   - Are there any recent amendments or cases?

3. PRACTICAL APPLICATION:
   - How does this apply to the specific situation?
   - What are the compliance requirements?

4. RECOMMENDATIONS:
   - What immediate steps should be taken?
   - When should professional legal advice be sought?

Please provide your reasoning for each step, then give a comprehensive final answer."""

        # Use parallel processing for agent mode to get fastest response
        response = await llm_manager.invoke_model_parallel(
            prompt=reasoning_prompt,
            max_concurrent=2
        )

        # Extract reasoning chain from response
        reasoning_chain = _extract_reasoning_chain(response.get("response_text", ""))

        response["reasoning_chain"] = reasoning_chain
        response["retrieval_strategy"] = "agent_reasoning"

        return response

    except Exception as e:
        logger.error(f"Error in agent mode query: {e}")
        return await _process_direct_optimized_query(request)

def _extract_reasoning_chain(response_text: str) -> List[str]:
    """Extract reasoning steps from agent response"""
    try:
        reasoning_steps = []
        lines = response_text.split('\n')

        current_step = ""
        for line in lines:
            if any(marker in line.upper() for marker in ["1.", "2.", "3.", "4.", "STEP", "ANALYSIS"]):
                if current_step:
                    reasoning_steps.append(current_step.strip())
                current_step = line
            elif current_step:
                current_step += " " + line

        if current_step:
            reasoning_steps.append(current_step.strip())

        return reasoning_steps[:4]  # Limit to 4 main steps

    except Exception:
        return ["Legal analysis completed with comprehensive reasoning"]

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

@router.get("/suggestions")
async def get_query_suggestions_alt(
    query: str,
    limit: int = 5
):
    """Get query suggestions based on partial input (alternative endpoint)"""
    try:
        # Enhanced suggestions for legal queries
        base_suggestions = [
            f"What are the legal requirements for {query} in Kenya?",
            f"How to comply with {query} regulations in Kenya?",
            f"What are the penalties for non-compliance with {query}?",
            f"What documents are needed for {query} in Kenya?",
            f"What are the procedures for {query} under Kenyan law?",
            f"What are the rights and obligations regarding {query}?",
            f"How does {query} affect employment law in Kenya?",
            f"What are the constitutional provisions on {query}?"
        ]

        return {
            "suggestions": base_suggestions[:limit],
            "query": query,
            "total_suggestions": len(base_suggestions[:limit])
        }

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return {
            "suggestions": [],
            "query": query,
            "total_suggestions": 0,
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

@router.get("/documents")
async def get_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get uploaded documents - redirects to multimodal service"""
    try:
        return {
            "documents": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "message": "Document management available at /api/v1/multimodal/documents",
            "redirect_url": "/api/v1/multimodal/documents"
        }

    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        return {
            "documents": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "error": str(e)
        }

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

@router.post("/query-stream")
async def stream_legal_question(
    query: str = Query(..., description="Legal question to analyze"),
    session_id: Optional[str] = Query(None, description="Session ID for tracking"),
    context: Optional[str] = Query(None, description="Additional context as JSON string")
):
    """
    STREAMING AGENT ENDPOINT
    =======================
    Stream agent response with real-time updates to prevent timeouts
    """
    try:
        # Parse context if provided
        parsed_context = None
        if context:
            import json
            try:
                parsed_context = json.loads(context)
            except json.JSONDecodeError:
                parsed_context = {"raw_context": context}

        # Stream the agent response
        return await streaming_agent_service.stream_agent_response(
            query=query,
            context=parsed_context,
            session_id=session_id
        )

    except Exception as e:
        logger.error(f"Error in streaming endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing streaming query"
        )

@router.post("/rag-stream")
async def stream_rag_query(
    query: str = Query(..., description="Legal question for RAG analysis"),
    legal_area: Optional[str] = Query(None, description="Legal area filter"),
    max_sources: int = Query(5, description="Maximum source documents"),
    session_id: Optional[str] = Query(None, description="Session ID for tracking")
):
    """
    STREAMING RAG ENDPOINT
    =====================
    Stream RAG response with progressive document retrieval and real-time feedback
    """
    try:
        # Stream the RAG response
        return await streaming_rag_service.stream_rag_response(
            query=query,
            legal_area=legal_area,
            max_sources=max_sources,
            session_id=session_id
        )

    except Exception as e:
        logger.error(f"Error in RAG streaming endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing streaming RAG query"
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@router.get("/monitoring/dashboard")
async def get_monitoring_dashboard():
    """
    PRODUCTION MONITORING DASHBOARD
    ==============================
    Get real-time performance metrics and analytics
    """
    try:
        # Get performance dashboard
        dashboard_data = production_monitoring_service.get_performance_dashboard()

        # Get cache analytics
        cache_analytics = intelligent_cache_service.get_cache_analytics()

        # Get search analytics if available
        search_analytics = {}
        try:
            from app.services.aws_opensearch_service import aws_opensearch_service
            search_analytics = await aws_opensearch_service.get_search_analytics()
        except Exception as e:
            search_analytics = {"error": f"Search analytics unavailable: {e}"}

        return {
            "performance": dashboard_data,
            "cache": cache_analytics,
            "search": search_analytics,
            "timestamp": datetime.utcnow(),
            "status": "active"
        }

    except Exception as e:
        logger.error(f"Error getting monitoring dashboard: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow(),
            "status": "error"
        }

@router.get("/monitoring/cache-stats")
async def get_cache_statistics():
    """Get detailed cache performance statistics"""
    try:
        return intelligent_cache_service.get_cache_analytics()
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        return {"error": str(e)}
