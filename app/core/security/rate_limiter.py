"""
Advanced Rate Limiting System for Kenyan Legal AI
Provides flexible rate limiting with Redis backend and multiple strategies
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from datetime import datetime, timedelta

# Redis completely removed - using local cache only
HAS_REDIS = False
redis = None

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    ADAPTIVE = "adaptive"

@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    name: str
    requests: int
    window: int  # seconds
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_allowance: int = 0
    key_func: Optional[str] = None  # Function to generate rate limit key
    exempt_roles: List[str] = field(default_factory=list)
    custom_message: Optional[str] = None
    headers_include: bool = True

class RateLimiter:
    """Advanced rate limiter with multiple strategies"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.local_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.rules = {}

        # Redis completely removed - always use local cache
        logger.info("Rate limiter initialized with local cache (Redis removed)")

        # Default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default rate limiting rules"""
        
        # General API rate limit - PRODUCTION OPTIMIZED
        self.add_rule(RateLimitRule(
            name="general_api",
            requests=1000,  # Increased from 100
            window=3600,  # 1 hour
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            burst_allowance=50,  # Increased from 10
            custom_message="API rate limit exceeded. Please try again later."
        ))

        # AI query rate limit - PRODUCTION OPTIMIZED
        self.add_rule(RateLimitRule(
            name="ai_queries",
            requests=500,  # Increased from 50
            window=3600,  # 1 hour
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            burst_allowance=25,  # Increased from 5
            exempt_roles=["admin", "premium"],
            custom_message="AI query rate limit exceeded. Upgrade to premium for higher limits."
        ))

        # Document generation rate limit - PRODUCTION OPTIMIZED
        self.add_rule(RateLimitRule(
            name="document_generation",
            requests=100,  # Increased from 20
            window=3600,  # 1 hour
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            burst_allowance=10,  # Increased from 2
            exempt_roles=["admin", "premium"],
            custom_message="Document generation rate limit exceeded."
        ))
        
        # Model management rate limit (admin only)
        self.add_rule(RateLimitRule(
            name="model_management",
            requests=10,
            window=3600,  # 1 hour
            strategy=RateLimitStrategy.FIXED_WINDOW,
            exempt_roles=["admin"],
            custom_message="Model management operations are limited."
        ))
        
        # Authentication rate limit
        self.add_rule(RateLimitRule(
            name="auth_attempts",
            requests=5,
            window=900,  # 15 minutes
            strategy=RateLimitStrategy.FIXED_WINDOW,
            custom_message="Too many authentication attempts. Please try again later."
        ))
    
    def add_rule(self, rule: RateLimitRule):
        """Add a rate limiting rule"""
        self.rules[rule.name] = rule
        logger.info(f"Added rate limit rule: {rule.name} ({rule.requests}/{rule.window}s)")
    
    async def check_rate_limit(
        self, 
        request: Request, 
        rule_name: str,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if request is within rate limits"""
        
        if rule_name not in self.rules:
            logger.warning(f"Rate limit rule '{rule_name}' not found")
            return {"allowed": True, "remaining": float('inf')}
        
        rule = self.rules[rule_name]
        
        # Check if user is exempt
        if user_role and user_role in rule.exempt_roles:
            return {"allowed": True, "remaining": float('inf'), "exempt": True}
        
        # Generate rate limit key
        key = self._generate_key(request, rule, user_id, custom_key)
        
        # Apply rate limiting strategy
        if rule.strategy == RateLimitStrategy.FIXED_WINDOW:
            result = await self._fixed_window_check(key, rule)
        elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            result = await self._sliding_window_check(key, rule)
        elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            result = await self._token_bucket_check(key, rule)
        elif rule.strategy == RateLimitStrategy.ADAPTIVE:
            result = await self._adaptive_check(key, rule, request)
        else:
            result = await self._sliding_window_check(key, rule)  # Default
        
        # Add rule information to result
        result.update({
            "rule_name": rule_name,
            "window": rule.window,
            "strategy": rule.strategy.value
        })
        
        return result
    
    async def _fixed_window_check(self, key: str, rule: RateLimitRule) -> Dict[str, Any]:
        """Fixed window rate limiting"""
        current_time = int(time.time())
        window_start = (current_time // rule.window) * rule.window
        window_key = f"{key}:{window_start}"
        
        if self.redis_client:
            try:
                # Use Redis for distributed rate limiting
                pipe = self.redis_client.pipeline()
                pipe.incr(window_key)
                pipe.expire(window_key, rule.window)
                results = await pipe.execute()
                
                current_count = results[0]
                remaining = max(0, rule.requests - current_count)
                
                return {
                    "allowed": current_count <= rule.requests,
                    "remaining": remaining,
                    "reset_time": window_start + rule.window,
                    "current_count": current_count
                }
            
            except Exception as e:
                logger.error(f"Redis rate limit check failed: {e}")
                # Fall back to local cache
        
        # Local cache fallback
        if window_key not in self.local_cache:
            self.local_cache[window_key] = {"count": 0, "expires": window_start + rule.window}
        
        cache_entry = self.local_cache[window_key]
        
        # Clean expired entries
        if cache_entry["expires"] <= current_time:
            self.local_cache[window_key] = {"count": 0, "expires": window_start + rule.window}
            cache_entry = self.local_cache[window_key]
        
        cache_entry["count"] += 1
        remaining = max(0, rule.requests - cache_entry["count"])
        
        return {
            "allowed": cache_entry["count"] <= rule.requests,
            "remaining": remaining,
            "reset_time": cache_entry["expires"],
            "current_count": cache_entry["count"]
        }
    
    async def _sliding_window_check(self, key: str, rule: RateLimitRule) -> Dict[str, Any]:
        """Sliding window rate limiting"""
        current_time = time.time()
        window_start = current_time - rule.window
        
        if self.redis_client:
            try:
                # Use Redis sorted sets for sliding window
                pipe = self.redis_client.pipeline()
                
                # Remove old entries
                pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current entries
                pipe.zcard(key)
                
                # Add current request
                pipe.zadd(key, {str(current_time): current_time})
                
                # Set expiration
                pipe.expire(key, rule.window)
                
                results = await pipe.execute()
                current_count = results[1] + 1  # +1 for the current request
                
                remaining = max(0, rule.requests - current_count)
                
                return {
                    "allowed": current_count <= rule.requests,
                    "remaining": remaining,
                    "reset_time": current_time + rule.window,
                    "current_count": current_count
                }
            
            except Exception as e:
                logger.error(f"Redis sliding window check failed: {e}")
        
        # Local cache fallback (simplified)
        if key not in self.local_cache:
            self.local_cache[key] = {"requests": [], "last_cleanup": current_time}
        
        cache_entry = self.local_cache[key]
        
        # Clean old requests
        if current_time - cache_entry["last_cleanup"] > 60:  # Cleanup every minute
            cache_entry["requests"] = [
                req_time for req_time in cache_entry["requests"]
                if req_time > window_start
            ]
            cache_entry["last_cleanup"] = current_time
        
        # Add current request
        cache_entry["requests"].append(current_time)
        
        # Count requests in window
        current_count = len([
            req_time for req_time in cache_entry["requests"]
            if req_time > window_start
        ])
        
        remaining = max(0, rule.requests - current_count)
        
        return {
            "allowed": current_count <= rule.requests,
            "remaining": remaining,
            "reset_time": current_time + rule.window,
            "current_count": current_count
        }
    
    async def _token_bucket_check(self, key: str, rule: RateLimitRule) -> Dict[str, Any]:
        """Token bucket rate limiting"""
        current_time = time.time()
        
        if self.redis_client:
            try:
                # Get current bucket state
                bucket_data = await self.redis_client.hgetall(key)
                
                if bucket_data:
                    tokens = float(bucket_data.get("tokens", rule.requests))
                    last_refill = float(bucket_data.get("last_refill", current_time))
                else:
                    tokens = rule.requests
                    last_refill = current_time
                
                # Calculate tokens to add
                time_passed = current_time - last_refill
                tokens_to_add = time_passed * (rule.requests / rule.window)
                tokens = min(rule.requests, tokens + tokens_to_add)
                
                # Check if request can be served
                if tokens >= 1:
                    tokens -= 1
                    allowed = True
                else:
                    allowed = False
                
                # Update bucket state
                await self.redis_client.hset(key, mapping={
                    "tokens": str(tokens),
                    "last_refill": str(current_time)
                })
                await self.redis_client.expire(key, rule.window * 2)
                
                return {
                    "allowed": allowed,
                    "remaining": int(tokens),
                    "reset_time": current_time + (1 - tokens) * (rule.window / rule.requests),
                    "tokens": tokens
                }
            
            except Exception as e:
                logger.error(f"Redis token bucket check failed: {e}")
        
        # Local cache fallback
        if key not in self.local_cache:
            self.local_cache[key] = {
                "tokens": rule.requests,
                "last_refill": current_time
            }
        
        bucket = self.local_cache[key]
        
        # Refill tokens
        time_passed = current_time - bucket["last_refill"]
        tokens_to_add = time_passed * (rule.requests / rule.window)
        bucket["tokens"] = min(rule.requests, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = current_time
        
        # Check if request can be served
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            allowed = True
        else:
            allowed = False
        
        return {
            "allowed": allowed,
            "remaining": int(bucket["tokens"]),
            "reset_time": current_time + (1 - bucket["tokens"]) * (rule.window / rule.requests),
            "tokens": bucket["tokens"]
        }
    
    async def _adaptive_check(self, key: str, rule: RateLimitRule, request: Request) -> Dict[str, Any]:
        """Adaptive rate limiting based on system load"""
        # Get system metrics (simplified)
        system_load = await self._get_system_load()
        
        # Adjust rate limit based on load
        if system_load > 0.8:
            adjusted_requests = int(rule.requests * 0.5)  # Reduce by 50%
        elif system_load > 0.6:
            adjusted_requests = int(rule.requests * 0.7)  # Reduce by 30%
        else:
            adjusted_requests = rule.requests
        
        # Create temporary rule with adjusted limits
        adjusted_rule = RateLimitRule(
            name=f"{rule.name}_adaptive",
            requests=adjusted_requests,
            window=rule.window,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        
        result = await self._sliding_window_check(key, adjusted_rule)
        result["adaptive"] = True
        result["system_load"] = system_load
        result["original_limit"] = rule.requests
        result["adjusted_limit"] = adjusted_requests
        
        return result
    
    async def _get_system_load(self) -> float:
        """Get current system load (simplified)"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1) / 100.0
        except ImportError:
            return 0.5  # Default moderate load
    
    def _generate_key(
        self, 
        request: Request, 
        rule: RateLimitRule, 
        user_id: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> str:
        """Generate rate limiting key"""
        
        if custom_key:
            return f"rate_limit:{rule.name}:{custom_key}"
        
        if user_id:
            return f"rate_limit:{rule.name}:user:{user_id}"
        
        # Use IP address as fallback
        client_ip = self._get_client_ip(request)
        return f"rate_limit:{rule.name}:ip:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded headers (common in production)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def create_rate_limit_response(self, rule_name: str, result: Dict[str, Any]) -> JSONResponse:
        """Create rate limit exceeded response"""
        rule = self.rules.get(rule_name)
        message = rule.custom_message if rule else "Rate limit exceeded"
        
        headers = {}
        if rule and rule.headers_include:
            headers.update({
                "X-RateLimit-Limit": str(rule.requests),
                "X-RateLimit-Remaining": str(result.get("remaining", 0)),
                "X-RateLimit-Reset": str(int(result.get("reset_time", time.time()))),
                "X-RateLimit-Window": str(rule.window)
            })
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": message,
                "retry_after": int(result.get("reset_time", time.time()) - time.time())
            },
            headers=headers
        )
    
    async def cleanup_expired_entries(self):
        """Cleanup expired entries from local cache"""
        current_time = time.time()
        expired_keys = []
        
        for key, data in self.local_cache.items():
            if isinstance(data, dict):
                if "expires" in data and data["expires"] <= current_time:
                    expired_keys.append(key)
                elif "last_refill" in data and current_time - data["last_refill"] > 3600:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self.local_cache[key]
        
        logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit entries")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics"""
        return {
            "rules_count": len(self.rules),
            "cache_size": len(self.local_cache),
            "redis_available": self.redis_client is not None,
            "rules": {
                name: {
                    "requests": rule.requests,
                    "window": rule.window,
                    "strategy": rule.strategy.value
                }
                for name, rule in self.rules.items()
            }
        }
