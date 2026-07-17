"""Latency Prediction — Predicts response latency for provider selection.

Uses historical data to predict which provider will be fastest.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class LatencySample:
    """Single latency measurement."""
    timestamp: float = 0.0
    latency_ms: float = 0.0
    tokens: int = 0
    model: str = ""


class LatencyPredictor:
    """Predicts latency for providers based on historical data.

    Usage:
        predictor = LatencyPredictor()
        predictor.record("groq", 45.0, tokens=500)
        predicted = predictor.predict("groq", tokens=1000)
    """

    def __init__(self, window_size: int = 200):
        self._samples: dict[str, list[LatencySample]] = defaultdict(list)
        self._window_size = window_size

    def record(self, provider: str, latency_ms: float, tokens: int = 0, model: str = ""):
        sample = LatencySample(
            timestamp=time.time(),
            latency_ms=latency_ms,
            tokens=tokens,
            model=model,
        )
        self._samples[provider].append(sample)
        # Trim old samples
        if len(self._samples[provider]) > self._window_size:
            self._samples[provider] = self._samples[provider][-self._window_size:]

    def predict(self, provider: str, tokens: int = 0) -> float:
        """Predict latency for a provider in ms."""
        samples = self._samples.get(provider, [])
        if not samples:
            return 500.0  # Default unknown

        # Weight recent samples more heavily
        recent = samples[-20:] if len(samples) > 20 else samples
        weights = [1.0 + i * 0.1 for i in range(len(recent))]
        total_weight = sum(weights)

        weighted_latency = sum(
            s.latency_ms * w for s, w in zip(recent, weights)
        ) / total_weight

        # Token-based adjustment
        if tokens > 0 and recent:
            avg_tokens = sum(s.tokens for s in recent if s.tokens > 0) / max(1, sum(1 for s in recent if s.tokens > 0))
            if avg_tokens > 0:
                token_factor = tokens / avg_tokens
                weighted_latency *= min(token_factor, 3.0)  # Cap at 3x

        return max(1.0, weighted_latency)

    def predict_tokens_per_second(self, provider: str) -> float:
        """Predict tokens per second throughput."""
        samples = self._samples.get(provider, [])
        valid = [s for s in samples[-20:] if s.tokens > 0 and s.latency_ms > 0]
        if not valid:
            return 50.0  # Default
        total_tokens = sum(s.tokens for s in valid)
        total_seconds = sum(s.latency_ms / 1000 for s in valid)
        return total_tokens / max(total_seconds, 0.001)

    def get_avg_latency(self, provider: str) -> float:
        samples = self._samples.get(provider, [])
        if not samples:
            return 0.0
        return sum(s.latency_ms for s in samples) / len(samples)

    def get_recent_trend(self, provider: str, window: int = 10) -> str:
        """Get if latency is improving, stable, or degrading."""
        samples = self._samples.get(provider, [])
        if len(samples) < window * 2:
            return "unknown"
        old = samples[-window * 2:-window]
        new = samples[-window:]
        old_avg = sum(s.latency_ms for s in old) / len(old)
        new_avg = sum(s.latency_ms for s in new) / len(new)
        diff = (new_avg - old_avg) / max(old_avg, 1.0)
        if diff < -0.1:
            return "improving"
        elif diff > 0.1:
            return "degrading"
        return "stable"

    def get_stats(self) -> dict[str, Any]:
        return {
            p: {
                "samples": len(s),
                "avg_latency_ms": round(self.get_avg_latency(p), 1),
                "predicted_ms": round(self.predict(p), 1),
                "trend": self.get_recent_trend(p),
                "tokens_per_sec": round(self.predict_tokens_per_second(p), 1),
            }
            for p, s in self._samples.items()
        }


# Global instance
latency_predictor = LatencyPredictor()

__all__ = ["LatencyPredictor", "LatencySample", "latency_predictor"]
