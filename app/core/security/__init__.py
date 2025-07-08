"""
Security module for Kenyan Legal AI
"""

from .rate_limiter import RateLimiter, RateLimitRule, RateLimitStrategy

# Import from parent security module
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from ..security import (
        create_access_token, verify_token, get_current_user,
        verify_password, get_password_hash, authenticate_user
    )
except ImportError:
    # Fallback imports
    def create_access_token(*args, **kwargs):
        raise NotImplementedError("JWT token creation not available")

    def verify_token(*args, **kwargs):
        raise NotImplementedError("JWT token verification not available")

    def get_current_user(*args, **kwargs):
        raise NotImplementedError("User authentication not available")

    def verify_password(*args, **kwargs):
        raise NotImplementedError("Password verification not available")

    def get_password_hash(*args, **kwargs):
        raise NotImplementedError("Password hashing not available")

    def authenticate_user(*args, **kwargs):
        raise NotImplementedError("User authentication not available")

__all__ = [
    "RateLimiter", "RateLimitRule", "RateLimitStrategy",
    "create_access_token", "verify_token", "get_current_user",
    "verify_password", "get_password_hash", "authenticate_user"
]
