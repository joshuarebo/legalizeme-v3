"""
API routes package
"""

from . import auth, documents, health, multimodal
from . import simple_agent as agents
from . import counsel

__all__ = ["auth", "counsel", "documents", "health", "agents", "multimodal"]
