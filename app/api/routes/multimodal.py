"""
Multimodal API Routes
Provides endpoints for multi-modal document processing and search
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any, Union
import logging
from datetime import datetime
import json
import tempfile
import os
from pathlib import Path

# Core services
from app.services.vector_service import VectorService
from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user
from app.config import settings

# Advanced services (with fallback)
try:
    from app.services.advanced.document_processor import DocumentProcessor
    HAS_DOCUMENT_PROCESSOR = True
except ImportError:
    HAS_DOCUMENT_PROCESSOR = False

try:
    from app.services.advanced.legal_rag import LegalRAGService
    HAS_LEGAL_RAG = True
except ImportError:
    HAS_LEGAL_RAG = False

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class MultimodalSearchRequest(BaseModel):
    """Request model for multimodal search"""
    query: str = Field(..., max_length=settings.MAX_QUERY_LENGTH, description="Search query")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of results")
    document_type: Optional[str] = Field(default=None, description="Filter by document type")
    confidence_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum confidence threshold")

class DocumentProcessingOptions(BaseModel):
    """Options for document processing"""
    generate_summary: bool = Field(default=True, description="Generate AI summary")
    summary_model: str = Field(default="claude-sonnet-4", description="Model for summarization")
    extract_entities: bool = Field(default=True, description="Extract legal entities")
    analyze_structure: bool = Field(default=True, description="Analyze document structure")

class ProcessedDocumentResponse(BaseModel):
    """Response model for processed documents"""
    success: bool
    filename: str
    document_type: str
    file_size: int
    processing_time_ms: float
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    entities: Optional[List[Dict[str, Any]]] = None
    structure_analysis: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class SearchResultResponse(BaseModel):
    """Response model for search results"""
    title: str
    content: str
    source: str
    document_type: str
    relevance_score: float
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MultimodalSearchResponse(BaseModel):
    """Response model for multimodal search"""
    query: str
    results: List[SearchResultResponse]
    total_results: int
    processing_time_ms: float
    search_strategy: str
    timestamp: datetime

class CapabilitiesResponse(BaseModel):
    """Response model for capabilities"""
    supported_formats: List[str]
    processor_capabilities: Dict[str, bool]
    features: List[str]
    vector_integration: bool
    ai_summarization: bool

# Initialize services
vector_service = VectorService()

if HAS_DOCUMENT_PROCESSOR:
    document_processor = DocumentProcessor()
else:
    document_processor = None

if HAS_LEGAL_RAG:
    legal_rag_service = LegalRAGService()
else:
    legal_rag_service = None

@router.post("/process-document", response_model=ProcessedDocumentResponse)
async def process_document(
    file: UploadFile = File(...),
    options: str = Form(default='{"generate_summary": true, "summary_model": "claude-sonnet-4"}'),
    current_user: User = Depends(get_current_user)
):
    """
    Process a multi-modal document (PDF, DOCX, images, text)
    
    Supports:
    - PDF text extraction and OCR
    - DOCX document processing
    - Image OCR processing
    - AI-powered summarization
    - Entity extraction
    - Document structure analysis
    """
    start_time = datetime.utcnow()
    
    try:
        # Parse options
        try:
            processing_options = DocumentProcessingOptions(**json.loads(options))
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid options format: {str(e)}"
            )
        
        # Check if document processor is available
        if not HAS_DOCUMENT_PROCESSOR or not document_processor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Document processing service is not available"
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        # Check file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 50MB limit"
            )
        
        # Save file temporarily
        file_extension = Path(file.filename).suffix.lower()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Initialize processor if needed
            if not document_processor._initialized:
                await document_processor.initialize()
            
            # Process based on file type
            if file_extension == '.pdf':
                result = await document_processor.analyze_pdf(temp_file_path)
            elif file_extension in ['.docx', '.doc']:
                result = await document_processor.analyze_docx(temp_file_path)
            elif file_extension in ['.txt', '.text']:
                result = await document_processor.analyze_text(temp_file_path)
            elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                result = await document_processor.analyze_image(temp_file_path)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file format: {file_extension}"
                )
            
            if not result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Document processing failed: {result.get('error', 'Unknown error')}"
                )
            
            # Extract text
            extracted_text = result.get("text", "")
            
            # Generate summary if requested
            summary = None
            if processing_options.generate_summary and extracted_text:
                summary_result = await document_processor.summarize_text(
                    extracted_text,
                    max_length=500,
                    model=processing_options.summary_model
                )
                if summary_result.get("success"):
                    summary = summary_result.get("summary")
            
            # Extract entities if requested
            entities = None
            if processing_options.extract_entities and extracted_text:
                # Simple entity extraction (can be enhanced)
                entities = []
            
            # Analyze structure if requested
            structure_analysis = None
            if processing_options.analyze_structure and extracted_text:
                structure_result = await document_processor.analyze_document_structure(extracted_text)
                structure_analysis = structure_result
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ProcessedDocumentResponse(
                success=True,
                filename=file.filename,
                document_type=result.get("document_type", "unknown"),
                file_size=file_size,
                processing_time_ms=processing_time,
                extracted_text=extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
                summary=summary,
                entities=entities,
                structure_analysis=structure_analysis,
                metadata=result.get("metadata", {})
            )
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ProcessedDocumentResponse(
            success=False,
            filename=file.filename if file.filename else "unknown",
            document_type="unknown",
            file_size=file_size,
            processing_time_ms=processing_time,
            error=str(e)
        )

@router.post("/search", response_model=MultimodalSearchResponse)
async def search_documents(
    request: MultimodalSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Search processed documents using multimodal capabilities

    Supports:
    - Semantic search across processed documents
    - Document type filtering
    - Confidence-based filtering
    - Hybrid search strategies
    """
    start_time = datetime.utcnow()

    try:
        # Use Legal RAG service if available, otherwise fall back to vector service
        if HAS_LEGAL_RAG and legal_rag_service:
            # Initialize if needed
            if not legal_rag_service._initialized:
                await legal_rag_service.initialize()

            # Use enhanced RAG search
            rag_response = await legal_rag_service.query_with_sources(
                query=request.query,
                max_sources=request.limit,
                strategy="hybrid"
            )

            # Convert to search results
            results = []
            for source in rag_response.sources:
                if source.relevance_score >= request.confidence_threshold:
                    # Filter by document type if specified
                    if request.document_type and source.document_type != request.document_type:
                        continue

                    results.append(SearchResultResponse(
                        title=source.title,
                        content=source.excerpt,
                        source=source.source,
                        document_type=source.document_type,
                        relevance_score=source.relevance_score,
                        url=source.url,
                        metadata=source.metadata
                    ))

            search_strategy = rag_response.retrieval_strategy

        else:
            # Fall back to basic vector search
            if not vector_service._initialized:
                await vector_service.initialize()

            # Search documents
            search_results = await vector_service.search_similar_documents(
                request.query,
                limit=request.limit
            )

            # Convert to response format
            results = []
            for doc in search_results:
                relevance_score = doc.get('relevance_score', 0.0)

                if relevance_score >= request.confidence_threshold:
                    # Filter by document type if specified
                    doc_type = doc.get('document_type', 'unknown')
                    if request.document_type and doc_type != request.document_type:
                        continue

                    results.append(SearchResultResponse(
                        title=doc.get('title', 'Unknown'),
                        content=doc.get('content', '')[:500] + "..." if len(doc.get('content', '')) > 500 else doc.get('content', ''),
                        source=doc.get('source', 'unknown'),
                        document_type=doc_type,
                        relevance_score=relevance_score,
                        url=doc.get('url'),
                        metadata=doc.get('metadata', {})
                    ))

            search_strategy = "vector_similarity"

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return MultimodalSearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            processing_time_ms=processing_time,
            search_strategy=search_strategy,
            timestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Error in multimodal search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(
    current_user: User = Depends(get_current_user)
):
    """Get multimodal processing capabilities"""
    try:
        # Get processor capabilities if available
        if HAS_DOCUMENT_PROCESSOR and document_processor:
            processor_caps = document_processor.get_capabilities()
            supported_formats = list(document_processor.supported_formats.values())
        else:
            processor_caps = {
                "pdf_extraction": False,
                "docx_extraction": False,
                "ocr_processing": False,
                "ai_summarization": False,
                "bedrock_integration": False,
                "structure_analysis": False,
                "embedding_generation": False
            }
            supported_formats = []

        features = []
        if processor_caps.get("pdf_extraction"):
            features.append("PDF text extraction")
        if processor_caps.get("docx_extraction"):
            features.append("DOCX document processing")
        if processor_caps.get("ocr_processing"):
            features.append("Image OCR processing")
        if processor_caps.get("ai_summarization"):
            features.append("AI-powered summarization")
        if processor_caps.get("structure_analysis"):
            features.append("Document structure analysis")
        if HAS_LEGAL_RAG:
            features.append("Enhanced semantic search")

        return CapabilitiesResponse(
            supported_formats=supported_formats,
            processor_capabilities=processor_caps,
            features=features,
            vector_integration=True,
            ai_summarization=processor_caps.get("ai_summarization", False)
        )

    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get capabilities: {str(e)}"
        )

@router.get("/health")
async def multimodal_health_check(
    current_user: User = Depends(get_current_user)
):
    """Health check for multimodal services"""
    try:
        health_status = {
            "status": "healthy",
            "services": {},
            "timestamp": datetime.utcnow().isoformat()
        }

        # Check document processor
        if HAS_DOCUMENT_PROCESSOR and document_processor:
            try:
                if not document_processor._initialized:
                    await document_processor.initialize()
                health_status["services"]["document_processor"] = {
                    "status": "healthy",
                    "capabilities": document_processor.get_capabilities()
                }
            except Exception as e:
                health_status["services"]["document_processor"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_status["services"]["document_processor"] = {
                "status": "not_available"
            }

        # Check vector service
        try:
            if not vector_service._initialized:
                await vector_service.initialize()
            health_status["services"]["vector_service"] = {"status": "healthy"}
        except Exception as e:
            health_status["services"]["vector_service"] = {
                "status": "error",
                "error": str(e)
            }

        # Check legal RAG service
        if HAS_LEGAL_RAG and legal_rag_service:
            try:
                rag_metrics = legal_rag_service.get_metrics()
                health_status["services"]["legal_rag"] = {
                    "status": "healthy" if rag_metrics["initialized"] else "not_initialized",
                    "metrics": rag_metrics
                }
            except Exception as e:
                health_status["services"]["legal_rag"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_status["services"]["legal_rag"] = {"status": "not_available"}

        return health_status

    except Exception as e:
        logger.error(f"Error in multimodal health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
