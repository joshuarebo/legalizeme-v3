"""
Context Engineering Framework for LegalResearchAgent
Provides multi-layered context management for production-grade legal AI
"""

from .context_manager import ContextManager, ContextLayer
from .context_blueprint import ContextBlueprint, QueryContext
from .context_router import ContextRouter
from .context_monitor import ContextMonitor

__all__ = [
    'ContextManager',
    'ContextLayer',
    'ContextBlueprint',
    'QueryContext',
    'ContextRouter',
    'ContextMonitor'
]
