"""cache — Shared cache system for all JARVIS components.

Provides unified caching for embeddings, food data, memory, conversation,
and prompts. Shared across all interfaces (CLI, Web, Speech).
"""

from __future__ import annotations

import time
import json
import hashlib
import logging
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: float = 3600.0  # Default 1 hour TTL
    hits: int = 0
    misses: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() - self.timestamp > self.ttl
    
    def touch(self) -> None:
        """Update timestamp on access."""
        self.timestamp = time.time()
        self.hits += 1


class LRUCache:
    """Simple LRU cache implementation."""
    
    def __init__(self, maxsize: int = 1000, default_ttl: float = 3600.0):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry.is_expired():
            self._remove(key)
            return None
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        entry.touch()
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        
        # Remove if exists to update
        if key in self._cache:
            self._remove(key)
        
        # Enforce maxsize
        if len(self._cache) >= self.maxsize:
            self._evict_oldest()
        
        entry = CacheEntry(value=value, ttl=ttl)
        self._cache[key] = entry
        self._access_order.append(key)
    
    def _remove(self, key: str) -> None:
        """Remove key from cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry."""
        if self._access_order:
            oldest = self._access_order.pop(0)
            self._remove(oldest)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_order.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(entry.hits for entry in self._cache.values())
        return {
            "size": len(self._cache),
            "maxsize": self.maxsize,
            "total_hits": total_hits,
            "hit_rate": total_hits / (total_hits + 1) if total_hits > 0 else 0.0
        }


class Cache:
    """Unified cache system for all JARVIS components."""
    
    def __init__(self):
        # Separate caches for different data types
        self.embedding_cache = LRUCache(maxsize=1000, default_ttl=7200.0)  # 2 hours
        self.food_cache = LRUCache(maxsize=500, default_ttl=86400.0)  # 24 hours
        self.memory_cache = LRUCache(maxsize=2000, default_ttl=3600.0)  # 1 hour
        self.conversation_cache = LRUCache(maxsize=100, default_ttl=1800.0)  # 30 min
        self.prompt_cache = LRUCache(maxsize=500, default_ttl=7200.0)  # 2 hours
        self.tool_cache = LRUCache(maxsize=200, default_ttl=3600.0)  # 1 hour
        self.context_cache = LRUCache(maxsize=300, default_ttl=600.0)  # 10 min
        
        self._caches = {
            "embedding": self.embedding_cache,
            "food": self.food_cache,
            "memory": self.memory_cache,
            "conversation": self.conversation_cache,
            "prompt": self.prompt_cache,
            "tool": self.tool_cache,
            "context": self.context_cache
        }
    
    def get(self, cache_type: str, key: str) -> Optional[Any]:
        """Get value from specific cache."""
        cache = self._caches.get(cache_type)
        if not cache:
            logger.warning(f"Unknown cache type: {cache_type}")
            return None
        
        return cache.get(key)
    
    def set(self, cache_type: str, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in specific cache."""
        cache = self._caches.get(cache_type)
        if not cache:
            logger.warning(f"Unknown cache type: {cache_type}")
            return
        
        cache.set(key, value, ttl)
    
    def get_embedding(self, text: str) -> Optional[list[float]]:
        """Get cached embedding for text."""
        key = self._hash_text(text)
        return self.get("embedding", key)
    
    def set_embedding(self, text: str, embedding: list[float]) -> None:
        """Cache embedding for text."""
        key = self._hash_text(text)
        self.set("embedding", key, embedding)
    
    def get_memory(self, key: str) -> Optional[Any]:
        """Get cached memory entry."""
        return self.get("memory", key)
    
    def set_memory(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Cache memory entry."""
        self.set("memory", key, value, ttl)
    
    def get_conversation(self, session_id: str) -> Optional[list]:
        """Get cached conversation history."""
        return self.get("conversation", session_id)
    
    def set_conversation(self, session_id: str, history: list) -> None:
        """Cache conversation history."""
        self.set("conversation", session_id, history)
    
    def get_prompt(self, prompt_hash: str) -> Optional[str]:
        """Get cached prompt response."""
        return self.get("prompt", prompt_hash)
    
    def set_prompt(self, prompt_hash: str, response: str) -> None:
        """Cache prompt response."""
        self.set("prompt", prompt_hash, response)
    
    def get_tool_result(self, tool_name: str, params_hash: str) -> Optional[Any]:
        """Get cached tool result."""
        key = f"{tool_name}:{params_hash}"
        return self.get("tool", key)
    
    def set_tool_result(self, tool_name: str, params_hash: str, result: Any) -> None:
        """Cache tool result."""
        key = f"{tool_name}:{params_hash}"
        self.set("tool", key, result)
    
    def get_context(self, context_key: str) -> Optional[Any]:
        """Get cached context."""
        return self.get("context", context_key)
    
    def set_context(self, context_key: str, value: Any) -> None:
        """Cache context."""
        self.set("context", context_key, value)
    
    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """Clear specific cache or all caches."""
        if cache_type:
            cache = self._caches.get(cache_type)
            if cache:
                cache.clear()
        else:
            for cache in self._caches.values():
                cache.clear()
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        return {
            cache_type: cache.stats()
            for cache_type, cache in self._caches.items()
        }
    
    def _hash_text(self, text: str) -> str:
        """Create hash key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _hash_params(self, params: Dict[str, Any]) -> str:
        """Create hash key for parameters."""
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(params_str.encode()).hexdigest()


def cached(cache_type: str, ttl: Optional[float] = None):
    """Decorator for caching function results."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = global_cache
            if not cache:
                return func(*args, **kwargs)
            
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = cache.get(cache_type, key)
            if cached_value is not None:
                return cached_value
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_type, key, result, ttl)
            return result
        return wrapper
    return decorator


# Global cache instance
global_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get global cache instance."""
    global global_cache
    if global_cache is None:
        global_cache = Cache()
    return global_cache


def set_cache(cache: Cache) -> None:
    """Set global cache instance."""
    global global_cache
    global_cache = cache
