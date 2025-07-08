"""
Middleware package for Kenyan Legal AI
"""

from .security_middleware import SecurityMiddleware

# Import setup_middleware from the parent middleware module
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from ..middleware import setup_middleware
except ImportError:
    def setup_middleware(app):
        """Fallback setup_middleware function"""
        pass

__all__ = ["SecurityMiddleware", "setup_middleware"]
