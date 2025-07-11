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
    # Context framework fields
    enable_context_framework: bool = Field(default=True, description="Enable context engineering framework")
    max_sources: Optional[int] = Field(default=None, ge=1, le=20, description="Maximum number of sources (overrides top_k)")

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
    # Context framework fields
    context_used: Optional[Dict[str, Any]] = Field(default=None, description="Context information used")
    component_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Individual component performance metrics")

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

@router.get("/research")
async def agent_research_info():
    """
    Get information about the LegalResearchAgent endpoint.
    This endpoint provides details about the agent's capabilities and usage.
    """
    return {
        "agent_name": "LegalResearchAgent",
        "version": "1.0.0",
        "description": "Advanced AI agent for legal research with multi-step reasoning",
        "capabilities": [
            "Multi-step legal reasoning (retrieve → summarize → synthesize → respond)",
            "Confidence-based model fallbacks",
            "Memory tracking with Redis",
            "Citation management with source attribution",
            "Agentic chaining for complex legal decision-making"
        ],
        "usage": {
            "method": "POST",
            "endpoint": "/agents/research",
            "required_fields": ["query"],
            "optional_fields": ["context", "max_iterations", "confidence_threshold"],
            "example_request": {
                "query": "What are the legal requirements for employment contracts in Kenya?",
                "context": "employment law",
                "max_iterations": 3,
                "confidence_threshold": 0.8
            }
        },
        "models": [
            "Claude Sonnet 4 (Primary)",
            "Claude 3.7 (Secondary)",
            "Mistral Large (Fallback)"
        ],
        "status": "Production Ready",
        "documentation": "See /docs for interactive API documentation"
    }

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
        
        # Configure context framework if requested
        if hasattr(legal_research_agent, 'enable_context_framework'):
            legal_research_agent.enable_context_framework = request.enable_context_framework

        # Determine max_sources (prioritize max_sources over top_k)
        max_sources = request.max_sources or request.top_k

        # Perform agent research using enhanced method
        result = await legal_research_agent.research(
            query=request.query,
            strategy=research_strategy,
            max_sources=max_sources,
            confidence_threshold=request.confidence_threshold,
            context=request.context or {}
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
        
        # Extract context framework fields if available
        context_used = getattr(result, 'context_used', None)
        component_metrics = getattr(result, 'component_metrics', None)

        return AgentResearchResponse(
            answer=result.answer,
            confidence=result.confidence,
            citations=citations_response,
            retrieval_strategy=result.retrieval_strategy,
            research_strategy=result.research_strategy.value,
            metadata=metadata_response,
            reasoning_chain=result.reasoning_chain,
            follow_up_suggestions=result.follow_up_suggestions,
            related_queries=result.related_queries,
            context_used=context_used,
            component_metrics=component_metrics
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

class BenchmarkRequest(BaseModel):
    """Request model for benchmark execution"""
    level: Optional[int] = Field(default=None, ge=1, le=3, description="Benchmark level (1=basic, 2=intermediate, 3=advanced)")
    category: Optional[str] = Field(default=None, description="Benchmark category (employment_law, contract_law, etc.)")
    max_cases: int = Field(default=5, ge=1, le=20, description="Maximum number of cases to run")

@router.post("/benchmark")
async def run_benchmark(
    request: BenchmarkRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Run GAIA-style benchmarks on the Legal Research Agent.
    This endpoint is for testing and evaluation purposes.
    """

    try:
        # Import benchmark manager
        from tests.gaia_cases import BenchmarkManager

        # Initialize benchmark manager
        benchmark_manager = BenchmarkManager()
        await benchmark_manager.initialize()

        # Initialize agent if needed
        if not legal_research_agent._initialized:
            await legal_research_agent.initialize()

        # Run benchmark suite
        logger.info(f"Running benchmarks - Level: {request.level}, Category: {request.category}, Max cases: {request.max_cases}")

        suite_results = await benchmark_manager.run_benchmark_suite(
            level=request.level,
            category=request.category,
            agent=legal_research_agent,
            max_cases=request.max_cases
        )

        # Convert results to serializable format
        results_list = []
        for result in suite_results.get("suite_results", []):
            result_dict = {
                "case_id": result.case_id,
                "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                "score": result.score,
                "confidence": result.confidence,
                "execution_time_ms": result.execution_time_ms,
                "accuracy_score": result.accuracy_score,
                "completeness_score": result.completeness_score,
                "reasoning_score": result.reasoning_score,
                "citation_score": result.citation_score
            }
            results_list.append(result_dict)

        statistics = suite_results.get("statistics", {})

        logger.info(f"Benchmark completed. Total cases: {suite_results.get('total_cases', 0)}, Average score: {statistics.get('average_score', 0.0):.3f}")

        return {
            "total_cases": suite_results.get("total_cases", 0),
            "completion_rate": statistics.get("completion_rate", 0.0),
            "average_score": statistics.get("average_score", 0.0),
            "pass_rate": statistics.get("pass_rate", 0.0),
            "results": results_list,
            "statistics": statistics,
            "timestamp": datetime.utcnow()
        }

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Benchmark system is not available"
        )
    except Exception as e:
        logger.error(f"Error running benchmarks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {str(e)}"
        )

@router.get("/metrics")
async def get_agent_metrics(current_user: User = Depends(get_current_user)):
    """
    Get detailed metrics and performance statistics for the Legal Research Agent.
    """

    try:
        metrics = {}

        # Get basic agent metrics
        if hasattr(legal_research_agent, 'metrics'):
            metrics["agent"] = legal_research_agent.metrics

        # Get context manager metrics if available
        if hasattr(legal_research_agent, 'context_manager') and legal_research_agent.context_manager:
            context_metrics = legal_research_agent.context_manager.get_context_metrics()
            metrics["context_manager"] = context_metrics

        # Get component metrics if available
        if hasattr(legal_research_agent, 'enable_context_framework') and legal_research_agent.enable_context_framework:
            component_metrics = {}

            if hasattr(legal_research_agent, 'vector_retriever'):
                component_metrics["vector_retriever"] = legal_research_agent.vector_retriever.get_metrics()
            if hasattr(legal_research_agent, 'multi_source_summarizer'):
                component_metrics["multi_source_summarizer"] = legal_research_agent.multi_source_summarizer.get_metrics()
            if hasattr(legal_research_agent, 'legal_reasoner'):
                component_metrics["legal_reasoner"] = legal_research_agent.legal_reasoner.get_metrics()
            if hasattr(legal_research_agent, 'answer_formatter'):
                component_metrics["answer_formatter"] = legal_research_agent.answer_formatter.get_metrics()

            metrics["components"] = component_metrics

        # Get monitoring metrics if available
        if hasattr(legal_research_agent, 'agent_monitor'):
            monitoring_metrics = {
                "failure_statistics": legal_research_agent.agent_monitor.get_failure_statistics(),
                "quality_statistics": legal_research_agent.agent_monitor.get_quality_statistics()
            }
            metrics["monitoring"] = monitoring_metrics

        # Get refinement metrics if available
        if hasattr(legal_research_agent, 'context_refinement'):
            refinement_metrics = legal_research_agent.context_refinement.get_refinement_statistics()
            metrics["refinement"] = refinement_metrics

        return {
            "metrics": metrics,
            "timestamp": datetime.utcnow()
        }

    except Exception as e:
        logger.error(f"Error getting agent metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )
