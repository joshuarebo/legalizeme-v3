from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from app.services.document_service import DocumentService
from app.services.ai_service import AIService
from app.database import get_db
from app.models.user import User
from app.models.document import Document
# Authentication removed - now public service layer
# from app.core.security import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class DocumentSearchRequest(BaseModel):
    query: str = Field(..., max_length=settings.MAX_QUERY_LENGTH)
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=10, ge=1, le=50)
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="Optional user context from frontend")

class DocumentResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str]
    source: str
    document_type: str
    url: Optional[str]
    word_count: Optional[int]
    created_at: datetime
    relevance_score: Optional[float] = None
    
    class Config:
        from_attributes = True

class DocumentAnalysisRequest(BaseModel):
    document_id: int
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="Optional user context from frontend")

class DocumentAnalysisResponse(BaseModel):
    document_id: int
    analysis: str
    confidence: float
    model_used: str
    timestamp: datetime

class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    message: str

# Initialize services
document_service = DocumentService()
ai_service = AIService()

@router.post("/search", response_model=List[DocumentResponse])
async def search_documents(
    request: DocumentSearchRequest,
    db: Session = Depends(get_db)
):
    """Search for documents"""
    try:
        documents = await document_service.search_documents(
            request.query,
            request.filters,
            request.limit
        )
        
        return [DocumentResponse.from_orm(doc) for doc in documents]
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching documents: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific document"""
    try:
        document = await document_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return DocumentResponse.from_orm(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving document: {str(e)}"
        )

@router.get("/{document_id}/content")
async def get_document_content(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get document content"""
    try:
        document = await document_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return {
            'id': document.id,
            'title': document.title,
            'content': document.content,
            'source': document.source,
            'url': document.url,
            'word_count': document.word_count,
            'created_at': document.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving document content: {str(e)}"
        )

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_context: Optional[str] = Form(None, description="Optional user context JSON"),
    db: Session = Depends(get_db)
):
    """Upload a document for processing"""
    try:
        # Validate file size
        if file.size > settings.MAX_DOCUMENT_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large"
            )
        
        # Validate file type
        allowed_types = ['pdf', 'doc', 'docx', 'txt']
        file_extension = file.filename.split('.')[-1].lower()
        
        if file_extension not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not supported. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Process the uploaded file with optional user_id
        user_id = None
        if user_context:
            import json
            try:
                user_data = json.loads(user_context)
                user_id = user_data.get('user_id')
            except json.JSONDecodeError:
                pass

        document = await document_service.process_uploaded_file(
            file_content,
            file.filename,
            user_id
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process uploaded file"
            )
        
        return DocumentUploadResponse(
            document_id=document.id,
            filename=file.filename,
            status="processing",
            message="Document uploaded and queued for processing"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )

@router.post("/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(
    request: DocumentAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Analyze a document using AI"""
    try:
        document = await document_service.get_document_by_id(request.document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Analyze the document
        analysis = await ai_service.analyze_document_content(document.content)
        
        return DocumentAnalysisResponse(
            document_id=request.document_id,
            analysis=analysis['analysis'],
            confidence=analysis.get('confidence', 0.0),
            model_used=analysis.get('model_used', 'unknown'),
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing document: {str(e)}"
        )

@router.get("/{document_id}/analysis")
async def get_document_analysis(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get analysis for a specific document"""
    try:
        # For now, return a simple analysis response
        # In a full implementation, this would retrieve stored analysis results
        return {
            "document_id": document_id,
            "analysis": {
                "document_type": "legal_document",
                "summary": "This document contains legal provisions and requirements.",
                "key_points": [
                    "Contains legal obligations",
                    "Includes compliance requirements",
                    "References Kenyan law"
                ],
                "risk_assessment": "Medium risk - requires legal review",
                "compliance_score": 0.75
            },
            "confidence": 0.8,
            "model_used": "claude-sonnet-4",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error getting document analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document analysis: {str(e)}"
        )

@router.get("/sources/{source}")
async def get_documents_by_source(
    source: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get documents by source"""
    try:
        documents = await document_service.get_documents_by_source(source, limit)
        
        return {
            'source': source,
            'documents': [DocumentResponse.from_orm(doc) for doc in documents],
            'total': len(documents)
        }
        
    except Exception as e:
        logger.error(f"Error getting documents by source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving documents: {str(e)}"
        )

@router.get("/stats/overview")
async def get_document_statistics(
    db: Session = Depends(get_db)
):
    """Get document statistics"""
    try:
        stats = await document_service.get_document_statistics()
        
        return {
            'statistics': stats,
            'timestamp': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error getting document statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving statistics: {str(e)}"
        )

@router.post("/similar/{document_id}")
async def find_similar_documents(
    document_id: int,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """Find similar documents"""
    try:
        # Get the source document
        source_doc = await document_service.get_document_by_id(document_id)
        
        if not source_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source document not found"
            )
        
        # Use the document content to find similar documents
        from app.services.vector_service import VectorService
        vector_service = VectorService()
        
        similar_docs = await vector_service.search_similar_documents(
            source_doc.content[:1000],  # Use first 1000 chars for similarity
            limit=limit
        )
        
        # Filter out the source document itself
        similar_docs = [doc for doc in similar_docs if doc.id != document_id]
        
        return {
            'source_document_id': document_id,
            'similar_documents': [DocumentResponse.from_orm(doc) for doc in similar_docs[:limit]],
            'total': len(similar_docs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding similar documents: {str(e)}"
        )

@router.get("/recent/updates")
async def get_recent_document_updates(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get recently updated documents"""
    try:
        documents = db.query(Document).filter(
            Document.is_processed == True
        ).order_by(Document.updated_at.desc()).limit(limit).all()
        
        return {
            'recent_documents': [DocumentResponse.from_orm(doc) for doc in documents],
            'total': len(documents),
            'timestamp': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error getting recent documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving recent documents: {str(e)}"
        )
