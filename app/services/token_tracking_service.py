"""
Token Tracking Service for CounselAI
Handles all token-related business logic
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.token_tracking import UserTokens, TokenUsageHistory, TOKEN_PLANS
from app.database import get_db

logger = logging.getLogger(__name__)


class TokenTrackingService:
    """Service for managing user token limits and usage tracking"""
    
    def __init__(self):
        self.admin_users = ['info.support@legalizeme.site', 'admin']
        logger.info("TokenTrackingService initialized")
    
    def get_user_token_status(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Get current token status for a user"""
        try:
            # Get or create user tokens record
            user_tokens = self._get_or_create_user_tokens(db, user_id)
            
            return {
                "success": True,
                "data": user_tokens.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error getting token status for user {user_id}: {e}")
            return {
                "success": False,
                "error": "Failed to retrieve token status",
                "code": 500
            }
    
    def check_token_availability(self, db: Session, user_id: str, estimated_tokens: int, request_type: str = "chat_completion") -> Dict[str, Any]:
        """Check if user has enough tokens for a request"""
        try:
            # Get or create user tokens record
            user_tokens = self._get_or_create_user_tokens(db, user_id)
            
            # Check if user can proceed
            can_proceed = user_tokens.can_use_tokens(estimated_tokens)
            
            response = {
                "success": True,
                "canProceed": can_proceed,
                "remaining": user_tokens.remaining_tokens,
                "estimatedTokens": estimated_tokens,
                "currentUsage": user_tokens.tokens_used,
                "limit": user_tokens.tokens_limit
            }
            
            # Add admin flag if applicable
            if user_tokens.is_admin:
                response["unlimited"] = True
                response["remaining"] = 999999999
                response["limit"] = 999999999
            
            # Add message if limit exceeded
            if not can_proceed and not user_tokens.is_admin:
                response["message"] = "Token limit exceeded"
            
            return response
            
        except Exception as e:
            logger.error(f"Error checking token availability for user {user_id}: {e}")
            return {
                "success": False,
                "error": "Failed to check token availability",
                "code": 500
            }
    
    def track_token_usage(self, db: Session, user_id: str, tokens_used: int, request_type: str, mode: str = None, session_id: str = None) -> Dict[str, Any]:
        """Track actual token usage after a request"""
        try:
            # Get or create user tokens record
            user_tokens = self._get_or_create_user_tokens(db, user_id)
            
            # Use tokens (this will check limits for non-admin users)
            if not user_tokens.use_tokens(tokens_used):
                return {
                    "success": False,
                    "error": "Token limit exceeded",
                    "code": 400
                }
            
            # Create usage history record
            usage_record = TokenUsageHistory(
                user_id=user_id,
                tokens_used=tokens_used,
                request_type=request_type,
                mode=mode,
                session_id=session_id
            )
            
            db.add(usage_record)
            db.commit()
            db.refresh(user_tokens)
            
            response = {
                "success": True,
                "tracked": True,
                "newUsage": user_tokens.tokens_used,
                "remaining": user_tokens.remaining_tokens,
                "limit": user_tokens.tokens_limit
            }
            
            # Add admin flag if applicable
            if user_tokens.is_admin:
                response["newUsage"] = 0
                response["remaining"] = 999999999
                response["limit"] = 999999999
            
            return response
            
        except Exception as e:
            logger.error(f"Error tracking token usage for user {user_id}: {e}")
            db.rollback()
            return {
                "success": False,
                "error": "Failed to track token usage",
                "code": 500
            }
    
    def get_usage_history(self, db: Session, user_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get user's token usage history"""
        try:
            # Validate limit
            limit = min(limit, 100)  # Max 100 records per request
            
            # Get usage history
            query = db.query(TokenUsageHistory).filter(
                TokenUsageHistory.user_id == user_id
            ).order_by(desc(TokenUsageHistory.timestamp))
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            history_records = query.offset(offset).limit(limit).all()
            
            # Convert to dict format
            history_data = [record.to_dict() for record in history_records]
            
            return {
                "success": True,
                "data": history_data,
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "hasMore": offset + limit < total
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting usage history for user {user_id}: {e}")
            return {
                "success": False,
                "error": "Failed to retrieve usage history",
                "code": 500
            }
    
    def _get_or_create_user_tokens(self, db: Session, user_id: str) -> UserTokens:
        """Get existing user tokens or create new record with default plan"""
        user_tokens = db.query(UserTokens).filter(UserTokens.user_id == user_id).first()
        
        if not user_tokens:
            # Create new user with default free trial plan
            plan_config = TOKEN_PLANS['counselai_free_trial']
            
            # Check if admin user
            if user_id in self.admin_users:
                plan_config = TOKEN_PLANS['admin_unlimited']
                plan_id = 'admin_unlimited'
            else:
                plan_id = 'counselai_free_trial'
            
            user_tokens = UserTokens(
                user_id=user_id,
                tokens_used=0,
                tokens_limit=plan_config['limit'],
                plan_id=plan_id,
                plan_name=plan_config['name'],
                reset_date=datetime.utcnow() + timedelta(days=plan_config['duration_days'])
            )
            
            db.add(user_tokens)
            db.commit()
            db.refresh(user_tokens)
            
            logger.info(f"Created new user tokens record for {user_id} with plan {plan_id}")
        
        return user_tokens
    
    def reset_user_tokens(self, db: Session, user_id: str, new_plan_id: str = None) -> Dict[str, Any]:
        """Reset user tokens (admin function)"""
        try:
            user_tokens = db.query(UserTokens).filter(UserTokens.user_id == user_id).first()
            
            if not user_tokens:
                return {
                    "success": False,
                    "error": "User not found",
                    "code": 404
                }
            
            # Use provided plan or keep current
            plan_id = new_plan_id or user_tokens.plan_id
            plan_config = TOKEN_PLANS.get(plan_id, TOKEN_PLANS['counselai_free_trial'])
            
            # Reset tokens
            user_tokens.tokens_used = 0
            user_tokens.plan_id = plan_id
            user_tokens.plan_name = plan_config['name']
            user_tokens.tokens_limit = plan_config['limit']
            user_tokens.reset_date = datetime.utcnow() + timedelta(days=plan_config['duration_days'])
            
            db.commit()
            
            return {
                "success": True,
                "message": f"Tokens reset for user {user_id}",
                "data": user_tokens.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error resetting tokens for user {user_id}: {e}")
            db.rollback()
            return {
                "success": False,
                "error": "Failed to reset tokens",
                "code": 500
            }


# Service class - instantiated via lazy initialization in routes
