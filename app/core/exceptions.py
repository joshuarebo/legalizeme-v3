from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Union

logger = logging.getLogger(__name__)

class CounselAIException(Exception):
    """Base exception for Counsel AI application"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class DocumentProcessingException(CounselAIException):
    """Exception raised during document processing"""
    pass

class AIServiceException(CounselAIException):
    """Exception raised by AI service"""
    pass

class VectorServiceException(CounselAIException):
    """Exception raised by vector service"""
    pass

class CrawlerException(CounselAIException):
    """Exception raised during web crawling"""
    pass

class AuthenticationException(CounselAIException):
    """Exception raised during authentication"""
    pass

class ValidationException(CounselAIException):
    """Exception raised during validation"""
    pass

# Exception handlers
async def counsel_ai_exception_handler(request: Request, exc: CounselAIException):
    """Handle custom Counsel AI exceptions"""
    logger.error(f"Counsel AI Exception: {exc.message} - Details: {exc.details}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation exceptions"""
    logger.error(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors()
        }
    )

async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
            "details": str(exc) if logger.isEnabledFor(logging.DEBUG) else None
        }
    )

def setup_exception_handlers(app):
    """Setup exception handlers for the application"""
    
    app.add_exception_handler(CounselAIException, counsel_ai_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers setup completed")
