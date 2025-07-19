"""
INTELLIGENT RESPONSE CACHE SERVICE
=================================
High-performance caching system for legal queries with semantic similarity matching.
Designed for sub-500ms response times on common legal questions.
"""

import json
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import OrderedDict
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cached response entry with metadata"""
    query: str
    response: Dict[str, Any]
    embedding: Optional[List[float]]
    timestamp: datetime
    access_count: int
    last_accessed: datetime
    confidence: float
    model_used: str
    processing_time_ms: float
    legal_area: Optional[str] = None
    query_type: Optional[str] = None

@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_response_time_ms: float = 0.0
    cache_size: int = 0
    hit_rate: float = 0.0

class IntelligentCacheService:
    """
    Intelligent caching service with semantic similarity matching
    for Kenyan legal queries
    """
    
    def __init__(self, max_cache_size: int = 5000, similarity_threshold: float = 0.75):  # Reduced size
        self.max_cache_size = max_cache_size
        self.similarity_threshold = similarity_threshold

        # In-memory cache with LRU eviction
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.embedding_cache: Dict[str, List[float]] = {}

        # Performance tracking
        self.stats = CacheStats()

        # Cache invalidation settings
        self.max_age_hours = 24  # Cache entries expire after 24 hours
        self.legal_area_versions: Dict[str, int] = {}  # Track legal area updates
        
        # Kenyan legal keywords for fast matching
        self.legal_keywords = {
            'employment': ['employment', 'job', 'work', 'salary', 'wage', 'termination', 'contract'],
            'company': ['company', 'business', 'registration', 'director', 'shareholder'],
            'land': ['land', 'property', 'title', 'ownership', 'transfer'],
            'family': ['marriage', 'divorce', 'custody', 'maintenance', 'family'],
            'constitutional': ['constitution', 'rights', 'freedom', 'bill of rights']
        }
        
        self._initialized = False
        
    async def initialize(self):
        """Initialize the cache service"""
        if self._initialized:
            return
            
        try:
            # Pre-populate with common Kenyan legal queries
            await self._preload_common_queries()
            self._initialized = True
            logger.info(f"Intelligent cache service initialized with {len(self.cache)} entries")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache service: {e}")
            self._initialized = True  # Continue without preloading
    
    async def get_cached_response(
        self, 
        query: str, 
        query_embedding: Optional[List[float]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response for query with semantic similarity matching
        
        Args:
            query: The user query
            query_embedding: Pre-computed embedding (optional)
            
        Returns:
            Cached response if found, None otherwise
        """
        start_time = time.time()
        self.stats.total_requests += 1
        
        try:
            # Fast exact match first
            query_hash = self._hash_query(query)
            if query_hash in self.cache:
                entry = self.cache[query_hash]
                entry.access_count += 1
                entry.last_accessed = datetime.utcnow()
                
                # Move to end (LRU)
                self.cache.move_to_end(query_hash)
                
                self.stats.cache_hits += 1
                self._update_hit_rate()
                
                logger.info(f"Cache HIT (exact): {query[:50]}... ({time.time() - start_time:.3f}s)")
                return self._format_cached_response(entry)
            
            # Semantic similarity search for near matches
            if query_embedding or len(self.cache) > 0:
                similar_entry = await self._find_similar_cached_query(query, query_embedding)
                if similar_entry:
                    similar_entry.access_count += 1
                    similar_entry.last_accessed = datetime.utcnow()
                    
                    self.stats.cache_hits += 1
                    self._update_hit_rate()
                    
                    logger.info(f"Cache HIT (semantic): {query[:50]}... ({time.time() - start_time:.3f}s)")
                    return self._format_cached_response(similar_entry)
            
            # Cache miss
            self.stats.cache_misses += 1
            self._update_hit_rate()
            
            logger.debug(f"Cache MISS: {query[:50]}... ({time.time() - start_time:.3f}s)")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None
    
    async def cache_response(
        self,
        query: str,
        response: Dict[str, Any],
        query_embedding: Optional[List[float]] = None,
        legal_area: Optional[str] = None,
        force_cache: bool = False
    ) -> bool:
        """
        Enhanced cache response with improved logic

        Args:
            query: The original query
            response: The response to cache
            query_embedding: Query embedding for similarity matching
            legal_area: Legal area classification
            force_cache: Force caching regardless of confidence

        Returns:
            True if cached successfully
        """
        try:
            # Normalize query for better matching
            normalized_query = self._normalize_query(query)

            # Enhanced confidence calculation
            confidence = self._calculate_enhanced_confidence(response)

            # Cache if confidence is good or forced
            if confidence >= 0.6 or force_cache:
                # Create cache entry
                entry = CacheEntry(
                    query=normalized_query,
                    response=response,
                    embedding=query_embedding,
                    timestamp=datetime.utcnow(),
                    access_count=1,
                    last_accessed=datetime.utcnow(),
                    confidence=confidence,
                    model_used=response.get('model_used', 'unknown'),
                    processing_time_ms=response.get('processing_time', 0.0),
                    legal_area=legal_area or self._classify_legal_area(normalized_query),
                    query_type=response.get('query_type', 'legal_query')
                )

                # Add to cache
                query_hash = self._hash_query(normalized_query)
                self.cache[query_hash] = entry

                # Store embedding separately for faster similarity search
                if query_embedding:
                    self.embedding_cache[query_hash] = query_embedding

                # Enforce cache size limit
                await self._enforce_cache_limit()

                logger.debug(f"Cached response for: {normalized_query[:50]}... (confidence: {confidence})")
                return True
            else:
                logger.debug(f"Skipped caching due to low confidence: {confidence}")
                return False

        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False

    def _normalize_query(self, query: str) -> str:
        """Normalize query for better cache matching"""
        import re

        # Convert to lowercase
        normalized = query.lower().strip()

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)

        # Remove common variations (less aggressive)
        normalized = re.sub(r'\b(please|kindly)\b', '', normalized)

        # Normalize question words
        normalized = re.sub(r'\bwhat are\b', 'what is', normalized)
        normalized = re.sub(r'\bhow do i\b', 'how to', normalized)

        # Remove punctuation except important legal punctuation
        normalized = re.sub(r'[^\w\s\-\(\)]', '', normalized)

        # Remove extra spaces again
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def _calculate_enhanced_confidence(self, response: Dict[str, Any]) -> float:
        """Calculate enhanced confidence score"""
        base_confidence = response.get('confidence', 0.8)

        # Boost confidence for successful responses
        if response.get('success', False):
            base_confidence += 0.1

        # Boost confidence for responses with legal citations
        response_text = response.get('response_text', '') or response.get('answer', '')
        if any(term in response_text.lower() for term in ['act', 'section', 'article', 'constitution']):
            base_confidence += 0.1

        # Boost confidence for longer, detailed responses
        if len(response_text) > 500:
            base_confidence += 0.05

        return min(base_confidence, 0.95)

    async def invalidate_cache_by_legal_area(self, legal_area: str):
        """Invalidate cache entries for a specific legal area"""
        try:
            invalidated_count = 0
            keys_to_remove = []

            for key, entry in self.cache.items():
                if entry.legal_area == legal_area:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                self.cache.pop(key, None)
                self.embedding_cache.pop(key, None)
                invalidated_count += 1

            # Update version for this legal area
            self.legal_area_versions[legal_area] = self.legal_area_versions.get(legal_area, 0) + 1

            logger.info(f"Invalidated {invalidated_count} cache entries for legal area: {legal_area}")
            return invalidated_count

        except Exception as e:
            logger.error(f"Error invalidating cache for legal area {legal_area}: {e}")
            return 0

    async def cleanup_expired_entries(self):
        """Remove expired cache entries"""
        try:
            from datetime import datetime, timedelta

            cutoff_time = datetime.utcnow() - timedelta(hours=self.max_age_hours)
            expired_keys = []

            for key, entry in self.cache.items():
                if entry.timestamp < cutoff_time:
                    expired_keys.append(key)

            for key in expired_keys:
                self.cache.pop(key, None)
                self.embedding_cache.pop(key, None)

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

        except Exception as e:
            logger.error(f"Error cleaning up expired entries: {e}")
            return 0

    def _is_entry_valid(self, entry: CacheEntry) -> bool:
        """Check if cache entry is still valid"""
        from datetime import datetime, timedelta

        # Check age
        if entry.timestamp < datetime.utcnow() - timedelta(hours=self.max_age_hours):
            return False

        # Check legal area version (if we track updates)
        if entry.legal_area in self.legal_area_versions:
            # Entry is invalid if it was created before the last legal area update
            # This is a simplified version - in production you'd have more sophisticated versioning
            pass

        return True
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        self.stats.cache_size = len(self.cache)
        return asdict(self.stats)
    
    def clear_cache(self) -> bool:
        """Clear all cached entries"""
        try:
            self.cache.clear()
            self.embedding_cache.clear()
            self.stats = CacheStats()
            logger.info("Cache cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query"""
        normalized_query = query.lower().strip()
        return hashlib.md5(normalized_query.encode()).hexdigest()
    
    def _classify_legal_area(self, query: str) -> str:
        """Classify query into legal area"""
        query_lower = query.lower()
        
        for area, keywords in self.legal_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return area
        
        return 'general'
    
    def _update_hit_rate(self):
        """Update cache hit rate"""
        if self.stats.total_requests > 0:
            self.stats.hit_rate = self.stats.cache_hits / self.stats.total_requests
    
    def _format_cached_response(self, entry: CacheEntry) -> Dict[str, Any]:
        """Format cached entry as response"""
        response = entry.response.copy()
        response['cached'] = True
        response['cache_timestamp'] = entry.timestamp.isoformat()
        response['cache_access_count'] = entry.access_count
        return response

    async def _find_similar_cached_query(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None
    ) -> Optional[CacheEntry]:
        """Find semantically similar cached query"""
        try:
            if not query_embedding:
                # Generate embedding for similarity search
                from app.services.aws_embedding_service import aws_embedding_service
                query_embedding = await aws_embedding_service.generate_embeddings(query)

            if not query_embedding:
                return None

            best_similarity = 0.0
            best_entry = None

            # Search through cached embeddings
            for query_hash, cached_embedding in self.embedding_cache.items():
                if query_hash in self.cache:
                    similarity = self._cosine_similarity(query_embedding, cached_embedding)

                    if similarity > best_similarity and similarity >= self.similarity_threshold:
                        best_similarity = similarity
                        best_entry = self.cache[query_hash]

            return best_entry

        except Exception as e:
            logger.error(f"Error finding similar cached query: {e}")
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            if len(vec1) != len(vec2):
                return 0.0

            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(a * a for a in vec2) ** 0.5

            if magnitude1 == 0.0 or magnitude2 == 0.0:
                return 0.0

            return dot_product / (magnitude1 * magnitude2)

        except Exception:
            return 0.0

    async def _enforce_cache_limit(self):
        """Enforce cache size limit with LRU eviction"""
        while len(self.cache) > self.max_cache_size:
            # Remove oldest entry (FIFO from OrderedDict)
            oldest_key, oldest_entry = self.cache.popitem(last=False)

            # Also remove from embedding cache
            if oldest_key in self.embedding_cache:
                del self.embedding_cache[oldest_key]

            logger.debug(f"Evicted cache entry: {oldest_entry.query[:50]}...")

    async def _preload_common_queries(self):
        """Pre-populate cache with common Kenyan legal queries"""
        common_queries = [
            {
                "query": "What are the basic employment rights in Kenya?",
                "response": {
                    "answer": "Under the Employment Act 2007 and Labour Relations Act 2007, employees in Kenya have rights to: minimum wage (KES 15,201/month), maximum 52 hours work week, 21 days annual leave, 3 months maternity leave, 2 weeks paternity leave, proper termination procedures with notice, and safe working conditions under OSHA 2007.",
                    "confidence": 0.95,
                    "model_used": "preloaded",
                    "processing_time": 0.0,
                    "success": True,
                    "legal_area": "employment"
                }
            },
            {
                "query": "How to register a company in Kenya?",
                "response": {
                    "answer": "To register a company in Kenya under the Companies Act 2015: 1) Reserve company name (KES 1,000), 2) Prepare incorporation documents (Memorandum & Articles), 3) Submit to Registrar of Companies, 4) Pay registration fees (KES 10,000-20,000), 5) Obtain certificate of incorporation. Process takes 7-14 days. Register for PIN and VAT separately.",
                    "confidence": 0.95,
                    "model_used": "preloaded",
                    "processing_time": 0.0,
                    "success": True,
                    "legal_area": "company"
                }
            },
            {
                "query": "What are constitutional rights in Kenya?",
                "response": {
                    "answer": "The Constitution of Kenya 2010 guarantees fundamental rights under Chapter 4 (Articles 19-59): right to life (Article 26), freedom of expression (Article 33), freedom of association (Article 36), right to education (Article 43), right to healthcare (Article 43), right to housing (Article 43), equality and non-discrimination (Article 27), and access to justice (Article 48).",
                    "confidence": 0.95,
                    "model_used": "preloaded",
                    "processing_time": 0.0,
                    "success": True,
                    "legal_area": "constitutional"
                }
            },
            {
                "query": "What is the minimum wage in Kenya?",
                "response": {
                    "answer": "As of 2024, the minimum wage in Kenya is KES 15,201 per month for general workers. Agricultural workers have a minimum wage of KES 13,572 per month. These rates are set by the Ministry of Labour and reviewed annually. Employers must also provide statutory deductions for NSSF, NHIF, and PAYE tax.",
                    "confidence": 0.95,
                    "model_used": "preloaded",
                    "processing_time": 0.0,
                    "success": True,
                    "legal_area": "employment"
                }
            },
            {
                "query": "How to terminate an employee in Kenya?",
                "response": {
                    "answer": "Under Employment Act 2007, employee termination requires: 1) Valid reason (misconduct, redundancy, poor performance), 2) Proper notice period (28 days for monthly paid, 7 days for others), 3) Due process including disciplinary hearing for misconduct, 4) Severance pay (15 days per year of service for redundancy), 5) Final settlement including accrued leave and benefits.",
                    "confidence": 0.95,
                    "model_used": "preloaded",
                    "processing_time": 0.0,
                    "success": True,
                    "legal_area": "employment"
                }
            }
        ]

        for item in common_queries:
            await self.cache_response(
                query=item["query"],
                response=item["response"],
                legal_area=item["response"]["legal_area"],
                force_cache=True  # Force cache preloaded queries
            )

    async def warm_cache_from_analytics(self, top_queries: int = 20):
        """Warm cache with popular queries from analytics"""
        try:
            # This would typically fetch from analytics service
            # For now, we'll use common legal query patterns
            popular_patterns = [
                "employment contract requirements",
                "company registration process",
                "land ownership rights",
                "marriage and divorce laws",
                "data protection compliance",
                "tax obligations for businesses",
                "intellectual property protection",
                "consumer rights in Kenya",
                "criminal law procedures",
                "court filing procedures"
            ]

            logger.info(f"Cache warming initiated for {len(popular_patterns)} query patterns")

            # In production, this would trigger background LLM calls
            # to pre-generate responses for popular queries

        except Exception as e:
            logger.error(f"Error warming cache: {e}")

    def get_cache_analytics(self) -> Dict[str, Any]:
        """Get detailed cache performance analytics"""
        try:
            # Calculate advanced metrics
            total_requests = self.stats.total_requests
            cache_hits = self.stats.cache_hits
            cache_misses = self.stats.cache_misses

            # Hit rate by legal area
            area_stats = {}
            for entry in self.cache.values():
                area = entry.legal_area or 'unknown'
                if area not in area_stats:
                    area_stats[area] = {'hits': 0, 'total': 0}
                area_stats[area]['total'] += entry.access_count
                if entry.access_count > 1:
                    area_stats[area]['hits'] += entry.access_count - 1

            # Calculate hit rates by area
            for area in area_stats:
                total = area_stats[area]['total']
                area_stats[area]['hit_rate'] = area_stats[area]['hits'] / total if total > 0 else 0

            # Memory usage estimation
            memory_usage_mb = sum(
                len(str(entry.query)) + len(str(entry.response)) +
                (len(entry.embedding) * 4 if entry.embedding else 0)
                for entry in self.cache.values()
            ) / (1024 * 1024)

            return {
                "basic_stats": asdict(self.stats),
                "cache_size": len(self.cache),
                "hit_rate_percentage": round(self.stats.hit_rate * 100, 2),
                "memory_usage_mb": round(memory_usage_mb, 2),
                "area_performance": area_stats,
                "top_queries": [
                    {
                        "query": entry.query[:100] + "..." if len(entry.query) > 100 else entry.query,
                        "access_count": entry.access_count,
                        "legal_area": entry.legal_area,
                        "confidence": entry.confidence
                    }
                    for entry in sorted(self.cache.values(), key=lambda x: x.access_count, reverse=True)[:10]
                ],
                "cache_efficiency": {
                    "avg_confidence": sum(e.confidence for e in self.cache.values()) / len(self.cache) if self.cache else 0,
                    "avg_processing_time": sum(e.processing_time_ms for e in self.cache.values()) / len(self.cache) if self.cache else 0,
                    "embedding_coverage": len(self.embedding_cache) / len(self.cache) if self.cache else 0
                }
            }

        except Exception as e:
            logger.error(f"Error generating cache analytics: {e}")
            return {"error": str(e)}

    async def invalidate_expired_entries(self, max_age_hours: int = 24):
        """Remove expired cache entries"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            expired_keys = []

            for key, entry in self.cache.items():
                if entry.timestamp < cutoff_time:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]
                if key in self.embedding_cache:
                    del self.embedding_cache[key]

            if expired_keys:
                logger.info(f"Invalidated {len(expired_keys)} expired cache entries")

        except Exception as e:
            logger.error(f"Error invalidating expired entries: {e}")

    async def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular cached queries"""
        try:
            sorted_entries = sorted(
                self.cache.values(),
                key=lambda x: x.access_count,
                reverse=True
            )

            return [
                {
                    "query": entry.query,
                    "access_count": entry.access_count,
                    "legal_area": entry.legal_area,
                    "confidence": entry.confidence
                }
                for entry in sorted_entries[:limit]
            ]

        except Exception as e:
            logger.error(f"Error getting popular queries: {e}")
            return []

# Global cache service instance
intelligent_cache_service = IntelligentCacheService()
