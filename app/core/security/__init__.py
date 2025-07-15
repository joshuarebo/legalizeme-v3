"""
Security module for Kenyan Legal AI
"""

from .rate_limiter import RateLimiter, RateLimitRule, RateLimitStrategy

# Import from parent security module
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Public service layer - no authentication required
# All functions return None or empty responses to maintain compatibility

def create_access_token(*args, **kwargs):
    """No-op function for public service layer"""
    return None

def verify_token(*args, **kwargs):
    """No-op function for public service layer"""
    return {}

def get_current_user(*args, **kwargs):
    """No-op function for public service layer - returns None for optional user context"""
    return None

def verify_password(*args, **kwargs):
    """No-op function for public service layer"""
    return False

def get_password_hash(*args, **kwargs):
    """No-op function for public service layer"""
    return ""

def authenticate_user(*args, **kwargs):
    """No-op function for public service layer"""
    return None

__all__ = [
    "RateLimiter", "RateLimitRule", "RateLimitStrategy",
    "create_access_token", "verify_token", "get_current_user",
    "verify_password", "get_password_hash", "authenticate_user"
]
