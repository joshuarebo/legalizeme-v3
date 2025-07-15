"""
Enhanced RAG Service with AWS-Native Components
Integrates AWS Vector Service, Embedding Service, and Token Service
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import json

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
    
    async def query(self, question: str, context: str = "", max_tokens: int = 4000) -> Dict[str, Any]:
        """Perform RAG query with enhanced context"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Step 1: Retrieve relevant documents
            retrieved_docs = await self.vector_service.search_similar(
                query=question,
                limit=self.max_retrieved_docs,
                threshold=self.similarity_threshold
            )
            
            # Step 2: Build context from retrieved documents
            rag_context = self._build_context(retrieved_docs, question)
            
            # Step 3: Combine with provided context
            full_context = f"{context}\n\n{rag_context}".strip()
            
            # Step 4: Check token limits and truncate if needed
            context_tokens = self.token_service.count_tokens(full_context)
            if context_tokens > self.max_context_tokens:
                full_context = self.token_service.truncate_to_limit(
                    full_context, 
                    limit=self.max_context_tokens
                )
            
            # Step 5: Generate response using LLM
            prompt = self._create_rag_prompt(question, full_context)
            
            # Use LLM manager for response generation
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                model_preference=['claude-3-sonnet', 'claude-3-haiku'],
                max_tokens=max_tokens
            )
            
            # Step 6: Calculate costs and metrics
            total_tokens = self.token_service.count_tokens(prompt + response.get('response_text', ''))
            cost_estimate = self.token_service.estimate_cost(
                prompt + response.get('response_text', ''),
                model=response.get('model_used', 'claude-3-sonnet')
            )
            
            return {
                'success': response.get('success', False),
                'response': response.get('response_text', ''),
                'model_used': response.get('model_used', ''),
                'retrieved_documents': len(retrieved_docs),
                'context_tokens': context_tokens,
                'total_tokens': total_tokens,
                'cost_estimate': cost_estimate,
                'sources': [doc['doc_id'] for doc in retrieved_docs],
                'similarities': [doc['similarity'] for doc in retrieved_docs],
                'latency_ms': response.get('latency_ms', 0)
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': '',
                'retrieved_documents': 0,
                'context_tokens': 0,
                'total_tokens': 0
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

# Global instance
enhanced_rag_service = EnhancedRAGService()
