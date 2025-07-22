from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any
import logging
import asyncio
import time
from collections import defaultdict, deque
from sqlalchemy import text

from app.services.mcp_service import MCPService
from app.services.vector_service import VectorService
# DocumentService removed - using CounselDocs instead
from app.services.crawler_service import CrawlerService
from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple rate limiter for health endpoint
class HealthRateLimiter:
    def __init__(self):
        self.requests = defaultdict(lambda: deque())

    def is_allowed(self, request: Request) -> bool:
        """Check if health check request is allowed (60 per minute)"""
        client_key = request.client.host if request.client else "unknown"
        now = time.time()
        requests = self.requests[client_key]

        # Remove old requests (60 second window)
        while requests and requests[0] < now - 60:
            requests.popleft()

        # Allow up to 60 requests per minute
        if len(requests) < 60:
            requests.append(now)
            return True

        return False

health_rate_limiter = HealthRateLimiter()

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
async def health_check(request: Request):
    """Comprehensive health check"""
    try:
        # Check rate limit
        if not health_rate_limiter.is_allowed(request):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many health check requests. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )

        # Perform health check using MCP service
        health_result = await mcp_service.health_check()
        
        services = {
            'database': {'status': 'unknown', 'details': {}},
            'vector_store': {'status': 'unknown', 'details': {}},
            'ai_service': {'status': 'unknown', 'details': {}},
            'crawler': {'status': 'unknown', 'details': {}}
        }
        
        # Check database
        try:
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                result = db.execute(text("SELECT 1"))
                result.fetchone()  # Actually fetch the result
                services['database'] = {
                    'status': 'healthy',
                    'details': {'connection': 'active'}
                }
            finally:
                db.close()
        except Exception as e:
            services['database'] = {
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
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                result = db.execute(text("SELECT 1"))
                result.fetchone()  # Actually fetch the result
                checks.append(True)
            finally:
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
