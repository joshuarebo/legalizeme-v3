"""
Document Analysis API for CounselDocs
Handles document upload, analysis, and results retrieval.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.counseldocs.models.document_analysis import DocumentAnalysis
from app.counseldocs.services.document_processor import document_processor
from app.counseldocs.services.compliance_analyzer import compliance_analyzer
from app.counseldocs.services.document_archive_service import document_archive_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/counseldocs/analysis", tags=["CounselDocs Analysis"])

class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    status: str
    progress: Optional[str] = None
    error_message: Optional[str] = None

class ReanalysisRequest(BaseModel):
    analysis_id: str
    user_id: str

@router.post("/upload")
async def upload_document_for_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    document_type: Optional[str] = Form(None)
):
    """
    Upload document for Kenya Law compliance analysis.
    
    - **file**: Document file (PDF, DOCX, PNG, JPG, etc.)
    - **user_id**: Azure user identifier
    - **document_type**: Optional document type hint
    """
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file provided"
            )
        
        # Create analysis record
        analysis_id = str(uuid.uuid4())
        
        with next(get_db()) as db:
            analysis = DocumentAnalysis(
                uuid=analysis_id,
                user_id=user_id,
                original_filename=file.filename,
                file_type=file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown',
                file_size_bytes=len(file_content),
                status="pending"
            )
            
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
        
        # Update user stats
        await document_archive_service.update_analysis_stats(user_id, "started", len(file_content))
        
        # Start background processing
        background_tasks.add_task(
            process_document_analysis,
            analysis_id,
            file_content,
            file.filename,
            file.content_type or 'application/octet-stream',
            user_id,
            document_type
        )
        
        return {
            "success": True,
            "analysis_id": analysis_id,
            "status": "pending",
            "message": "Document uploaded successfully. Analysis in progress.",
            "estimated_time_minutes": 2
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/status/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    """
    Get analysis status and progress.
    
    - **analysis_id**: Analysis UUID
    """
    
    try:
        with next(get_db()) as db:
            analysis = db.query(DocumentAnalysis).filter(
                DocumentAnalysis.uuid == analysis_id
            ).first()
            
            if not analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Analysis not found"
                )
            
            response_data = {
                "analysis_id": analysis_id,
                "status": analysis.status,
                "progress": _get_progress_message(analysis.status),
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                "processing_time_seconds": analysis.processing_time_seconds
            }
            
            if analysis.error_message:
                response_data["error_message"] = analysis.error_message
            
            return response_data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status retrieval failed: {str(e)}"
        )

@router.get("/result/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """
    Get complete analysis results.
    
    - **analysis_id**: Analysis UUID
    """
    
    try:
        with next(get_db()) as db:
            analysis = db.query(DocumentAnalysis).filter(
                DocumentAnalysis.uuid == analysis_id
            ).first()
            
            if not analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Analysis not found"
                )
            
            if analysis.status != "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Analysis not completed. Current status: {analysis.status}"
                )
            
            return {
                "analysis_id": analysis_id,
                "document_info": {
                    "original_filename": analysis.original_filename,
                    "file_type": analysis.file_type,
                    "file_size_bytes": analysis.file_size_bytes,
                    "document_type_detected": analysis.document_type_detected
                },
                "compliance_results": {
                    "compliance_score": analysis.compliance_score,
                    "confidence_score": analysis.confidence_score,
                    "key_areas": analysis.key_areas,
                    "recommendations": analysis.recommendations,
                    "citations": analysis.citations
                },
                "analysis_metadata": {
                    "model_used": analysis.model_used,
                    "processing_time_seconds": analysis.processing_time_seconds,
                    "analyzed_at": analysis.completed_at.isoformat() if analysis.completed_at else None
                },
                "content_summary": analysis.content_summary
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Result retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Result retrieval failed: {str(e)}"
        )

@router.post("/reanalyze")
async def reanalyze_document(
    background_tasks: BackgroundTasks,
    request: ReanalysisRequest
):
    """
    Reanalyze an existing document.
    
    - **analysis_id**: Original analysis UUID
    - **user_id**: User identifier
    """
    
    try:
        with next(get_db()) as db:
            # Get original analysis
            original_analysis = db.query(DocumentAnalysis).filter(
                DocumentAnalysis.uuid == request.analysis_id,
                DocumentAnalysis.user_id == request.user_id
            ).first()
            
            if not original_analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Original analysis not found"
                )
            
            # Create new analysis record
            new_analysis_id = str(uuid.uuid4())
            
            new_analysis = DocumentAnalysis(
                uuid=new_analysis_id,
                user_id=request.user_id,
                original_filename=original_analysis.original_filename,
                file_type=original_analysis.file_type,
                file_size_bytes=original_analysis.file_size_bytes,
                s3_file_path=original_analysis.s3_file_path,
                status="pending",
                is_reanalysis=True,
                original_analysis_id=original_analysis.id
            )
            
            db.add(new_analysis)
            db.commit()
            db.refresh(new_analysis)
        
        # Get file from S3
        file_content = await document_processor.get_document_from_s3(original_analysis.s3_file_path)
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original document file not found"
            )
        
        # Start reanalysis
        background_tasks.add_task(
            process_document_analysis,
            new_analysis_id,
            file_content,
            original_analysis.original_filename,
            'application/octet-stream',  # Content type not critical for reanalysis
            request.user_id,
            original_analysis.document_type_detected
        )
        
        return {
            "success": True,
            "new_analysis_id": new_analysis_id,
            "original_analysis_id": request.analysis_id,
            "status": "pending",
            "message": "Document reanalysis started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reanalysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reanalysis failed: {str(e)}"
        )

async def process_document_analysis(
    analysis_id: str,
    file_content: bytes,
    filename: str,
    content_type: str,
    user_id: str,
    document_type: Optional[str] = None
):
    """Background task to process document analysis"""
    
    try:
        with next(get_db()) as db:
            analysis = db.query(DocumentAnalysis).filter(
                DocumentAnalysis.uuid == analysis_id
            ).first()
            
            if not analysis:
                logger.error(f"Analysis record not found: {analysis_id}")
                return
            
            # Update status to processing
            analysis.status = "processing"
            db.commit()
            
            # Process document
            processing_result = await document_processor.process_document(
                file_content, filename, content_type, user_id
            )
            
            if not processing_result['success']:
                analysis.status = "failed"
                analysis.error_message = processing_result['error']
                db.commit()
                await document_archive_service.update_analysis_stats(user_id, "failed")
                return
            
            # Extract content
            extracted_content = processing_result['extraction_result']['extracted_text']
            
            # Perform compliance analysis
            compliance_result = await compliance_analyzer.analyze_document_compliance(
                extracted_content, document_type, user_id
            )
            
            if not compliance_result['success']:
                analysis.status = "failed"
                analysis.error_message = compliance_result['error']
                db.commit()
                await document_archive_service.update_analysis_stats(user_id, "failed")
                return
            
            # Update analysis record with results
            analysis.status = "completed"
            analysis.completed_at = datetime.utcnow()
            analysis.extracted_content = extracted_content
            analysis.document_type_detected = compliance_result['document_type_detected']
            analysis.compliance_score = compliance_result['compliance_score']
            analysis.confidence_score = compliance_result['confidence_score']
            analysis.key_areas = compliance_result['key_areas']
            analysis.recommendations = compliance_result['recommendations']
            analysis.citations = compliance_result['citations']
            analysis.analysis_results = compliance_result
            analysis.processing_time_seconds = compliance_result['processing_time_seconds']
            analysis.model_used = "titan-text-premier"
            analysis.s3_file_path = processing_result['file_info']['s3_file_path']
            
            # Generate content summary
            analysis.content_summary = extracted_content[:500] + "..." if len(extracted_content) > 500 else extracted_content
            
            db.commit()
            
            # Update user stats
            await document_archive_service.update_analysis_stats(user_id, "completed")
            
            logger.info(f"Analysis completed successfully: {analysis_id}")
            
    except Exception as e:
        logger.error(f"Document analysis processing failed: {str(e)}")
        
        try:
            with next(get_db()) as db:
                analysis = db.query(DocumentAnalysis).filter(
                    DocumentAnalysis.uuid == analysis_id
                ).first()
                
                if analysis:
                    analysis.status = "failed"
                    analysis.error_message = str(e)
                    db.commit()
                    
                    await document_archive_service.update_analysis_stats(user_id, "failed")
        except Exception as update_error:
            logger.error(f"Failed to update analysis status: {update_error}")

def _get_progress_message(status: str) -> str:
    """Get user-friendly progress message"""
    
    status_messages = {
        "pending": "Document uploaded, waiting to start analysis",
        "processing": "Analyzing document for Kenya Law compliance",
        "completed": "Analysis completed successfully",
        "failed": "Analysis failed - please try again"
    }
    
    return status_messages.get(status, "Unknown status")
