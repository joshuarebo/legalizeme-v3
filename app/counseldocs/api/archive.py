"""
Document Archive API for CounselDocs
Handles document archive, analytics, and dashboard functionality.
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.counseldocs.services.document_archive_service import document_archive_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/counseldocs/archive", tags=["CounselDocs Archive"])

class DeleteDocumentRequest(BaseModel):
    user_id: str
    document_id: str
    document_type: str  # 'analysis' or 'generation'

@router.get("/dashboard")
async def get_dashboard_data(user_id: str = Query(..., description="Azure user identifier")):
    """
    Get comprehensive dashboard data for user.
    
    - **user_id**: Azure user identifier
    
    Returns analytics, recent documents, and archive summary.
    """
    
    try:
        dashboard_data = await document_archive_service.get_dashboard_data(user_id)
        
        return {
            "success": True,
            "dashboard_data": dashboard_data,
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Dashboard data retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard retrieval failed: {str(e)}"
        )

@router.get("/documents")
async def get_user_documents(
    user_id: str = Query(..., description="Azure user identifier"),
    document_type: Optional[str] = Query(None, description="Filter by type: analysis, generation"),
    status: Optional[str] = Query(None, description="Filter by status: pending, completed, failed"),
    limit: int = Query(50, ge=1, le=100, description="Number of documents to return"),
    offset: int = Query(0, ge=0, description="Number of documents to skip")
):
    """
    Get user's documents with filtering and pagination.
    
    - **user_id**: Azure user identifier
    - **document_type**: Filter by document type (optional)
    - **status**: Filter by status (optional)
    - **limit**: Number of documents to return (1-100)
    - **offset**: Number of documents to skip for pagination
    """
    
    try:
        documents_data = await document_archive_service.get_user_documents(
            user_id, document_type, status, limit, offset
        )
        
        return {
            "success": True,
            "documents": documents_data,
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Documents retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Documents retrieval failed: {str(e)}"
        )

@router.get("/analytics")
async def get_detailed_analytics(user_id: str = Query(..., description="Azure user identifier")):
    """
    Get detailed analytics for user.
    
    - **user_id**: Azure user identifier
    
    Returns comprehensive analytics including trends, usage patterns, and statistics.
    """
    
    try:
        # Get dashboard data which includes analytics
        dashboard_data = await document_archive_service.get_dashboard_data(user_id)
        analytics = dashboard_data.get('analytics', {})
        
        # Add additional analytics calculations
        enhanced_analytics = {
            **analytics,
            "usage_trends": await _calculate_usage_trends(user_id),
            "compliance_trends": await _calculate_compliance_trends(user_id),
            "document_type_insights": await _calculate_document_insights(user_id),
            "efficiency_metrics": await _calculate_efficiency_metrics(user_id)
        }
        
        return {
            "success": True,
            "analytics": enhanced_analytics,
            "calculated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analytics retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics retrieval failed: {str(e)}"
        )

@router.delete("/document")
async def delete_document(request: DeleteDocumentRequest):
    """
    Delete (archive) a document.
    
    - **user_id**: User identifier
    - **document_id**: Document UUID
    - **document_type**: Type of document ('analysis' or 'generation')
    """
    
    try:
        success = await document_archive_service.delete_document(
            request.user_id, request.document_id, request.document_type
        )
        
        if success:
            return {
                "success": True,
                "message": "Document archived successfully",
                "document_id": request.document_id,
                "archived_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document deletion failed: {str(e)}"
        )

@router.get("/summary")
async def get_archive_summary(user_id: str = Query(..., description="Azure user identifier")):
    """
    Get quick archive summary for user.
    
    - **user_id**: Azure user identifier
    
    Returns high-level statistics and counts.
    """
    
    try:
        archive_data = await document_archive_service.get_user_archive(user_id)
        
        summary = {
            "total_documents": archive_data["total_documents_analyzed"] + archive_data["total_documents_generated"],
            "analysis_summary": {
                "total": archive_data["total_documents_analyzed"],
                "pending": archive_data["pending_analyses"],
                "completed": archive_data["completed_analyses"],
                "failed": archive_data["failed_analyses"]
            },
            "generation_summary": {
                "total": archive_data["total_documents_generated"],
                "pending": archive_data["pending_generations"],
                "completed": archive_data["completed_generations"],
                "failed": archive_data["failed_generations"],
                "downloads": archive_data["total_downloads"]
            },
            "storage_usage": {
                "total_bytes": archive_data["total_storage_bytes"],
                "analysis_bytes": archive_data["analysis_storage_bytes"],
                "generation_bytes": archive_data["generation_storage_bytes"]
            },
            "last_activity": archive_data["last_activity_at"]
        }
        
        return {
            "success": True,
            "summary": summary,
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Archive summary retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Archive summary retrieval failed: {str(e)}"
        )

# Helper functions for enhanced analytics

async def _calculate_usage_trends(user_id: str) -> dict:
    """Calculate usage trends over time"""
    
    try:
        # Placeholder for usage trends calculation
        # In production, this would analyze historical data
        return {
            "daily_usage": {
                "analyses_per_day": 2.5,
                "generations_per_day": 1.8,
                "trend": "increasing"
            },
            "weekly_usage": {
                "analyses_per_week": 17.5,
                "generations_per_week": 12.6,
                "trend": "stable"
            },
            "peak_usage_hours": [9, 10, 14, 15, 16],
            "most_active_day": "Tuesday"
        }
        
    except Exception as e:
        logger.error(f"Usage trends calculation failed: {e}")
        return {}

async def _calculate_compliance_trends(user_id: str) -> dict:
    """Calculate compliance score trends"""
    
    try:
        # Placeholder for compliance trends
        return {
            "average_compliance_score": 0.82,
            "compliance_improvement": 0.15,
            "common_issues": [
                "Working hours compliance",
                "Minimum wage requirements",
                "Annual leave provisions"
            ],
            "improvement_areas": [
                "Contract termination clauses",
                "Dispute resolution mechanisms"
            ]
        }
        
    except Exception as e:
        logger.error(f"Compliance trends calculation failed: {e}")
        return {}

async def _calculate_document_insights(user_id: str) -> dict:
    """Calculate document type insights"""
    
    try:
        # Placeholder for document insights
        return {
            "most_analyzed_type": "employment_contract",
            "most_generated_template": "civil_plaint",
            "success_rates": {
                "analysis": 0.95,
                "generation": 0.98
            },
            "average_processing_times": {
                "analysis_seconds": 45.2,
                "generation_seconds": 12.8
            }
        }
        
    except Exception as e:
        logger.error(f"Document insights calculation failed: {e}")
        return {}

async def _calculate_efficiency_metrics(user_id: str) -> dict:
    """Calculate efficiency metrics"""
    
    try:
        # Placeholder for efficiency metrics
        return {
            "time_saved_hours": 24.5,
            "documents_processed": 156,
            "automation_rate": 0.87,
            "error_reduction": 0.65,
            "cost_savings_estimate": "KES 45,000"
        }
        
    except Exception as e:
        logger.error(f"Efficiency metrics calculation failed: {e}")
        return {}
