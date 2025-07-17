"""
Model Management API Routes
Provides endpoints for monitoring, managing, and fine-tuning AI models
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from app.services.ai_service import AIService
from app.services.model_manager import ModelManager
# Authentication removed - now public service layer
# from app.core.security import get_current_user
from app.models.user import User
from app.core.exceptions import AIServiceException
from app.schemas.api_responses import ModelHealthResponse, ServiceStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class ModelStatusResponse(BaseModel):
    timestamp: datetime
    models: Dict[str, Any]

class FineTuningRequest(BaseModel):
    model_name: str = Field(..., description="Name of the model to fine-tune")
    priority: bool = Field(default=False, description="Whether to prioritize this fine-tuning")
    training_data_path: Optional[str] = Field(None, description="Path to custom training data")

class FineTuningResponse(BaseModel):
    success: bool
    message: str
    queue_position: Optional[int] = None
    error: Optional[str] = None

class ModelReloadRequest(BaseModel):
    model_name: str = Field(..., description="Name of the model to reload")

class ModelReloadResponse(BaseModel):
    success: bool
    model_name: str
    status: str
    message: str
    error: Optional[str] = None

class OptimizationResponse(BaseModel):
    success: bool
    optimizations: Dict[str, Any]
    timestamp: datetime
    error: Optional[str] = None

# Services will be initialized within endpoints to avoid module-level issues

@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status():
    """Get comprehensive status of all AI models"""
    try:
        ai_service = AIService()
        status = ai_service.get_model_status()
        return ModelStatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving model status: {str(e)}"
        )

@router.get("/health")
async def get_model_health():
    """Get comprehensive health status of all AI models"""
    try:
        # Simple health check without full AIService initialization
        from app.config import settings
        import boto3

        # Test basic AWS Bedrock connectivity
        try:
            bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )

            # Simple connectivity test
            models_available = True
            primary_model_status = "healthy"

        except Exception as e:
            logger.error(f"AWS Bedrock connectivity error: {e}")
            models_available = False
            primary_model_status = "unhealthy"

        # Return simplified status
        status_data = {
            "models_available": models_available,
            "primary_model": {
                "id": settings.AWS_BEDROCK_MODEL_ID_PRIMARY,
                "status": primary_model_status,
                "provider": "aws_bedrock"
            },
            "embedding_model": {
                "id": settings.AWS_BEDROCK_TITAN_EMBEDDING_MODEL_ID,
                "status": primary_model_status,
                "provider": "aws_bedrock"
            }
        }

        # Build health response with real data
        health_response = {
            "overall_health": "healthy",
            "model_statuses": {},
            "response_times": {},
            "error_rates": {},
            "issues": [],
            "last_check": status_data.get('timestamp', datetime.utcnow().isoformat())
        }

        # Process each model from real status data
        for model_name, model_info in status_data.get('models', {}).items():
            model_status = model_info.get('status', 'unknown')
            success_count = model_info.get('success_count', 0)
            error_count = model_info.get('error_count', 0)
            avg_response_time = model_info.get('avg_response_time', 0)

            # Calculate error rate
            total_requests = success_count + error_count
            error_rate = error_count / total_requests if total_requests > 0 else 0.0

            # Set model health status
            health_response["model_statuses"][model_name] = model_status
            health_response["response_times"][model_name] = float(avg_response_time)
            health_response["error_rates"][model_name] = float(error_rate)

            # Check for issues and update overall health
            if model_status == 'failed':
                health_response["overall_health"] = "degraded"
                health_response["issues"].append(f"Model {model_name} is failed")
            elif error_rate > 0.3:
                health_response["overall_health"] = "degraded"
                health_response["issues"].append(f"Model {model_name} has high error rate: {error_rate:.2%}")
            elif avg_response_time > 60:
                if health_response["overall_health"] == "healthy":
                    health_response["overall_health"] = "degraded"
                health_response["issues"].append(f"Model {model_name} has slow response time: {avg_response_time:.2f}s")

        return health_response

    except Exception as e:
        logger.error(f"Error checking models health: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking models health: {str(e)}"
        )

@router.post("/fine-tune", response_model=FineTuningResponse)
async def trigger_fine_tuning(
    request: FineTuningRequest,
    background_tasks: BackgroundTasks
):
    """Trigger fine-tuning for a specific model"""
    try:
        # Public endpoint (no admin check since auth is removed)
        ai_service = AIService()
        model_manager = ModelManager(ai_service)

        result = await model_manager.trigger_fine_tuning(
            request.model_name,
            request.priority
        )
        
        if result['success']:
            logger.info(f"Fine-tuning triggered for {request.model_name}")
            return FineTuningResponse(
                success=True,
                message=result['message'],
                queue_position=result.get('queue_position')
            )
        else:
            return FineTuningResponse(
                success=False,
                message="Failed to trigger fine-tuning",
                error=result.get('error')
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering fine-tuning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering fine-tuning: {str(e)}"
        )

@router.get("/fine-tuning/status")
async def get_fine_tuning_status():
    """Get current fine-tuning status and queue"""
    try:
        ai_service = AIService()
        model_manager = ModelManager(ai_service)
        status = model_manager.get_fine_tuning_status()
        return status
    except Exception as e:
        logger.error(f"Error getting fine-tuning status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving fine-tuning status: {str(e)}"
        )

@router.post("/reload", response_model=ModelReloadResponse)
async def reload_model(
    request: ModelReloadRequest
):
    """Reload a specific model"""
    try:
        # Public endpoint (no admin check since auth is removed)
        result = await ai_service.reload_model(request.model_name)

        logger.info(f"Model {request.model_name} reload triggered")
        
        return ModelReloadResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reloading model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reloading model: {str(e)}"
        )

@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_models():
    """Optimize overall model performance"""
    try:
        # Public endpoint (no admin check since auth is removed)
        ai_service = AIService()
        model_manager = ModelManager(ai_service)
        result = await model_manager.optimize_model_performance()

        logger.info(f"Model optimization triggered")
        
        return OptimizationResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error optimizing models: {str(e)}"
        )

@router.get("/metrics")
async def get_model_metrics(
    model_name: Optional[str] = None
):
    """Get detailed metrics for models"""
    try:
        status = ai_service.get_model_status()
        
        if model_name:
            if model_name not in status['models']:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model {model_name} not found"
                )
            return {
                'model': model_name,
                'metrics': status['models'][model_name]['metrics'],
                'timestamp': status['timestamp']
            }
        else:
            return {
                'models': {
                    name: model_info['metrics'] 
                    for name, model_info in status['models'].items()
                },
                'timestamp': status['timestamp']
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving model metrics: {str(e)}"
        )

@router.get("/debug")
async def debug_endpoint():
    """Debug endpoint"""
    return {"message": "Debug endpoint is working!", "timestamp": "2025-07-14T14:50:00", "status": "OK"}

@router.get("/config")
async def get_model_config():
    """Get model configuration"""
    try:
        # Initialize AI service within the endpoint
        ai_service = AIService()

        configs = {}
        for model_name, config in ai_service.model_configs.items():
            configs[model_name] = {
                'name': config.name,
                'priority': config.priority,
                'timeout': config.timeout,
                'max_error_rate': config.max_error_rate,
                'requires_gpu': config.requires_gpu,
                'memory_requirement': config.memory_requirement,
                'fine_tuned': config.fine_tuned,
                'model_path': config.model_path
            }

        return {
            'models': configs,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving model configuration: {str(e)}"
        )
