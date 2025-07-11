"""
Prompt Templates and PRP System for LegalResearchAgent
Provides structured prompt templates for different legal use cases
"""

from .prp_manager import PRPManager, PRPTemplate
from .template_loader import TemplateLoader

__all__ = [
    'PRPManager',
    'PRPTemplate', 
    'TemplateLoader'
]
