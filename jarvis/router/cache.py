from __future__ import annotations

import time
import logging
from collections import OrderedDict
from typing import Any, Generic, TypeVar

from .config import RouterConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LRUCache(Generic[T]):
    """Simple LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, ttl: float = 300.0):
        self._max_size = max_size
        self._ttl = ttl
        self._cache: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        if key not in self._cache:
            return None
        created, value = self._cache.pop(key)
        if time.time() - created > self._ttl:
            return None
        self._cache[key] = (created, value)
        return value

    def set(self, key: str, value: T) -> None:
        if key in self._cache:
            self._cache.pop(key)
        elif len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        self._cache.clear()

    def remove(self, key: str) -> None:
        self._cache.pop(key, None)

    @property
    def size(self) -> int:
        return len(self._cache)


class RouterCache:
    """Multi-purpose cache for the AI Router."""

    def __init__(self, config: RouterConfig | None = None):
        self.config = config or RouterConfig()
        self.response_cache = LRUCache[Any](
            max_size=self.config.cache_max_size,
            ttl=self.config.cache_ttl_response,
        )
        self.embedding_cache = LRUCache[list[list[float]]](
            max_size=self.config.cache_max_size,
            ttl=self.config.cache_ttl_embedding,
        )
        self.model_cache = LRUCache[dict](
            max_size=100, ttl=self.config.cache_ttl_health,
        )
        self.capability_cache = LRUCache[list](
            max_size=100, ttl=self.config.cache_ttl_health,
        )
        self.health_cache = LRUCache[dict](
            max_size=50, ttl=self.config.cache_ttl_health,
        )
        self.quota_cache = LRUCache[dict](
            max_size=50, ttl=self.config.quota_check_interval,
        )

    def get_response(self, key: str) -> Any:
        return self.response_cache.get(key)

    def set_response(self, key: str, value: Any) -> None:
        self.response_cache.set(key, value)

    def get_embedding(self, key: str) -> list[list[float]] | None:
        return self.embedding_cache.get(key)

    def set_embedding(self, key: str, value: list[list[float]]) -> None:
        self.embedding_cache.set(key, value)

    def clear_all(self) -> None:
        self.response_cache.clear()
        self.embedding_cache.clear()
        self.model_cache.clear()
        self.capability_cache.clear()
        self.health_cache.clear()
        self.quota_cache.clear()
