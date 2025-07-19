"""
STREAMING RAG SERVICE
====================
Production-grade streaming service for RAG queries with progressive document retrieval.
Provides real-time feedback during document search and response generation.
"""

import json
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass
import uuid

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.services.aws_rag_service import aws_rag_service
from app.services.aws_opensearch_service import aws_opensearch_service
from app.services.kenyan_legal_prompt_optimizer import kenyan_legal_prompt_optimizer
from app.services.intelligent_cache_service import intelligent_cache_service
from app.services.llm_manager import llm_manager

logger = logging.getLogger(__name__)

@dataclass
class RAGStreamingChunk:
    """RAG streaming response chunk"""
    id: str
    event: str
    data: Dict[str, Any]
    timestamp: datetime

class StreamingRAGService:
    """
    Production-grade streaming service for RAG queries
    Implements progressive document retrieval and response streaming
    """
    
    def __init__(self):
        self.active_streams: Dict[str, bool] = {}
        self.max_concurrent_streams = 30
        self.stream_timeout_seconds = 180  # 3 minutes for RAG
        self._initialized = False
    
    async def initialize(self):
        """Initialize streaming RAG service"""
        if self._initialized:
            return
        
        try:
            # Initialize dependencies
            await aws_rag_service.initialize()
            await aws_opensearch_service.initialize()
            await kenyan_legal_prompt_optimizer.initialize()
            await intelligent_cache_service.initialize()
            
            self._initialized = True
            logger.info("Streaming RAG Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Streaming RAG Service: {e}")
            self._initialized = True
    
    async def stream_rag_response(
        self,
        query: str,
        legal_area: Optional[str] = None,
        max_sources: int = 5,
        session_id: Optional[str] = None
    ) -> StreamingResponse:
        """
        Stream RAG response with progressive document retrieval
        
        Args:
            query: User query
            legal_area: Legal area filter
            max_sources: Maximum source documents
            session_id: Session identifier
            
        Returns:
            StreamingResponse with SSE
        """
        if not self._initialized:
            await self.initialize()
        
        # Check concurrent stream limit
        if len(self.active_streams) >= self.max_concurrent_streams:
            raise HTTPException(
                status_code=429,
                detail="Too many concurrent RAG streams. Please try again later."
            )
        
        stream_id = session_id or str(uuid.uuid4())
        self.active_streams[stream_id] = True
        
        async def generate_rag_stream():
            try:
                # Send initial status
                yield self._format_sse_chunk(
                    event="status",
                    data={"status": "initializing", "message": "Starting document search..."},
                    stream_id=stream_id
                )
                
                # Step 1: Check cache first
                yield self._format_sse_chunk(
                    event="status",
                    data={"status": "cache_check", "message": "Checking intelligent cache..."},
                    stream_id=stream_id
                )
                
                cached_response = await intelligent_cache_service.get_cached_response(query)
                if cached_response:
                    yield self._format_sse_chunk(
                        event="cache_hit",
                        data={"message": "Found cached response", "confidence": cached_response.get("confidence", 0.8)},
                        stream_id=stream_id
                    )
                    
                    yield self._format_sse_chunk(
                        event="content",
                        data={"content": cached_response.get("answer", "")},
                        stream_id=stream_id
                    )
                    
                    yield self._format_sse_chunk(
                        event="complete",
                        data={
                            "status": "completed",
                            "cached": True,
                            "sources": cached_response.get("sources", []),
                            "confidence": cached_response.get("confidence", 0.8)
                        },
                        stream_id=stream_id
                    )
                    return
                
                # Step 2: Document search
                yield self._format_sse_chunk(
                    event="status",
                    data={"status": "searching", "message": "Searching legal documents..."},
                    stream_id=stream_id
                )
                
                # Perform hybrid search
                search_results = await aws_opensearch_service.hybrid_search(
                    query=query,
                    legal_area=legal_area,
                    max_results=max_sources * 2
                )
                
                yield self._format_sse_chunk(
                    event="search_results",
                    data={
                        "total_found": search_results.total_found,
                        "strategy": search_results.search_strategy,
                        "message": f"Found {search_results.total_found} relevant documents"
                    },
                    stream_id=stream_id
                )
                
                # Step 3: Stream document processing
                yield self._format_sse_chunk(
                    event="status",
                    data={"status": "processing", "message": "Processing documents..."},
                    stream_id=stream_id
                )
                
                # Stream document summaries
                for i, result in enumerate(search_results.combined_results[:max_sources]):
                    yield self._format_sse_chunk(
                        event="document_processed",
                        data={
                            "document_id": result.document_id,
                            "legal_area": result.legal_area,
                            "relevance_score": result.score,
                            "preview": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                            "progress": f"{i + 1}/{min(len(search_results.combined_results), max_sources)}"
                        },
                        stream_id=stream_id
                    )
                    
                    # Small delay for better UX
                    await asyncio.sleep(0.1)
                
                # Step 4: Generate response
                yield self._format_sse_chunk(
                    event="status",
                    data={"status": "generating", "message": "Generating legal analysis..."},
                    stream_id=stream_id
                )
                
                # Build context and generate response
                rag_context = self._build_streaming_context(search_results.combined_results[:max_sources])
                
                # Stream the LLM response
                async for chunk in self._stream_rag_llm_response(query, rag_context, stream_id):
                    if not self.active_streams.get(stream_id, False):
                        break
                    yield chunk
                
                # Step 5: Final metadata
                yield self._format_sse_chunk(
                    event="metadata",
                    data={
                        "sources": [
                            {
                                "document_id": result.document_id,
                                "legal_area": result.legal_area,
                                "relevance_score": result.score,
                                "source_url": result.source_url
                            }
                            for result in search_results.combined_results[:max_sources]
                        ],
                        "search_strategy": search_results.search_strategy,
                        "total_documents": search_results.total_found
                    },
                    stream_id=stream_id
                )
                
                # Send completion
                yield self._format_sse_chunk(
                    event="complete",
                    data={"status": "completed", "cached": False},
                    stream_id=stream_id
                )
                
            except Exception as e:
                logger.error(f"Error in RAG streaming response: {e}")
                yield self._format_sse_chunk(
                    event="error",
                    data={"error": str(e), "message": "An error occurred during RAG processing"},
                    stream_id=stream_id
                )
            finally:
                # Cleanup
                self.active_streams.pop(stream_id, None)
        
        return StreamingResponse(
            generate_rag_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    
    def _build_streaming_context(self, search_results: List[Any]) -> str:
        """Build context from search results for streaming"""
        context_parts = []
        
        for i, result in enumerate(search_results):
            context_part = f"""
[DOCUMENT {i + 1} - {result.legal_area.upper()} LAW - Relevance: {result.score:.3f}]
Source: {result.source_url or 'Legal Database'}
Content: {result.content[:1000]}...

Key Points: {' | '.join(result.highlights[:2]) if result.highlights else 'N/A'}
"""
            context_parts.append(context_part)
        
        return "\n\n".join(context_parts)
    
    async def _stream_rag_llm_response(
        self, 
        query: str, 
        context: str, 
        stream_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response for RAG query"""
        
        try:
            # Build RAG prompt
            rag_prompt = f"""You are a Kenyan legal expert. Use the following legal documents to answer the user's question accurately and comprehensively.

LEGAL CONTEXT FROM KENYAN LAW DATABASE:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
1. Base your answer primarily on the provided legal context
2. Cite specific legal provisions, sections, and acts when available
3. Reference the document sources and their relevance scores
4. If the context doesn't fully address the question, clearly state what information is missing
5. Provide practical, actionable guidance specific to Kenyan law
6. Structure your response with clear headings for better readability

Please provide a comprehensive, well-structured answer based on the legal context provided above."""

            # Use LLM manager for response
            response = await llm_manager.invoke_model(
                prompt=rag_prompt,
                model_preference="claude-sonnet-4"
            )
            
            if response.get("success"):
                response_text = response.get("response_text", "")
                
                # Stream response in chunks
                words = response_text.split()
                current_chunk = []
                
                for word in words:
                    current_chunk.append(word)
                    
                    if len(' '.join(current_chunk)) >= 150:  # Larger chunks for RAG
                        chunk_text = ' '.join(current_chunk)
                        
                        yield self._format_sse_chunk(
                            event="content",
                            data={"content": chunk_text},
                            stream_id=stream_id
                        )
                        
                        current_chunk = []
                        await asyncio.sleep(0.05)
                
                # Send remaining content
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    yield self._format_sse_chunk(
                        event="content",
                        data={"content": chunk_text},
                        stream_id=stream_id
                    )
            else:
                yield self._format_sse_chunk(
                    event="error",
                    data={"error": "Failed to generate response"},
                    stream_id=stream_id
                )
            
        except Exception as e:
            logger.error(f"Error streaming RAG LLM response: {e}")
            yield self._format_sse_chunk(
                event="error",
                data={"error": str(e)},
                stream_id=stream_id
            )
    
    def _format_sse_chunk(
        self, 
        event: str, 
        data: Dict[str, Any], 
        stream_id: str
    ) -> str:
        """Format Server-Sent Event chunk"""
        
        chunk_data = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "stream_id": stream_id,
            **data
        }
        
        return f"event: {event}\ndata: {json.dumps(chunk_data)}\n\n"
    
    def stop_stream(self, stream_id: str) -> bool:
        """Stop an active RAG stream"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id] = False
            return True
        return False
    
    def get_active_streams(self) -> List[str]:
        """Get list of active RAG stream IDs"""
        return [sid for sid, active in self.active_streams.items() if active]

# Global streaming RAG service instance
streaming_rag_service = StreamingRAGService()
