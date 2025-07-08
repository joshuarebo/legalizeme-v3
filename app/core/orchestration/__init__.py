"""
Modular Orchestration System for Kenyan Legal AI
Provides adapters, RAG orchestration, and prompt engineering for dynamic intelligence enhancement
"""

from .adapters import *
from .rag_orchestrator import *
from .prompt_engine import *
from .intelligence_enhancer import *

__all__ = [
    "BaseAdapter",
    "ModelAdapter", 
    "PromptAdapter",
    "RAGAdapter",
    "RAGOrchestrator",
    "PromptEngine",
    "IntelligenceEnhancer"
]
