"""
Document Archive Service for CounselDocs
Manages document archive, analytics, and dashboard functionality.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.database import get_db
from app.counseldocs.models.document_analysis import DocumentAnalysis
from app.counseldocs.models.document_generation import DocumentGeneration
from app.counseldocs.models.document_archive import DocumentArchive

logger = logging.getLogger(__name__)

class DocumentArchiveService:
    """
    Service for managing document archives and analytics.
    Provides dashboard data and document management functionality.
    """
    
    def __init__(self):
        """Initialize archive service"""
        pass
    
    async def get_user_archive(self, user_id: str) -> Dict[str, Any]:
        """Get or create user archive record"""
        
        try:
            with next(get_db()) as db:
                archive = db.query(DocumentArchive).filter(
                    DocumentArchive.user_id == user_id
                ).first()
                
                if not archive:
                    # Create new archive record
                    archive = DocumentArchive(user_id=user_id)
                    db.add(archive)
                    db.commit()
                    db.refresh(archive)
                
                return archive.to_dict()
                
        except Exception as e:
            logger.error(f"Failed to get user archive: {e}")
            raise Exception(f"Archive retrieval failed: {str(e)}")
    
    async def get_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive dashboard data for user"""
        
        try:
            with next(get_db()) as db:
                # Get archive record
                archive = await self.get_user_archive(user_id)
                
                # Get recent analyses
                recent_analyses = db.query(DocumentAnalysis).filter(
                    DocumentAnalysis.user_id == user_id,
                    DocumentAnalysis.is_archived == False
                ).order_by(desc(DocumentAnalysis.created_at)).limit(10).all()
                
                # Get recent generations
                recent_generations = db.query(DocumentGeneration).filter(
                    DocumentGeneration.user_id == user_id,
                    DocumentGeneration.is_archived == False
                ).order_by(desc(DocumentGeneration.created_at)).limit(10).all()
                
                # Get analytics data
                analytics = await self._calculate_analytics(user_id, db)
                
                return {
                    'archive_summary': archive,
                    'recent_analyses': [analysis.to_dict() for analysis in recent_analyses],
                    'recent_generations': [gen.to_dict() for gen in recent_generations],
                    'analytics': analytics,
                    'dashboard_generated_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Dashboard data retrieval failed: {e}")
            raise Exception(f"Dashboard error: {str(e)}")
    
    async def get_user_documents(
        self, 
        user_id: str, 
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's documents with filtering"""
        
        try:
            with next(get_db()) as db:
                # Build query for analyses
                analysis_query = db.query(DocumentAnalysis).filter(
                    DocumentAnalysis.user_id == user_id,
                    DocumentAnalysis.is_archived == False
                )
                
                if status:
                    analysis_query = analysis_query.filter(DocumentAnalysis.status == status)
                
                # Build query for generations
                generation_query = db.query(DocumentGeneration).filter(
                    DocumentGeneration.user_id == user_id,
                    DocumentGeneration.is_archived == False
                )
                
                if status:
                    generation_query = generation_query.filter(DocumentGeneration.status == status)
                
                if document_type:
                    if document_type == 'analysis':
                        generation_query = generation_query.filter(False)  # Exclude generations
                    elif document_type == 'generation':
                        analysis_query = analysis_query.filter(False)  # Exclude analyses
                
                # Get results
                analyses = analysis_query.order_by(desc(DocumentAnalysis.created_at)).offset(offset).limit(limit).all()
                generations = generation_query.order_by(desc(DocumentGeneration.created_at)).offset(offset).limit(limit).all()
                
                # Get total counts
                total_analyses = analysis_query.count()
                total_generations = generation_query.count()
                
                return {
                    'analyses': [analysis.to_dict() for analysis in analyses],
                    'generations': [gen.to_dict() for gen in generations],
                    'pagination': {
                        'total_analyses': total_analyses,
                        'total_generations': total_generations,
                        'limit': limit,
                        'offset': offset,
                        'has_more_analyses': total_analyses > offset + len(analyses),
                        'has_more_generations': total_generations > offset + len(generations)
                    }
                }
                
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            raise Exception(f"Document retrieval error: {str(e)}")
    
    async def update_analysis_stats(
        self, 
        user_id: str, 
        status_change: str, 
        file_size: int = 0
    ) -> bool:
        """Update analysis statistics for user"""
        
        try:
            with next(get_db()) as db:
                archive = db.query(DocumentArchive).filter(
                    DocumentArchive.user_id == user_id
                ).first()
                
                if not archive:
                    archive = DocumentArchive(user_id=user_id)
                    db.add(archive)
                
                archive.update_analysis_stats(status_change, file_size)
                db.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update analysis stats: {e}")
            return False
    
    async def update_generation_stats(
        self, 
        user_id: str, 
        status_change: str, 
        file_size: int = 0,
        download: bool = False
    ) -> bool:
        """Update generation statistics for user"""
        
        try:
            with next(get_db()) as db:
                archive = db.query(DocumentArchive).filter(
                    DocumentArchive.user_id == user_id
                ).first()
                
                if not archive:
                    archive = DocumentArchive(user_id=user_id)
                    db.add(archive)
                
                archive.update_generation_stats(status_change, file_size, download)
                db.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update generation stats: {e}")
            return False
    
    async def delete_document(self, user_id: str, document_id: str, document_type: str) -> bool:
        """Delete (archive) a document"""
        
        try:
            with next(get_db()) as db:
                if document_type == 'analysis':
                    document = db.query(DocumentAnalysis).filter(
                        DocumentAnalysis.uuid == document_id,
                        DocumentAnalysis.user_id == user_id
                    ).first()
                elif document_type == 'generation':
                    document = db.query(DocumentGeneration).filter(
                        DocumentGeneration.uuid == document_id,
                        DocumentGeneration.user_id == user_id
                    ).first()
                else:
                    return False
                
                if document:
                    document.is_archived = True
                    db.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Document deletion failed: {e}")
            return False
    
    async def _calculate_analytics(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Calculate detailed analytics for user"""
        
        try:
            # Time periods for analytics
            now = datetime.utcnow()
            last_30_days = now - timedelta(days=30)
            last_7_days = now - timedelta(days=7)
            
            # Analysis analytics
            total_analyses = db.query(DocumentAnalysis).filter(
                DocumentAnalysis.user_id == user_id
            ).count()
            
            analyses_last_30_days = db.query(DocumentAnalysis).filter(
                DocumentAnalysis.user_id == user_id,
                DocumentAnalysis.created_at >= last_30_days
            ).count()
            
            analyses_last_7_days = db.query(DocumentAnalysis).filter(
                DocumentAnalysis.user_id == user_id,
                DocumentAnalysis.created_at >= last_7_days
            ).count()
            
            # Generation analytics
            total_generations = db.query(DocumentGeneration).filter(
                DocumentGeneration.user_id == user_id
            ).count()
            
            generations_last_30_days = db.query(DocumentGeneration).filter(
                DocumentGeneration.user_id == user_id,
                DocumentGeneration.created_at >= last_30_days
            ).count()
            
            generations_last_7_days = db.query(DocumentGeneration).filter(
                DocumentGeneration.user_id == user_id,
                DocumentGeneration.created_at >= last_7_days
            ).count()
            
            # Compliance score analytics
            avg_compliance_score = db.query(func.avg(DocumentAnalysis.compliance_score)).filter(
                DocumentAnalysis.user_id == user_id,
                DocumentAnalysis.compliance_score.isnot(None)
            ).scalar() or 0.0
            
            # Document type distribution
            doc_type_distribution = db.query(
                DocumentAnalysis.document_type_detected,
                func.count(DocumentAnalysis.id)
            ).filter(
                DocumentAnalysis.user_id == user_id
            ).group_by(DocumentAnalysis.document_type_detected).all()
            
            # Template usage
            template_usage = db.query(
                DocumentGeneration.template_id,
                func.count(DocumentGeneration.id)
            ).filter(
                DocumentGeneration.user_id == user_id
            ).group_by(DocumentGeneration.template_id).all()
            
            return {
                'analysis_stats': {
                    'total': total_analyses,
                    'last_30_days': analyses_last_30_days,
                    'last_7_days': analyses_last_7_days,
                    'avg_compliance_score': round(avg_compliance_score, 2)
                },
                'generation_stats': {
                    'total': total_generations,
                    'last_30_days': generations_last_30_days,
                    'last_7_days': generations_last_7_days
                },
                'document_type_distribution': [
                    {'type': doc_type or 'unknown', 'count': count}
                    for doc_type, count in doc_type_distribution
                ],
                'template_usage': [
                    {'template_id': template_id, 'count': count}
                    for template_id, count in template_usage
                ],
                'calculated_at': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Analytics calculation failed: {e}")
            return {
                'analysis_stats': {'total': 0, 'last_30_days': 0, 'last_7_days': 0, 'avg_compliance_score': 0.0},
                'generation_stats': {'total': 0, 'last_30_days': 0, 'last_7_days': 0},
                'document_type_distribution': [],
                'template_usage': [],
                'calculated_at': now.isoformat()
            }

# Global instance
document_archive_service = DocumentArchiveService()
