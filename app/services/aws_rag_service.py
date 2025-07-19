"""
AWS-NATIVE RAG SERVICE
=====================
World-class RAG implementation using AWS services:
- AWS RDS PostgreSQL with pgvector for vector storage
- AWS Bedrock Titan for embeddings
- AWS OpenSearch for hybrid search (optional)
- Advanced semantic chunking for legal documents
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import boto3
from sqlalchemy import text
import numpy as np

from app.config import settings
from app.database import get_db
from app.services.aws_embedding_service import aws_embedding_service
from app.services.llm_manager import llm_manager
from app.services.aws_opensearch_service import aws_opensearch_service

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Document chunk with metadata"""
    id: str
    content: str
    embedding: List[float]
    document_id: str
    chunk_index: int
    legal_area: str
    source_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class RAGResult:
    """RAG query result"""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]
    model_used: str
    retrieval_strategy: str
    processing_time_ms: float

class AWSRAGService:
    """
    AWS-native RAG service for Kenyan legal documents
    Uses PostgreSQL with pgvector extension for vector storage
    """
    
    def __init__(self):
        self.embedding_service = aws_embedding_service
        self.llm_manager = llm_manager
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.max_context_tokens = 8000
        self._initialized = False
        
        # Legal document structure patterns
        self.legal_patterns = {
            'section_headers': [r'Section \d+', r'Article \d+', r'Chapter \d+'],
            'subsection_markers': [r'\(\d+\)', r'\([a-z]\)', r'\(i+\)'],
            'legal_citations': [r'\[\d{4}\]', r'Cap\. \d+', r'Act No\. \d+'],
            'paragraph_breaks': [r'\n\n', r'\n\d+\.', r'\n\([a-z]\)']
        }
    
    async def initialize(self):
        """Initialize AWS RAG service with OpenSearch integration"""
        if self._initialized:
            return

        try:
            # Initialize embedding service
            await self.embedding_service.initialize()

            # Initialize OpenSearch service
            await aws_opensearch_service.initialize()
            await aws_opensearch_service.create_index_if_not_exists()

            # Ensure pgvector extension and tables exist (fallback)
            await self._setup_vector_database()

            self._initialized = True
            logger.info("AWS RAG Service initialized with OpenSearch integration")

        except Exception as e:
            logger.error(f"Failed to initialize AWS RAG Service: {e}")
            self._initialized = True  # Continue without vector storage
    
    async def _setup_vector_database(self):
        """Setup PostgreSQL with pgvector extension"""
        try:
            async for db in get_db():
                # Enable pgvector extension
                await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                
                # Create document chunks table
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id VARCHAR PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(1536),  -- Titan embedding dimension
                    document_id VARCHAR NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    legal_area VARCHAR(100),
                    source_url TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
                await db.execute(text(create_table_sql))
                
                # Create indexes for performance
                index_sql = [
                    "CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops);",
                    "CREATE INDEX IF NOT EXISTS idx_chunks_legal_area ON document_chunks (legal_area);",
                    "CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks (document_id);"
                ]
                
                for sql in index_sql:
                    await db.execute(text(sql))
                
                await db.commit()
                logger.info("Vector database setup completed")
                break
                
        except Exception as e:
            logger.warning(f"Vector database setup failed: {e}")
    
    async def add_document(
        self, 
        document_id: str, 
        content: str, 
        legal_area: str,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add document to vector database with advanced chunking
        
        Args:
            document_id: Unique document identifier
            content: Document content
            legal_area: Legal practice area
            source_url: Source URL
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Advanced semantic chunking for legal documents
            chunks = await self._semantic_chunk_legal_document(content, legal_area)
            
            # Generate embeddings for all chunks
            chunk_embeddings = []
            for chunk in chunks:
                embedding = await self.embedding_service.generate_embeddings(chunk)
                if embedding:
                    chunk_embeddings.append(embedding)
                else:
                    logger.warning(f"Failed to generate embedding for chunk in {document_id}")
                    chunk_embeddings.append([0.0] * 1536)  # Zero vector fallback
            
            # Store chunks in database
            async for db in get_db():
                for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                    chunk_id = f"{document_id}_chunk_{i}"
                    
                    insert_sql = """
                    INSERT INTO document_chunks 
                    (id, content, embedding, document_id, chunk_index, legal_area, source_url, metadata)
                    VALUES (:id, :content, :embedding, :document_id, :chunk_index, :legal_area, :source_url, :metadata)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP;
                    """
                    
                    await db.execute(text(insert_sql), {
                        'id': chunk_id,
                        'content': chunk,
                        'embedding': embedding,
                        'document_id': document_id,
                        'chunk_index': i,
                        'legal_area': legal_area,
                        'source_url': source_url,
                        'metadata': json.dumps(metadata or {})
                    })
                
                await db.commit()
                logger.info(f"Added {len(chunks)} chunks for document {document_id}")
                break
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding document {document_id}: {e}")
            return False
    
    async def _semantic_chunk_legal_document(self, content: str, legal_area: str) -> List[str]:
        """
        Advanced semantic chunking for legal documents
        Respects legal document structure and maintains context
        """
        try:
            # Clean and normalize content
            content = self._clean_legal_text(content)
            
            # Split by legal structure first
            structural_chunks = self._split_by_legal_structure(content)
            
            # Further chunk if pieces are too large
            final_chunks = []
            for chunk in structural_chunks:
                if len(chunk) <= self.chunk_size:
                    final_chunks.append(chunk)
                else:
                    # Split large chunks with overlap
                    sub_chunks = self._split_with_overlap(chunk, self.chunk_size, self.chunk_overlap)
                    final_chunks.extend(sub_chunks)
            
            # Filter out very small chunks
            final_chunks = [chunk for chunk in final_chunks if len(chunk.strip()) > 50]
            
            logger.debug(f"Created {len(final_chunks)} chunks for {legal_area} document")
            return final_chunks
            
        except Exception as e:
            logger.error(f"Error in semantic chunking: {e}")
            # Fallback to simple chunking
            return self._split_with_overlap(content, self.chunk_size, self.chunk_overlap)
    
    def _clean_legal_text(self, text: str) -> str:
        """Clean and normalize legal text"""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Normalize legal citations
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1\n\2', text)
        
        return text.strip()
    
    def _split_by_legal_structure(self, content: str) -> List[str]:
        """Split content by legal document structure"""
        import re
        
        # Split by major sections first
        section_pattern = r'(?=(?:Section|Article|Chapter|Part)\s+\d+)'
        sections = re.split(section_pattern, content, flags=re.IGNORECASE)
        
        if len(sections) <= 1:
            # No clear sections, split by paragraphs
            paragraphs = content.split('\n\n')
            return [p.strip() for p in paragraphs if p.strip()]
        
        return [section.strip() for section in sections if section.strip()]
    
    def _split_with_overlap(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text with overlap to maintain context"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to break at sentence boundary
            chunk = text[start:end]
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            
            break_point = max(last_period, last_newline)
            if break_point > start + chunk_size // 2:  # Don't break too early
                end = start + break_point + 1
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return chunks

    async def query_with_context(
        self,
        query: str,
        context: Dict[str, Any] = None,
        max_sources: int = 5,
        query_embedding: Optional[List[float]] = None,
        use_hybrid_search: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced query with AWS OpenSearch hybrid search

        Args:
            query: User query
            context: Additional context
            max_sources: Maximum number of source documents
            query_embedding: Pre-computed query embedding
            use_hybrid_search: Use hybrid semantic + keyword search

        Returns:
            RAG result with answer and sources
        """
        start_time = datetime.utcnow()

        try:
            if not self._initialized:
                await self.initialize()

            # Determine legal area from context or query
            legal_area = context.get('legal_area') if context else None
            if not legal_area:
                legal_area = self._detect_legal_area_from_query(query)

            # Use hybrid search for better results
            if use_hybrid_search:
                search_results = await aws_opensearch_service.hybrid_search(
                    query=query,
                    legal_area=legal_area,
                    max_results=max_sources * 2,
                    semantic_weight=0.7
                )

                relevant_documents = search_results.combined_results
                retrieval_strategy = f"hybrid_search_{search_results.search_strategy}"
            else:
                # Fallback to vector similarity search
                if not query_embedding:
                    query_embedding = await self.embedding_service.generate_embeddings(query)

                if not query_embedding:
                    logger.warning("Failed to generate query embedding, using fallback")
                    return await self._fallback_query(query)

                relevant_chunks = await self._vector_similarity_search(
                    query_embedding, max_sources * 2, context
                )
                relevant_documents = self._convert_chunks_to_search_results(relevant_chunks)
                retrieval_strategy = "vector_similarity_fallback"

            if not relevant_documents:
                logger.warning("No relevant documents found")
                return await self._fallback_query(query)

            # Build enhanced context from search results
            rag_context = self._build_enhanced_rag_context(relevant_documents, query)

            # Generate response using LLM with enhanced RAG context
            response = await self._generate_enhanced_rag_response(query, rag_context, context, relevant_documents)

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return {
                "answer": response.get("response_text", ""),
                "confidence": self._calculate_enhanced_confidence(response, relevant_documents),
                "sources": self._format_enhanced_sources(relevant_documents[:max_sources]),
                "documents": self._format_enhanced_documents(relevant_documents[:max_sources]),
                "model_used": response.get("model_used", "claude-sonnet-4"),
                "retrieval_strategy": retrieval_strategy,
                "processing_time_ms": processing_time,
                "search_metadata": {
                    "total_found": len(relevant_documents),
                    "legal_area": legal_area,
                    "hybrid_search": use_hybrid_search
                }
            }

        except Exception as e:
            logger.error(f"Error in enhanced RAG query: {e}")
            return await self._fallback_query(query)

    async def _vector_similarity_search(
        self,
        query_embedding: List[float],
        limit: int,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            async for db in get_db():
                # Build query with optional legal area filter
                where_clause = ""
                params = {
                    'embedding': query_embedding,
                    'limit': limit
                }

                if context and context.get('legal_area'):
                    where_clause = "WHERE legal_area = :legal_area"
                    params['legal_area'] = context['legal_area']

                # Vector similarity search using cosine distance
                search_sql = f"""
                SELECT
                    id, content, document_id, chunk_index, legal_area,
                    source_url, metadata,
                    1 - (embedding <=> :embedding::vector) as similarity
                FROM document_chunks
                {where_clause}
                ORDER BY embedding <=> :embedding::vector
                LIMIT :limit;
                """

                result = await db.execute(text(search_sql), params)
                rows = result.fetchall()

                chunks = []
                for row in rows:
                    chunks.append({
                        'id': row.id,
                        'content': row.content,
                        'document_id': row.document_id,
                        'chunk_index': row.chunk_index,
                        'legal_area': row.legal_area,
                        'source_url': row.source_url,
                        'metadata': json.loads(row.metadata) if row.metadata else {},
                        'similarity': float(row.similarity)
                    })

                logger.info(f"Found {len(chunks)} relevant chunks")
                return chunks

        except Exception as e:
            logger.error(f"Error in vector similarity search: {e}")
            return []

    def _build_rag_context(self, chunks: List[Dict[str, Any]], query: str) -> str:
        """Build context from retrieved chunks"""
        try:
            context_parts = []
            total_tokens = 0
            max_tokens = self.max_context_tokens

            # Sort chunks by similarity
            sorted_chunks = sorted(chunks, key=lambda x: x.get('similarity', 0), reverse=True)

            for chunk in sorted_chunks:
                content = chunk['content']
                # Rough token estimation (1 token ≈ 4 characters)
                chunk_tokens = len(content) // 4

                if total_tokens + chunk_tokens > max_tokens:
                    break

                # Format chunk with metadata
                legal_area = chunk.get('legal_area', 'general')
                source = chunk.get('source_url', 'Unknown source')

                formatted_chunk = f"""
[{legal_area.upper()} LAW - {source}]
{content}
"""
                context_parts.append(formatted_chunk)
                total_tokens += chunk_tokens

            context = "\n\n".join(context_parts)
            logger.debug(f"Built RAG context with {len(context_parts)} chunks, ~{total_tokens} tokens")

            return context

        except Exception as e:
            logger.error(f"Error building RAG context: {e}")
            return ""

    async def _generate_rag_response(
        self,
        query: str,
        context: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate response using LLM with RAG context"""
        try:
            # Build RAG-enhanced prompt
            rag_prompt = f"""You are a Kenyan legal expert. Use the following legal documents and context to answer the user's question accurately and comprehensively.

LEGAL CONTEXT:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
1. Base your answer primarily on the provided legal context
2. Cite specific legal provisions and sources when available
3. If the context doesn't fully address the question, clearly state what information is missing
4. Provide practical, actionable guidance
5. Recommend professional legal consultation when appropriate

Please provide a comprehensive answer based on the legal context provided above."""

            # Use LLM manager for response generation
            response = await self.llm_manager.invoke_model(
                prompt=rag_prompt,
                model_preference="claude-sonnet-4"
            )

            return response

        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return {"success": False, "response_text": "Error generating response"}

    async def _fallback_query(self, query: str) -> Dict[str, Any]:
        """Fallback query without RAG context"""
        try:
            from app.services.kenyan_legal_prompt_optimizer import kenyan_legal_prompt_optimizer

            optimized_prompt = kenyan_legal_prompt_optimizer.optimize_for_speed(query)
            response = await self.llm_manager.invoke_model(
                prompt=optimized_prompt,
                model_preference="claude-sonnet-4"
            )

            return {
                "answer": response.get("response_text", ""),
                "confidence": 0.6,  # Lower confidence for fallback
                "sources": [],
                "documents": [],
                "model_used": response.get("model_used", "claude-sonnet-4"),
                "retrieval_strategy": "fallback_direct"
            }

        except Exception as e:
            logger.error(f"Error in fallback query: {e}")
            return {
                "answer": "I apologize, but I'm unable to process your query at the moment.",
                "confidence": 0.1,
                "sources": [],
                "documents": [],
                "model_used": "error",
                "retrieval_strategy": "error"
            }

    def _calculate_confidence(self, response: Dict[str, Any], chunks: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on response and retrieved chunks"""
        base_confidence = 0.8 if response.get("success") else 0.3

        # Boost confidence if we have high-similarity chunks
        if chunks:
            avg_similarity = sum(chunk.get('similarity', 0) for chunk in chunks) / len(chunks)
            similarity_boost = min(avg_similarity * 0.2, 0.15)
            base_confidence += similarity_boost

        return min(base_confidence, 0.95)

    def _format_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format sources for response"""
        sources = []
        seen_sources = set()

        for chunk in chunks:
            source_url = chunk.get('source_url', '')
            if source_url and source_url not in seen_sources:
                sources.append({
                    'url': source_url,
                    'legal_area': chunk.get('legal_area', 'general'),
                    'similarity': chunk.get('similarity', 0),
                    'document_id': chunk.get('document_id', '')
                })
                seen_sources.add(source_url)

        return sources

    def _format_documents(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format documents for response"""
        return [
            {
                'id': chunk.get('document_id', ''),
                'content_preview': chunk.get('content', '')[:200] + "...",
                'legal_area': chunk.get('legal_area', 'general'),
                'similarity': chunk.get('similarity', 0),
                'source': chunk.get('source_url', '')
            }
            for chunk in chunks
        ]

    def _detect_legal_area_from_query(self, query: str) -> Optional[str]:
        """Detect legal area from query content"""
        query_lower = query.lower()

        legal_area_keywords = {
            'employment': ['employment', 'job', 'work', 'salary', 'wage', 'termination', 'contract', 'leave'],
            'company': ['company', 'business', 'registration', 'director', 'shareholder', 'incorporation'],
            'constitutional': ['constitution', 'rights', 'freedom', 'bill of rights', 'fundamental'],
            'land': ['land', 'property', 'title', 'ownership', 'transfer', 'lease'],
            'family': ['marriage', 'divorce', 'custody', 'maintenance', 'family', 'matrimonial'],
            'data_protection': ['data', 'privacy', 'protection', 'gdpr', 'personal information'],
            'criminal': ['criminal', 'crime', 'offense', 'prosecution', 'court', 'sentence']
        }

        for area, keywords in legal_area_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return area

        return None

    def _convert_chunks_to_search_results(self, chunks: List[Dict[str, Any]]) -> List[Any]:
        """Convert old chunk format to SearchResult format"""
        from app.services.aws_opensearch_service import SearchResult

        results = []
        for chunk in chunks:
            results.append(SearchResult(
                document_id=chunk.get('document_id', ''),
                content=chunk.get('content', ''),
                score=chunk.get('similarity', 0),
                legal_area=chunk.get('legal_area', 'general'),
                source_url=chunk.get('source_url'),
                metadata=chunk.get('metadata', {}),
                highlights=[chunk.get('content', '')[:200] + "..."]
            ))
        return results

    def _build_enhanced_rag_context(self, search_results: List[Any], query: str) -> str:
        """Build enhanced context from OpenSearch results"""
        try:
            context_parts = []
            total_tokens = 0
            max_tokens = self.max_context_tokens

            # Sort by score
            sorted_results = sorted(search_results, key=lambda x: x.score, reverse=True)

            for result in sorted_results:
                content = result.content
                # Rough token estimation
                content_tokens = len(content) // 4

                if total_tokens + content_tokens > max_tokens:
                    break

                # Format with enhanced metadata
                formatted_content = f"""
[{result.legal_area.upper()} LAW - Score: {result.score:.3f}]
Source: {result.source_url or 'Legal Database'}
{content}

Highlights: {' | '.join(result.highlights[:2])}
"""
                context_parts.append(formatted_content)
                total_tokens += content_tokens

            context = "\n\n".join(context_parts)
            logger.debug(f"Built enhanced RAG context with {len(context_parts)} documents, ~{total_tokens} tokens")

            return context

        except Exception as e:
            logger.error(f"Error building enhanced RAG context: {e}")
            return ""

    async def _generate_enhanced_rag_response(
        self,
        query: str,
        context: str,
        user_context: Optional[Dict[str, Any]] = None,
        search_results: List[Any] = None
    ) -> Dict[str, Any]:
        """Generate enhanced response with search result metadata"""
        try:
            # Build enhanced RAG prompt
            legal_areas = list(set(result.legal_area for result in search_results)) if search_results else []

            enhanced_prompt = f"""You are a Kenyan legal expert. Use the following legal documents and context to answer the user's question accurately and comprehensively.

LEGAL CONTEXT FROM KENYAN LAW DATABASE:
{context}

SEARCH METADATA:
- Legal Areas Covered: {', '.join(legal_areas)}
- Number of Sources: {len(search_results) if search_results else 0}
- Query Type: Legal Research and Analysis

USER QUESTION: {query}

ENHANCED INSTRUCTIONS:
1. Base your answer primarily on the provided legal context from official Kenyan sources
2. Cite specific legal provisions, sections, and acts when available
3. Reference the source documents and their relevance scores
4. If the context doesn't fully address the question, clearly state what information is missing
5. Provide practical, actionable guidance specific to Kenyan law
6. Include compliance requirements and deadlines where applicable
7. Recommend professional legal consultation for complex matters
8. Structure your response with clear headings for better readability

Please provide a comprehensive, well-structured answer based on the legal context provided above."""

            # Use enhanced model selection
            response = await self.llm_manager.invoke_model(
                prompt=enhanced_prompt,
                model_preference="claude-sonnet-4"
            )

            return response

        except Exception as e:
            logger.error(f"Error generating enhanced RAG response: {e}")
            return {"success": False, "response_text": "Error generating response"}

    def _calculate_enhanced_confidence(self, response: Dict[str, Any], search_results: List[Any]) -> float:
        """Calculate enhanced confidence based on search results"""
        base_confidence = 0.8 if response.get("success") else 0.3

        if search_results:
            # Boost confidence based on search result quality
            avg_score = sum(result.score for result in search_results) / len(search_results)
            score_boost = min(avg_score * 0.15, 0.1)
            base_confidence += score_boost

            # Boost confidence if multiple legal areas covered
            legal_areas = set(result.legal_area for result in search_results)
            if len(legal_areas) > 1:
                base_confidence += 0.05

        return min(base_confidence, 0.95)

    def _format_enhanced_sources(self, search_results: List[Any]) -> List[Dict[str, Any]]:
        """Format enhanced sources with search metadata"""
        sources = []
        seen_sources = set()

        for result in search_results:
            source_url = result.source_url or f"legal_db_{result.document_id}"
            if source_url not in seen_sources:
                sources.append({
                    'url': source_url,
                    'legal_area': result.legal_area,
                    'relevance_score': result.score,
                    'document_id': result.document_id,
                    'highlights': result.highlights[:2]  # Top 2 highlights
                })
                seen_sources.add(source_url)

        return sources

    def _format_enhanced_documents(self, search_results: List[Any]) -> List[Dict[str, Any]]:
        """Format enhanced documents with search metadata"""
        return [
            {
                'id': result.document_id,
                'content_preview': result.content[:300] + "..." if len(result.content) > 300 else result.content,
                'legal_area': result.legal_area,
                'relevance_score': result.score,
                'source': result.source_url or 'Legal Database',
                'highlights': result.highlights,
                'metadata': result.metadata
            }
            for result in search_results
        ]

# Global AWS RAG service instance
aws_rag_service = AWSRAGService()
