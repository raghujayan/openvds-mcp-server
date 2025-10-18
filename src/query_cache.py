"""
Query Cache - In-memory caching for search results and facets

Provides fast access to frequently queried data without hitting Elasticsearch
"""

import time
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from collections import OrderedDict
import logging

logger = logging.getLogger("query-cache")


class LRUCache:
    """Simple LRU cache with TTL support"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self.hits = 0
        self.misses = 0

    def _make_key(self, **kwargs) -> str:
        """Create cache key from parameters"""
        # Sort dict for consistent hashing
        sorted_params = json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(sorted_params.encode()).hexdigest()

    def get(self, **kwargs) -> Optional[Any]:
        """Get value from cache"""
        key = self._make_key(**kwargs)

        # Check if key exists and not expired
        if key in self.cache:
            timestamp = self.timestamps.get(key, 0)
            age = time.time() - timestamp

            if age < self.ttl_seconds:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                logger.debug(f"Cache HIT: {key[:8]}... (age: {age:.1f}s)")
                return self.cache[key]
            else:
                # Expired, remove
                logger.debug(f"Cache EXPIRED: {key[:8]}... (age: {age:.1f}s)")
                del self.cache[key]
                del self.timestamps[key]

        self.misses += 1
        logger.debug(f"Cache MISS: {key[:8]}...")
        return None

    def set(self, value: Any, **kwargs):
        """Set value in cache"""
        key = self._make_key(**kwargs)

        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
            logger.debug(f"Cache EVICT: {oldest_key[:8]}...")

        self.cache[key] = value
        self.timestamps[key] = time.time()
        self.cache.move_to_end(key)
        logger.debug(f"Cache SET: {key[:8]}...")

    def invalidate_all(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.timestamps.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


class QueryCache:
    """Query cache for VDS search operations"""

    def __init__(self):
        # Search results cache (5 minutes TTL)
        self.search_cache = LRUCache(max_size=100, ttl_seconds=300)

        # Facets cache (longer TTL since data changes slowly)
        self.facets_cache = LRUCache(max_size=50, ttl_seconds=900)  # 15 min

        # Pre-computed facets (loaded once at startup)
        self.precomputed_facets: Optional[Dict[str, Any]] = None
        self.facets_timestamp: float = 0

    def get_search_results(
        self,
        search_query: Optional[str] = None,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None,
        max_results: int = 1000
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results"""
        return self.search_cache.get(
            search_query=search_query,
            filter_region=filter_region,
            filter_year=filter_year,
            max_results=max_results
        )

    def set_search_results(
        self,
        results: List[Dict[str, Any]],
        search_query: Optional[str] = None,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None,
        max_results: int = 1000
    ):
        """Cache search results"""
        self.search_cache.set(
            results,
            search_query=search_query,
            filter_region=filter_region,
            filter_year=filter_year,
            max_results=max_results
        )

    def get_facets(
        self,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached facets"""
        return self.facets_cache.get(
            filter_region=filter_region,
            filter_year=filter_year
        )

    def set_facets(
        self,
        facets: Dict[str, Any],
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None
    ):
        """Cache facets"""
        self.facets_cache.set(
            facets,
            filter_region=filter_region,
            filter_year=filter_year
        )

    def set_precomputed_facets(self, facets: Dict[str, Any]):
        """Set pre-computed facets (computed once at startup)"""
        self.precomputed_facets = facets
        self.facets_timestamp = time.time()
        logger.info("Pre-computed facets loaded")

    def get_precomputed_facets(self) -> Optional[Dict[str, Any]]:
        """Get pre-computed facets"""
        # Refresh if older than 1 hour
        if self.precomputed_facets and (time.time() - self.facets_timestamp) < 3600:
            return self.precomputed_facets
        return None

    def invalidate_all(self):
        """Clear all caches"""
        self.search_cache.invalidate_all()
        self.facets_cache.invalidate_all()
        self.precomputed_facets = None
        logger.info("All caches cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "search_cache": self.search_cache.get_stats(),
            "facets_cache": self.facets_cache.get_stats(),
            "precomputed_facets_age_seconds": (
                int(time.time() - self.facets_timestamp)
                if self.precomputed_facets else None
            )
        }


# Global cache instance
_global_cache: Optional[QueryCache] = None


def get_cache() -> QueryCache:
    """Get global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = QueryCache()
    return _global_cache
