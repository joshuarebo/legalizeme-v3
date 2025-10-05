"""
Enhanced RAG Service with AWS-Native Components
Integrates AWS Vector Service, Embedding Service, and Token Service
Supports interactive citations with inline [1], [2], [3] references
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import re

from app.services.aws_vector_service import aws_vector_service
from app.services.aws_embedding_service import aws_embedding_service
from app.services.token_service import token_service
from app.services.llm_manager import llm_manager
from app.config import settings

logger = logging.getLogger(__name__)

class EnhancedRAGService:
    """Enhanced RAG service using AWS-native components"""
    
    def __init__(self):
        self.vector_service = aws_vector_service
        self.embedding_service = aws_embedding_service
        self.token_service = token_service
        self.llm_manager = llm_manager
        self._initialized = False
        
        # RAG configuration
        self.max_context_tokens = 6000
        self.similarity_threshold = 0.7
        self.max_retrieved_docs = 5
        
    async def initialize(self):
        """Initialize all services"""
        if self._initialized:
            return
            
        try:
            # Initialize all component services
            await self.vector_service.initialize()
            await self.embedding_service.initialize()
            
            self._initialized = True
            logger.info("Enhanced RAG Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced RAG Service: {e}")
            raise
    
    async def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add document to RAG system"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Check token count
            token_info = self.token_service.check_token_limit(content, limit=8000)
            if not token_info['within_limit']:
                logger.warning(f"Document {doc_id} exceeds token limit, truncating")
                content = self.token_service.truncate_to_limit(content, limit=8000)
            
            # Add to vector store
            success = await self.vector_service.add_document(doc_id, content, metadata)
            
            if success:
                logger.info(f"Successfully added document {doc_id} to RAG system")
            else:
                logger.error(f"Failed to add document {doc_id} to RAG system")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding document {doc_id}: {e}")
            return False
    
    async def query(self, question: str, context: str = "", max_tokens: int = 4000, use_citations: bool = True) -> Dict[str, Any]:
        """Perform RAG query with enhanced context and interactive citations

        Args:
            question: User's legal question
            context: Additional context (optional)
            max_tokens: Maximum tokens for response
            use_citations: Whether to use citation-aware prompting (default: True)

        Returns:
            Dict with answer, structured sources, citation_map, and metadata
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Step 1: Retrieve relevant documents from vector store
            retrieved_docs = await self.vector_service.search_similar(
                query=question,
                limit=self.max_retrieved_docs,
                threshold=self.similarity_threshold
            )

            if not retrieved_docs:
                logger.warning(f"No documents retrieved for query: {question[:50]}...")
                return {
                    'success': True,
                    'answer': "I couldn't find any relevant legal documents to answer your question. Please try rephrasing or contact a legal professional.",
                    'sources': [],
                    'citation_map': {},
                    'model_used': 'none',
                    'retrieved_documents': 0,
                    'context_tokens': 0,
                    'total_tokens': 0,
                    'cost_estimate': {'total': 0},
                    'latency_ms': 0,
                    'metadata': {'confidence': 0.0, 'freshness_score': 0.0}
                }

            # Step 2: Build citation-aware context or standard context
            if use_citations:
                citation_context, citation_map = self._build_citation_context(retrieved_docs, question)
                full_context = f"{context}\n\n{citation_context}".strip() if context else citation_context
            else:
                # Fallback to old method for backward compatibility
                rag_context = self._build_context(retrieved_docs, question)
                full_context = f"{context}\n\n{rag_context}".strip() if context else rag_context
                citation_map = {}

            # Step 3: Check token limits and truncate if needed
            context_tokens = self.token_service.count_tokens(full_context)
            if context_tokens > self.max_context_tokens:
                logger.warning(f"Context exceeds limit ({context_tokens} > {self.max_context_tokens}), truncating...")
                full_context = self.token_service.truncate_to_limit(
                    full_context,
                    limit=self.max_context_tokens
                )
                context_tokens = self.max_context_tokens

            # Step 4: Create prompt (citation-aware or standard)
            if use_citations:
                prompt = self._create_citation_aware_prompt(question, full_context, citation_map)
            else:
                prompt = self._create_rag_prompt(question, full_context)

            # Step 5: Generate response using LLM
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                model_preference=['claude-3-sonnet', 'claude-3-haiku'],
                max_tokens=max_tokens
            )

            # Step 6: Build structured sources for frontend
            structured_sources = self._build_structured_sources(retrieved_docs, citation_map, question)

            # Step 7: Calculate costs, metrics, and confidence
            answer_text = response.get('response_text', '')
            total_tokens = self.token_service.count_tokens(prompt + answer_text)
            cost_estimate = self.token_service.estimate_cost(
                prompt + answer_text,
                model=response.get('model_used', 'claude-3-sonnet')
            )

            confidence = self._calculate_confidence(structured_sources)
            freshness = self._calculate_overall_freshness(structured_sources)

            # Step 8: Return enhanced RAG response
            return {
                'success': response.get('success', False),
                'answer': answer_text,
                'sources': structured_sources,
                'citation_map': citation_map,
                'model_used': response.get('model_used', ''),
                'retrieved_documents': len(retrieved_docs),
                'context_tokens': context_tokens,
                'total_tokens': total_tokens,
                'cost_estimate': cost_estimate,
                'latency_ms': response.get('latency_ms', 0),
                'metadata': {
                    'confidence': confidence,
                    'freshness_score': freshness,
                    'citation_count': len(citation_map),
                    'use_citations': use_citations
                }
            }

        except Exception as e:
            logger.error(f"Error in RAG query: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'answer': '',
                'sources': [],
                'citation_map': {},
                'model_used': '',
                'retrieved_documents': 0,
                'context_tokens': 0,
                'total_tokens': 0,
                'cost_estimate': {'total': 0},
                'latency_ms': 0,
                'metadata': {'confidence': 0.0, 'freshness_score': 0.0}
            }
    
    def _build_context(self, retrieved_docs: List[Dict[str, Any]], question: str) -> str:
        """Build context from retrieved documents"""
        if not retrieved_docs:
            return ""
        
        context_parts = []
        context_parts.append("=== RELEVANT LEGAL DOCUMENTS ===\n")
        
        for i, doc in enumerate(retrieved_docs, 1):
            doc_info = doc.get('document', {})
            text = doc_info.get('text', '')
            metadata = doc_info.get('metadata', {})
            similarity = doc.get('similarity', 0)
            
            # Truncate document text if too long
            if len(text) > 1000:
                text = text[:1000] + "..."
            
            context_parts.append(f"Document {i} (Similarity: {similarity:.3f}):")
            if metadata.get('title'):
                context_parts.append(f"Title: {metadata['title']}")
            if metadata.get('source'):
                context_parts.append(f"Source: {metadata['source']}")
            context_parts.append(f"Content: {text}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _create_rag_prompt(self, question: str, context: str) -> str:
        """Create RAG prompt for LLM"""
        return f"""You are a Kenyan legal AI assistant. Use the provided legal documents and context to answer the user's question accurately and comprehensively.

CONTEXT AND LEGAL DOCUMENTS:
{context}

USER QUESTION:
{question}

INSTRUCTIONS:
1. Base your answer primarily on the provided legal documents
2. If the documents don't contain sufficient information, clearly state this
3. Cite specific documents when making legal references
4. Provide practical, actionable legal guidance when appropriate
5. Use clear, professional language suitable for legal consultation
6. Include relevant Kenyan legal statutes, cases, or regulations when applicable

RESPONSE:"""
    
    async def get_similar_documents(self, text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get documents similar to provided text"""
        if not self._initialized:
            await self.initialize()
            
        try:
            return await self.vector_service.search_similar(
                query=text,
                limit=limit,
                threshold=self.similarity_threshold
            )
        except Exception as e:
            logger.error(f"Error getting similar documents: {e}")
            return []
    
    async def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        if not self._initialized:
            await self.initialize()
            
        try:
            return await self.embedding_service.calculate_similarity(text1, text2)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    async def analyze_query_complexity(self, question: str) -> Dict[str, Any]:
        """Analyze query complexity and suggest optimal parameters"""
        try:
            # Basic complexity analysis
            word_count = len(question.split())
            char_count = len(question)
            
            # Determine complexity level
            if word_count < 5:
                complexity = "simple"
                suggested_docs = 2
                suggested_tokens = 2000
            elif word_count < 15:
                complexity = "moderate"
                suggested_docs = 3
                suggested_tokens = 3000
            else:
                complexity = "complex"
                suggested_docs = 5
                suggested_tokens = 4000
            
            # Check for legal keywords
            legal_keywords = ['law', 'legal', 'court', 'statute', 'regulation', 'case', 'constitution']
            has_legal_terms = any(keyword in question.lower() for keyword in legal_keywords)
            
            return {
                'complexity': complexity,
                'word_count': word_count,
                'character_count': char_count,
                'has_legal_terms': has_legal_terms,
                'suggested_max_docs': suggested_docs,
                'suggested_max_tokens': suggested_tokens,
                'estimated_processing_time': word_count * 0.1  # seconds
            }
            
        except Exception as e:
            logger.error(f"Error analyzing query complexity: {e}")
            return {
                'complexity': 'unknown',
                'error': str(e)
            }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status"""
        try:
            vector_stats = await self.vector_service.get_collection_stats()
            embedding_info = await self.embedding_service.get_service_info()

            return {
                'initialized': self._initialized,
                'vector_service': vector_stats,
                'embedding_service': embedding_info,
                'token_service': {
                    'available': True,
                    'supported_models': list(self.token_service.model_ratios.keys())
                },
                'configuration': {
                    'max_context_tokens': self.max_context_tokens,
                    'similarity_threshold': self.similarity_threshold,
                    'max_retrieved_docs': self.max_retrieved_docs
                }
            }

        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                'initialized': self._initialized,
                'error': str(e)
            }

    # ============================================================================
    # INTERACTIVE CITATION METHODS (Phase 1: Step 1.2)
    # ============================================================================

    def _build_citation_context(self, docs: List[Dict], question: str) -> Tuple[str, Dict[int, str]]:
        """Build context with citation markers for LLM to reference

        Args:
            docs: Retrieved documents from vector search
            question: User's question (for relevance)

        Returns:
            Tuple of (citation_context_string, citation_map)
        """
        context_parts = []
        citation_map = {}

        for idx, doc in enumerate(docs, start=1):
            doc_info = doc.get('document', {})
            text = doc_info.get('text', '')
            metadata = doc_info.get('metadata', {})

            # Build citation text
            title = metadata.get('title', f'Source {idx}')
            citation_text = self._format_citation(metadata, title)
            citation_map[idx] = citation_text

            # Truncate text if too long (keep first 1000 chars for context)
            if len(text) > 1000:
                text = text[:1000] + "..."

            # Build source block with citation ID
            context_parts.append(f"[SOURCE {idx}: {citation_text}]")
            context_parts.append(f"{text}\n")

        return "\n".join(context_parts), citation_map

    def _format_citation(self, metadata: Dict, title: str) -> str:
        """Format citation text based on document type"""
        doc_type = metadata.get('document_type', 'unknown')

        if doc_type == 'legislation':
            # "Employment Act 2007, Section 35"
            act = metadata.get('title', title)
            section = metadata.get('section', '')
            # Only add section if it's not already in the title
            if section and section not in act:
                return f"{act}, {section}"
            return act

        elif doc_type == 'judgment':
            # "ABC Ltd v XYZ [2024] eKLR"
            case_name = metadata.get('title', title)
            citation = metadata.get('citation', '')
            # Only add citation if it's not already in the title
            if citation and citation not in case_name:
                return f"{case_name} {citation}"
            return case_name

        else:
            return title

    def _create_citation_aware_prompt(self, question: str, citation_context: str, citation_map: Dict) -> str:
        """Create prompt that instructs LLM to use inline citations"""

        citation_guide = "\n".join([f"[{idx}] = {text}" for idx, text in citation_map.items()])

        return f"""You are a Kenyan legal AI assistant. Answer the question using ONLY the provided sources.

CRITICAL CITATION RULES:
1. ALWAYS cite sources using [1], [2], [3] format after relevant statements
2. Place citations IMMEDIATELY after the statement they support
3. Use multiple citations if multiple sources support a point: [1][2]
4. Do NOT make claims without citing a source
5. If information is not in the sources, say "This information is not available in the provided sources."

AVAILABLE SOURCES:
{citation_guide}

SOURCE CONTENT:
{citation_context}

USER QUESTION:
{question}

RESPONSE (with inline citations [1], [2], etc.):"""

    def _build_structured_sources(self, docs: List[Dict], citation_map: Dict, question: str) -> List[Dict[str, Any]]:
        """Build rich source metadata for frontend interactive display

        Returns list of StructuredSource-compatible dictionaries
        """
        sources = []

        for idx, doc in enumerate(docs, start=1):
            doc_info = doc.get('document', {})
            text = doc_info.get('text', '')
            metadata = doc_info.get('metadata', {})
            similarity = doc.get('similarity', 0.0)

            # Generate snippet (200 chars)
            snippet = text[:200] + "..." if len(text) > 200 else text

            # Calculate freshness score
            crawled_at = metadata.get('crawled_at') or metadata.get('created_at')
            freshness = self._calculate_document_freshness(crawled_at)

            # Highlight query terms in snippet
            highlighted = self._highlight_query_terms(snippet, question)

            # Build structured source with SourceMetadata-compatible format
            source = {
                'source_id': str(metadata.get('uuid', '')),  # Document UUID for /sources/{id} endpoints
                'citation_id': idx,
                'title': metadata.get('title', f'Source {idx}'),
                'url': metadata.get('url', ''),
                'snippet': snippet,
                'document_type': metadata.get('document_type', 'unknown'),
                'legal_area': metadata.get('legal_area') or metadata.get('category'),
                'relevance_score': round(similarity, 3),
                'highlighted_excerpt': highlighted,
                'metadata': {
                    'source': metadata.get('source', 'kenya_law'),
                    'crawled_at': crawled_at,
                    'last_verified': metadata.get('last_verified_at'),
                    'freshness_score': freshness,
                    'document_date': metadata.get('document_date'),
                    'court_name': metadata.get('court_name'),
                    'case_number': metadata.get('case_number'),
                    'act_chapter': metadata.get('act_chapter'),
                    'citation_text': citation_map.get(idx, ''),
                    'crawl_status': metadata.get('crawl_status', 'active')
                }
            }

            sources.append(source)

        return sources

    def _calculate_document_freshness(self, crawled_at: Optional[str]) -> float:
        """Calculate freshness score (1.0 = today, decreases over time)"""
        if not crawled_at:
            return 0.5

        try:
            # Parse datetime
            if isinstance(crawled_at, str):
                crawled_date = datetime.fromisoformat(crawled_at.replace('Z', '+00:00'))
            elif isinstance(crawled_at, datetime):
                crawled_date = crawled_at
            else:
                return 0.5

            # Calculate days old
            days_old = (datetime.now() - crawled_date.replace(tzinfo=None)).days

            # Freshness decay curve
            if days_old == 0:
                return 1.0
            elif days_old <= 30:
                return 0.95
            elif days_old <= 90:
                return 0.85
            elif days_old <= 365:
                return 0.7
            elif days_old <= 1825:  # 5 years
                return 0.5
            else:
                return 0.3

        except Exception as e:
            logger.warning(f"Error calculating freshness: {e}")
            return 0.5

    def _highlight_query_terms(self, text: str, query: str) -> str:
        """Highlight query terms in text for frontend display using <mark> tags"""
        try:
            # Extract meaningful words from query (> 3 chars, not common stopwords)
            stopwords = {'the', 'and', 'for', 'with', 'this', 'that', 'what', 'when', 'where', 'who', 'how'}
            query_words = [word for word in query.lower().split() if len(word) > 3 and word not in stopwords]

            highlighted_text = text
            for word in query_words:
                # Use word boundaries to avoid partial matches
                pattern = re.compile(f"\\b({re.escape(word)})\\b", re.IGNORECASE)
                highlighted_text = pattern.sub(r"<mark>\1</mark>", highlighted_text)

            return highlighted_text

        except Exception as e:
            logger.warning(f"Error highlighting terms: {e}")
            return text

    def _calculate_confidence(self, sources: List[Dict]) -> float:
        """Calculate overall confidence based on source quality"""
        if not sources:
            return 0.0

        # Average of relevance scores weighted by freshness
        total_weighted_score = 0
        total_weight = 0

        for source in sources:
            relevance = source.get('relevance_score', 0.0)
            freshness = source.get('metadata', {}).get('freshness_score', 0.5)
            weight = freshness

            total_weighted_score += relevance * weight
            total_weight += weight

        return round(total_weighted_score / total_weight if total_weight > 0 else 0.0, 3)

    def _calculate_overall_freshness(self, sources: List[Dict]) -> float:
        """Calculate average freshness score across all sources"""
        if not sources:
            return 0.5

        freshness_scores = [s.get('metadata', {}).get('freshness_score', 0.5) for s in sources]
        return round(sum(freshness_scores) / len(freshness_scores), 3)

# Global instance
enhanced_rag_service = EnhancedRAGService()
