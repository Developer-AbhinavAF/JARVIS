from __future__ import annotations

import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .models import ProviderMetrics, RouterStats

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and aggregates runtime metrics for providers and the router."""

    def __init__(self) -> None:
        self._provider_metrics: dict[str, ProviderMetrics] = {}
        self._router_stats = RouterStats()
        self._start_time = time.time()

    def record_request(
        self,
        provider: str,
        model: str,
        latency_ms: float,
        tokens_used: int = 0,
        success: bool = True,
        error_type: str | None = None,
    ) -> None:
        self._router_stats.total_requests += 1
        if success:
            self._router_stats.successful_requests += 1
        else:
            self._router_stats.failed_requests += 1

        if provider not in self._provider_metrics:
            self._provider_metrics[provider] = ProviderMetrics(name=provider)

        pm = self._provider_metrics[provider]
        pm.total_requests += 1
        if success:
            pm.successful_requests += 1
        else:
            pm.failed_requests += 1
            if error_type:
                pm.error_counts[error_type] = pm.error_counts.get(error_type, 0) + 1
        pm.total_tokens += tokens_used
        pm.total_latency_ms += latency_ms
        pm.last_latency_ms = latency_ms
        pm.last_request_time = time.time()

        if latency_ms > 0 and tokens_used > 0:
            pm.avg_tokens_per_sec = (tokens_used / latency_ms) * 1000

    def record_stream_chunk(self, provider: str) -> None:
        if provider in self._provider_metrics:
            self._provider_metrics[provider].total_requests += 1

    def record_embedding(self, provider: str) -> None:
        if provider in self._provider_metrics:
            self._provider_metrics[provider].embedding_requests += 1

    def get_provider_metrics(self, provider: str) -> ProviderMetrics | None:
        return self._provider_metrics.get(provider)

    def get_all_provider_metrics(self) -> dict[str, ProviderMetrics]:
        return dict(self._provider_metrics)

    def get_router_stats(self) -> RouterStats:
        self._router_stats.provider_stats = dict(self._provider_metrics)
        total_latency = sum(pm.total_latency_ms for pm in self._provider_metrics.values())
        total_successful = sum(pm.successful_requests for pm in self._provider_metrics.values())
        self._router_stats.avg_latency_ms = total_latency / total_successful if total_successful > 0 else 0.0
        return self._router_stats

    def summary(self) -> dict[str, Any]:
        return {
            "router": {
                "total_requests": self._router_stats.total_requests,
                "successful_requests": self._router_stats.successful_requests,
                "failed_requests": self._router_stats.failed_requests,
                "cached_requests": self._router_stats.cached_requests,
                "success_rate": self._router_stats.success_rate,
                "uptime_seconds": time.time() - self._start_time,
            },
            "providers": {
                name: {
                    "total_requests": pm.total_requests,
                    "success_rate": pm.success_rate,
                    "avg_latency_ms": pm.avg_latency_ms,
                    "total_tokens": pm.total_tokens,
                }
                for name, pm in self._provider_metrics.items()
            },
        }

    def reset(self) -> None:
        self._provider_metrics.clear()
        self._router_stats = RouterStats()
        self._start_time = time.time()
