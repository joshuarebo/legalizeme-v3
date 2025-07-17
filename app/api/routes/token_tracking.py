"""
Token Tracking API Routes for CounselAI
Provides endpoints for token usage tracking and management
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.token_tracking_service import TokenTrackingService

logger = logging.getLogger(__name__)
router = APIRouter()

# Global token tracking service instance (lazy-initialized)
_token_tracking_service = None

def get_token_tracking_service():
    """Get token tracking service instance with lazy initialization"""
    global _token_tracking_service
    if _token_tracking_service is None:
        try:
            _token_tracking_service = TokenTrackingService()
            logger.info("✅ TokenTrackingService lazy-initialized successfully")
        except Exception as e:
            logger.error(f"❌ TokenTrackingService lazy initialization failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Token tracking service unavailable: {e}"
            )
    return _token_tracking_service

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TokenCheckRequest(BaseModel):
    userId: str = Field(..., description="User ID from Azure authentication")
    estimatedTokens: int = Field(..., ge=1, description="Estimated tokens for the request")
    requestType: str = Field(default="chat_completion", description="Type of request")

class TokenTrackRequest(BaseModel):
    userId: str = Field(..., description="User ID from Azure authentication")
    tokensUsed: int = Field(..., ge=0, description="Actual tokens used")
    requestType: str = Field(..., description="Type of request")
    mode: Optional[str] = Field(default=None, description="Request mode (enhanced, direct, etc.)")
    timestamp: Optional[str] = Field(default=None, description="Request timestamp")
    sessionId: Optional[str] = Field(default=None, description="Session ID for tracking")

class TokenResetRequest(BaseModel):
    userId: str = Field(..., description="User ID to reset")
    newPlanId: Optional[str] = Field(default=None, description="New plan ID (optional)")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/status/{user_id}")
async def get_user_token_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    🎯 ENDPOINT 1: GET USER TOKEN STATUS
    Get current token usage and limits for a specific user
    """
    try:
        logger.info(f"Getting token status for user: {user_id}")
        
        result = get_token_tracking_service().get_user_token_status(db, user_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=result.get("code", 500),
                detail=result.get("error", "Failed to get token status")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_token_status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/check")
async def check_token_availability(
    request: TokenCheckRequest,
    db: Session = Depends(get_db)
):
    """
    🎯 ENDPOINT 2: CHECK TOKEN AVAILABILITY
    Check if user has enough tokens before making an AI request
    """
    try:
        logger.info(f"Checking token availability for user: {request.userId}, tokens: {request.estimatedTokens}")
        
        result = get_token_tracking_service().check_token_availability(
            db=db,
            user_id=request.userId,
            estimated_tokens=request.estimatedTokens,
            request_type=request.requestType
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=result.get("code", 500),
                detail=result.get("error", "Failed to check token availability")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_token_availability: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/track")
async def track_token_usage(
    request: TokenTrackRequest,
    db: Session = Depends(get_db)
):
    """
    🎯 ENDPOINT 3: TRACK TOKEN USAGE
    Record actual token usage after an AI request is completed
    """
    try:
        logger.info(f"Tracking token usage for user: {request.userId}, tokens: {request.tokensUsed}")
        
        result = get_token_tracking_service().track_token_usage(
            db=db,
            user_id=request.userId,
            tokens_used=request.tokensUsed,
            request_type=request.requestType,
            mode=request.mode,
            session_id=request.sessionId
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=result.get("code", 500),
                detail=result.get("error", "Failed to track token usage")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in track_token_usage: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/history/{user_id}")
async def get_usage_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    🎯 ENDPOINT 4: GET USAGE HISTORY
    Get user's token usage history for analytics and debugging
    """
    try:
        logger.info(f"Getting usage history for user: {user_id}, limit: {limit}, offset: {offset}")
        
        result = get_token_tracking_service().get_usage_history(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=result.get("code", 500),
                detail=result.get("error", "Failed to get usage history")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_usage_history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

# ============================================================================
# ADMIN ENDPOINTS (Optional - for management)
# ============================================================================

@router.post("/admin/reset")
async def reset_user_tokens(
    request: TokenResetRequest,
    db: Session = Depends(get_db)
):
    """
    ADMIN ENDPOINT: Reset user tokens
    For administrative use only
    """
    try:
        logger.info(f"Admin resetting tokens for user: {request.userId}")
        
        result = get_token_tracking_service().reset_user_tokens(
            db=db,
            user_id=request.userId,
            new_plan_id=request.newPlanId
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=result.get("code", 500),
                detail=result.get("error", "Failed to reset tokens")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reset_user_tokens: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/debug-token-service")
async def debug_token_service():
    """Debug token tracking service status"""
    try:
        # Check if TokenTrackingService can be imported
        from app.services.token_tracking_service import TokenTrackingService
        import_success = True
        import_error = None
    except Exception as e:
        import_success = False
        import_error = str(e)

    # Check global variable
    global _token_tracking_service
    service_status = "initialized" if _token_tracking_service is not None else "not_initialized"

    # Try to initialize
    init_success = False
    init_error = None
    try:
        test_service = get_token_tracking_service()
        init_success = True
    except Exception as e:
        init_error = str(e)

    return {
        "import_success": import_success,
        "import_error": import_error,
        "service_status": service_status,
        "init_success": init_success,
        "init_error": init_error,
        "function_exists": callable(get_token_tracking_service)
    }

@router.get("/health")
async def token_tracking_health():
    """Health check for token tracking system"""
    return {
        "status": "healthy",
        "service": "token_tracking",
        "version": "1.0.0",
        "endpoints": [
            "GET /api/v1/tokens/status/{userId}",
            "POST /api/v1/tokens/check",
            "POST /api/v1/tokens/track",
            "GET /api/v1/tokens/history/{userId}"
        ]
    }
