"""Models — Data types for the AI Router.

Provider, Model, Capability, Route, RoutingResult, Metrics.
"""

from __future__ import annotations

import time
import logging
from typing import Any, AsyncIterator, Iterator
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════

class Capability(Enum):
    CHAT = "chat"
    REASONING = "reasoning"
    VISION = "vision"
    SPEECH = "speech"
    EMBEDDINGS = "embeddings"
    IMAGE_GENERATION = "image_generation"
    SEARCH = "search"
    AUDIO = "audio"
    CODING = "coding"
    TOOL_USE = "tool_use"
    STREAMING = "streaming"


class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LoadBalanceStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    WEIGHTED = "weighted"
    CAPABILITY = "capability"
    HEALTH_BASED = "health_based"
    ADAPTIVE = "adaptive"


class RouteStatus(Enum):
    SUCCESS = "success"
    FALLBACK = "fallback"
    FAILED = "failed"
    CACHED = "cached"


# ═══════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Model:
    """An AI model offered by a provider."""
    model_id: str = ""
    provider: str = ""
    display_name: str = ""
    capabilities: list[Capability] = field(default_factory=list)
    context_window: int = 4096
    max_output: int = 4096
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    avg_latency_ms: float = 0.0
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "capabilities": [c.value for c in self.capabilities],
            "context_window": self.context_window,
            "supports_streaming": self.supports_streaming,
            "supports_vision": self.supports_vision,
        }


@dataclass
class Route:
    """A selected route for a request."""
    provider: str = ""
    model: str = ""
    capability: Capability = Capability.CHAT
    status: RouteStatus = RouteStatus.SUCCESS
    latency_ms: float = 0.0
    cost_estimate: float = 0.0
    health_score: float = 1.0
    attempt: int = 1
    fallback_chain: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "capability": self.capability.value,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 1),
            "cost_estimate": round(self.cost_estimate, 6),
            "attempt": self.attempt,
        }


@dataclass
class RouterRequest:
    """A request to be routed."""
    text: str = ""
    capability: Capability = Capability.CHAT
    model_preference: str = ""
    provider_preference: str = ""
    requires_vision: bool = False
    requires_tools: bool = False
    requires_streaming: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7
    context: dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    timeout: float = 30.0


@dataclass
class RouterResponse:
    """Response from the router."""
    content: str = ""
    route: Route = field(default_factory=Route)
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: Any = None
    streaming: bool = False
    error: str = ""

    @property
    def success(self) -> bool:
        return not self.error and bool(self.content)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content[:200],
            "route": self.route.to_dict(),
            "usage": self.usage,
            "success": self.success,
            "streaming": self.streaming,
        }


@dataclass
class HealthScore:
    """Health metrics for a provider."""
    provider: str = ""
    status: ProviderStatus = ProviderStatus.UNKNOWN
    score: float = 1.0           # 0.0-1.0
    latency_ms: float = 0.0
    success_rate: float = 1.0
    failure_rate: float = 0.0
    total_requests: int = 0
    total_failures: int = 0
    last_check: float = field(default_factory=time.time)
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    uptime_ratio: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status.value,
            "score": round(self.score, 3),
            "latency_ms": round(self.latency_ms, 1),
            "success_rate": round(self.success_rate, 3),
            "total_requests": self.total_requests,
            "consecutive_failures": self.consecutive_failures,
        }


@dataclass
class QuotaInfo:
    """Quota tracking for a provider."""
    provider: str = ""
    rpm_used: int = 0
    rpm_limit: int = 60
    tpm_used: int = 0
    tpm_limit: int = 100000
    daily_used: int = 0
    daily_limit: int = 10000
    monthly_used: int = 0
    monthly_limit: int = 300000

    @property
    def rpm_available(self) -> bool:
        return self.rpm_used < self.rpm_limit

    @property
    def daily_available(self) -> bool:
        return self.daily_used < self.daily_limit

    @property
    def available(self) -> bool:
        return self.rpm_available and self.daily_available

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "rpm": f"{self.rpm_used}/{self.rpm_limit}",
            "daily": f"{self.daily_used}/{self.daily_limit}",
            "available": self.available,
        }


__all__ = [
    "Capability", "ProviderStatus", "LoadBalanceStrategy", "RouteStatus",
    "Model", "Route", "RouterRequest", "RouterResponse",
    "HealthScore", "QuotaInfo",
]
