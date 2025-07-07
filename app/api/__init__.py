"""
API package for Counsel AI Backend
"""

from .routes import auth, counsel, documents, health

__all__ = ["auth", "counsel", "documents", "health"]
