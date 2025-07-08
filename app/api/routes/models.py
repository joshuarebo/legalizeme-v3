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
from app.core.security import get_current_user
from app.models.user import User
from app.core.exceptions import AIServiceException

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

# Initialize services
ai_service = AIService()
model_manager = ModelManager(ai_service)

@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status(
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive status of all AI models"""
    try:
        status = ai_service.get_model_status()
        return ModelStatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving model status: {str(e)}"
        )

@router.post("/fine-tune", response_model=FineTuningResponse)
async def trigger_fine_tuning(
    request: FineTuningRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Trigger fine-tuning for a specific model"""
    try:
        # Check if user is admin (only admins can trigger fine-tuning)
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can trigger model fine-tuning"
            )
        
        result = await model_manager.trigger_fine_tuning(
            request.model_name, 
            request.priority
        )
        
        if result['success']:
            logger.info(f"Fine-tuning triggered for {request.model_name} by user {current_user.username}")
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
async def get_fine_tuning_status(
    current_user: User = Depends(get_current_user)
):
    """Get current fine-tuning status and queue"""
    try:
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
    request: ModelReloadRequest,
    current_user: User = Depends(get_current_user)
):
    """Reload a specific model"""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can reload models"
            )
        
        result = await ai_service.reload_model(request.model_name)
        
        logger.info(f"Model {request.model_name} reload triggered by user {current_user.username}")
        
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
async def optimize_models(
    current_user: User = Depends(get_current_user)
):
    """Optimize overall model performance"""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can optimize models"
            )
        
        result = await model_manager.optimize_model_performance()
        
        logger.info(f"Model optimization triggered by user {current_user.username}")
        
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
    model_name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
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

@router.get("/health")
async def check_model_health(
    current_user: User = Depends(get_current_user)
):
    """Check health of all models"""
    try:
        status = ai_service.get_model_status()
        
        health_summary = {
            'overall_status': 'healthy',
            'models': {},
            'issues': []
        }
        
        for model_name, model_info in status['models'].items():
            model_status = model_info['status']
            metrics = model_info['metrics']
            
            health_summary['models'][model_name] = {
                'status': model_status,
                'healthy': model_status == 'healthy',
                'error_rate': metrics['error_rate'],
                'avg_response_time': metrics['avg_response_time']
            }
            
            # Check for issues
            if model_status == 'failed':
                health_summary['overall_status'] = 'degraded'
                health_summary['issues'].append(f"Model {model_name} is failed")
            elif metrics['error_rate'] > 0.3:
                health_summary['overall_status'] = 'degraded'
                health_summary['issues'].append(f"Model {model_name} has high error rate: {metrics['error_rate']:.2%}")
            elif metrics['avg_response_time'] > 60:
                if health_summary['overall_status'] == 'healthy':
                    health_summary['overall_status'] = 'degraded'
                health_summary['issues'].append(f"Model {model_name} has slow response time: {metrics['avg_response_time']:.2f}s")
        
        return health_summary
    
    except Exception as e:
        logger.error(f"Error checking model health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking model health: {str(e)}"
        )

@router.get("/config")
async def get_model_config(
    current_user: User = Depends(get_current_user)
):
    """Get model configuration"""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view model configuration"
            )
        
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
