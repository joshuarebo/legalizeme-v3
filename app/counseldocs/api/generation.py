"""
Document Generation API for CounselDocs
Handles court document generation from Kenya Law templates.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.counseldocs.models.document_generation import DocumentGeneration
from app.counseldocs.services.template_generator import template_generator
from app.counseldocs.services.document_archive_service import document_archive_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/counseldocs/generation", tags=["CounselDocs Generation"])

class GenerationRequest(BaseModel):
    template_id: str = Field(..., description="Template identifier")
    user_id: str = Field(..., description="Azure user identifier")
    template_data: Dict[str, Any] = Field(..., description="Template field data")
    generation_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Generation options")
    user_plan: Optional[str] = Field(default="free", description="User subscription plan (free, premium, pro, enterprise)")

class RegenerationRequest(BaseModel):
    generation_id: str = Field(..., description="Original generation UUID")
    user_id: str = Field(..., description="User identifier")
    template_data: Optional[Dict[str, Any]] = Field(None, description="Updated template data")

@router.get("/templates")
async def get_available_templates():
    """
    Get list of available court document templates.
    
    Returns templates from Kenya Law Civil Procedure Rules 2010 Appendix.
    """
    
    try:
        templates = await template_generator.get_available_templates()
        
        return {
            "success": True,
            "templates": templates,
            "total_templates": len(templates),
            "categories": list(set(t["category"] for t in templates)),
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Template retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Template retrieval failed: {str(e)}"
        )

@router.post("/generate")
async def generate_document(
    background_tasks: BackgroundTasks,
    request: GenerationRequest
):
    """
    Generate court document from template.
    
    - **template_id**: Template identifier (e.g., "civil_plaint")
    - **user_id**: Azure user identifier
    - **template_data**: Field data for template
    - **generation_options**: Output format, filename, etc.
    """
    
    try:
        # Extract generation options
        options = request.generation_options or {}
        output_format = options.get("output_format", "pdf")
        custom_filename = options.get("custom_filename")
        
        # Validate output format
        if output_format not in ["pdf", "html"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid output format. Supported: pdf, html"
            )
        
        # Create generation record
        generation_id = str(uuid.uuid4())
        
        with next(get_db()) as db:
            generation = DocumentGeneration(
                uuid=generation_id,
                user_id=request.user_id,
                template_id=request.template_id,
                template_name="",  # Will be updated after generation
                template_data=request.template_data,
                file_format=output_format,
                custom_filename=custom_filename,
                status="pending"
            )
            
            db.add(generation)
            db.commit()
            db.refresh(generation)
        
        # Update user stats
        await document_archive_service.update_generation_stats(request.user_id, "started")
        
        # Start background generation
        background_tasks.add_task(
            process_document_generation,
            generation_id,
            request.template_id,
            request.template_data,
            request.user_id,
            output_format,
            custom_filename,
            request.user_plan
        )
        
        return {
            "success": True,
            "generation_id": generation_id,
            "status": "pending",
            "message": "Document generation started",
            "estimated_time_minutes": 1,
            "download_url": f"/api/v1/counseldocs/generation/download/{generation_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document generation request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation request failed: {str(e)}"
        )

@router.get("/status/{generation_id}")
async def get_generation_status(generation_id: str):
    """
    Get document generation status.
    
    - **generation_id**: Generation UUID
    """
    
    try:
        with next(get_db()) as db:
            generation = db.query(DocumentGeneration).filter(
                DocumentGeneration.uuid == generation_id
            ).first()
            
            if not generation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Generation not found"
                )
            
            return {
                "generation_id": generation_id,
                "status": generation.status,
                "template_id": generation.template_id,
                "template_name": generation.template_name,
                "file_format": generation.file_format,
                "custom_filename": generation.custom_filename,
                "created_at": generation.created_at.isoformat() if generation.created_at else None,
                "completed_at": generation.completed_at.isoformat() if generation.completed_at else None,
                "generation_time_seconds": generation.generation_time_seconds,
                "download_count": generation.download_count,
                "error_message": generation.error_message
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status retrieval failed: {str(e)}"
        )

@router.get("/download/{generation_id}")
async def download_generated_document(generation_id: str):
    """
    Download generated document.
    
    - **generation_id**: Generation UUID
    """
    
    try:
        with next(get_db()) as db:
            generation = db.query(DocumentGeneration).filter(
                DocumentGeneration.uuid == generation_id
            ).first()
            
            if not generation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Generated document not found"
                )
            
            if generation.status != "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Document not ready. Current status: {generation.status}"
                )
            
            # Get file from S3
            file_content = await template_generator.get_document_from_s3(generation.s3_file_path)
            
            if not file_content:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document file not found"
                )
            
            # Update download count
            generation.increment_download_count()
            db.commit()
            
            # Update user stats
            await document_archive_service.update_generation_stats(
                generation.user_id, None, 0, download=True
            )
            
            # Determine content type and filename
            content_types = {
                'pdf': 'application/pdf',
                'html': 'text/html'
            }
            
            content_type = content_types.get(generation.file_format, 'application/octet-stream')
            filename = generation.get_download_info()["filename"]
            
            # Return file as streaming response
            return StreamingResponse(
                iter([file_content]),
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Content-Length": str(len(file_content))
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document download failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}"
        )

@router.post("/regenerate")
async def regenerate_document(
    background_tasks: BackgroundTasks,
    request: RegenerationRequest
):
    """
    Regenerate document with updated data.
    
    - **generation_id**: Original generation UUID
    - **user_id**: User identifier
    - **template_data**: Updated template data (optional)
    """
    
    try:
        with next(get_db()) as db:
            # Get original generation
            original_generation = db.query(DocumentGeneration).filter(
                DocumentGeneration.uuid == request.generation_id,
                DocumentGeneration.user_id == request.user_id
            ).first()
            
            if not original_generation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Original generation not found"
                )
            
            # Create new generation record
            new_generation_id = str(uuid.uuid4())
            
            # Use updated data or original data
            template_data = request.template_data or original_generation.template_data
            
            new_generation = DocumentGeneration(
                uuid=new_generation_id,
                user_id=request.user_id,
                template_id=original_generation.template_id,
                template_name=original_generation.template_name,
                template_data=template_data,
                file_format=original_generation.file_format,
                custom_filename=original_generation.custom_filename,
                status="pending",
                is_regeneration=True,
                original_generation_id=original_generation.id
            )
            
            db.add(new_generation)
            db.commit()
            db.refresh(new_generation)
        
        # Start regeneration
        background_tasks.add_task(
            process_document_generation,
            new_generation_id,
            original_generation.template_id,
            template_data,
            request.user_id,
            original_generation.file_format,
            original_generation.custom_filename
        )
        
        return {
            "success": True,
            "new_generation_id": new_generation_id,
            "original_generation_id": request.generation_id,
            "status": "pending",
            "message": "Document regeneration started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Regeneration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regeneration failed: {str(e)}"
        )

async def process_document_generation(
    generation_id: str,
    template_id: str,
    template_data: Dict[str, Any],
    user_id: str,
    output_format: str,
    custom_filename: Optional[str] = None,
    user_plan: str = "free"
):
    """Background task to process document generation"""
    
    try:
        with next(get_db()) as db:
            generation = db.query(DocumentGeneration).filter(
                DocumentGeneration.uuid == generation_id
            ).first()
            
            if not generation:
                logger.error(f"Generation record not found: {generation_id}")
                return
            
            # Update status to generating
            generation.status = "generating"
            db.commit()
            
            # Generate document
            start_time = datetime.utcnow()
            
            result = await template_generator.generate_document(
                template_id, template_data, user_id, output_format, custom_filename, user_plan
            )
            
            if not result['success']:
                generation.status = "failed"
                generation.error_message = result['error']
                db.commit()
                await document_archive_service.update_generation_stats(user_id, "failed")
                return
            
            # Update generation record with results
            generation.status = "completed"
            generation.completed_at = datetime.utcnow()
            generation.template_name = result['template_name']
            generation.generated_content = "Generated successfully"  # Placeholder
            generation.s3_file_path = result['s3_path']
            generation.file_size_bytes = result['file_size_bytes']
            generation.generation_time_seconds = result['processing_time_seconds']
            
            db.commit()
            
            # Update user stats
            await document_archive_service.update_generation_stats(
                user_id, "completed", result['file_size_bytes']
            )
            
            logger.info(f"Document generation completed successfully: {generation_id}")
            
    except Exception as e:
        logger.error(f"Document generation processing failed: {str(e)}")
        
        try:
            with next(get_db()) as db:
                generation = db.query(DocumentGeneration).filter(
                    DocumentGeneration.uuid == generation_id
                ).first()
                
                if generation:
                    generation.status = "failed"
                    generation.error_message = str(e)
                    db.commit()
                    
                    await document_archive_service.update_generation_stats(user_id, "failed")
        except Exception as update_error:
            logger.error(f"Failed to update generation status: {update_error}")
