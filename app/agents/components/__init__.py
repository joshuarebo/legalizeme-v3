"""
Modular Chaining Components for LegalResearchAgent
Provides structured, context-aware components for legal research pipeline
"""

from .base_component import BaseComponent, ComponentResult, ComponentError
from .vector_retriever import VectorRetriever
from .multi_source_summarizer import MultiSourceSummarizer
from .legal_reasoner import LegalReasoner
from .answer_formatter import AnswerFormatter

__all__ = [
    'BaseComponent',
    'ComponentResult',
    'ComponentError',
    'VectorRetriever',
    'MultiSourceSummarizer', 
    'LegalReasoner',
    'AnswerFormatter'
]
