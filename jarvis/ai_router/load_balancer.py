"""Load Balancing — Selects the best provider for each request.

Strategies: round_robin, least_latency, weighted, capability, health_based, adaptive.
"""

from __future__ import annotations

import time
import random
import logging
from typing import Any

from .models import (
    Model, Capability, LoadBalanceStrategy, HealthScore, ProviderStatus
)
from .config import ProviderConfig

logger = logging.getLogger(__name__)


class LoadBalancer:
    """Selects providers using configurable strategies.

    Usage:
        lb = LoadBalancer(strategy=LoadBalanceStrategy.ADAPTIVE)
        provider = lb.select(models, health_scores, quotas)
    """

    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ADAPTIVE):
        self._strategy = strategy
        self._round_robin_index: dict[str, int] = {}
        self._provider_scores: dict[str, float] = {}
        self._request_counts: dict[str, int] = {}

    @property
    def strategy(self) -> LoadBalanceStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, value: LoadBalanceStrategy):
        self._strategy = value

    def select(
        self,
        models: list[Model],
        health_scores: dict[str, HealthScore],
        quotas: dict[str, Any],
        capability: Capability = Capability.CHAT,
        provider_preference: str = "",
    ) -> Model | None:
        """Select the best model from candidates."""
        if not models:
            return None

        # Filter enabled models
        enabled = [m for m in models if m.enabled]
        if not enabled:
            enabled = models

        # Apply preference
        if provider_preference:
            preferred = [m for m in enabled if m.provider == provider_preference]
            if preferred:
                enabled = preferred

        # Apply strategy
        if self._strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._select_round_robin(enabled)
        elif self._strategy == LoadBalanceStrategy.LEAST_LATENCY:
            return self._select_least_latency(enabled, health_scores)
        elif self._strategy == LoadBalanceStrategy.WEIGHTED:
            return self._select_weighted(enabled, health_scores)
        elif self._strategy == LoadBalanceStrategy.HEALTH_BASED:
            return self._select_health_based(enabled, health_scores)
        elif self._strategy == LoadBalanceStrategy.ADAPTIVE:
            return self._select_adaptive(enabled, health_scores, capability)
        else:
            return self._select_health_based(enabled, health_scores)

    def _select_round_robin(self, models: list[Model]) -> Model:
        key = "default"
        idx = self._round_robin_index.get(key, 0) % len(models)
        self._round_robin_index[key] = idx + 1
        return models[idx]

    def _select_least_latency(self, models: list[Model], health: dict[str, HealthScore]) -> Model:
        def sort_key(m: Model) -> float:
            h = health.get(m.provider)
            if h and h.latency_ms > 0:
                return h.latency_ms
            return m.avg_latency_ms or 9999.0
        return min(models, key=sort_key)

    def _select_weighted(self, models: list[Model], health: dict[str, HealthScore]) -> Model:
        weights = []
        for m in models:
            h = health.get(m.provider)
            w = h.score if h else 0.5
            weights.append(max(w, 0.01))
        total = sum(weights)
        r = random.random() * total
        cumulative = 0.0
        for model, weight in zip(models, weights):
            cumulative += weight
            if r <= cumulative:
                return model
        return models[-1]

    def _select_health_based(self, models: list[Model], health: dict[str, HealthScore]) -> Model:
        def sort_key(m: Model) -> float:
            h = health.get(m.provider)
            if h:
                return -h.score
            return 0.0
        return min(models, key=sort_key)

    def _select_adaptive(
        self,
        models: list[Model],
        health: dict[str, HealthScore],
        capability: Capability,
    ) -> Model:
        """Adaptive: combines health, latency, capability fit, and learning."""
        scores: list[tuple[Model, float]] = []
        for m in models:
            h = health.get(m.provider)
            score = 0.0
            # Health factor (0-0.4)
            if h:
                score += h.score * 0.4
            else:
                score += 0.2 * 0.4
            # Latency factor (0-0.3)
            lat = h.latency_ms if h and h.latency_ms > 0 else (m.avg_latency_ms or 200.0)
            if lat < 50:
                score += 0.3
            elif lat < 200:
                score += 0.2
            elif lat < 1000:
                score += 0.1
            # Capability factor (0-0.2)
            cap_count = len(m.capabilities)
            score += min(cap_count / 5, 1.0) * 0.2
            # Provider priority (0-0.1)
            score += (10 - min(5, 5)) * 0.01

            # Learning score
            learned = self._provider_scores.get(f"{m.provider}:{capability.value}", 0.5)
            score += learned * 0.1

            scores.append((m, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        winner = scores[0][0]

        # Update request counts
        self._request_counts[winner.provider] = self._request_counts.get(winner.provider, 0) + 1

        return winner

    def update_learning(self, provider: str, capability: str, success: bool, latency_ms: float):
        """Update learning scores based on outcomes."""
        key = f"{provider}:{capability}"
        current = self._provider_scores.get(key, 0.5)
        if success:
            reward = 0.05 if latency_ms < 200 else 0.02
            self._provider_scores[key] = min(1.0, current + reward)
        else:
            self._provider_scores[key] = max(0.0, current - 0.1)

    def get_stats(self) -> dict[str, Any]:
        return {
            "strategy": self._strategy.value,
            "request_counts": dict(self._request_counts),
            "learned_scores": {k: round(v, 3) for k, v in self._provider_scores.items()},
        }


__all__ = ["LoadBalancer"]
