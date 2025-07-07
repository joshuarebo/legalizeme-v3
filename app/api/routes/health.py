from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any
import logging
import asyncio

from app.services.mcp_service import MCPService
from app.services.vector_service import VectorService
from app.services.document_service import DocumentService
from app.services.crawler_service import CrawlerService
from app.database import get_db, redis_client
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    uptime: str
    services: Dict[str, Any]

class ServiceStatus(BaseModel):
    status: str
    details: Dict[str, Any]

# Initialize services
mcp_service = MCPService()

@router.get("/", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check"""
    try:
        # Perform health check using MCP service
        health_result = await mcp_service.health_check()
        
        services = {
            'database': {'status': 'unknown', 'details': {}},
            'redis': {'status': 'unknown', 'details': {}},
            'vector_store': {'status': 'unknown', 'details': {}},
            'ai_service': {'status': 'unknown', 'details': {}},
            'crawler': {'status': 'unknown', 'details': {}}
        }
        
        # Check database
        try:
            db_gen = get_db()
            db = next(db_gen)
            db.execute("SELECT 1")
            services['database'] = {
                'status': 'healthy',
                'details': {'connection': 'active'}
            }
        except Exception as e:
            services['database'] = {
                'status': 'unhealthy',
                'details': {'error': str(e)}
            }
        finally:
            try:
                db.close()
            except:
                pass
        
        # Check Redis
        try:
            if redis_client:
                redis_client.ping()
                services['redis'] = {
                    'status': 'healthy',
                    'details': {'connection': 'active'}
                }
            else:
                services['redis'] = {
                    'status': 'unhealthy',
                    'details': {'error': 'Redis client not initialized'}
                }
        except Exception as e:
            services['redis'] = {
                'status': 'unhealthy',
                'details': {'error': str(e)}
            }
        
        # Update services from health check
        if health_result.get('success'):
            check_results = health_result.get('service_checks', {})
            
            services['vector_store'] = {
                'status': 'healthy' if check_results.get('vector_service') else 'unhealthy',
                'details': {'initialized': check_results.get('vector_service', False)}
            }
            
            services['ai_service'] = {
                'status': 'healthy' if check_results.get('ai_service') else 'unhealthy',
                'details': {'embeddings': check_results.get('ai_service', False)}
            }
        
        # Check crawler service
        try:
            crawler_service = CrawlerService()
            crawler_status = await crawler_service.get_crawl_status()
            services['crawler'] = {
                'status': 'healthy' if crawler_status.get('is_running') else 'inactive',
                'details': {
                    'running': crawler_status.get('is_running', False),
                    'active_tasks': crawler_status.get('active_tasks', 0),
                    'total_documents': crawler_status.get('total_documents', 0)
                }
            }
        except Exception as e:
            services['crawler'] = {
                'status': 'unhealthy',
                'details': {'error': str(e)}
            }
        
        # Determine overall status
        service_statuses = [s['status'] for s in services.values()]
        if all(status in ['healthy', 'inactive'] for status in service_statuses):
            overall_status = 'healthy'
        elif any(status == 'healthy' for status in service_statuses):
            overall_status = 'degraded'
        else:
            overall_status = 'unhealthy'
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="1.0.0",
            uptime="N/A",  # Could implement uptime tracking
            services=services
        )
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )

@router.get("/services")
async def get_service_status():
    """Get detailed service status"""
    try:
        # Get comprehensive service status
        status_result = await mcp_service.get_service_status()
        
        return {
            'timestamp': datetime.utcnow(),
            'service_status': status_result
        }
        
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving service status: {str(e)}"
        )

@router.get("/ready")
async def readiness_check():
    """Readiness check for load balancer"""
    try:
        # Quick check of critical services
        checks = []
        
        # Database check
        try:
            db_gen = get_db()
            db = next(db_gen)
            db.execute("SELECT 1")
            checks.append(True)
            db.close()
        except:
            checks.append(False)
        
        # Vector service check
        try:
            vector_service = VectorService()
            if not vector_service._initialized:
                await vector_service.initialize()
            checks.append(True)
        except:
            checks.append(False)
        
        if all(checks):
            return {"status": "ready", "timestamp": datetime.utcnow()}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in readiness check: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )

@router.get("/live")
async def liveness_check():
    """Liveness check for load balancer"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow(),
        "message": "Counsel AI Backend is running"
    }

@router.get("/version")
async def get_version():
    """Get application version and build info"""
    return {
        "version": "1.0.0",
        "build_time": "N/A",
        "git_commit": "N/A",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow()
    }
