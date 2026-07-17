"""Fallback System — Ensures no request fails after a single error.

Primary → Retry → Alt Provider → Alt Model → Local Model → Cached → User.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

from .models import (
    Model, Capability, Route, RouteStatus, HealthScore, ProviderStatus
)
from .config import ProviderConfig

logger = logging.getLogger(__name__)


@dataclass
class FallbackChain:
    """Ordered list of fallback options."""
    provider: str = ""
    model: str = ""
    reason: str = ""
    priority: int = 0


class FallbackManager:
    """Manages fallback chains for failed requests.

    Usage:
        fb = FallbackManager()
        chain = fb.build_chain(primary_provider, primary_model, all_models)
        next_option = fb.get_next(chain, failed_provider, attempt)
    """

    def __init__(self, max_retries: int = 3):
        self._max_retries = max_retries
        self._cache: dict[str, Any] = {}
        self._failure_counts: dict[str, int] = {}

    def build_chain(
        self,
        primary_provider: str,
        primary_model: str,
        available_models: list[Model],
        health_scores: dict[str, HealthScore],
        capability: Capability = Capability.CHAT,
    ) -> list[FallbackChain]:
        """Build ordered fallback chain."""
        chain: list[FallbackChain] = []

        # 1. Same provider, retry
        chain.append(FallbackChain(
            provider=primary_provider, model=primary_model,
            reason="retry", priority=0
        ))

        # 2. Same capability, different healthy provider (sorted by health)
        alt_models = [
            m for m in available_models
            if m.provider != primary_provider
            and capability in m.capabilities
            and m.enabled
        ]
        alt_models.sort(key=lambda m: (
            -(health_scores.get(m.provider, HealthScore()).score),
            m.avg_latency_ms or 9999,
        ))
        for m in alt_models[:3]:
            chain.append(FallbackChain(
                provider=m.provider, model=m.model_id,
                reason="alternative_provider", priority=1
            ))

        # 3. Same capability, local model
        local_models = [m for m in available_models if m.provider == "ollama" and capability in m.capabilities]
        for m in local_models[:1]:
            chain.append(FallbackChain(
                provider="ollama", model=m.model_id,
                reason="local_fallback", priority=2
            ))

        # 4. Cached result
        cache_key = f"{primary_provider}:{primary_model}:{capability.value}"
        if cache_key in self._cache:
            chain.append(FallbackChain(
                provider="cache", model=cache_key,
                reason="cached_result", priority=3
            ))

        return chain

    def get_next(
        self,
        chain: list[FallbackChain],
        failed_provider: str,
        failed_model: str,
        attempt: int,
    ) -> FallbackChain | None:
        """Get next option in fallback chain."""
        if attempt >= len(chain):
            return None
        option = chain[min(attempt, len(chain) - 1)]

        # Track failures
        key = f"{failed_provider}:{failed_model}"
        self._failure_counts[key] = self._failure_counts.get(key, 0) + 1

        return option

    def should_give_up(self, attempt: int, chain_length: int) -> bool:
        return attempt >= min(self._max_retries, chain_length)

    def cache_result(self, key: str, value: Any, ttl: float = 300.0):
        self._cache[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl,
        }

    def get_cached(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry and time.time() - entry["timestamp"] < entry["ttl"]:
            return entry["value"]
        return None

    def get_failure_count(self, provider: str, model: str) -> int:
        return self._failure_counts.get(f"{provider}:{model}", 0)

    def reset_failures(self, provider: str, model: str):
        self._failure_counts.pop(f"{provider}:{model}", None)

    def get_stats(self) -> dict[str, Any]:
        return {
            "cache_size": len(self._cache),
            "failure_counts": dict(self._failure_counts),
            "max_retries": self._max_retries,
        }


__all__ = ["FallbackManager", "FallbackChain"]
