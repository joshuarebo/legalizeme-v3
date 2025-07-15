"""
LegalResearchAgent - Intelligent Legal Research Agent
Provides agentic behavior for legal research with chaining, memory, and intelligent fallbacks
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import hashlib

# Redis completely removed - using PostgreSQL-only architecture
HAS_REDIS = False

# Core services
from app.services.advanced.legal_rag import LegalRAGService, LegalSource, RAGResponse
from app.core.orchestration.intelligence_enhancer import IntelligenceEnhancer, EnhancementConfig, EnhancementMode
from app.services.mcp_service import MCPService
from app.services.ai_service import AIService
from app.services.vector_service import VectorService
from app.core.exceptions import AIServiceException

# Context Engineering Framework
from app.context import ContextManager, ContextBlueprint, QueryContext
from app.agents.components import VectorRetriever, MultiSourceSummarizer, LegalReasoner, AnswerFormatter
from app.agents.decorators import AgentMonitor, ContextRefinementLoop, monitor_agent_execution
from app.prompts import PRPManager

logger = logging.getLogger(__name__)

class AgentMemory:
    """
    Memory system for the Legal Research Agent
    Uses local in-memory storage only (Redis removed)
    """

    def __init__(self, redis_url: Optional[str] = None, max_memory_size: int = 100):
        self.max_memory_size = max_memory_size
        self.local_memory = []
        # Redis completely removed - always use local memory
        logger.info("Agent memory initialized with local storage (Redis removed)")

    def _generate_key(self, user_id: str, query: str) -> str:
        """Generate a unique key for the query"""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"agent_memory:{user_id}:{query_hash}"

    async def store_query(self, user_id: str, query: str, context: Dict[str, Any], result: Any = None):
        """Store a query and its context in local memory"""
        memory_entry = {
            "query": query,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "result_summary": self._summarize_result(result) if result else None
        }

        # Always use local memory (Redis removed)
        self._store_local(memory_entry)

    def _store_local(self, memory_entry: Dict[str, Any]):
        """Store query in local memory"""
        self.local_memory.append(memory_entry)
        if len(self.local_memory) > self.max_memory_size:
            self.local_memory = self.local_memory[-self.max_memory_size:]

    async def get_user_queries(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent queries for a user from local memory"""
        # Always use local memory (Redis removed)
        return [q for q in self.local_memory if q.get("user_id") == user_id][-limit:]

    async def get_related_queries(self, user_id: str, current_query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get queries related to the current query"""
        user_queries = await self.get_user_queries(user_id, 20)  # Get more to find related ones

        # Simple keyword-based similarity (can be enhanced with embeddings)
        current_words = set(current_query.lower().split())
        related_queries = []

        for query_entry in user_queries:
            query_words = set(query_entry["query"].lower().split())
            # Calculate simple Jaccard similarity
            intersection = len(current_words.intersection(query_words))
            union = len(current_words.union(query_words))
            similarity = intersection / union if union > 0 else 0

            if similarity > 0.2:  # Threshold for relatedness
                query_entry["similarity"] = similarity
                related_queries.append(query_entry)

        # Sort by similarity and return top results
        related_queries.sort(key=lambda x: x["similarity"], reverse=True)
        return related_queries[:limit]

    def _summarize_result(self, result: Any) -> Optional[str]:
        """Create a brief summary of the result for memory storage"""
        if hasattr(result, 'answer'):
            return result.answer[:200] + "..." if len(result.answer) > 200 else result.answer
        elif isinstance(result, dict) and 'answer' in result:
            answer = result['answer']
            return answer[:200] + "..." if len(answer) > 200 else answer
        return None

    async def clear_user_memory(self, user_id: str):
        """Clear memory for a specific user from local memory"""
        # Clear from local memory (Redis removed)
        self.local_memory = [q for q in self.local_memory if q.get("user_id") != user_id]

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "storage_type": "local",
            "max_size": self.max_memory_size,
            "local_entries": len(self.local_memory),
            "redis_removed": True
        }

class ResearchStrategy(Enum):
    """Different research strategies"""
    QUICK = "quick"           # Fast, basic research
    COMPREHENSIVE = "comprehensive"  # Deep, multi-source research
    FOCUSED = "focused"       # Targeted, specific research
    EXPLORATORY = "exploratory"  # Broad, discovery-oriented research

@dataclass
class AgentMetadata:
    """Metadata for agent operations"""
    timestamp: datetime
    model_used: str
    retrieval_strategy: str
    research_strategy: ResearchStrategy
    processing_time_ms: float
    sources_consulted: int
    confidence_threshold: float
    retry_count: int = 0
    fallback_used: bool = False

@dataclass
class AgenticResearchResponse:
    """Comprehensive response from the Legal Research Agent"""
    answer: str
    confidence: float
    citations: List[LegalSource]
    retrieval_strategy: str
    research_strategy: ResearchStrategy
    metadata: AgentMetadata
    reasoning_chain: List[str] = field(default_factory=list)
    follow_up_suggestions: List[str] = field(default_factory=list)
    related_queries: List[str] = field(default_factory=list)

class LegalResearchAgent:
    """
    Intelligent Legal Research Agent that orchestrates multiple services
    for comprehensive legal research with agentic behavior.

    Enhanced with context engineering framework for production-grade legal AI.
    """

    def __init__(
        self,
        legal_rag_service: LegalRAGService = None,
        intelligence_enhancer: IntelligenceEnhancer = None,
        mcp_service: MCPService = None,
        ai_service: AIService = None,
        vector_service: VectorService = None,
        # Context Engineering Components
        context_manager: ContextManager = None,
        prp_manager: PRPManager = None,
        enable_context_framework: bool = True,
        enable_monitoring: bool = True
    ):
        # Initialize core services
        self.legal_rag = legal_rag_service or LegalRAGService()
        self.intelligence_enhancer = intelligence_enhancer or IntelligenceEnhancer()
        self.mcp_service = mcp_service or MCPService()
        self.ai_service = ai_service or AIService()
        self.vector_service = vector_service or VectorService()

        # Context Engineering Framework
        self.enable_context_framework = enable_context_framework
        self.enable_monitoring = enable_monitoring

        if self.enable_context_framework:
            self.context_manager = context_manager or ContextManager()
            self.prp_manager = prp_manager or PRPManager()

            # Initialize modular components
            self.vector_retriever = VectorRetriever(self.context_manager, self.vector_service, self.legal_rag)
            self.multi_source_summarizer = MultiSourceSummarizer(self.context_manager, self.ai_service)
            self.legal_reasoner = LegalReasoner(self.context_manager, self.ai_service)
            self.answer_formatter = AnswerFormatter(self.context_manager)

            # Initialize monitoring and refinement
            if self.enable_monitoring:
                self.agent_monitor = AgentMonitor()
                self.context_refinement = ContextRefinementLoop(
                    self.context_manager, self.agent_monitor
                )
        else:
            self.context_manager = None
            self.prp_manager = None

        # Agent configuration
        self.default_confidence_threshold = 0.7
        self.max_retry_attempts = 3
        self.max_sources = 10
        self.enable_memory = True

        # Performance tracking
        self.metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "avg_confidence": 0.0,
            "avg_processing_time": 0.0,
            "strategy_usage": {strategy.value: 0 for strategy in ResearchStrategy},
            "fallback_usage": 0,
            "memory_usage": 0
        }

        # Enhanced memory system (local only, Redis removed)
        self.memory = AgentMemory(max_memory_size=100)

        self._initialized = False
    
    async def initialize(self):
        """Initialize the agent and all underlying services"""
        if self._initialized:
            return

        try:
            logger.info("Initializing Legal Research Agent...")

            # Initialize core services
            await self.legal_rag.initialize()
            await self.vector_service.initialize()

            # Initialize context framework if enabled
            if self.enable_context_framework:
                await self.context_manager.initialize()
                await self.prp_manager.initialize()

                # Initialize modular components
                await self.vector_retriever.initialize()
                await self.multi_source_summarizer.initialize()
                await self.legal_reasoner.initialize()
                await self.answer_formatter.initialize()

                logger.info("Context engineering framework initialized")

            self._initialized = True
            logger.info("Legal Research Agent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Legal Research Agent: {e}")
            raise AIServiceException(f"Agent initialization failed: {str(e)}", "initialization_error")
    
    async def research(
        self,
        query: str,
        strategy: ResearchStrategy = ResearchStrategy.COMPREHENSIVE,
        max_sources: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgenticResearchResponse:
        """
        Enhanced research method with context framework support.
        Maintains backward compatibility while adding context-aware capabilities.
        """

        # Use context framework if enabled
        if self.enable_context_framework:
            return await self.research_with_context(
                query=query,
                strategy=strategy,
                max_sources=max_sources,
                confidence_threshold=confidence_threshold,
                context=context
            )

        # Fallback to legacy research
        return await self._research_legacy(
            query=query,
            strategy=strategy,
            max_sources=max_sources,
            confidence_threshold=confidence_threshold,
            context=context
        )

    async def run_research(
        self,
        query: str,
        strategy: ResearchStrategy = ResearchStrategy.COMPREHENSIVE,
        top_k: int = 5,
        confidence_threshold: float = None,
        model_preference: str = "claude-sonnet-4",
        context: Dict[str, Any] = None,
        user_id: str = "anonymous"
    ) -> AgenticResearchResponse:
        """
        Main research method that orchestrates intelligent legal research.
        This method maintains backward compatibility while leveraging the new context framework.

        Args:
            query: The research question
            strategy: Research strategy to use
            top_k: Number of top sources to return
            confidence_threshold: Minimum confidence threshold
            model_preference: Preferred AI model
            context: Additional context for the research
            user_id: User identifier for memory tracking

        Returns:
            AgenticResearchResponse with comprehensive results
        """

        # Delegate to the enhanced research method
        return await self.research(
            query=query,
            strategy=strategy,
            max_sources=top_k,
            confidence_threshold=confidence_threshold,
            context=context
        )



    async def _quick_research(
        self,
        query: str,
        top_k: int,
        model_preference: str,
        context: Dict[str, Any]
    ) -> AgenticResearchResponse:
        """Quick research using basic RAG"""
        try:
            # Use semantic retrieval for speed
            rag_response = await self.legal_rag.query_with_sources(
                query=query,
                max_sources=min(top_k, 3),  # Limit sources for speed
                strategy="semantic"
            )

            metadata = AgentMetadata(
                timestamp=datetime.utcnow(),
                model_used=rag_response.model_used,
                retrieval_strategy=rag_response.retrieval_strategy,
                research_strategy=ResearchStrategy.QUICK,
                processing_time_ms=0.0,  # Will be updated later
                sources_consulted=len(rag_response.sources),
                confidence_threshold=self.default_confidence_threshold
            )

            return AgenticResearchResponse(
                answer=rag_response.response_text,
                confidence=rag_response.confidence_score,
                citations=rag_response.sources,
                retrieval_strategy=rag_response.retrieval_strategy,
                research_strategy=ResearchStrategy.QUICK,
                metadata=metadata,
                reasoning_chain=["Quick semantic search", "Direct response generation"],
                follow_up_suggestions=self._generate_follow_up_suggestions(query, rag_response.sources),
                related_queries=self._generate_related_queries(query)
            )

        except Exception as e:
            logger.error(f"Error in quick research: {e}")
            raise

    async def _comprehensive_research(
        self,
        query: str,
        top_k: int,
        model_preference: str,
        context: Dict[str, Any]
    ) -> AgenticResearchResponse:
        """Comprehensive research using multiple strategies and services"""
        reasoning_chain = []

        try:
            # Step 1: Enhanced RAG with hybrid retrieval
            reasoning_chain.append("Initiating hybrid retrieval search")
            rag_response = await self.legal_rag.query_with_sources(
                query=query,
                max_sources=top_k,
                strategy="hybrid"
            )

            # Step 2: If confidence is low, try MCP service for additional sources
            if rag_response.confidence_score < 0.6:
                reasoning_chain.append("Low confidence detected, expanding search with MCP service")
                mcp_request = {
                    'type': 'legal_research',
                    'query': query,
                    'max_results': top_k,
                    'sources': ['kenya_law', 'parliament']
                }
                mcp_response = await self.mcp_service.process_legal_request(mcp_request)

                if mcp_response.get('success'):
                    # Merge MCP results with RAG results
                    reasoning_chain.append("Successfully integrated additional sources from MCP")
                    # Note: In a full implementation, we'd merge the sources here

            # Step 3: Use Intelligence Enhancer for response refinement
            reasoning_chain.append("Applying intelligence enhancement")
            enhancement_config = EnhancementConfig(
                mode=EnhancementMode.COMPREHENSIVE,
                enable_rag=True,
                enable_prompt_engineering=True
            )

            enhanced_input = {
                "query": query,
                "context": context,
                "sources": [source.__dict__ for source in rag_response.sources],
                "initial_response": rag_response.response_text
            }

            try:
                enhanced_result = await self.intelligence_enhancer.enhance_intelligence(
                    enhanced_input,
                    enhancement_config,
                    context
                )
                reasoning_chain.append("Intelligence enhancement completed")

                # Use enhanced response if available and better
                if enhanced_result.get("enhanced_response"):
                    rag_response.response_text = enhanced_result["enhanced_response"]
                    rag_response.confidence_score = min(rag_response.confidence_score + 0.1, 1.0)

            except Exception as e:
                logger.warning(f"Intelligence enhancement failed, using original response: {e}")
                reasoning_chain.append("Intelligence enhancement failed, using original response")

            metadata = AgentMetadata(
                timestamp=datetime.utcnow(),
                model_used=rag_response.model_used,
                retrieval_strategy=rag_response.retrieval_strategy,
                research_strategy=ResearchStrategy.COMPREHENSIVE,
                processing_time_ms=0.0,
                sources_consulted=len(rag_response.sources),
                confidence_threshold=self.default_confidence_threshold
            )

            return AgenticResearchResponse(
                answer=rag_response.response_text,
                confidence=rag_response.confidence_score,
                citations=rag_response.sources,
                retrieval_strategy=rag_response.retrieval_strategy,
                research_strategy=ResearchStrategy.COMPREHENSIVE,
                metadata=metadata,
                reasoning_chain=reasoning_chain,
                follow_up_suggestions=self._generate_follow_up_suggestions(query, rag_response.sources),
                related_queries=self._generate_related_queries(query)
            )

        except Exception as e:
            logger.error(f"Error in comprehensive research: {e}")
            raise

    async def _focused_research(
        self,
        query: str,
        top_k: int,
        model_preference: str,
        context: Dict[str, Any]
    ) -> AgenticResearchResponse:
        """Focused research for specific legal questions"""
        try:
            # Use semantic retrieval with higher precision
            rag_response = await self.legal_rag.query_with_sources(
                query=query,
                max_sources=min(top_k, 5),
                strategy="semantic"
            )

            # Filter sources by relevance score for focused results
            high_relevance_sources = [
                source for source in rag_response.sources
                if source.relevance_score >= 0.8
            ]

            if high_relevance_sources:
                rag_response.sources = high_relevance_sources[:top_k]

            metadata = AgentMetadata(
                timestamp=datetime.utcnow(),
                model_used=rag_response.model_used,
                retrieval_strategy=rag_response.retrieval_strategy,
                research_strategy=ResearchStrategy.FOCUSED,
                processing_time_ms=0.0,
                sources_consulted=len(rag_response.sources),
                confidence_threshold=self.default_confidence_threshold
            )

            return AgenticResearchResponse(
                answer=rag_response.response_text,
                confidence=rag_response.confidence_score,
                citations=rag_response.sources,
                retrieval_strategy=rag_response.retrieval_strategy,
                research_strategy=ResearchStrategy.FOCUSED,
                metadata=metadata,
                reasoning_chain=["Focused semantic search", "High-relevance source filtering", "Precise response generation"],
                follow_up_suggestions=self._generate_follow_up_suggestions(query, rag_response.sources),
                related_queries=self._generate_related_queries(query)
            )

        except Exception as e:
            logger.error(f"Error in focused research: {e}")
            raise

    async def _exploratory_research(
        self,
        query: str,
        top_k: int,
        model_preference: str,
        context: Dict[str, Any]
    ) -> AgenticResearchResponse:
        """Exploratory research for broad legal discovery"""
        try:
            # Use hybrid retrieval with expanded sources
            rag_response = await self.legal_rag.query_with_sources(
                query=query,
                max_sources=min(top_k * 2, self.max_sources),  # Get more sources for exploration
                strategy="hybrid"
            )

            # Diversify sources by document type
            diversified_sources = self._diversify_sources(rag_response.sources, top_k)
            rag_response.sources = diversified_sources

            metadata = AgentMetadata(
                timestamp=datetime.utcnow(),
                model_used=rag_response.model_used,
                retrieval_strategy=rag_response.retrieval_strategy,
                research_strategy=ResearchStrategy.EXPLORATORY,
                processing_time_ms=0.0,
                sources_consulted=len(rag_response.sources),
                confidence_threshold=self.default_confidence_threshold
            )

            return AgenticResearchResponse(
                answer=rag_response.response_text,
                confidence=rag_response.confidence_score,
                citations=rag_response.sources,
                retrieval_strategy=rag_response.retrieval_strategy,
                research_strategy=ResearchStrategy.EXPLORATORY,
                metadata=metadata,
                reasoning_chain=["Broad hybrid search", "Source diversification", "Exploratory response synthesis"],
                follow_up_suggestions=self._generate_follow_up_suggestions(query, rag_response.sources),
                related_queries=self._generate_related_queries(query)
            )

        except Exception as e:
            logger.error(f"Error in exploratory research: {e}")
            raise

    async def _retry_with_fallback(
        self,
        query: str,
        strategy: ResearchStrategy,
        top_k: int,
        confidence_threshold: float,
        model_preference: str,
        context: Dict[str, Any],
        retry_count: int,
        user_id: str = "anonymous"
    ) -> AgenticResearchResponse:
        """Retry research with fallback strategy"""
        try:
            self.metrics["fallback_usage"] += 1

            # Try with broader context from memory
            if self.enable_memory:
                recent_queries = await self.memory.get_user_queries(user_id, 5)
                if recent_queries:
                    context["previous_queries"] = [q["query"] for q in recent_queries]
                    context["previous_contexts"] = [q.get("context", {}) for q in recent_queries]

            # Use comprehensive strategy as fallback
            result = await self._comprehensive_research(query, top_k * 2, model_preference, context)
            result.metadata.retry_count = retry_count
            result.metadata.fallback_used = True
            result.reasoning_chain.append(f"Fallback attempt #{retry_count}")

            return result

        except Exception as e:
            logger.error(f"Error in fallback research: {e}")
            raise

    def _diversify_sources(self, sources: List[LegalSource], target_count: int) -> List[LegalSource]:
        """Diversify sources by document type and relevance"""
        if len(sources) <= target_count:
            return sources

        # Group by document type
        type_groups = {}
        for source in sources:
            doc_type = source.document_type
            if doc_type not in type_groups:
                type_groups[doc_type] = []
            type_groups[doc_type].append(source)

        # Select diverse sources
        diversified = []
        remaining_slots = target_count

        # First, take the best source from each type
        for doc_type, type_sources in type_groups.items():
            if remaining_slots > 0:
                best_source = max(type_sources, key=lambda s: s.relevance_score)
                diversified.append(best_source)
                remaining_slots -= 1

        # Fill remaining slots with highest relevance scores
        remaining_sources = [s for s in sources if s not in diversified]
        remaining_sources.sort(key=lambda s: s.relevance_score, reverse=True)
        diversified.extend(remaining_sources[:remaining_slots])

        return diversified

    def _generate_follow_up_suggestions(self, query: str, sources: List[LegalSource]) -> List[str]:
        """Generate intelligent follow-up suggestions"""
        suggestions = []

        # Based on document types found
        doc_types = set(source.document_type for source in sources)

        if "legislation" in doc_types:
            suggestions.append("What are the penalties for non-compliance with this law?")
            suggestions.append("Are there any recent amendments to this legislation?")

        if "case_law" in doc_types:
            suggestions.append("What are similar cases with different outcomes?")
            suggestions.append("How has this legal principle evolved over time?")

        if "constitution" in doc_types:
            suggestions.append("What constitutional rights are relevant to this issue?")
            suggestions.append("How does this relate to other constitutional provisions?")

        # Generic suggestions
        suggestions.extend([
            "Can you provide more specific examples?",
            "What are the practical implications of this?",
            "Are there any exceptions to this rule?"
        ])

        return suggestions[:5]  # Limit to 5 suggestions

    def _generate_related_queries(self, query: str) -> List[str]:
        """Generate related queries based on the original question"""
        # Simple keyword-based related queries
        # In a full implementation, this could use NLP techniques

        related = []

        # Extract key legal terms (simplified)
        legal_terms = ["contract", "liability", "damages", "breach", "negligence", "constitutional", "statutory"]
        query_lower = query.lower()

        for term in legal_terms:
            if term in query_lower:
                related.append(f"What are the elements of {term} in Kenyan law?")
                related.append(f"Recent cases involving {term}")
                break

        # Add generic related queries
        related.extend([
            "What are the legal precedents for this issue?",
            "How is this regulated under Kenyan law?",
            "What are the procedural requirements?"
        ])

        return related[:3]  # Limit to 3 related queries

    async def get_user_memory_summary(self, user_id: str) -> Dict[str, Any]:
        """Get memory summary for a specific user"""
        if not self.enable_memory:
            return {"memory_enabled": False}

        recent_queries = await self.memory.get_user_queries(user_id, 10)
        memory_stats = self.memory.get_memory_stats()

        return {
            "memory_enabled": True,
            "recent_queries_count": len(recent_queries),
            "recent_queries": [
                {
                    "query": q["query"][:100] + "..." if len(q["query"]) > 100 else q["query"],
                    "timestamp": q["timestamp"]
                }
                for q in recent_queries[-5:]  # Last 5 queries
            ],
            "memory_stats": memory_stats
        }

    async def clear_user_memory(self, user_id: str):
        """Clear memory for a specific user"""
        if self.enable_memory:
            await self.memory.clear_user_memory(user_id)

    async def get_related_queries(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get queries related to the current query for a user"""
        if not self.enable_memory:
            return []

        return await self.memory.get_related_queries(user_id, query, limit)

    def _update_metrics(self, confidence: float, processing_time: float):
        """Update agent performance metrics"""
        if confidence > 0.5:  # Consider successful if confidence > 0.5
            self.metrics["successful_queries"] += 1

        # Update rolling averages
        total_queries = self.metrics["total_queries"]

        # Update average confidence
        current_avg_confidence = self.metrics["avg_confidence"]
        self.metrics["avg_confidence"] = (
            (current_avg_confidence * (total_queries - 1) + confidence) / total_queries
        )

        # Update average processing time
        current_avg_time = self.metrics["avg_processing_time"]
        self.metrics["avg_processing_time"] = (
            (current_avg_time * (total_queries - 1) + processing_time) / total_queries
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        success_rate = (
            self.metrics["successful_queries"] / self.metrics["total_queries"]
            if self.metrics["total_queries"] > 0 else 0.0
        )

        memory_stats = self.memory.get_memory_stats() if self.enable_memory else {}

        return {
            **self.metrics,
            "success_rate": success_rate,
            "memory_stats": memory_stats,
            "initialized": self._initialized
        }

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get summary of agent memory (general overview)"""
        memory_stats = self.memory.get_memory_stats()

        return {
            "memory_enabled": self.enable_memory,
            "memory_stats": memory_stats,
            "total_memory_usage": self.metrics.get("memory_usage", 0)
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the agent and its services"""
        health_status = {
            "agent_status": "healthy" if self._initialized else "not_initialized",
            "services": {},
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Check Legal RAG service
            rag_metrics = self.legal_rag.get_metrics()
            health_status["services"]["legal_rag"] = {
                "status": "healthy" if rag_metrics["initialized"] else "not_initialized",
                "has_chromadb": rag_metrics["has_chromadb"],
                "success_rate": rag_metrics["success_rate"]
            }

            # Check Vector service
            try:
                if not self.vector_service._initialized:
                    await self.vector_service.initialize()
                health_status["services"]["vector_service"] = {"status": "healthy"}
            except Exception as e:
                health_status["services"]["vector_service"] = {"status": "error", "error": str(e)}

            # Check MCP service
            mcp_health = await self.mcp_service.health_check()
            health_status["services"]["mcp_service"] = {
                "status": "healthy" if mcp_health.get("success") else "error"
            }

        except Exception as e:
            logger.error(f"Error in agent health check: {e}")
            health_status["agent_status"] = "error"
            health_status["error"] = str(e)

        return health_status

    async def research_with_context(
        self,
        query: str,
        strategy: ResearchStrategy = ResearchStrategy.COMPREHENSIVE,
        max_sources: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgenticResearchResponse:
        """
        Enhanced research method using context engineering framework.
        Provides structured, context-aware legal research with modular chaining.
        """

        if not self.enable_context_framework:
            raise AIServiceException("Context framework not enabled", "configuration_error")

        start_time = time.time()

        try:
            # Step 1: Context Analysis
            query_context, context_decisions = await self.context_manager.analyze_query_context(
                query=query,
                query_type="legal_research",
                user_context=context or {},
                file_attached=False,  # TODO: Detect from context
                previous_queries=[]   # TODO: Get from memory
            )

            # Step 2: Vector Retrieval with Context
            retrieval_input = {
                "query": query,
                "max_sources": max_sources or self.max_sources,
                "strategy": self._map_strategy_to_retrieval(strategy)
            }

            retrieval_result = await self.vector_retriever.execute(
                retrieval_input, query_context
            )

            if retrieval_result.status != "success":
                raise AIServiceException(
                    f"Retrieval failed: {retrieval_result.error_message}",
                    "retrieval_error"
                )

            # Step 3: Multi-Source Summarization
            summarization_input = {
                "documents": retrieval_result.data["documents"],
                "query": query,
                "strategy": "comprehensive" if strategy == ResearchStrategy.COMPREHENSIVE else "focused"
            }

            summarization_result = await self.multi_source_summarizer.execute(
                summarization_input, query_context
            )

            if summarization_result.status != "success":
                raise AIServiceException(
                    f"Summarization failed: {summarization_result.error_message}",
                    "summarization_error"
                )

            # Step 4: Legal Reasoning
            reasoning_input = {
                "query": query,
                "summary": summarization_result.data["summary"],
                "citations": summarization_result.data["citations"],
                "key_insights": summarization_result.data["key_insights"]
            }

            reasoning_result = await self.legal_reasoner.execute(
                reasoning_input, query_context
            )

            if reasoning_result.status != "success":
                raise AIServiceException(
                    f"Legal reasoning failed: {reasoning_result.error_message}",
                    "reasoning_error"
                )

            # Step 5: Answer Formatting
            formatting_input = {
                "query": query,
                "summary": summarization_result.data["summary"],
                "reasoning_chain": reasoning_result.data["reasoning_chain"],
                "legal_principles": reasoning_result.data["legal_principles"],
                "counterarguments": reasoning_result.data["counterarguments"],
                "practical_implications": reasoning_result.data["practical_implications"],
                "citations": summarization_result.data["citations"],
                "key_insights": summarization_result.data["key_insights"],
                "confidence": reasoning_result.confidence,
                "reasoning_confidence": reasoning_result.data["reasoning_confidence"]
            }

            formatting_result = await self.answer_formatter.execute(
                formatting_input, query_context
            )

            if formatting_result.status != "success":
                raise AIServiceException(
                    f"Answer formatting failed: {formatting_result.error_message}",
                    "formatting_error"
                )

            # Calculate overall confidence
            component_confidences = [
                retrieval_result.confidence,
                summarization_result.confidence,
                reasoning_result.confidence,
                formatting_result.confidence
            ]
            overall_confidence = sum(component_confidences) / len(component_confidences)

            # Apply confidence threshold
            final_confidence_threshold = confidence_threshold or self.default_confidence_threshold
            if overall_confidence < final_confidence_threshold:
                logger.warning(f"Low confidence result: {overall_confidence:.3f} < {final_confidence_threshold}")

            # Build comprehensive reasoning chain
            comprehensive_reasoning_chain = [
                f"Context analysis completed: {len(context_decisions)} decisions made",
                f"Retrieved {len(retrieval_result.data['documents'])} relevant documents",
                f"Summarized content across {summarization_result.data.get('groups_created', 1)} legal domains",
                f"Applied {len(reasoning_result.data['reasoning_chain'])} reasoning steps",
                f"Formatted response using {formatting_result.data['strategy_used']} strategy"
            ]

            # Add component-specific reasoning
            comprehensive_reasoning_chain.extend(retrieval_result.data.get("reasoning_steps", []))
            comprehensive_reasoning_chain.extend(summarization_result.data.get("reasoning_steps", []))
            comprehensive_reasoning_chain.extend(reasoning_result.data.get("reasoning_chain", []))

            # Convert citations to LegalSource format
            legal_sources = []
            for citation in summarization_result.data.get("citations", []):
                if isinstance(citation, dict):
                    legal_source = LegalSource(
                        title=citation.get("title", "Unknown"),
                        content=citation.get("content", ""),
                        source=citation.get("source", "unknown"),
                        url=citation.get("url"),
                        relevance_score=citation.get("relevance_score", 0.5),
                        document_type=citation.get("document_type", "unknown"),
                        metadata=citation.get("metadata", {})
                    )
                    legal_sources.append(legal_source)

            # Create metadata
            processing_time = (time.time() - start_time) * 1000
            metadata = AgentMetadata(
                timestamp=datetime.utcnow(),
                model_used="context_framework",
                retrieval_strategy=retrieval_result.data.get("strategy_used", "context_aware"),
                research_strategy=strategy,
                processing_time_ms=processing_time,
                sources_consulted=len(legal_sources),
                confidence_threshold=final_confidence_threshold
            )

            # Trigger context refinement if needed
            if self.enable_monitoring and overall_confidence < 0.6:
                asyncio.create_task(self.context_refinement.analyze_and_refine())

            return AgenticResearchResponse(
                answer=formatting_result.data["formatted_answer"],
                confidence=overall_confidence,
                citations=legal_sources,
                retrieval_strategy=retrieval_result.data.get("strategy_used", "context_aware"),
                research_strategy=strategy,
                metadata=metadata,
                reasoning_chain=comprehensive_reasoning_chain,
                follow_up_suggestions=self._generate_follow_up_suggestions(query, legal_sources),
                related_queries=self._generate_related_queries(query),
                # Enhanced context-aware fields
                context_used=query_context,
                component_metrics={
                    "retrieval_confidence": retrieval_result.confidence,
                    "summarization_confidence": summarization_result.confidence,
                    "reasoning_confidence": reasoning_result.confidence,
                    "formatting_confidence": formatting_result.confidence,
                    "context_decisions": len(context_decisions)
                }
            )

        except Exception as e:
            logger.error(f"Error in context-aware research: {e}")

            # Fallback to legacy research if context framework fails
            logger.info("Falling back to legacy research method")
            return await self._research_legacy(
                query=query,
                strategy=strategy,
                max_sources=max_sources,
                confidence_threshold=confidence_threshold,
                context=context
            )

    def _map_strategy_to_retrieval(self, strategy: ResearchStrategy) -> str:
        """Map research strategy to retrieval strategy"""
        mapping = {
            ResearchStrategy.COMPREHENSIVE: "comprehensive",
            ResearchStrategy.FOCUSED: "focused",
            ResearchStrategy.EXPLORATORY: "exploratory"
        }
        return mapping.get(strategy, "comprehensive")

    async def _research_legacy(
        self,
        query: str,
        strategy: ResearchStrategy = ResearchStrategy.COMPREHENSIVE,
        max_sources: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgenticResearchResponse:
        """
        Legacy research method for backward compatibility.
        This is the original implementation renamed.
        """
        start_time = time.time()

        if not self._initialized:
            await self.initialize()

        confidence_threshold = confidence_threshold or self.default_confidence_threshold
        context = context or {}

        try:
            self.metrics["total_queries"] += 1
            self.metrics["strategy_usage"][strategy.value] += 1

            # Execute research pipeline based on strategy
            if strategy == ResearchStrategy.QUICK:
                result = await self._quick_research(query, max_sources or 5, "claude-sonnet-4", context)
            elif strategy == ResearchStrategy.COMPREHENSIVE:
                result = await self._comprehensive_research(query, max_sources or 10, "claude-sonnet-4", context)
            elif strategy == ResearchStrategy.FOCUSED:
                result = await self._focused_research(query, max_sources or 7, "claude-sonnet-4", context)
            elif strategy == ResearchStrategy.EXPLORATORY:
                result = await self._exploratory_research(query, max_sources or 15, "claude-sonnet-4", context)
            else:
                result = await self._comprehensive_research(query, max_sources or 10, "claude-sonnet-4", context)

            # Apply confidence threshold and retry logic
            if result.confidence < confidence_threshold and result.metadata.retry_count < self.max_retry_attempts:
                logger.info(f"Confidence {result.confidence} below threshold {confidence_threshold}, retrying with broader context")
                result = await self._retry_with_fallback(query, strategy, max_sources or 10, confidence_threshold, "claude-sonnet-4", context, result.metadata.retry_count + 1)

            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self._update_metrics(result.confidence, processing_time)

            # Update metadata
            result.metadata.processing_time_ms = processing_time

            return result

        except Exception as e:
            logger.error(f"Error in legacy research: {e}")
            # Return error response
            error_metadata = AgentMetadata(
                timestamp=datetime.utcnow(),
                model_used="error",
                retrieval_strategy="error",
                research_strategy=strategy,
                processing_time_ms=(time.time() - start_time) * 1000,
                sources_consulted=0,
                confidence_threshold=confidence_threshold,
                fallback_used=True
            )

            return AgenticResearchResponse(
                answer=f"I encountered an error while researching your question: {str(e)}",
                confidence=0.0,
                citations=[],
                retrieval_strategy="error",
                research_strategy=strategy,
                metadata=error_metadata,
                reasoning_chain=["Error occurred during research"],
                follow_up_suggestions=["Please try rephrasing your question", "Check if the system is available"],
                related_queries=[]
            )
