"""
Agent API Routes
Provides endpoints for intelligent agent interactions and research
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
from enum import Enum

from app.agents.legal_research_agent import LegalResearchAgent, ResearchStrategy, AgenticResearchResponse
from app.database import get_db
from app.models.user import User
from app.models.query import Query
from app.core.security import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for API
class ResearchStrategyEnum(str, Enum):
    """Research strategy options for API"""
    QUICK = "quick"
    COMPREHENSIVE = "comprehensive"
    FOCUSED = "focused"
    EXPLORATORY = "exploratory"

class AgentResearchRequest(BaseModel):
    """Request model for agent research"""
    query: str = Field(..., max_length=settings.MAX_QUERY_LENGTH, description="The research question")
    strategy: ResearchStrategyEnum = Field(default=ResearchStrategyEnum.COMPREHENSIVE, description="Research strategy to use")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top sources to return")
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum confidence threshold")
    model_preference: str = Field(default="claude-sonnet-4", description="Preferred AI model")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for research")

class LegalSourceResponse(BaseModel):
    """Response model for legal sources"""
    title: str
    source: str
    url: Optional[str] = None
    document_type: str
    relevance_score: float
    excerpt: str
    citation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentMetadataResponse(BaseModel):
    """Response model for agent metadata"""
    timestamp: datetime
    model_used: str
    retrieval_strategy: str
    research_strategy: str
    processing_time_ms: float
    sources_consulted: int
    confidence_threshold: float
    retry_count: int = 0
    fallback_used: bool = False

class AgentResearchResponse(BaseModel):
    """Response model for agent research"""
    answer: str
    confidence: float
    citations: List[LegalSourceResponse]
    retrieval_strategy: str
    research_strategy: str
    metadata: AgentMetadataResponse
    reasoning_chain: List[str] = Field(default_factory=list)
    follow_up_suggestions: List[str] = Field(default_factory=list)
    related_queries: List[str] = Field(default_factory=list)

class AgentHealthResponse(BaseModel):
    """Response model for agent health check"""
    agent_status: str
    services: Dict[str, Any]
    timestamp: str

class AgentMetricsResponse(BaseModel):
    """Response model for agent metrics"""
    total_queries: int
    successful_queries: int
    success_rate: float
    avg_confidence: float
    avg_processing_time: float
    strategy_usage: Dict[str, int]
    fallback_usage: int
    memory_size: int
    initialized: bool

class AgentMemoryResponse(BaseModel):
    """Response model for agent memory"""
    total_queries: int
    recent_queries: List[Dict[str, Any]]

# Initialize agent with Redis support if available
redis_url = getattr(settings, 'REDIS_URL', None)
legal_research_agent = LegalResearchAgent(redis_url=redis_url)

@router.post("/research", response_model=AgentResearchResponse)
async def agent_research(
    request: AgentResearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform intelligent legal research using the Legal Research Agent
    
    This endpoint provides agentic behavior with intelligent chaining,
    fallback strategies, and comprehensive source analysis.
    """
    try:
        # Create query record for tracking
        query_record = Query(
            user_id=current_user.id,
            query_text=request.query,
            query_type="agent_research",
            context=request.context,
            status="processing"
        )
        
        db.add(query_record)
        db.commit()
        db.refresh(query_record)
        
        # Convert enum to ResearchStrategy
        strategy_mapping = {
            ResearchStrategyEnum.QUICK: ResearchStrategy.QUICK,
            ResearchStrategyEnum.COMPREHENSIVE: ResearchStrategy.COMPREHENSIVE,
            ResearchStrategyEnum.FOCUSED: ResearchStrategy.FOCUSED,
            ResearchStrategyEnum.EXPLORATORY: ResearchStrategy.EXPLORATORY
        }
        
        research_strategy = strategy_mapping[request.strategy]
        
        # Perform agent research
        result = await legal_research_agent.run_research(
            query=request.query,
            strategy=research_strategy,
            top_k=request.top_k,
            confidence_threshold=request.confidence_threshold,
            model_preference=request.model_preference,
            context=request.context or {},
            user_id=str(current_user.id)  # Pass user ID for memory
        )
        
        # Update query record
        query_record.status = "completed"
        query_record.response = result.answer
        query_record.confidence = result.confidence
        query_record.model_used = result.metadata.model_used
        query_record.processing_time = result.metadata.processing_time_ms / 1000.0  # Convert to seconds
        db.commit()
        
        # Convert to response model
        citations_response = [
            LegalSourceResponse(
                title=citation.title,
                source=citation.source,
                url=citation.url,
                document_type=citation.document_type,
                relevance_score=citation.relevance_score,
                excerpt=citation.excerpt,
                citation=citation.citation,
                metadata=citation.metadata
            )
            for citation in result.citations
        ]
        
        metadata_response = AgentMetadataResponse(
            timestamp=result.metadata.timestamp,
            model_used=result.metadata.model_used,
            retrieval_strategy=result.metadata.retrieval_strategy,
            research_strategy=result.metadata.research_strategy.value,
            processing_time_ms=result.metadata.processing_time_ms,
            sources_consulted=result.metadata.sources_consulted,
            confidence_threshold=result.metadata.confidence_threshold,
            retry_count=result.metadata.retry_count,
            fallback_used=result.metadata.fallback_used
        )
        
        return AgentResearchResponse(
            answer=result.answer,
            confidence=result.confidence,
            citations=citations_response,
            retrieval_strategy=result.retrieval_strategy,
            research_strategy=result.research_strategy.value,
            metadata=metadata_response,
            reasoning_chain=result.reasoning_chain,
            follow_up_suggestions=result.follow_up_suggestions,
            related_queries=result.related_queries
        )
        
    except Exception as e:
        # Update query record with error
        if 'query_record' in locals():
            query_record.status = "failed"
            query_record.error_message = str(e)
            db.commit()
        
        logger.error(f"Error in agent research: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent research failed: {str(e)}"
        )

@router.get("/health", response_model=AgentHealthResponse)
async def agent_health_check(
    current_user: User = Depends(get_current_user)
):
    """Get health status of the Legal Research Agent and its services"""
    try:
        health_status = await legal_research_agent.health_check()

        return AgentHealthResponse(
            agent_status=health_status["agent_status"],
            services=health_status["services"],
            timestamp=health_status["timestamp"]
        )

    except Exception as e:
        logger.error(f"Error in agent health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent health check failed: {str(e)}"
        )

@router.get("/metrics", response_model=AgentMetricsResponse)
async def agent_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for the Legal Research Agent"""
    try:
        metrics = legal_research_agent.get_metrics()

        return AgentMetricsResponse(
            total_queries=metrics["total_queries"],
            successful_queries=metrics["successful_queries"],
            success_rate=metrics["success_rate"],
            avg_confidence=metrics["avg_confidence"],
            avg_processing_time=metrics["avg_processing_time"],
            strategy_usage=metrics["strategy_usage"],
            fallback_usage=metrics["fallback_usage"],
            memory_size=metrics["memory_size"],
            initialized=metrics["initialized"]
        )

    except Exception as e:
        logger.error(f"Error getting agent metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent metrics: {str(e)}"
        )

@router.get("/memory", response_model=AgentMemoryResponse)
async def agent_memory(
    current_user: User = Depends(get_current_user)
):
    """Get agent memory summary for current user"""
    try:
        user_memory = await legal_research_agent.get_user_memory_summary(str(current_user.id))

        return AgentMemoryResponse(
            total_queries=user_memory.get("recent_queries_count", 0),
            recent_queries=user_memory.get("recent_queries", [])
        )

    except Exception as e:
        logger.error(f"Error getting agent memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent memory: {str(e)}"
        )

@router.delete("/memory")
async def clear_agent_memory(
    current_user: User = Depends(get_current_user)
):
    """Clear agent memory for current user"""
    try:
        await legal_research_agent.clear_user_memory(str(current_user.id))

        return {
            "success": True,
            "message": "Agent memory cleared successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error clearing agent memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear agent memory: {str(e)}"
        )

@router.get("/memory/related")
async def get_related_queries(
    query: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user)
):
    """Get queries related to the provided query for current user"""
    try:
        related_queries = await legal_research_agent.get_related_queries(
            str(current_user.id),
            query,
            limit
        )

        return {
            "query": query,
            "related_queries": related_queries,
            "count": len(related_queries),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting related queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get related queries: {str(e)}"
        )

@router.post("/initialize")
async def initialize_agent(
    current_user: User = Depends(get_current_user)
):
    """Initialize the Legal Research Agent and its services"""
    try:
        # Check if user is admin for initialization
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can initialize the agent"
            )

        await legal_research_agent.initialize()

        return {
            "success": True,
            "message": "Legal Research Agent initialized successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error initializing agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent initialization failed: {str(e)}"
        )
