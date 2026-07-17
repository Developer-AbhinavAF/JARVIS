"""Analytics — Tracks usage statistics, all local.

Response time, session duration, tool usage, memory growth, learning stats.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class UsageMetric:
    """Single usage metric."""
    timestamp: float = 0.0
    category: str = ""
    event: str = ""
    value: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class Analytics:
    """Local-only analytics tracker.

    Usage:
        analytics = Analytics()
        analytics.track("tool", "web_search", latency_ms=150.0)
        analytics.track("session", "started")
        stats = analytics.get_summary()
    """

    def __init__(self, max_metrics: int = 50000):
        self._metrics: list[UsageMetric] = []
        self._max_metrics = max_metrics
        self._counters: dict[str, int] = defaultdict(int)
        self._timers: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._session_start = time.time()

    def track(self, category: str, event: str, value: float = 0.0, metadata: dict[str, Any] | None = None):
        metric = UsageMetric(
            timestamp=time.time(),
            category=category,
            event=event,
            value=value,
            metadata=metadata or {},
        )
        with self._lock:
            self._metrics.append(metric)
            self._counters[f"{category}:{event}"] += 1
            if value > 0:
                self._timers[f"{category}:{event}"].append(value)
            if len(self._metrics) > self._max_metrics:
                self._metrics = self._metrics[-self._max_metrics:]

    def increment(self, category: str, event: str):
        with self._lock:
            self._counters[f"{category}:{event}"] += 1

    def count(self, category: str, event: str) -> int:
        return self._counters.get(f"{category}:{event}", 0)

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
            timers = dict(self._timers)

        summary: dict[str, Any] = {
            "session_duration_seconds": round(time.time() - self._session_start, 1),
            "total_events": sum(counters.values()),
            "categories": {},
        }

        for key, count in sorted(counters.items()):
            cat, event = key.split(":", 1) if ":" in key else (key, "")
            if cat not in summary["categories"]:
                summary["categories"][cat] = {"count": 0, "events": {}}
            summary["categories"][cat]["count"] += count
            summary["categories"][cat]["events"][event] = count

        # Add timing stats
        for key, values in timers.items():
            if values:
                cat, event = key.split(":", 1) if ":" in key else (key, "")
                if cat in summary["categories"]:
                    summary["categories"][cat]["events"][f"{event}_avg_ms"] = round(sum(values) / len(values), 2)

        return summary

    def get_category(self, category: str) -> dict[str, int]:
        with self._lock:
            return {
                k.split(":", 1)[1]: v
                for k, v in self._counters.items()
                if k.startswith(f"{category}:")
            }

    def get_recent(self, category: str | None = None, limit: int = 50) -> list[UsageMetric]:
        with self._lock:
            metrics = list(self._metrics)
        if category:
            metrics = [m for m in metrics if m.category == category]
        return metrics[-limit:]

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_metrics": len(self._metrics),
                "total_counters": len(self._counters),
                "session_seconds": round(time.time() - self._session_start, 1),
            }


# Global instance
analytics = Analytics()

__all__ = ["Analytics", "UsageMetric", "analytics"]
