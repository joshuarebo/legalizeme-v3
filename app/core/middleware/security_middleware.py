"""
Security Middleware for Kenyan Legal AI
Provides comprehensive security features including rate limiting, request validation, and security headers
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import re

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.security.rate_limiter import RateLimiter
from app.config import settings

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    def __init__(
        self, 
        app: ASGIApp,
        rate_limiter: Optional[RateLimiter] = None,
        enable_request_logging: bool = True,
        enable_security_headers: bool = True,
        enable_content_validation: bool = True
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter(settings.REDIS_URL)
        self.enable_request_logging = enable_request_logging
        self.enable_security_headers = enable_security_headers
        self.enable_content_validation = enable_content_validation
        
        # Security configuration
        self.max_request_size = getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)  # 10MB
        self.max_query_length = getattr(settings, 'MAX_QUERY_LENGTH', 2000)
        self.max_document_size = getattr(settings, 'MAX_DOCUMENT_SIZE', 10 * 1024 * 1024)  # 10MB
        
        # Blocked patterns
        self.blocked_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS attempts
            r'javascript:',  # JavaScript URLs
            r'data:text/html',  # Data URLs
            r'vbscript:',  # VBScript
            r'onload\s*=',  # Event handlers
            r'onerror\s*=',
            r'onclick\s*=',
        ]
        
        # Rate limiting rules mapping
        self.rate_limit_rules = {
            '/counsel/query': 'ai_queries',
            '/counsel/generate-document': 'document_generation',
            '/models/': 'model_management',
            '/auth/': 'auth_attempts',
        }
        
        # Request metrics
        self.metrics = {
            'total_requests': 0,
            'blocked_requests': 0,
            'rate_limited_requests': 0,
            'avg_response_time': 0.0,
            'security_violations': 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch method"""
        start_time = time.time()

        try:
            # Skip security checks for docs and health endpoints
            if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health", "/health/live"]:
                response = await call_next(request)
                return response

            # Pre-request security checks
            security_check = await self._pre_request_security_check(request)
            if not security_check['allowed']:
                return self._create_security_response(security_check)
            
            # Rate limiting check
            rate_limit_check = await self._check_rate_limits(request)
            if not rate_limit_check['allowed']:
                return self.rate_limiter.create_rate_limit_response(
                    rate_limit_check['rule_name'], 
                    rate_limit_check
                )
            
            # Content validation
            if self.enable_content_validation:
                content_check = await self._validate_request_content(request)
                if not content_check['valid']:
                    return self._create_validation_response(content_check)
            
            # Process request
            response = await call_next(request)
            
            # Post-request processing
            response = await self._post_request_processing(request, response)
            
            # Update metrics
            self._update_metrics(request, response, time.time() - start_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            self.metrics['security_violations'] += 1
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal security error"}
            )
    
    async def _pre_request_security_check(self, request: Request) -> Dict[str, Any]:
        """Perform pre-request security checks"""
        
        # Check request size
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_request_size:
            return {
                'allowed': False,
                'reason': 'request_too_large',
                'message': f'Request size exceeds maximum allowed ({self.max_request_size} bytes)'
            }
        
        # Check for suspicious patterns in URL
        url_path = str(request.url.path)
        for pattern in self.blocked_patterns:
            if re.search(pattern, url_path, re.IGNORECASE):
                logger.warning(f"Blocked suspicious URL pattern: {url_path}")
                self.metrics['blocked_requests'] += 1
                return {
                    'allowed': False,
                    'reason': 'suspicious_pattern',
                    'message': 'Request contains suspicious patterns'
                }
        
        # Check User-Agent
        user_agent = request.headers.get('user-agent', '')
        if self._is_suspicious_user_agent(user_agent):
            logger.warning(f"Blocked suspicious User-Agent: {user_agent}")
            self.metrics['blocked_requests'] += 1
            return {
                'allowed': False,
                'reason': 'suspicious_user_agent',
                'message': 'Suspicious user agent detected'
            }
        
        # Check for common attack patterns in headers
        for header_name, header_value in request.headers.items():
            if self._contains_attack_patterns(header_value):
                logger.warning(f"Attack pattern detected in header {header_name}: {header_value}")
                self.metrics['security_violations'] += 1
                return {
                    'allowed': False,
                    'reason': 'attack_pattern',
                    'message': 'Malicious content detected'
                }
        
        return {'allowed': True}
    
    async def _check_rate_limits(self, request: Request) -> Dict[str, Any]:
        """Check rate limits for the request"""
        
        # Determine which rate limit rule to apply
        rule_name = self._get_rate_limit_rule(request)
        if not rule_name:
            return {'allowed': True}
        
        # Extract user information
        user_id = self._extract_user_id(request)
        user_role = self._extract_user_role(request)
        
        # Check rate limit
        result = await self.rate_limiter.check_rate_limit(
            request, rule_name, user_id, user_role
        )
        
        if not result['allowed']:
            self.metrics['rate_limited_requests'] += 1
            logger.warning(f"Rate limit exceeded for {user_id or 'anonymous'} on {rule_name}")
        
        return result
    
    async def _validate_request_content(self, request: Request) -> Dict[str, Any]:
        """Validate request content"""
        
        # Skip validation for certain content types
        content_type = request.headers.get('content-type', '')
        if content_type.startswith('multipart/form-data'):
            return {'valid': True}  # File uploads handled separately
        
        try:
            # Read request body if present
            if request.method in ['POST', 'PUT', 'PATCH']:
                body = await request.body()
                
                if body:
                    # Check body size
                    if len(body) > self.max_request_size:
                        return {
                            'valid': False,
                            'reason': 'body_too_large',
                            'message': f'Request body exceeds maximum size ({self.max_request_size} bytes)'
                        }
                    
                    # Parse and validate JSON content
                    if content_type.startswith('application/json'):
                        try:
                            data = json.loads(body.decode('utf-8'))
                            validation_result = await self._validate_json_content(data, request)
                            if not validation_result['valid']:
                                return validation_result
                        except json.JSONDecodeError:
                            return {
                                'valid': False,
                                'reason': 'invalid_json',
                                'message': 'Invalid JSON format'
                            }
                    
                    # Check for malicious patterns in body
                    body_str = body.decode('utf-8', errors='ignore')
                    if self._contains_attack_patterns(body_str):
                        return {
                            'valid': False,
                            'reason': 'malicious_content',
                            'message': 'Malicious content detected in request body'
                        }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            return {
                'valid': False,
                'reason': 'validation_error',
                'message': 'Content validation failed'
            }
    
    async def _validate_json_content(self, data: Dict[str, Any], request: Request) -> Dict[str, Any]:
        """Validate JSON content based on endpoint"""
        
        path = request.url.path
        
        # Validate query content
        if '/counsel/query' in path:
            query = data.get('query', '')
            if len(query) > self.max_query_length:
                return {
                    'valid': False,
                    'reason': 'query_too_long',
                    'message': f'Query exceeds maximum length ({self.max_query_length} characters)'
                }
            
            if self._contains_attack_patterns(query):
                return {
                    'valid': False,
                    'reason': 'malicious_query',
                    'message': 'Query contains suspicious patterns'
                }
        
        # Validate document generation parameters
        elif '/counsel/generate-document' in path:
            doc_type = data.get('document_type', '')
            if not doc_type or not isinstance(doc_type, str):
                return {
                    'valid': False,
                    'reason': 'invalid_document_type',
                    'message': 'Valid document type is required'
                }
            
            # Check for valid document types
            valid_doc_types = [
                'contract', 'agreement', 'notice', 'petition', 
                'affidavit', 'memorandum', 'will', 'power_of_attorney'
            ]
            if doc_type not in valid_doc_types:
                return {
                    'valid': False,
                    'reason': 'unsupported_document_type',
                    'message': f'Document type must be one of: {", ".join(valid_doc_types)}'
                }
        
        return {'valid': True}
    
    async def _post_request_processing(self, request: Request, response: Response) -> Response:
        """Post-request processing"""
        
        # Add security headers
        if self.enable_security_headers:
            self._add_security_headers(response)
        
        # Log request if enabled
        if self.enable_request_logging:
            await self._log_request(request, response)
        
        return response
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""

        # Content Security Policy - Allow Swagger UI CDN resources
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https: data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        # Other security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (only for HTTPS)
        if hasattr(response, 'url') and str(response.url).startswith('https'):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    async def _log_request(self, request: Request, response: Response):
        """Log request details"""
        
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'method': request.method,
            'path': request.url.path,
            'status_code': response.status_code,
            'user_agent': request.headers.get('user-agent', ''),
            'client_ip': self._get_client_ip(request),
            'user_id': self._extract_user_id(request)
        }
        
        # Log based on status code
        if response.status_code >= 400:
            logger.warning(f"HTTP {response.status_code}: {json.dumps(log_data)}")
        else:
            logger.info(f"Request: {json.dumps(log_data)}")
    
    def _get_rate_limit_rule(self, request: Request) -> Optional[str]:
        """Determine which rate limit rule applies to the request"""
        
        path = request.url.path
        
        for path_pattern, rule_name in self.rate_limit_rules.items():
            if path_pattern in path:
                return rule_name
        
        # Default rule for all other endpoints
        return 'general_api'
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request"""
        
        # Try to get from JWT token
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            try:
                # This would normally decode the JWT token
                # For now, return a placeholder
                return "user_from_token"
            except Exception:
                pass
        
        # Fallback to session or other methods
        return None
    
    def _extract_user_role(self, request: Request) -> Optional[str]:
        """Extract user role from request"""
        
        # Similar to user ID extraction
        # This would normally come from the JWT token or user session
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        
        # Check forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        
        suspicious_patterns = [
            r'bot',
            r'crawler',
            r'spider',
            r'scraper',
            r'curl',
            r'wget',
            r'python-requests',
            r'sqlmap',
            r'nikto',
            r'nmap'
        ]
        
        # Allow legitimate bots and browsers
        allowed_patterns = [
            'googlebot',
            'bingbot',
            'slurp',
            'mozilla',  # Most browsers include Mozilla in User-Agent
            'chrome',
            'firefox',
            'safari',
            'edge',
            'opera',
            'elb-healthchecker'  # AWS Load Balancer health checks
        ]
        
        user_agent_lower = user_agent.lower()
        
        # Check if it's an allowed pattern (bots or browsers)
        for allowed in allowed_patterns:
            if allowed in user_agent_lower:
                return False
        
        # Check for suspicious patterns
        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent_lower):
                return True
        
        return False
    
    def _contains_attack_patterns(self, content: str) -> bool:
        """Check if content contains attack patterns"""
        
        content_lower = content.lower()
        
        # SQL injection patterns
        sql_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'insert\s+into',
            r'delete\s+from',
            r'update\s+.*\s+set',
            r'exec\s*\(',
            r'sp_executesql'
        ]
        
        # XSS patterns
        xss_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*='
        ]
        
        # Command injection patterns
        cmd_patterns = [
            r';\s*rm\s+',
            r';\s*cat\s+',
            r';\s*ls\s+',
            r';\s*pwd',
            r'\|\s*nc\s+',
            r'&&\s*rm\s+'
        ]
        
        all_patterns = sql_patterns + xss_patterns + cmd_patterns
        
        for pattern in all_patterns:
            if re.search(pattern, content_lower):
                return True
        
        return False
    
    def _create_security_response(self, security_check: Dict[str, Any]) -> JSONResponse:
        """Create security violation response"""
        
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "Security violation",
                "message": security_check.get('message', 'Request blocked for security reasons'),
                "reason": security_check.get('reason', 'security_violation')
            }
        )
    
    def _create_validation_response(self, validation_result: Dict[str, Any]) -> JSONResponse:
        """Create validation error response"""
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation failed",
                "message": validation_result.get('message', 'Request validation failed'),
                "reason": validation_result.get('reason', 'validation_error')
            }
        )
    
    def _update_metrics(self, request: Request, response: Response, response_time: float):
        """Update middleware metrics"""
        
        self.metrics['total_requests'] += 1
        
        # Update average response time
        total = self.metrics['total_requests']
        current_avg = self.metrics['avg_response_time']
        self.metrics['avg_response_time'] = (
            (current_avg * (total - 1) + response_time) / total
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get middleware metrics"""
        
        return {
            **self.metrics,
            'rate_limiter_metrics': self.rate_limiter.get_metrics() if self.rate_limiter else {}
        }
