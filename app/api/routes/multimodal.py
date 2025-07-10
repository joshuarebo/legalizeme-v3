"""
Multi-Modal Document Processing API Routes
Production-ready endpoints for enhanced document processing capabilities
"""

import logging
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user
from app.services.advanced_multimodal import (
    MultiModalDocumentProcessor,
    DocumentRouter,
    MultiModalVectorIntegration
)

logger = logging.getLogger(__name__)

# Initialize services
document_processor = MultiModalDocumentProcessor()
document_router = DocumentRouter()
vector_integration = MultiModalVectorIntegration()

router = APIRouter()

# Pydantic models for request/response
class ProcessingOptions(BaseModel):
    """Processing configuration options"""
    generate_summary: bool = Field(default=True, description="Generate document summary")
    summary_model: str = Field(default="claude-sonnet-4", description="Model for summarization")
    extract_entities: bool = Field(default=True, description="Extract legal entities")
    include_confidence: bool = Field(default=True, description="Include confidence scores")
    chunk_for_vector: bool = Field(default=True, description="Create chunks for vector search")

class DocumentProcessingResponse(BaseModel):
    """Response model for document processing"""
    success: bool
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    extraction_method: Optional[str] = None
    word_count: Optional[int] = None
    char_count: Optional[int] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    summary: Optional[Dict[str, Any]] = None
    entities: Optional[Dict[str, List[str]]] = None
    recommendations: Optional[List[str]] = None
    error: Optional[str] = None

class VectorSearchRequest(BaseModel):
    """Request model for vector search"""
    query: str = Field(..., description="Search query")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of results")
    document_type: Optional[str] = Field(None, description="Filter by document type")
    extraction_method: Optional[str] = Field(None, description="Filter by extraction method")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence score")

class VectorSearchResponse(BaseModel):
    """Response model for vector search"""
    success: bool
    results: List[Dict[str, Any]]
    total_results: int
    query: str
    filters_applied: Dict[str, Any]
    error: Optional[str] = None

class CapabilitiesResponse(BaseModel):
    """Response model for capabilities"""
    multimodal_processing: bool
    supported_formats: List[str]
    ocr_available: bool
    vector_indexing: bool
    bedrock_integration: bool
    features: List[str]

@router.post("/process-document", response_model=DocumentProcessingResponse)
async def process_document(
    file: UploadFile = File(..., description="Document file to process"),
    options: str = Form(default="{}", description="Processing options as JSON string"),
    current_user: User = Depends(get_current_user)
):
    """
    Process a document using multi-modal capabilities
    
    Supports PDF, images (PNG, JPG, TIFF), and text files with:
    - Enhanced text extraction
    - OCR for images
    - Document type detection
    - AI-powered summarization
    - Entity extraction
    - Vector indexing
    """
    start_time = datetime.now()
    temp_file_path = None
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Check file size (100MB limit)
        file_content = await file.read()
        if len(file_content) > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum size is 100MB"
            )
        
        # Parse processing options
        try:
            import json
            processing_options = json.loads(options) if options != "{}" else {}
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid processing options JSON"
            )
        
        # Save file temporarily
        file_extension = Path(file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(file_content)
            temp_file_path = Path(temp_file.name)
        
        # Process document
        result = await document_router.process_document(temp_file_path, processing_options)
        
        if not result.get("success"):
            return DocumentProcessingResponse(
                success=False,
                error=result.get("error", "Processing failed")
            )
        
        # Index in vector database if requested
        vector_result = None
        if processing_options.get("chunk_for_vector", True):
            try:
                vector_result = await vector_integration.process_and_index_document(
                    temp_file_path, processing_options
                )
            except Exception as e:
                logger.warning(f"Vector indexing failed: {e}")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Format response
        summary_data = result.get("summary_data", {})
        
        return DocumentProcessingResponse(
            success=True,
            document_id=vector_result.get("indexing_result", {}).get("document_id") if vector_result else None,
            document_type=result.get("document_type"),
            extraction_method=result.get("extraction_method"),
            word_count=result.get("word_count"),
            char_count=result.get("char_count"),
            confidence=result.get("confidence"),
            processing_time=processing_time,
            summary=summary_data if summary_data.get("success") else None,
            entities=summary_data.get("extracted_entities") if summary_data else None,
            recommendations=result.get("processing_recommendations", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file_path and temp_file_path.exists():
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")

@router.post("/search", response_model=VectorSearchResponse)
async def search_documents(
    request: VectorSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Search processed documents using vector similarity
    
    Features:
    - Semantic search across processed documents
    - Filter by document type, extraction method, confidence
    - Enhanced metadata and relevance scoring
    """
    try:
        # Build filters
        filters = {}
        if request.document_type:
            filters["document_type"] = request.document_type
        if request.extraction_method:
            filters["extraction_method"] = request.extraction_method
        if request.confidence_threshold:
            filters["confidence_threshold"] = request.confidence_threshold
        
        # Perform search
        results = await vector_integration.search_multimodal_documents(
            query=request.query,
            filters=filters,
            limit=request.limit
        )
        
        return VectorSearchResponse(
            success=True,
            results=results,
            total_results=len(results),
            query=request.query,
            filters_applied=filters
        )
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """
    Get multi-modal processing capabilities and status
    
    Returns information about:
    - Supported file formats
    - Available features
    - Service status
    """
    try:
        # Initialize services if needed
        if not document_processor._initialized:
            await document_processor.initialize()
        if not document_router._initialized:
            await document_router.initialize()
        if not vector_integration._initialized:
            await vector_integration.initialize()
        
        # Get capabilities
        processor_caps = document_processor.get_capabilities()
        router_caps = document_router.get_router_capabilities()
        integration_caps = vector_integration.get_integration_capabilities()
        
        return CapabilitiesResponse(
            multimodal_processing=True,
            supported_formats=router_caps.get("supported_formats", []),
            ocr_available=processor_caps.get("enhanced_ocr", False),
            vector_indexing=integration_caps.get("vector_indexing", False),
            bedrock_integration=processor_caps.get("bedrock_integration", False),
            features=integration_caps.get("features", [])
        )
        
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get capabilities: {str(e)}"
        )

@router.get("/stats")
async def get_collection_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about the multi-modal document collection
    
    Returns:
    - Total documents processed
    - Document type distribution
    - Extraction method statistics
    - Collection health metrics
    """
    try:
        stats = await vector_integration.get_collection_stats()
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection stats: {str(e)}"
        )

@router.delete("/document/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a document and its chunks from the multi-modal collection
    """
    try:
        success = await vector_integration.delete_document(document_id)
        
        if success:
            return {"success": True, "message": f"Document {document_id} deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    Health check for multi-modal processing services
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "document_processor": document_processor._initialized,
                "document_router": document_router._initialized,
                "vector_integration": vector_integration._initialized
            }
        }
        
        return JSONResponse(content=health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
