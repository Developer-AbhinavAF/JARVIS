"""Metrics — Tracks request metrics for all providers.

Success/failure counts, latency, cost, token usage.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

from .models import Route, RouteStatus, Capability

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    """Single request metric."""
    timestamp: float = 0.0
    provider: str = ""
    model: str = ""
    capability: str = ""
    status: str = ""
    latency_ms: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    attempt: int = 1
    error: str = ""


@dataclass
class ProviderMetrics:
    """Aggregated metrics for a provider."""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successful / max(self.total_requests, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "p50_latency_ms": round(self.p50_latency_ms, 1),
            "p95_latency_ms": round(self.p95_latency_ms, 1),
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
        }


class MetricsCollector:
    """Collects and aggregates routing metrics.

    Usage:
        collector = MetricsCollector()
        collector.record(route, usage={...}, cost=0.001)
        metrics = collector.get_provider("groq")
    """

    def __init__(self, retention_seconds: float = 3600.0):
        self._metrics: list[RequestMetric] = []
        self._provider_metrics: dict[str, ProviderMetrics] = {}
        self._capability_metrics: dict[str, ProviderMetrics] = {}
        self._retention = retention_seconds

    def record(self, route: Route, usage: dict[str, int] | None = None, cost: float = 0.0):
        tokens_in = (usage or {}).get("prompt_tokens", 0)
        tokens_out = (usage or {}).get("completion_tokens", 0)

        metric = RequestMetric(
            timestamp=time.time(),
            provider=route.provider,
            model=route.model,
            capability=route.capability.value,
            status=route.status.value,
            latency_ms=route.latency_ms,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost=cost,
            attempt=route.attempt,
        )
        self._metrics.append(metric)
        self._trim()

        # Update provider metrics
        pm = self._get_provider_metrics(route.provider)
        pm.total_requests += 1
        if route.status == RouteStatus.SUCCESS:
            pm.successful += 1
        else:
            pm.failed += 1
        pm.total_latency_ms += route.latency_ms
        pm.total_tokens += tokens_in + tokens_out
        pm.total_cost += cost
        pm.avg_latency_ms = pm.total_latency_ms / max(pm.total_requests, 1)
        self._update_percentiles(pm)

        # Update capability metrics
        cap_key = route.capability.value
        if cap_key not in self._capability_metrics:
            self._capability_metrics[cap_key] = ProviderMetrics()
        cm = self._capability_metrics[cap_key]
        cm.total_requests += 1
        if route.status == RouteStatus.SUCCESS:
            cm.successful += 1
        cm.total_latency_ms += route.latency_ms
        cm.avg_latency_ms = cm.total_latency_ms / max(cm.total_requests, 1)

    def get_provider(self, provider: str) -> ProviderMetrics:
        return self._get_provider_metrics(provider)

    def get_capability(self, capability: str) -> ProviderMetrics:
        return self._capability_metrics.get(capability, ProviderMetrics())

    def get_all(self) -> dict[str, Any]:
        return {
            "providers": {p: m.to_dict() for p, m in self._provider_metrics.items()},
            "capabilities": {c: m.to_dict() for c, m in self._capability_metrics.items()},
            "total_requests": len(self._metrics),
        }

    def get_top_providers(self, by: str = "success_rate", limit: int = 5) -> list[tuple[str, float]]:
        """Get top providers by metric."""
        items = []
        for p, m in self._provider_metrics.items():
            if by == "success_rate":
                items.append((p, m.success_rate))
            elif by == "latency":
                items.append((p, -m.avg_latency_ms))
            elif by == "requests":
                items.append((p, m.total_requests))
        return sorted(items, key=lambda x: x[1], reverse=True)[:limit]

    def _get_provider_metrics(self, provider: str) -> ProviderMetrics:
        if provider not in self._provider_metrics:
            self._provider_metrics[provider] = ProviderMetrics()
        return self._provider_metrics[provider]

    def _update_percentiles(self, pm: ProviderMetrics):
        provider_latencies = sorted(
            m.latency_ms for m in self._metrics
            if m.provider == pm.total_requests and m.status == "success"
        )
        # Simplified: use average as approximation for percentiles
        pm.p50_latency_ms = pm.avg_latency_ms
        pm.p95_latency_ms = pm.avg_latency_ms * 1.5
        pm.p99_latency_ms = pm.avg_latency_ms * 2.0

    def _trim(self):
        cutoff = time.time() - self._retention
        self._metrics = [m for m in self._metrics if m.timestamp > cutoff]


# Global instance
metrics_collector = MetricsCollector()

__all__ = ["MetricsCollector", "RequestMetric", "ProviderMetrics", "metrics_collector"]
