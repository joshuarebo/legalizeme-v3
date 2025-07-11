"""
Vector Retriever Component - Context-aware document retrieval
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .base_component import BaseComponent, ComponentResult, ComponentStatus, ComponentError
from app.services.vector_service import VectorService
from app.services.advanced.legal_rag import LegalRAGService

logger = logging.getLogger(__name__)

@dataclass
class RetrievalStrategy:
    """Configuration for retrieval strategy"""
    name: str
    use_semantic: bool = True
    use_keyword: bool = True
    use_hybrid: bool = False
    max_sources: int = 10
    relevance_threshold: float = 0.3
    diversify_results: bool = True

class VectorRetriever(BaseComponent):
    """
    Context-aware vector retrieval component that intelligently
    selects and executes retrieval strategies based on context
    """
    
    def __init__(self, context_manager=None, vector_service=None, legal_rag_service=None):
        super().__init__("VectorRetriever", context_manager)
        self.vector_service = vector_service or VectorService()
        self.legal_rag_service = legal_rag_service or LegalRAGService()
        
        # Retrieval strategies
        self.strategies = {
            "quick": RetrievalStrategy(
                name="quick",
                use_semantic=True,
                use_keyword=False,
                max_sources=5,
                relevance_threshold=0.4
            ),
            "comprehensive": RetrievalStrategy(
                name="comprehensive",
                use_semantic=True,
                use_keyword=True,
                use_hybrid=True,
                max_sources=15,
                relevance_threshold=0.2,
                diversify_results=True
            ),
            "focused": RetrievalStrategy(
                name="focused",
                use_semantic=True,
                use_keyword=True,
                max_sources=8,
                relevance_threshold=0.5
            ),
            "exploratory": RetrievalStrategy(
                name="exploratory",
                use_semantic=True,
                use_keyword=True,
                use_hybrid=True,
                max_sources=20,
                relevance_threshold=0.1,
                diversify_results=True
            )
        }
    
    async def _initialize_component(self):
        """Initialize vector services"""
        await self.vector_service.initialize()
        await self.legal_rag_service.initialize()
    
    async def _validate_input(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate retrieval input"""
        if "query" not in input_data:
            return {"valid": False, "error": "Query is required"}
        
        query = input_data["query"]
        if not isinstance(query, str) or len(query.strip()) == 0:
            return {"valid": False, "error": "Query must be a non-empty string"}
        
        return {"valid": True}
    
    async def _execute_component(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute context-aware document retrieval"""
        
        query = input_data["query"]
        max_sources = input_data.get("max_sources", 10)
        
        # Determine retrieval strategy from context
        strategy = self._select_retrieval_strategy(context, input_data)
        
        # Apply context-specific filters
        filters = self._build_context_filters(context, input_data)
        
        # Execute retrieval with selected strategy
        retrieved_docs = await self._execute_retrieval_strategy(
            query, strategy, filters, max_sources
        )
        
        # Post-process and rank results
        processed_docs = await self._post_process_results(retrieved_docs, query, context)
        
        # Generate reasoning steps
        reasoning_steps = self._generate_reasoning_steps(strategy, filters, len(processed_docs))
        
        return {
            "documents": processed_docs,
            "strategy_used": strategy.name,
            "total_retrieved": len(processed_docs),
            "filters_applied": filters,
            "reasoning_steps": reasoning_steps,
            "query_processed": query
        }
    
    def _select_retrieval_strategy(self, context: Dict[str, Any], input_data: Dict[str, Any]) -> RetrievalStrategy:
        """Select appropriate retrieval strategy based on context"""
        
        # Check for explicit strategy in input
        if "strategy" in input_data and input_data["strategy"] in self.strategies:
            return self.strategies[input_data["strategy"]]
        
        # Analyze context for strategy selection
        query_complexity = context.get("query_complexity", {})
        urgency_analysis = context.get("urgency_analysis", {})
        routing_rules = context.get("routing_rules", {})
        
        # High urgency -> quick strategy
        if urgency_analysis.get("level") == "high":
            return self.strategies["quick"]
        
        # High complexity -> comprehensive strategy
        if query_complexity.get("level") == "high":
            return self.strategies["comprehensive"]
        
        # Specific routing rules
        if "document_processing" in routing_rules:
            return self.strategies["focused"]
        
        if "case_law_research" in routing_rules:
            return self.strategies["comprehensive"]
        
        # Check for exploratory indicators
        if query_complexity.get("level") == "low" and "exploratory" in context.get("detected_domains", []):
            return self.strategies["exploratory"]
        
        # Default to focused strategy
        return self.strategies["focused"]
    
    def _build_context_filters(self, context: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build retrieval filters based on context"""
        filters = {}
        
        # Domain-specific filters
        detected_domains = context.get("detected_domains", [])
        if detected_domains:
            # Map domains to document categories
            domain_categories = {
                "employment": ["employment", "labor", "workplace"],
                "contract": ["contracts", "agreements", "commercial"],
                "property": ["property", "real_estate", "land"]
            }
            
            categories = []
            for domain in detected_domains:
                if domain in domain_categories:
                    categories.extend(domain_categories[domain])
            
            if categories:
                filters["categories"] = categories
        
        # Document type filters from routing rules
        routing_rules = context.get("routing_rules", {})
        if "document_processing" in routing_rules:
            filters["document_types"] = ["pdf", "contract", "agreement"]
        
        # Source filters
        query_info = context.get("query_info", {})
        if query_info.get("file_attached"):
            filters["include_user_documents"] = True
        
        # Jurisdiction filter (always Kenya for this system)
        filters["jurisdiction"] = "kenya"
        
        # Time-based filters if urgency is detected
        urgency_analysis = context.get("urgency_analysis", {})
        if urgency_analysis.get("level") == "high":
            filters["prioritize_recent"] = True
        
        return filters
    
    async def _execute_retrieval_strategy(
        self,
        query: str,
        strategy: RetrievalStrategy,
        filters: Dict[str, Any],
        max_sources: int
    ) -> List[Dict[str, Any]]:
        """Execute the selected retrieval strategy"""
        
        all_documents = []
        
        try:
            # Semantic retrieval
            if strategy.use_semantic:
                semantic_docs = await self._semantic_retrieval(
                    query, min(strategy.max_sources, max_sources), filters
                )
                all_documents.extend(semantic_docs)
            
            # Keyword retrieval
            if strategy.use_keyword:
                keyword_docs = await self._keyword_retrieval(
                    query, min(strategy.max_sources, max_sources), filters
                )
                all_documents.extend(keyword_docs)
            
            # Hybrid retrieval (if supported)
            if strategy.use_hybrid and hasattr(self.legal_rag_service, '_hybrid_retrieval'):
                hybrid_docs = await self.legal_rag_service._hybrid_retrieval(
                    query, min(strategy.max_sources, max_sources)
                )
                all_documents.extend(hybrid_docs)
            
            # Remove duplicates and apply relevance threshold
            unique_docs = self._deduplicate_documents(all_documents)
            filtered_docs = [
                doc for doc in unique_docs
                if doc.get("relevance_score", 0) >= strategy.relevance_threshold
            ]
            
            # Diversify results if requested
            if strategy.diversify_results:
                filtered_docs = self._diversify_results(filtered_docs)
            
            # Limit to max sources
            return filtered_docs[:max_sources]
            
        except Exception as e:
            logger.error(f"Error in retrieval strategy execution: {e}")
            raise ComponentError(f"Retrieval failed: {str(e)}", self.name, "retrieval_error")
    
    async def _semantic_retrieval(
        self,
        query: str,
        limit: int,
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Perform semantic retrieval"""
        try:
            # Use legal RAG service for semantic retrieval
            if hasattr(self.legal_rag_service, '_semantic_retrieval'):
                return await self.legal_rag_service._semantic_retrieval(query, limit)
            else:
                # Fallback to vector service
                documents = await self.vector_service.search_similar_documents(
                    query, limit, filters
                )
                return [self._convert_document_to_dict(doc) for doc in documents]
        except Exception as e:
            logger.warning(f"Semantic retrieval failed: {e}")
            return []
    
    async def _keyword_retrieval(
        self,
        query: str,
        limit: int,
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Perform keyword-based retrieval"""
        try:
            # Use vector service for keyword search
            documents = await self.vector_service.search_similar_documents(
                query, limit, filters
            )
            return [self._convert_document_to_dict(doc) for doc in documents]
        except Exception as e:
            logger.warning(f"Keyword retrieval failed: {e}")
            return []
    
    def _convert_document_to_dict(self, document) -> Dict[str, Any]:
        """Convert document object to dictionary"""
        if isinstance(document, dict):
            return document
        
        # Convert document object to dictionary
        return {
            "id": getattr(document, 'id', None),
            "title": getattr(document, 'title', 'Unknown'),
            "content": getattr(document, 'content', ''),
            "source": getattr(document, 'source', 'unknown'),
            "document_type": getattr(document, 'document_type', 'unknown'),
            "url": getattr(document, 'url', None),
            "relevance_score": getattr(document, 'relevance_score', 0.5),
            "metadata": getattr(document, 'metadata', {})
        }
    
    def _deduplicate_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate documents"""
        seen_ids = set()
        unique_docs = []
        
        for doc in documents:
            doc_id = doc.get("id") or doc.get("title", "")
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_docs.append(doc)
        
        return unique_docs
    
    def _diversify_results(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Diversify results to avoid too many similar documents"""
        if len(documents) <= 5:
            return documents
        
        # Group by source and document type
        source_groups = {}
        for doc in documents:
            source = doc.get("source", "unknown")
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(doc)
        
        # Select diverse documents
        diversified = []
        max_per_source = max(2, len(documents) // len(source_groups))
        
        for source, docs in source_groups.items():
            # Sort by relevance and take top documents from each source
            sorted_docs = sorted(docs, key=lambda x: x.get("relevance_score", 0), reverse=True)
            diversified.extend(sorted_docs[:max_per_source])
        
        # Sort final results by relevance
        return sorted(diversified, key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    async def _post_process_results(
        self,
        documents: List[Dict[str, Any]],
        query: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Post-process retrieval results"""
        
        # Add query relevance scores
        for doc in documents:
            if "relevance_score" not in doc:
                doc["relevance_score"] = self._calculate_query_relevance(doc, query)
        
        # Sort by relevance
        documents.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Add context-specific metadata
        for doc in documents:
            doc["retrieval_context"] = {
                "query": query,
                "timestamp": context.get("query_info", {}).get("timestamp"),
                "context_domains": context.get("detected_domains", [])
            }
        
        return documents
    
    def _calculate_query_relevance(self, document: Dict[str, Any], query: str) -> float:
        """Calculate relevance score between document and query"""
        # Simple relevance calculation based on keyword overlap
        doc_text = (document.get("title", "") + " " + document.get("content", "")).lower()
        query_words = set(query.lower().split())
        doc_words = set(doc_text.split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(doc_words))
        return overlap / len(query_words)
    
    def _generate_reasoning_steps(
        self,
        strategy: RetrievalStrategy,
        filters: Dict[str, Any],
        result_count: int
    ) -> List[str]:
        """Generate reasoning steps for the retrieval process"""
        steps = [
            f"Selected '{strategy.name}' retrieval strategy",
            f"Applied {len(filters)} context-based filters"
        ]
        
        if strategy.use_semantic:
            steps.append("Performed semantic similarity search")
        
        if strategy.use_keyword:
            steps.append("Performed keyword-based search")
        
        if strategy.use_hybrid:
            steps.append("Applied hybrid retrieval combining multiple methods")
        
        if strategy.diversify_results:
            steps.append("Diversified results across different sources")
        
        steps.append(f"Retrieved {result_count} relevant documents")
        
        return steps
    
    async def _calculate_confidence(self, output_data: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate confidence based on retrieval quality"""
        documents = output_data.get("documents", [])
        
        if not documents:
            return 0.0
        
        # Base confidence on average relevance score
        avg_relevance = sum(doc.get("relevance_score", 0) for doc in documents) / len(documents)
        
        # Boost confidence if we have diverse sources
        unique_sources = len(set(doc.get("source", "unknown") for doc in documents))
        diversity_bonus = min(unique_sources / 3, 0.2)  # Up to 20% bonus
        
        # Penalty for very few results
        count_penalty = 0.0
        if len(documents) < 3:
            count_penalty = 0.1
        
        confidence = min(1.0, avg_relevance + diversity_bonus - count_penalty)
        return max(0.0, confidence)

    async def _component_health_check(self) -> Dict[str, Any]:
        """Component-specific health check"""
        health_info = {}

        # Check vector service health
        try:
            if hasattr(self.vector_service, 'health_check'):
                vector_health = await self.vector_service.health_check()
                health_info["vector_service"] = vector_health
            else:
                health_info["vector_service"] = "available"
        except Exception as e:
            health_info["vector_service"] = f"error: {str(e)}"

        # Check legal RAG service health
        try:
            if hasattr(self.legal_rag_service, 'health_check'):
                rag_health = await self.legal_rag_service.health_check()
                health_info["legal_rag_service"] = rag_health
            else:
                health_info["legal_rag_service"] = "available"
        except Exception as e:
            health_info["legal_rag_service"] = f"error: {str(e)}"

        return health_info
