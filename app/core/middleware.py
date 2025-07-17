from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
import time
import logging
import uuid
from typing import Callable

from app.config import settings

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Log request
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"from {client_ip} - User-Agent: {request.headers.get('user-agent', 'unknown')}"
        )
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Response {request_id}: {response.status_code} - "
            f"Process time: {process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security headers"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.anthropic.com https://bedrock.amazonaws.com; "
            "frame-ancestors 'none'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean up old entries
        self.clients = {
            ip: times for ip, times in self.clients.items()
            if any(t > current_time - self.period for t in times)
        }
        
        # Check rate limit
        if client_ip in self.clients:
            # Filter recent requests
            recent_requests = [
                t for t in self.clients[client_ip]
                if t > current_time - self.period
            ]
            
            if len(recent_requests) >= self.calls:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return Response(
                    content="Rate limit exceeded",
                    status_code=429,
                    headers={"Retry-After": str(self.period)}
                )
            
            self.clients[client_ip] = recent_requests + [current_time]
        else:
            self.clients[client_ip] = [current_time]
        
        return await call_next(request)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
            
            # Return generic error response
            return Response(
                content="Internal server error",
                status_code=500,
                headers={"Content-Type": "text/plain"}
            )

def setup_middleware(app: FastAPI):
    """Setup all middleware for the application"""
    
    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=3600,  # 1 hour
        https_only=settings.ENVIRONMENT == "production"
    )
    
    # Add rate limiting - PRODUCTION OPTIMIZED
    if settings.ENVIRONMENT == "production":
        app.add_middleware(RateLimitMiddleware, calls=500, period=60)  # Increased from 100 to 500
    
    # Add security headers
    app.add_middleware(SecurityMiddleware)
    
    # Add logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Add error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)
    
    logger.info("Middleware setup completed")
