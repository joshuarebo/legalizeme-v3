"""
CounselDocs API Endpoints
Document analysis, generation, and archive management endpoints.
"""

from .analysis import router as analysis_router
from .generation import router as generation_router
from .archive import router as archive_router

__all__ = [
    "analysis_router",
    "generation_router",
    "archive_router"
]
