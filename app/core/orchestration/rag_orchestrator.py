"""
RAG Orchestrator for Dynamic Retrieval-Augmented Generation
Manages multiple retrieval sources and orchestrates intelligent document retrieval
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from datetime import datetime
import hashlib

try:
    from app.services.vector_service import VectorService
except ImportError:
    VectorService = None

from app.core.exceptions import AIServiceException

logger = logging.getLogger(__name__)

class RetrievalStrategy(Enum):
    """Different retrieval strategies"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    CONTEXTUAL = "contextual"
    LEGAL_SPECIFIC = "legal_specific"

class DocumentSource(Enum):
    """Available document sources"""
    KENYAN_LAW = "kenyan_law"
    CASE_LAW = "case_law"
    REGULATIONS = "regulations"
    PARLIAMENT = "parliament"
    GAZETTE = "gazette"
    LEGAL_FORMS = "legal_forms"

@dataclass
class RetrievalConfig:
    """Configuration for retrieval operations"""
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    max_documents: int = 5
    relevance_threshold: float = 0.7
    sources: List[DocumentSource] = field(default_factory=lambda: [DocumentSource.KENYAN_LAW])
    enable_reranking: bool = True
    context_window: int = 1000
    include_metadata: bool = True

@dataclass
class RetrievedDocument:
    """Represents a retrieved document"""
    id: str
    title: str
    content: str
    source: DocumentSource
    relevance_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    url: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

class RAGOrchestrator:
    """Orchestrates retrieval-augmented generation with multiple strategies"""
    
    def __init__(self, vector_service: VectorService = None):
        self.vector_service = vector_service or VectorService()
        self.retrieval_cache = {}
        self.cache_ttl = 3600  # 1 hour
        self.performance_metrics = {
            "total_retrievals": 0,
            "cache_hits": 0,
            "avg_retrieval_time": 0.0,
            "strategy_usage": {}
        }
    
    async def retrieve_and_rank(
        self, 
        query: str, 
        config: RetrievalConfig = None,
        context: Dict[str, Any] = None
    ) -> List[RetrievedDocument]:
        """Main retrieval and ranking method"""
        config = config or RetrievalConfig()
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(query, config)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.performance_metrics["cache_hits"] += 1
                return cached_result
            
            # Perform retrieval based on strategy
            documents = await self._execute_retrieval_strategy(query, config, context)
            
            # Apply post-processing
            processed_docs = await self._post_process_documents(documents, query, config)
            
            # Cache the result
            self._cache_result(cache_key, processed_docs)
            
            # Update metrics
            self._update_metrics(config.strategy, time.time() - start_time)
            
            return processed_docs
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            raise AIServiceException(f"Document retrieval failed: {str(e)}", "retrieval_error")
    
    async def _execute_retrieval_strategy(
        self, 
        query: str, 
        config: RetrievalConfig,
        context: Dict[str, Any]
    ) -> List[RetrievedDocument]:
        """Execute the specified retrieval strategy"""
        
        if config.strategy == RetrievalStrategy.SEMANTIC:
            return await self._semantic_retrieval(query, config, context)
        elif config.strategy == RetrievalStrategy.KEYWORD:
            return await self._keyword_retrieval(query, config, context)
        elif config.strategy == RetrievalStrategy.HYBRID:
            return await self._hybrid_retrieval(query, config, context)
        elif config.strategy == RetrievalStrategy.CONTEXTUAL:
            return await self._contextual_retrieval(query, config, context)
        elif config.strategy == RetrievalStrategy.LEGAL_SPECIFIC:
            return await self._legal_specific_retrieval(query, config, context)
        else:
            raise AIServiceException(f"Unknown retrieval strategy: {config.strategy}", "invalid_strategy")
    
    async def _semantic_retrieval(
        self, 
        query: str, 
        config: RetrievalConfig,
        context: Dict[str, Any]
    ) -> List[RetrievedDocument]:
        """Perform semantic similarity-based retrieval"""
        try:
            # Use vector service for semantic search
            similar_docs = await self.vector_service.search_similar_documents(
                query, 
                limit=config.max_documents * 2  # Get more for filtering
            )
            
            documents = []
            for doc in similar_docs:
                if hasattr(doc, 'relevance_score') and doc.relevance_score >= config.relevance_threshold:
                    retrieved_doc = RetrievedDocument(
                        id=str(doc.id),
                        title=doc.title,
                        content=doc.content[:config.context_window],
                        source=DocumentSource.KENYAN_LAW,  # Default, should be from doc metadata
                        relevance_score=doc.relevance_score,
                        metadata={"vector_search": True},
                        url=getattr(doc, 'url', None)
                    )
                    documents.append(retrieved_doc)
            
            return documents[:config.max_documents]
            
        except Exception as e:
            logger.error(f"Semantic retrieval failed: {e}")
            return []
    
    async def _keyword_retrieval(
        self, 
        query: str, 
        config: RetrievalConfig,
        context: Dict[str, Any]
    ) -> List[RetrievedDocument]:
        """Perform keyword-based retrieval"""
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        
        # Mock keyword search - in production, this would use a search engine
        mock_results = [
            {
                "id": "kw_1",
                "title": "Companies Act 2015 - Registration",
                "content": "Company registration requirements under Kenyan law...",
                "source": DocumentSource.KENYAN_LAW,
                "score": 0.85
            },
            {
                "id": "kw_2", 
                "title": "Employment Termination Procedures",
                "content": "Legal procedures for employment termination in Kenya...",
                "source": DocumentSource.CASE_LAW,
                "score": 0.78
            }
        ]
        
        documents = []
        for result in mock_results:
            if result["score"] >= config.relevance_threshold:
                doc = RetrievedDocument(
                    id=result["id"],
                    title=result["title"],
                    content=result["content"],
                    source=result["source"],
                    relevance_score=result["score"],
                    metadata={"keywords": keywords, "keyword_search": True}
                )
                documents.append(doc)
        
        return documents[:config.max_documents]
    
    async def _hybrid_retrieval(
        self, 
        query: str, 
        config: RetrievalConfig,
        context: Dict[str, Any]
    ) -> List[RetrievedDocument]:
        """Combine semantic and keyword retrieval"""
        # Run both strategies in parallel
        semantic_task = self._semantic_retrieval(query, config, context)
        keyword_task = self._keyword_retrieval(query, config, context)
        
        semantic_docs, keyword_docs = await asyncio.gather(semantic_task, keyword_task)
        
        # Merge and deduplicate results
        all_docs = {}
        
        # Add semantic results with weight
        for doc in semantic_docs:
            doc.relevance_score *= 0.7  # Weight semantic results
            doc.metadata["retrieval_method"] = "semantic"
            all_docs[doc.id] = doc
        
        # Add keyword results with weight
        for doc in keyword_docs:
            if doc.id in all_docs:
                # Combine scores for documents found by both methods
                existing_doc = all_docs[doc.id]
                combined_score = (existing_doc.relevance_score + doc.relevance_score * 0.3) / 1.3
                existing_doc.relevance_score = combined_score
                existing_doc.metadata["retrieval_method"] = "hybrid"
            else:
                doc.relevance_score *= 0.3  # Weight keyword results
                doc.metadata["retrieval_method"] = "keyword"
                all_docs[doc.id] = doc
        
        # Sort by combined relevance score
        sorted_docs = sorted(all_docs.values(), key=lambda x: x.relevance_score, reverse=True)
        
        return sorted_docs[:config.max_documents]
    
    async def _contextual_retrieval(
        self, 
        query: str, 
        config: RetrievalConfig,
        context: Dict[str, Any]
    ) -> List[RetrievedDocument]:
        """Perform context-aware retrieval"""
        # Enhance query with context
        enhanced_query = self._enhance_query_with_context(query, context)
        
        # Use enhanced query for semantic retrieval
        return await self._semantic_retrieval(enhanced_query, config, context)
    
    async def _legal_specific_retrieval(
        self, 
        query: str, 
        config: RetrievalConfig,
        context: Dict[str, Any]
    ) -> List[RetrievedDocument]:
        """Perform legal domain-specific retrieval"""
        # Extract legal entities and concepts
        legal_entities = self._extract_legal_entities(query)
        
        # Enhance query with legal context
        legal_query = self._enhance_query_for_legal_search(query, legal_entities, context)
        
        # Perform hybrid retrieval with legal focus
        return await self._hybrid_retrieval(legal_query, config, context)
    
    async def _post_process_documents(
        self, 
        documents: List[RetrievedDocument], 
        query: str,
        config: RetrievalConfig
    ) -> List[RetrievedDocument]:
        """Post-process retrieved documents"""
        if not documents:
            return documents
        
        processed_docs = documents.copy()
        
        # Apply reranking if enabled
        if config.enable_reranking:
            processed_docs = await self._rerank_documents(processed_docs, query)
        
        # Filter by final relevance threshold
        processed_docs = [
            doc for doc in processed_docs 
            if doc.relevance_score >= config.relevance_threshold
        ]
        
        # Add processing metadata
        for doc in processed_docs:
            doc.metadata["processed_at"] = datetime.utcnow().isoformat()
            doc.metadata["query_hash"] = hashlib.md5(query.encode()).hexdigest()[:8]
        
        return processed_docs[:config.max_documents]
    
    async def _rerank_documents(
        self, 
        documents: List[RetrievedDocument], 
        query: str
    ) -> List[RetrievedDocument]:
        """Rerank documents using advanced scoring"""
        # Simple reranking based on title relevance and content quality
        for doc in documents:
            title_bonus = 0.1 if any(word.lower() in doc.title.lower() for word in query.split()) else 0
            content_quality = min(len(doc.content) / 1000, 1.0) * 0.05  # Longer content gets slight bonus
            
            doc.relevance_score += title_bonus + content_quality
            doc.metadata["reranked"] = True
        
        return sorted(documents, key=lambda x: x.relevance_score, reverse=True)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        # Simple keyword extraction - in production, use NLP libraries
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words = query.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return keywords
    
    def _extract_legal_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract legal entities from query"""
        # Mock legal entity extraction
        legal_entities = {
            "acts": [],
            "cases": [],
            "courts": [],
            "legal_concepts": []
        }
        
        # Simple pattern matching for legal terms
        query_lower = query.lower()
        
        if "company" in query_lower or "corporation" in query_lower:
            legal_entities["acts"].append("Companies Act 2015")
        
        if "employment" in query_lower or "termination" in query_lower:
            legal_entities["acts"].append("Employment Act 2007")
        
        if "constitution" in query_lower:
            legal_entities["acts"].append("Constitution of Kenya 2010")
        
        return legal_entities
    
    def _enhance_query_with_context(self, query: str, context: Dict[str, Any]) -> str:
        """Enhance query with contextual information"""
        if not context:
            return query
        
        enhancements = []
        
        if context.get("legal_area"):
            enhancements.append(f"Legal area: {context['legal_area']}")
        
        if context.get("jurisdiction"):
            enhancements.append(f"Jurisdiction: {context['jurisdiction']}")
        
        if context.get("user_type"):
            enhancements.append(f"User type: {context['user_type']}")
        
        if enhancements:
            return f"{' '.join(enhancements)} - {query}"
        
        return query
    
    def _enhance_query_for_legal_search(
        self, 
        query: str, 
        legal_entities: Dict[str, List[str]], 
        context: Dict[str, Any]
    ) -> str:
        """Enhance query specifically for legal search"""
        enhanced_parts = [query]
        
        # Add relevant legal acts
        if legal_entities["acts"]:
            enhanced_parts.extend(legal_entities["acts"])
        
        # Add Kenyan legal context
        enhanced_parts.append("Kenya law")
        
        return " ".join(enhanced_parts)
    
    def _generate_cache_key(self, query: str, config: RetrievalConfig) -> str:
        """Generate cache key for retrieval results"""
        key_data = {
            "query": query,
            "strategy": config.strategy.value,
            "max_docs": config.max_documents,
            "threshold": config.relevance_threshold,
            "sources": [s.value for s in config.sources]
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[RetrievedDocument]]:
        """Get cached retrieval result"""
        if cache_key in self.retrieval_cache:
            cached_data = self.retrieval_cache[cache_key]
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                return cached_data["documents"]
            else:
                del self.retrieval_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, documents: List[RetrievedDocument]):
        """Cache retrieval result"""
        self.retrieval_cache[cache_key] = {
            "documents": documents,
            "timestamp": time.time()
        }
        
        # Limit cache size
        if len(self.retrieval_cache) > 1000:
            # Remove oldest entries
            sorted_cache = sorted(
                self.retrieval_cache.items(), 
                key=lambda x: x[1]["timestamp"]
            )
            for key, _ in sorted_cache[:100]:
                del self.retrieval_cache[key]
    
    def _update_metrics(self, strategy: RetrievalStrategy, retrieval_time: float):
        """Update performance metrics"""
        self.performance_metrics["total_retrievals"] += 1
        
        # Update average retrieval time
        total = self.performance_metrics["total_retrievals"]
        current_avg = self.performance_metrics["avg_retrieval_time"]
        self.performance_metrics["avg_retrieval_time"] = (
            (current_avg * (total - 1) + retrieval_time) / total
        )
        
        # Update strategy usage
        strategy_name = strategy.value
        if strategy_name not in self.performance_metrics["strategy_usage"]:
            self.performance_metrics["strategy_usage"][strategy_name] = 0
        self.performance_metrics["strategy_usage"][strategy_name] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "cache_hit_rate": (
                self.performance_metrics["cache_hits"] / 
                max(self.performance_metrics["total_retrievals"], 1)
            ),
            "avg_retrieval_time": self.performance_metrics["avg_retrieval_time"],
            "total_retrievals": self.performance_metrics["total_retrievals"],
            "strategy_usage": self.performance_metrics["strategy_usage"].copy(),
            "cache_size": len(self.retrieval_cache)
        }
