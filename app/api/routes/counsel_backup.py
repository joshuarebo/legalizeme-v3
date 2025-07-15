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
# from app.services.conversation_service import ConversationService

# Enhanced RAG services (with fallback)
try:
    from app.services.advanced.legal_rag import LegalRAGService
    HAS_ENHANCED_RAG = True
except ImportError:
    HAS_ENHANCED_RAG = False

# Agent services (with fallback)
try:
    from app.agents.legal_research_agent import LegalResearchAgent, ResearchStrategy
    HAS_AGENT = True
except ImportError:
    HAS_AGENT = False
from app.database import get_db
from app.models.user import User
from app.models.query import Query
from app.models.conversation import Conversation, ConversationMessage
import uuid
# Authentication removed - now public service layer
# from app.core.security import get_current_user
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
    use_enhanced_rag: bool = Field(default=True, description="Use enhanced RAG system (enabled by default for production)")
    agent_mode: bool = Field(default=False, description="Use intelligent agent mode for comprehensive research")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="Optional user context from frontend")
    # Conversation support
    conversation_id: Optional[str] = Field(default=None, description="Optional conversation ID for threading")
    message_history: Optional[List[Dict[str, str]]] = Field(default=None, description="Optional message history for context")

class LegalQueryResponse(BaseModel):
    query_id: str
    answer: str
    relevant_documents: List[Dict[str, Any]]
    confidence: float
    model_used: str
    processing_time: float
    timestamp: datetime
    # Enhanced RAG fields (optional)
    enhanced: bool = Field(default=False, description="Whether enhanced RAG was used")
    sources: Optional[List[Dict[str, Any]]] = Field(default=None, description="Enhanced source information")
    retrieval_strategy: Optional[str] = Field(default=None, description="Retrieval strategy used")
    # Agent mode fields (optional)
    agent_mode: bool = Field(default=False, description="Whether agent mode was used")
    research_strategy: Optional[str] = Field(default=None, description="Research strategy used by agent")
    reasoning_chain: Optional[List[str]] = Field(default=None, description="Agent reasoning chain")
    follow_up_suggestions: Optional[List[str]] = Field(default=None, description="Agent follow-up suggestions")
    related_queries: Optional[List[str]] = Field(default=None, description="Agent related queries")
    # Conversation support
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID if part of a conversation")
    message_id: Optional[str] = Field(default=None, description="Message ID in conversation")

class DocumentGenerationRequest(BaseModel):
    document_type: str = Field(..., description="Type of document to generate")
    parameters: Dict[str, Any] = Field(..., description="Parameters for document generation")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="Optional user context from frontend")

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

# Conversation models
class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Conversation title")
    agent_mode: Optional[bool] = Field(False, description="Enable agent mode")
    use_enhanced_rag: Optional[bool] = Field(True, description="Use enhanced RAG")

class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    agent_mode: bool
    use_enhanced_rag: bool
    message_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

class DirectQueryRequest(BaseModel):
    query: str = Field(..., max_length=settings.MAX_QUERY_LENGTH)
    model_preference: Optional[str] = Field(default=None, description="Preferred model: claude-sonnet, claude-haiku, or mistral-7b")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="Optional user context from frontend")

class DirectQueryResponse(BaseModel):
    response_text: str
    model_used: str
    model_id: str
    latency_ms: float
    success: bool
    timestamp: datetime

# Conversation Management Models
class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="Optional conversation title")
    agent_mode: bool = Field(default=False, description="Enable agent mode for this conversation")
    use_enhanced_rag: bool = Field(default=True, description="Enable enhanced RAG for this conversation")
    initial_context: Optional[Dict[str, Any]] = Field(default=None, description="Initial conversation context")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="User context from frontend")

class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    agent_mode: bool
    use_enhanced_rag: bool
    message_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime]

class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    agent_mode: Optional[bool] = None
    use_enhanced_rag: Optional[bool] = None
    context: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class ConversationMessageResponse(BaseModel):
    message_id: str
    role: str  # 'user' or 'assistant'
    content: str
    confidence: Optional[int] = None  # 0-100
    model_used: Optional[str] = None
    processing_time: Optional[int] = None  # milliseconds
    reasoning_chain: Optional[List[str]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    follow_up_suggestions: Optional[List[str]] = None
    created_at: datetime

class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    title: str
    message_count: int
    messages: List[ConversationMessageResponse]

# Initialize services
ai_service = AIService()
mcp_service = MCPService()
vector_service = VectorService()
# Initialize conversation service lazily to avoid startup issues
conversation_service = None

def get_conversation_service():
    """Get conversation service instance (lazy initialization)"""
    # Disabled for now to avoid NLTK issues
    return None

# Simple conversation endpoints for testing
@router.post("/conversations")
async def create_conversation_simple(
    request: ConversationCreateRequest,
    user_id: Optional[str] = FastAPIQuery(None, description="User ID for access control"),
    db: Session = Depends(get_db)
):
    """Create a new conversation (simplified version)"""
    try:
        # Simple conversation creation without complex service
        conversation_id = str(uuid.uuid4())

        return ConversationResponse(
            conversation_id=conversation_id,
            title=request.title or "New Conversation",
            agent_mode=request.agent_mode or False,
            use_enhanced_rag=request.use_enhanced_rag or True,
            message_count=0,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_message_at=None
        )

    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating conversation"
        )

@router.get("/conversations")
async def get_user_conversations_simple(
    user_id: Optional[str] = FastAPIQuery(None, description="User ID for access control"),
    limit: int = FastAPIQuery(10, description="Maximum number of conversations to return"),
    offset: int = FastAPIQuery(0, description="Number of conversations to skip"),
    active_only: bool = FastAPIQuery(True, description="Return only active conversations"),
    db: Session = Depends(get_db)
):
    """Get conversations for a user (simplified version)"""
    try:
        # Return empty list for now
        return []

    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversations"
        )

# Initialize agent (with fallback)
if HAS_AGENT:
    legal_research_agent = LegalResearchAgent()
else:
    legal_research_agent = None

@router.post("/query", response_model=LegalQueryResponse)
async def ask_legal_question(
    request: LegalQueryRequest,
    db: Session = Depends(get_db)
):
    """Ask a legal question and get AI-powered response"""
    start_time = datetime.utcnow()
    
    try:
        # Create query record with optional user_id
        user_id = None
        if request.user_context and 'user_id' in request.user_context:
            user_id = request.user_context['user_id']

        query_record = Query(
            user_id=user_id,
            query_text=request.query,
            query_type=request.query_type,
            context=request.context,
            status="processing"
        )
        
        db.add(query_record)
        db.commit()
        db.refresh(query_record)

        # Handle conversation threading
        conversation_id = request.conversation_id
        conversation_context = {}
        message_id = None

        if conversation_id:
            # Get conversation context
            conversation_context = get_conversation_service().get_conversation_context(
                db=db,
                conversation_id=conversation_id,
                include_messages=True,
                message_limit=10
            )

            # Add user message to conversation
            user_message = get_conversation_service().add_message(
                db=db,
                conversation_id=conversation_id,
                role="user",
                content=request.query,
                metadata={"query_id": str(query_record.uuid)}
            )

            # Merge conversation context with request context
            if conversation_context.get("conversation_context"):
                request.context = {**(request.context or {}), **conversation_context["conversation_context"]}

            # Override agent_mode and use_enhanced_rag from conversation settings
            if "agent_mode" in conversation_context:
                request.agent_mode = conversation_context["agent_mode"]
            if "use_enhanced_rag" in conversation_context:
                request.use_enhanced_rag = conversation_context["use_enhanced_rag"]

        # Initialize response tracking variables
        enhanced_used = False
        enhanced_sources = None
        retrieval_strategy = None
        agent_used = False
        research_strategy = None
        reasoning_chain = None
        follow_up_suggestions = None
        related_queries = None

        # Try agent mode first if requested and available
        if request.agent_mode and HAS_AGENT and legal_research_agent:
            try:
                logger.info(f"Using agent mode for query: {request.query[:50]}...")

                # Use comprehensive strategy for agent mode
                agent_result = await legal_research_agent.run_research(
                    query=request.query,
                    strategy=ResearchStrategy.COMPREHENSIVE,
                    top_k=5,
                    context=request.context or {}
                )

                if agent_result.confidence >= 0.5:  # Accept agent result if confidence is reasonable
                    # Convert agent response to standard format
                    relevant_docs = []
                    enhanced_sources = []

                    for citation in agent_result.citations:
                        # For backward compatibility
                        relevant_docs.append({
                            'title': citation.title,
                            'content': citation.excerpt,
                            'source': citation.source,
                            'relevance_score': citation.relevance_score
                        })

                        # For enhanced response
                        enhanced_sources.append({
                            'title': citation.title,
                            'citation': citation.citation,
                            'relevance_score': citation.relevance_score,
                            'url': citation.url,
                            'excerpt': citation.excerpt,
                            'document_type': citation.document_type
                        })

                    response = {
                        'answer': agent_result.answer,
                        'confidence': agent_result.confidence,
                        'model_used': agent_result.metadata.model_used,
                        'relevant_documents': relevant_docs
                    }

                    agent_used = True
                    retrieval_strategy = agent_result.retrieval_strategy
                    research_strategy = agent_result.research_strategy.value
                    reasoning_chain = agent_result.reasoning_chain
                    follow_up_suggestions = agent_result.follow_up_suggestions
                    related_queries = agent_result.related_queries

                    logger.info(f"Agent mode used successfully for query: {request.query[:50]}...")
                else:
                    # Fall back to enhanced RAG if agent confidence is low
                    logger.info("Agent confidence too low, falling back to enhanced RAG")
                    response = None  # Will trigger fallback below

            except Exception as e:
                logger.error(f"Agent mode failed, falling back to enhanced RAG: {e}")
                response = None  # Will trigger fallback below
        else:
            response = None  # Will use enhanced RAG or traditional approach

        # Try enhanced RAG if agent mode wasn't used or failed
        if not agent_used and request.use_enhanced_rag and HAS_ENHANCED_RAG and response is None:
            try:
                # Initialize enhanced RAG service
                enhanced_rag = LegalRAGService()
                await enhanced_rag.initialize()

                # Use enhanced RAG
                rag_response = await enhanced_rag.query_with_sources(
                    query=request.query,
                    max_sources=5,
                    strategy="hybrid"
                )

                if rag_response.confidence_score > 0.3:  # Use enhanced response if confident
                    response = {
                        'answer': rag_response.response_text,
                        'confidence': rag_response.confidence_score,
                        'model_used': rag_response.model_used,
                        'relevant_documents': []  # Will be populated from sources
                    }

                    # Convert enhanced sources to relevant documents format
                    relevant_docs = []
                    enhanced_sources = []

                    for source in rag_response.sources:
                        # For backward compatibility
                        relevant_docs.append({
                            'title': source.title,
                            'content': source.excerpt,
                            'source': source.source,
                            'relevance_score': source.relevance_score
                        })

                        # For enhanced response
                        enhanced_sources.append({
                            'title': source.title,
                            'citation': source.citation,
                            'relevance_score': source.relevance_score,
                            'url': source.url,
                            'excerpt': source.excerpt,
                            'document_type': source.document_type
                        })

                    response['relevant_documents'] = relevant_docs
                    enhanced_used = True
                    retrieval_strategy = rag_response.retrieval_strategy

                    logger.info(f"Enhanced RAG used successfully for query: {request.query[:50]}...")
                else:
                    # Fall back to traditional approach
                    logger.info("Enhanced RAG confidence too low, falling back to traditional approach")
                    response = await ai_service.answer_legal_query(request.query, request.context)

            except Exception as e:
                logger.error(f"Enhanced RAG failed, falling back to traditional: {e}")
                response = await ai_service.answer_legal_query(request.query, request.context)
        elif response is None:
            # Use traditional AI service as final fallback
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

        # Add assistant message to conversation if part of a conversation
        if conversation_id:
            assistant_message = get_conversation_service().add_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=response['answer'],
                query_id=str(query_record.uuid),
                confidence=response.get('confidence', 0.0),
                model_used=response.get('model_used', 'unknown'),
                processing_time=processing_time,
                reasoning_chain=reasoning_chain,
                citations=enhanced_sources,
                follow_up_suggestions=follow_up_suggestions,
                metadata={
                    "enhanced": enhanced_used,
                    "retrieval_strategy": retrieval_strategy,
                    "agent_mode": agent_used,
                    "research_strategy": research_strategy,
                    "related_queries": related_queries
                }
            )
            if assistant_message:
                message_id = str(assistant_message.uuid)

        return LegalQueryResponse(
            query_id=str(query_record.uuid),
            answer=response['answer'],
            relevant_documents=response.get('relevant_documents', []),
            confidence=response.get('confidence', 0.0),
            model_used=response.get('model_used', 'unknown'),
            processing_time=processing_time,
            timestamp=datetime.utcnow(),
            enhanced=enhanced_used,
            sources=enhanced_sources,
            retrieval_strategy=retrieval_strategy,
            agent_mode=agent_used,
            research_strategy=research_strategy,
            reasoning_chain=reasoning_chain,
            follow_up_suggestions=follow_up_suggestions,
            related_queries=related_queries,
            conversation_id=conversation_id,
            message_id=message_id
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
    request: DirectQueryRequest
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
        user_info = "anonymous"
        if request.user_context and 'user_id' in request.user_context:
            user_info = request.user_context['user_id']
        logger.info(f"Document generated for user {user_info}: {request.document_type}")
        
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
    db: Session = Depends(get_db)
):
    """Submit feedback for a query"""
    try:
        # Find the query (no user restriction since auth is removed)
        query = db.query(Query).filter(
            Query.uuid == feedback.query_id
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
    limit: int = FastAPIQuery(10, ge=1, le=50, description="Maximum number of results")
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
    user_id: Optional[str] = FastAPIQuery(None, description="Optional user ID to filter history"),
    db: Session = Depends(get_db)
):
    """Get query history (optionally filtered by user_id)"""
    try:
        query_filter = db.query(Query)
        if user_id:
            query_filter = query_filter.filter(Query.user_id == user_id)

        queries = query_filter.order_by(Query.created_at.desc()).offset(offset).limit(limit).all()
        
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
    query: str
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
async def get_user_conversations(
    user_id: Optional[str] = FastAPIQuery(None, description="User ID to filter conversations"),
    limit: int = FastAPIQuery(20, ge=1, le=100, description="Maximum number of conversations"),
    offset: int = FastAPIQuery(0, ge=0, description="Offset for pagination"),
    active_only: bool = FastAPIQuery(True, description="Only return active conversations"),
    db: Session = Depends(get_db)
):
    """Get conversations for a user"""
    try:
        if not user_id:
            return []

        conversations = get_conversation_service().get_user_conversations(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset,
            active_only=active_only
        )

        return [
            ConversationResponse(
                conversation_id=str(conv.uuid),
                title=conv.title,
                agent_mode=conv.agent_mode,
                use_enhanced_rag=conv.use_enhanced_rag,
                message_count=conv.message_count,
                is_active=conv.is_active,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                last_message_at=conv.last_message_at
            )
            for conv in conversations
        ]

    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversations"
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user_id: Optional[str] = FastAPIQuery(None, description="User ID for access control"),
    db: Session = Depends(get_db)
):
    """Get a specific conversation"""
    try:
        conversation = get_conversation_service().get_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return ConversationResponse(
            conversation_id=str(conversation.uuid),
            title=conversation.title,
            agent_mode=conversation.agent_mode,
            use_enhanced_rag=conversation.use_enhanced_rag,
            message_count=conversation.message_count,
            is_active=conversation.is_active,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversation"
        )

@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    user_id: Optional[str] = FastAPIQuery(None, description="User ID for access control"),
    db: Session = Depends(get_db)
):
    """Update a conversation"""
    try:
        # Verify conversation exists and user has access
        existing = get_conversation_service().get_conversation(db, conversation_id, user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        conversation = get_conversation_service().update_conversation(
            db=db,
            conversation_id=conversation_id,
            title=request.title,
            agent_mode=request.agent_mode,
            use_enhanced_rag=request.use_enhanced_rag,
            context=request.context,
            is_active=request.is_active
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return ConversationResponse(
            conversation_id=str(conversation.uuid),
            title=conversation.title,
            agent_mode=conversation.agent_mode,
            use_enhanced_rag=conversation.use_enhanced_rag,
            message_count=conversation.message_count,
            is_active=conversation.is_active,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating conversation"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: Optional[str] = FastAPIQuery(None, description="User ID for access control"),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    try:
        success = get_conversation_service().delete_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return {"message": "Conversation deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting conversation"
        )

@router.get("/conversations/{conversation_id}/messages", response_model=ConversationHistoryResponse)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = FastAPIQuery(50, ge=1, le=100, description="Maximum number of messages"),
    offset: int = FastAPIQuery(0, ge=0, description="Offset for pagination"),
    user_id: Optional[str] = FastAPIQuery(None, description="User ID for access control"),
    db: Session = Depends(get_db)
):
    """Get messages for a conversation"""
    try:
        # Verify conversation exists and user has access
        conversation = get_conversation_service().get_conversation(db, conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        messages = get_conversation_service().get_conversation_messages(
            db=db,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )

        message_responses = [
            ConversationMessageResponse(
                message_id=str(msg.uuid),
                role=msg.role,
                content=msg.content,
                confidence=msg.confidence,
                model_used=msg.model_used,
                processing_time=msg.processing_time,
                reasoning_chain=msg.reasoning_chain,
                citations=msg.citations,
                follow_up_suggestions=msg.follow_up_suggestions,
                created_at=msg.created_at
            )
            for msg in messages
        ]

        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            title=conversation.title,
            message_count=conversation.message_count,
            messages=message_responses
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversation messages"
        )
