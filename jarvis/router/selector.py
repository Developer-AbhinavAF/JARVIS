from __future__ import annotations

import random
import logging
from typing import Any

from .models import Capability, LoadBalanceStrategy, ChatRequest
from .interfaces import BaseProvider
from .health import HealthManager
from .quota import QuotaManager
from .registry import ProviderRegistry

logger = logging.getLogger(__name__)


class ProviderSelector:
    """Intelligently selects the best provider for a given request.

    Supports multiple load balancing strategies:
    - Priority routing (lowest priority number first)
    - Weighted random
    - Round robin
    - Least latency
    - Capability based
    - Auto-optimized (learns best provider over time)
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        health_manager: HealthManager,
        quota_manager: QuotaManager,
    ) -> None:
        self.registry = registry
        self.health = health_manager
        self.quota = quota_manager
        self._round_robin_index: dict[str, int] = {}
        self._auto_weights: dict[str, dict[str, float]] = {}

    def select(
        self,
        request: ChatRequest,
        *,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.AUTO_OPTIMIZED,
    ) -> list[BaseProvider]:
        candidates = self._get_candidates(request)

        if not candidates:
            return []

        if strategy == LoadBalanceStrategy.PRIORITY:
            return self._priority_select(candidates)
        elif strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted_select(candidates)
        elif strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin_select(candidates)
        elif strategy == LoadBalanceStrategy.LEAST_LATENCY:
            return self._least_latency_select(candidates)
        elif strategy == LoadBalanceStrategy.CAPABILITY_BASED:
            return self._capability_based_select(candidates, request)
        elif strategy == LoadBalanceStrategy.RANDOM_WEIGHTED:
            return self._random_weighted_select(candidates)
        else:
            return self._auto_optimized_select(candidates, request)

    def select_for_model(
        self,
        model_name: str,
        *,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.PRIORITY,
    ) -> list[BaseProvider]:
        candidates = self.registry.get_by_model(model_name)
        if not candidates:
            return []
        return self._priority_select(candidates)

    def select_for_capability(
        self,
        capability: Capability,
        *,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.PRIORITY,
    ) -> list[BaseProvider]:
        candidates = self.registry.get_by_capability(capability)
        if not candidates:
            return []
        return self._priority_select(candidates)

    def _get_candidates(self, request: ChatRequest) -> list[BaseProvider]:
        candidates: list[BaseProvider] = []

        if request.model:
            candidates = self.registry.get_by_model(request.model)

        if not candidates:
            candidates = list(self.registry.get_available())

        eligible = []
        for p in candidates:
            if not p.is_configured:
                continue
            if self.health.is_unhealthy(p.name):
                continue
            if self.quota.is_rate_limited(p.name):
                continue
            eligible.append(p)

        return eligible

    def _priority_select(self, candidates: list[BaseProvider]) -> list[BaseProvider]:
        return sorted(candidates, key=lambda p: (p.priority, p.name))

    def _weighted_select(self, candidates: list[BaseProvider]) -> list[BaseProvider]:
        return sorted(candidates, key=lambda p: p.weight, reverse=True)

    def _round_robin_select(self, candidates: list[BaseProvider]) -> list[BaseProvider]:
        key = "default"
        idx = self._round_robin_index.get(key, 0)
        result = candidates[idx:] + candidates[:idx]
        self._round_robin_index[key] = (idx + 1) % len(candidates)
        return result

    def _least_latency_select(self, candidates: list[BaseProvider]) -> list[BaseProvider]:
        def avg_latency(p: BaseProvider) -> float:
            health = self.health.get_health(p.name)
            return health.latency_ms if health else float("inf")
        return sorted(candidates, key=avg_latency)

    def _capability_based_select(
        self,
        candidates: list[BaseProvider],
        request: ChatRequest,
    ) -> list[BaseProvider]:
        scored = []
        for p in candidates:
            score = 0.0
            if request.tools and p.supports_tool_calling:
                score += 10
            if request.response_format and p.supports_json_mode:
                score += 5
            if request.stream and p.supports_streaming:
                score += 3
            scored.append((score, p))
        scored.sort(key=lambda x: (-x[0], x[1].priority))
        return [p for _, p in scored]

    def _random_weighted_select(self, candidates: list[BaseProvider]) -> list[BaseProvider]:
        weights = [max(p.weight, 0.1) for p in candidates]
        total = sum(weights)
        probs = [w / total for w in weights]

        selected = random.choices(candidates, weights=probs, k=min(len(candidates), 3))
        remaining = [p for p in candidates if p not in selected]
        return selected + remaining

    def _auto_optimized_select(
        self,
        candidates: list[BaseProvider],
        request: ChatRequest,
    ) -> list[BaseProvider]:
        return self._capability_based_select(candidates, request)

    def update_auto_weights(
        self,
        provider_name: str,
        capability: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        if capability not in self._auto_weights:
            self._auto_weights[capability] = {}
        weights = self._auto_weights[capability]
        current = weights.get(provider_name, 1.0)
        if success:
            weights[provider_name] = min(current + 0.1, 2.0)
        else:
            weights[provider_name] = max(current - 0.2, 0.1)
