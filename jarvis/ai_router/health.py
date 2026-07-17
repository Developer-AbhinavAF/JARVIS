"""Health Monitoring — Tracks provider health in real time.

Latency, success rate, failure rate, availability, uptime.
Continuously updates provider health scores.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

from .models import HealthScore, ProviderStatus

logger = logging.getLogger(__name__)


@dataclass
class HealthEntry:
    """Single health measurement."""
    timestamp: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: str = ""


class HealthMonitor:
    """Monitors provider health with rolling windows.

    Usage:
        monitor = HealthMonitor()
        monitor.record_success("groq", 45.0)
        monitor.record_failure("openai", "timeout")
        score = monitor.get_score("groq")
    """

    def __init__(self, window_size: int = 100, stale_threshold: float = 300.0):
        self._entries: dict[str, list[HealthEntry]] = defaultdict(list)
        self._scores: dict[str, HealthScore] = {}
        self._window_size = window_size
        self._stale_threshold = stale_threshold

    def _ensure_score(self, provider: str) -> HealthScore:
        if provider not in self._scores:
            self._scores[provider] = HealthScore(provider=provider)
        return self._scores[provider]

    def record_success(self, provider: str, latency_ms: float):
        entry = HealthEntry(timestamp=time.time(), latency_ms=latency_ms, success=True)
        self._entries[provider].append(entry)
        self._trim(provider)

        score = self._ensure_score(provider)
        score.total_requests += 1
        score.last_success = time.time()
        score.consecutive_failures = 0
        score.latency_ms = self._avg_latency(provider)
        score.success_rate = self._success_rate(provider)
        score.failure_rate = 1.0 - score.success_rate
        score.score = self._compute_score(score)
        score.status = self._compute_status(score)

    def record_failure(self, provider: str, error: str = ""):
        entry = HealthEntry(timestamp=time.time(), latency_ms=0.0, success=False, error=error)
        self._entries[provider].append(entry)
        self._trim(provider)

        score = self._ensure_score(provider)
        score.total_requests += 1
        score.total_failures += 1
        score.last_failure = time.time()
        score.consecutive_failures += 1
        score.success_rate = self._success_rate(provider)
        score.failure_rate = 1.0 - score.success_rate
        score.score = self._compute_score(score)
        score.status = self._compute_status(score)

    def get_score(self, provider: str) -> HealthScore:
        return self._ensure_score(provider)

    def get_all_scores(self) -> dict[str, HealthScore]:
        return {p: self._ensure_score(p) for p in set(list(self._entries.keys()) + list(self._scores.keys()))}

    def get_healthy_providers(self, min_score: float = 0.5) -> list[str]:
        return [
            p for p, s in self.get_all_scores().items()
            if s.score >= min_score and s.status != ProviderStatus.UNHEALTHY
        ]

    def get_best_provider(self, candidates: list[str] | None = None) -> str | None:
        if candidates is None:
            candidates = list(self.get_all_scores().keys())
        healthy = [(p, self._ensure_score(p)) for p in candidates]
        healthy = [(p, s) for p, s in healthy if s.status != ProviderStatus.UNHEALTHY]
        if not healthy:
            return None
        return max(healthy, key=lambda x: x[1].score)[0]

    def get_stats(self) -> dict[str, Any]:
        return {
            p: s.to_dict()
            for p, s in self.get_all_scores().items()
        }

    def _trim(self, provider: str):
        entries = self._entries[provider]
        if len(entries) > self._window_size:
            self._entries[provider] = entries[-self._window_size:]

    def _avg_latency(self, provider: str) -> float:
        success_entries = [e for e in self._entries[provider] if e.success]
        if not success_entries:
            return 0.0
        return sum(e.latency_ms for e in success_entries) / len(success_entries)

    def _success_rate(self, provider: str) -> float:
        entries = self._entries[provider]
        if not entries:
            return 1.0
        return sum(1 for e in entries if e.success) / len(entries)

    def _compute_score(self, score: HealthScore) -> float:
        s = 1.0
        # Success rate factor (0.0-0.5)
        s *= 0.5 + 0.5 * score.success_rate
        # Latency factor (lower is better)
        if score.latency_ms > 0:
            if score.latency_ms < 100:
                lat_factor = 1.0
            elif score.latency_ms < 500:
                lat_factor = 0.8
            elif score.latency_ms < 2000:
                lat_factor = 0.5
            else:
                lat_factor = 0.2
            s *= lat_factor
        # Consecutive failure penalty
        if score.consecutive_failures > 0:
            penalty = max(0.0, 1.0 - score.consecutive_failures * 0.2)
            s *= penalty
        return max(0.0, min(1.0, s))

    def _compute_status(self, score: HealthScore) -> ProviderStatus:
        if score.score >= 0.7:
            return ProviderStatus.HEALTHY
        elif score.score >= 0.3:
            return ProviderStatus.DEGRADED
        else:
            return ProviderStatus.UNHEALTHY


# Global instance
health_monitor = HealthMonitor()

__all__ = ["HealthMonitor", "HealthEntry", "health_monitor"]
