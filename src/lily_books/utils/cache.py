"""Caching utilities for LLM responses."""

import hashlib
import json
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

try:
    from langchain_community.cache import InMemoryCache, RedisSemanticCache
    from langchain_core.caches import BaseCache
except ImportError:
    # Fallback for older versions
    from langchain.cache import InMemoryCache, RedisSemanticCache
    from langchain.cache import BaseCache

from ..config import settings

logger = logging.getLogger(__name__)


class SemanticCache:
    """Wrapper for semantic caching with fallback to in-memory cache."""
    
    def __init__(self):
        self.cache: Optional[BaseCache] = None
        self._setup_cache()
    
    def _setup_cache(self) -> None:
        """Setup cache based on configuration."""
        if not settings.cache_enabled:
            logger.info("Caching disabled")
            return
        
        try:
            if settings.cache_type == "redis":
                self.cache = RedisSemanticCache(
                    redis_url=settings.redis_url,
                    ttl=settings.cache_ttl_seconds
                )
                logger.info(f"Redis cache initialized: {settings.redis_url}")
            else:
                self.cache = InMemoryCache()
                logger.info("In-memory cache initialized")
                
        except Exception as e:
            logger.warning(f"Failed to initialize {settings.cache_type} cache: {e}")
            logger.info("Falling back to in-memory cache")
            self.cache = InMemoryCache()
    
    def get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key for prompt and model."""
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt: str, model: str) -> Optional[Any]:
        """Get cached response."""
        if not self.cache:
            return None
        
        try:
            cache_key = self.get_cache_key(prompt, model)
            return self.cache.lookup(prompt, cache_key)
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")
            return None
    
    def put(self, prompt: str, model: str, response: Any) -> None:
        """Store response in cache."""
        if not self.cache:
            return
        
        try:
            cache_key = self.get_cache_key(prompt, model)
            self.cache.update(prompt, cache_key, response)
            logger.debug(f"Cached response for {model}: {len(str(prompt))} chars")
        except Exception as e:
            logger.warning(f"Cache store failed: {e}")
    
    def clear(self) -> None:
        """Clear all cached responses."""
        if not self.cache:
            return
        
        try:
            if hasattr(self.cache, 'clear'):
                self.cache.clear()
                logger.info("Cache cleared")
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.cache:
            return {"enabled": False}
        
        try:
            if hasattr(self.cache, 'get_stats'):
                return self.cache.get_stats()
            else:
                return {
                    "enabled": True,
                    "type": settings.cache_type,
                    "ttl_seconds": settings.cache_ttl_seconds
                }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"enabled": True, "error": str(e)}


# Global cache instance
semantic_cache = SemanticCache()


def get_cached_llm(llm, cache_enabled: bool = None) -> Any:
    """Wrap LLM with caching if enabled."""
    if cache_enabled is None:
        cache_enabled = settings.cache_enabled
    
    if not cache_enabled or not semantic_cache.cache:
        return llm
    
    # Return LLM with cache
    llm.cache = semantic_cache.cache
    return llm


def log_cache_hit(prompt: str, model: str, hit: bool) -> None:
    """Log cache hit/miss for monitoring."""
    if hit:
        logger.info(f"Cache HIT for {model}: {len(prompt)} chars")
    else:
        logger.debug(f"Cache MISS for {model}: {len(prompt)} chars")
