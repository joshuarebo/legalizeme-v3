"""
Advanced Performance Optimization & Caching System
Comprehensive caching strategies, database optimization, and performance enhancements.
"""

import asyncio
import json
import logging
import time
import hashlib
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass, asdict
import pickle
import sqlite3
from pathlib import Path
import threading
from collections import OrderedDict, defaultdict

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry structure"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int
    last_accessed: datetime
    size_bytes: int
    cache_type: str

@dataclass
class PerformanceMetrics:
    """Performance metrics structure"""
    operation: str
    execution_time: float
    cache_hit: bool
    memory_usage: float
    cpu_usage: float
    timestamp: datetime

class AdvancedCache:
    """Advanced multi-level caching system"""
    
    def __init__(self, max_memory_mb: int = 512, max_disk_mb: int = 2048):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.max_disk_bytes = max_disk_mb * 1024 * 1024
        
        # Memory cache (LRU)
        self.memory_cache = OrderedDict()
        self.memory_usage = 0
        
        # Disk cache
        self.disk_cache_path = Path("cache_storage")
        self.disk_cache_path.mkdir(exist_ok=True)
        self.disk_cache_index = {}
        
        # Cache statistics
        self.stats = {
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
        
        # Performance metrics
        self.performance_metrics = []
        
        # Cache locks
        self.memory_lock = threading.RLock()
        self.disk_lock = threading.RLock()
        
        # Load disk cache index
        self._load_disk_cache_index()
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    def _load_disk_cache_index(self):
        """Load disk cache index from file"""
        try:
            index_file = self.disk_cache_path / "cache_index.json"
            if index_file.exists():
                with open(index_file, 'r') as f:
                    index_data = json.load(f)
                    
                for key, data in index_data.items():
                    self.disk_cache_index[key] = CacheEntry(
                        key=data['key'],
                        value=None,  # Value loaded on demand
                        created_at=datetime.fromisoformat(data['created_at']),
                        expires_at=datetime.fromisoformat(data['expires_at']) if data['expires_at'] else None,
                        access_count=data['access_count'],
                        last_accessed=datetime.fromisoformat(data['last_accessed']),
                        size_bytes=data['size_bytes'],
                        cache_type=data['cache_type']
                    )
                    
                logger.info(f"Loaded {len(self.disk_cache_index)} disk cache entries")
                
        except Exception as e:
            logger.error(f"Error loading disk cache index: {e}")
    
    def _save_disk_cache_index(self):
        """Save disk cache index to file"""
        try:
            index_file = self.disk_cache_path / "cache_index.json"
            index_data = {}
            
            for key, entry in self.disk_cache_index.items():
                index_data[key] = {
                    'key': entry.key,
                    'created_at': entry.created_at.isoformat(),
                    'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
                    'access_count': entry.access_count,
                    'last_accessed': entry.last_accessed.isoformat(),
                    'size_bytes': entry.size_bytes,
                    'cache_type': entry.cache_type
                }
            
            with open(index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving disk cache index: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (memory first, then disk)"""
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        try:
            # Check memory cache first
            with self.memory_lock:
                if key in self.memory_cache:
                    entry = self.memory_cache[key]
                    
                    # Check expiration
                    if entry.expires_at and datetime.utcnow() > entry.expires_at:
                        del self.memory_cache[key]
                        self.memory_usage -= entry.size_bytes
                    else:
                        # Move to end (LRU)
                        self.memory_cache.move_to_end(key)
                        entry.access_count += 1
                        entry.last_accessed = datetime.utcnow()
                        
                        self.stats['memory_hits'] += 1
                        self._record_performance_metric('cache_get', time.time() - start_time, True)
                        return entry.value
            
            # Check disk cache
            with self.disk_lock:
                if key in self.disk_cache_index:
                    entry = self.disk_cache_index[key]
                    
                    # Check expiration
                    if entry.expires_at and datetime.utcnow() > entry.expires_at:
                        self._remove_from_disk_cache(key)
                    else:
                        # Load value from disk
                        cache_file = self.disk_cache_path / f"{key}.cache"
                        if cache_file.exists():
                            with open(cache_file, 'rb') as f:
                                value = pickle.load(f)
                            
                            entry.access_count += 1
                            entry.last_accessed = datetime.utcnow()
                            
                            # Promote to memory cache if frequently accessed
                            if entry.access_count > 5:
                                await self._promote_to_memory(key, value, entry)
                            
                            self.stats['disk_hits'] += 1
                            self._record_performance_metric('cache_get', time.time() - start_time, True)
                            return value
            
            # Cache miss
            self.stats['misses'] += 1
            self._record_performance_metric('cache_get', time.time() - start_time, False)
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, 
                  cache_type: str = "general") -> bool:
        """Set value in cache"""
        try:
            # Calculate size
            size_bytes = len(pickle.dumps(value))
            
            # Create cache entry
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                access_count=1,
                last_accessed=datetime.utcnow(),
                size_bytes=size_bytes,
                cache_type=cache_type
            )
            
            # Try memory cache first
            if size_bytes <= self.max_memory_bytes // 10:  # Max 10% of memory for single item
                await self._set_memory_cache(key, entry)
                return True
            
            # Use disk cache for larger items
            await self._set_disk_cache(key, entry)
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def _set_memory_cache(self, key: str, entry: CacheEntry):
        """Set value in memory cache"""
        with self.memory_lock:
            # Remove existing entry if present
            if key in self.memory_cache:
                old_entry = self.memory_cache[key]
                self.memory_usage -= old_entry.size_bytes
                del self.memory_cache[key]
            
            # Ensure we have space
            while (self.memory_usage + entry.size_bytes > self.max_memory_bytes and 
                   self.memory_cache):
                # Evict least recently used
                oldest_key, oldest_entry = self.memory_cache.popitem(last=False)
                self.memory_usage -= oldest_entry.size_bytes
                self.stats['evictions'] += 1
                
                # Move to disk cache if valuable
                if oldest_entry.access_count > 3:
                    await self._set_disk_cache(oldest_key, oldest_entry)
            
            # Add new entry
            self.memory_cache[key] = entry
            self.memory_usage += entry.size_bytes
    
    async def _set_disk_cache(self, key: str, entry: CacheEntry):
        """Set value in disk cache"""
        with self.disk_lock:
            try:
                # Save value to disk
                cache_file = self.disk_cache_path / f"{key}.cache"
                with open(cache_file, 'wb') as f:
                    pickle.dump(entry.value, f)
                
                # Update index
                self.disk_cache_index[key] = entry
                
                # Save index
                self._save_disk_cache_index()
                
            except Exception as e:
                logger.error(f"Error setting disk cache for {key}: {e}")
    
    async def _promote_to_memory(self, key: str, value: Any, entry: CacheEntry):
        """Promote frequently accessed disk cache item to memory"""
        if entry.size_bytes <= self.max_memory_bytes // 10:
            entry.value = value
            await self._set_memory_cache(key, entry)
            
            # Remove from disk cache
            self._remove_from_disk_cache(key)
    
    def _remove_from_disk_cache(self, key: str):
        """Remove entry from disk cache"""
        try:
            cache_file = self.disk_cache_path / f"{key}.cache"
            if cache_file.exists():
                cache_file.unlink()
            
            if key in self.disk_cache_index:
                del self.disk_cache_index[key]
                
        except Exception as e:
            logger.error(f"Error removing disk cache for {key}: {e}")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired cache entries"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                current_time = datetime.utcnow()
                
                # Clean memory cache
                with self.memory_lock:
                    expired_keys = []
                    for key, entry in self.memory_cache.items():
                        if entry.expires_at and current_time > entry.expires_at:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        entry = self.memory_cache[key]
                        self.memory_usage -= entry.size_bytes
                        del self.memory_cache[key]
                
                # Clean disk cache
                with self.disk_lock:
                    expired_keys = []
                    for key, entry in self.disk_cache_index.items():
                        if entry.expires_at and current_time > entry.expires_at:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        self._remove_from_disk_cache(key)
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    def _record_performance_metric(self, operation: str, execution_time: float, cache_hit: bool):
        """Record performance metric"""
        metric = PerformanceMetrics(
            operation=operation,
            execution_time=execution_time,
            cache_hit=cache_hit,
            memory_usage=self.memory_usage,
            cpu_usage=0.0,  # Would integrate with system monitoring
            timestamp=datetime.utcnow()
        )
        
        self.performance_metrics.append(metric)
        
        # Keep only last 1000 metrics
        if len(self.performance_metrics) > 1000:
            self.performance_metrics = self.performance_metrics[-1000:]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats['total_requests']
        
        return {
            'memory_cache': {
                'entries': len(self.memory_cache),
                'size_bytes': self.memory_usage,
                'size_mb': self.memory_usage / (1024 * 1024),
                'max_size_mb': self.max_memory_bytes / (1024 * 1024),
                'utilization': self.memory_usage / self.max_memory_bytes if self.max_memory_bytes > 0 else 0
            },
            'disk_cache': {
                'entries': len(self.disk_cache_index),
                'estimated_size_mb': sum(e.size_bytes for e in self.disk_cache_index.values()) / (1024 * 1024)
            },
            'performance': {
                'total_requests': total_requests,
                'memory_hits': self.stats['memory_hits'],
                'disk_hits': self.stats['disk_hits'],
                'misses': self.stats['misses'],
                'hit_rate': (self.stats['memory_hits'] + self.stats['disk_hits']) / total_requests if total_requests > 0 else 0,
                'memory_hit_rate': self.stats['memory_hits'] / total_requests if total_requests > 0 else 0,
                'evictions': self.stats['evictions']
            },
            'recent_metrics': [asdict(m) for m in self.performance_metrics[-10:]]
        }

class PerformanceOptimizer:
    """Main performance optimization service"""
    
    def __init__(self):
        self.cache = AdvancedCache()
        self.query_optimizer = DatabaseQueryOptimizer()
        self.ai_response_cache = AIResponseCache()
        
    async def optimize_ai_request(self, prompt: str, model: str, **kwargs) -> Any:
        """Optimize AI request with caching and performance monitoring"""
        # Create cache key
        cache_key = self._create_ai_cache_key(prompt, model, kwargs)
        
        # Check cache first
        cached_response = await self.cache.get(cache_key)
        if cached_response:
            return cached_response
        
        # If not cached, make request and cache result
        # This would integrate with actual AI service
        start_time = time.time()
        
        # Simulate AI request (replace with actual AI service call)
        response = await self._make_ai_request(prompt, model, **kwargs)
        
        execution_time = time.time() - start_time
        
        # Cache response with appropriate TTL
        ttl = self._calculate_ai_cache_ttl(prompt, execution_time)
        await self.cache.set(cache_key, response, ttl, "ai_response")
        
        return response
    
    def _create_ai_cache_key(self, prompt: str, model: str, kwargs: Dict) -> str:
        """Create cache key for AI request"""
        # Create deterministic hash of request parameters
        key_data = {
            'prompt': prompt,
            'model': model,
            'kwargs': sorted(kwargs.items())
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _calculate_ai_cache_ttl(self, prompt: str, execution_time: float) -> int:
        """Calculate appropriate TTL for AI response cache"""
        # Longer TTL for expensive requests
        base_ttl = 3600  # 1 hour
        
        if execution_time > 30:  # Expensive request
            return base_ttl * 4  # 4 hours
        elif execution_time > 10:
            return base_ttl * 2  # 2 hours
        else:
            return base_ttl  # 1 hour
    
    async def _make_ai_request(self, prompt: str, model: str, **kwargs) -> Any:
        """Make actual AI request (placeholder)"""
        # This would integrate with the actual AI service
        await asyncio.sleep(0.1)  # Simulate request time
        return {"response": "AI generated content", "model": model}

class DatabaseQueryOptimizer:
    """Database query optimization"""
    
    def __init__(self):
        self.query_cache = {}
        self.query_stats = defaultdict(list)
    
    def optimize_query(self, query: str, params: tuple = ()) -> str:
        """Optimize database query"""
        # Add query hints and optimizations
        optimized_query = query
        
        # Add indexes hints for common patterns
        if "WHERE" in query.upper() and "ORDER BY" in query.upper():
            # Suggest composite index
            pass
        
        return optimized_query

class AIResponseCache:
    """Specialized cache for AI responses"""
    
    def __init__(self):
        self.response_patterns = {}
        self.semantic_cache = {}
    
    async def get_similar_response(self, prompt: str) -> Optional[Any]:
        """Get semantically similar cached response"""
        # This would implement semantic similarity matching
        # For now, return None (no similar response found)
        return None

# Global instances
performance_optimizer = PerformanceOptimizer()
advanced_cache = performance_optimizer.cache
