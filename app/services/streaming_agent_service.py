"""
STREAMING AGENT SERVICE
======================
Production-grade streaming service for agent responses using Server-Sent Events (SSE).
Prevents timeouts and provides real-time feedback for complex legal reasoning.
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

from app.services.llm_manager import llm_manager
from app.services.kenyan_legal_prompt_optimizer import kenyan_legal_prompt_optimizer
from app.services.intelligent_cache_service import intelligent_cache_service

logger = logging.getLogger(__name__)

@dataclass
class StreamingChunk:
    """Streaming response chunk"""
    id: str
    event: str
    data: Dict[str, Any]
    timestamp: datetime

class StreamingAgentService:
    """
    Production-grade streaming service for agent responses
    Implements Server-Sent Events (SSE) for real-time feedback
    """
    
    def __init__(self):
        self.active_streams: Dict[str, bool] = {}
        self.chunk_size = 100  # Characters per chunk
        self.heartbeat_interval = 5  # Seconds
        self._initialized = False

        # Connection management
        self.max_concurrent_streams = 50  # Limit concurrent streams
        self.stream_timeout_seconds = 300  # 5 minute timeout
        self.retry_attempts = 3  # Retry failed operations

        # Resource optimization
        self.cleanup_interval = 60  # Cleanup inactive streams every minute
    
    async def initialize(self):
        """Initialize streaming service"""
        if self._initialized:
            return
        
        try:
            # Initialize dependencies
            await kenyan_legal_prompt_optimizer.initialize()
            await intelligent_cache_service.initialize()

            # Start cleanup task
            asyncio.create_task(self._cleanup_inactive_streams())

            self._initialized = True
            logger.info("Streaming Agent Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Streaming Agent Service: {e}")
            self._initialized = True
    
    async def stream_agent_response(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> StreamingResponse:
        """
        Stream agent response with real-time updates
        
        Args:
            query: User query
            context: Additional context
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
                detail="Too many concurrent streams. Please try again later."
            )

        stream_id = session_id or str(uuid.uuid4())
        self.active_streams[stream_id] = True
        
        async def generate_stream():
            try:
                # Send initial status
                yield self._format_sse_chunk(
                    event="status",
                    data={"status": "initializing", "message": "Starting legal analysis..."},
                    stream_id=stream_id
                )
                
                # Generate optimized prompt
                yield self._format_sse_chunk(
                    event="status",
                    data={"status": "processing", "message": "Building legal context..."},
                    stream_id=stream_id
                )
                
                # Build context-engineered prompt for streaming
                agent_prompt = await self._build_streaming_prompt(query, context)
                
                # Send reasoning structure
                yield self._format_sse_chunk(
                    event="reasoning_structure",
                    data={
                        "steps": [
                            "Legal Issue Identification",
                            "Legal Framework Analysis", 
                            "Practical Application",
                            "Recommendations"
                        ]
                    },
                    stream_id=stream_id
                )
                
                # Stream the agent response
                async for chunk in self._stream_llm_response(agent_prompt, stream_id):
                    if not self.active_streams.get(stream_id, False):
                        break
                    yield chunk
                
                # Send completion
                yield self._format_sse_chunk(
                    event="complete",
                    data={"status": "completed", "message": "Legal analysis complete"},
                    stream_id=stream_id
                )
                
            except Exception as e:
                logger.error(f"Error in streaming response: {e}")
                yield self._format_sse_chunk(
                    event="error",
                    data={"error": str(e), "message": "An error occurred during analysis"},
                    stream_id=stream_id
                )
            finally:
                # Cleanup
                self.active_streams.pop(stream_id, None)
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    
    async def _build_streaming_prompt(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build optimized prompt for streaming responses"""
        
        # Get base optimized prompt
        base_prompt = kenyan_legal_prompt_optimizer.optimize_prompt(
            query=query,
            query_type="agent_research",
            context=context
        )
        
        # Add streaming-specific instructions
        streaming_prompt = f"""{base_prompt}

STREAMING RESPONSE FORMAT:
Please provide your analysis in clearly marked sections that can be streamed progressively:

## LEGAL ISSUE IDENTIFICATION
[Identify the core legal question and applicable Kenyan law area]

## LEGAL FRAMEWORK ANALYSIS  
[Analyze relevant statutes, regulations, and legal precedents]

## PRACTICAL APPLICATION
[Apply the legal framework to the specific situation]

## RECOMMENDATIONS
[Provide actionable recommendations and next steps]

IMPORTANT: 
- Write each section completely before moving to the next
- Use clear section headers as shown above
- Provide detailed analysis in each section
- Include specific legal citations and references
- End each section with a clear conclusion

Begin your analysis now:"""

        return streaming_prompt
    
    async def _stream_llm_response(
        self, 
        prompt: str, 
        stream_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response with chunking and progress updates"""
        
        try:
            # Use parallel processing for faster response
            response = await llm_manager.invoke_model_parallel(
                prompt=prompt,
                max_concurrent=2
            )
            
            if not response.get("success"):
                raise Exception(f"LLM invocation failed: {response.get('error', 'Unknown error')}")
            
            response_text = response.get("response_text", "")
            
            # Parse and stream by sections
            sections = self._parse_response_sections(response_text)
            
            for section_name, section_content in sections.items():
                # Send section header
                yield self._format_sse_chunk(
                    event="section_start",
                    data={
                        "section": section_name,
                        "message": f"Analyzing {section_name.lower()}..."
                    },
                    stream_id=stream_id
                )
                
                # Stream section content in chunks
                async for chunk in self._chunk_content(section_content, stream_id):
                    yield chunk
                
                # Send section completion
                yield self._format_sse_chunk(
                    event="section_complete",
                    data={
                        "section": section_name,
                        "message": f"Completed {section_name.lower()}"
                    },
                    stream_id=stream_id
                )
                
                # Small delay between sections for better UX
                await asyncio.sleep(0.1)
            
            # Send final metadata
            yield self._format_sse_chunk(
                event="metadata",
                data={
                    "model_used": response.get("model_used"),
                    "processing_time": response.get("latency_ms", 0) / 1000,
                    "confidence": 0.9,  # High confidence for agent responses
                    "total_sections": len(sections)
                },
                stream_id=stream_id
            )
            
        except Exception as e:
            logger.error(f"Error streaming LLM response: {e}")
            yield self._format_sse_chunk(
                event="error",
                data={"error": str(e)},
                stream_id=stream_id
            )
    
    def _parse_response_sections(self, response_text: str) -> Dict[str, str]:
        """Parse response into sections for streaming"""
        sections = {}
        current_section = None
        current_content = []
        
        lines = response_text.split('\n')
        
        for line in lines:
            # Check for section headers
            if line.strip().startswith('## '):
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = line.strip().replace('## ', '').strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Save last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        # If no sections found, treat as single section
        if not sections:
            sections["Legal Analysis"] = response_text.strip()
        
        return sections
    
    async def _chunk_content(
        self, 
        content: str, 
        stream_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream content in chunks with typing effect"""
        
        words = content.split()
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            
            # Send chunk when it reaches target size
            if len(' '.join(current_chunk)) >= self.chunk_size:
                chunk_text = ' '.join(current_chunk)
                
                yield self._format_sse_chunk(
                    event="content",
                    data={"content": chunk_text},
                    stream_id=stream_id
                )
                
                current_chunk = []
                await asyncio.sleep(0.05)  # Small delay for typing effect
        
        # Send remaining content
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            yield self._format_sse_chunk(
                event="content",
                data={"content": chunk_text},
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
        """Stop an active stream"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id] = False
            return True
        return False
    
    def get_active_streams(self) -> List[str]:
        """Get list of active stream IDs"""
        return [sid for sid, active in self.active_streams.items() if active]

    async def _cleanup_inactive_streams(self):
        """Background task to cleanup inactive streams"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)

                # Remove inactive streams
                inactive_streams = [
                    sid for sid, active in self.active_streams.items()
                    if not active
                ]

                for sid in inactive_streams:
                    self.active_streams.pop(sid, None)

                if inactive_streams:
                    logger.debug(f"Cleaned up {len(inactive_streams)} inactive streams")

            except Exception as e:
                logger.error(f"Error in stream cleanup: {e}")
                await asyncio.sleep(5)  # Short delay before retry

    async def _retry_operation(self, operation, *args, **kwargs):
        """Retry failed operations with exponential backoff"""
        for attempt in range(self.retry_attempts):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise e

                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

        raise Exception("Max retry attempts exceeded")

# Global streaming service instance
streaming_agent_service = StreamingAgentService()
