"""Tool Learning — Learns which tools work best.

Store: Tool Used, Latency, Reliability, Failures,
User Satisfaction, Preferred Tool
Future tool selection should improve automatically.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ToolProfile:
    """Learned profile for a tool."""
    tool_name: str = ""
    total_uses: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    last_used: float = field(default_factory=time.time)
    error_types: dict[str, int] = field(default_factory=dict)
    user_satisfaction: float = 0.5     # inferred from re-uses
    preferred_for: list[str] = field(default_factory=list)

    @property
    def reliability(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "total_uses": self.total_uses,
            "reliability": round(self.reliability, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "failure_count": self.failure_count,
        }


class ToolLearner:
    """Learns tool performance and user preferences."""

    def __init__(self) -> None:
        self._profiles: dict[str, ToolProfile] = {}
        self._total_uses: int = 0

    def record_use(
        self,
        tool_name: str,
        success: bool,
        latency_ms: float = 0.0,
        error_type: str = "",
        intent: str = "",
    ) -> ToolProfile:
        """Record a tool usage."""
        if tool_name not in self._profiles:
            self._profiles[tool_name] = ToolProfile(tool_name=tool_name)
        profile = self._profiles[tool_name]

        profile.total_uses += 1
        profile.last_used = time.time()
        if success:
            profile.success_count += 1
        else:
            profile.failure_count += 1
            if error_type:
                profile.error_types[error_type] = profile.error_types.get(error_type, 0) + 1

        profile.total_latency_ms += latency_ms
        profile.avg_latency_ms = profile.total_latency_ms / profile.total_uses

        if intent and intent not in profile.preferred_for:
            profile.preferred_for.append(intent)
            if len(profile.preferred_for) > 10:
                profile.preferred_for = profile.preferred_for[-10:]

        self._total_uses += 1
        return profile

    def get_reliability(self, tool_name: str) -> float:
        profile = self._profiles.get(tool_name)
        return profile.reliability if profile else 0.5

    def get_preferred_tool(self, intent: str) -> str | None:
        """Get the most reliable tool for an intent."""
        candidates = [
            (name, p) for name, p in self._profiles.items()
            if intent in p.preferred_for and p.total_uses >= 3
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[1].reliability, -x[1].total_uses))
        return candidates[0][0]

    def get_profile(self, tool_name: str) -> dict[str, Any] | None:
        profile = self._profiles.get(tool_name)
        return profile.to_dict() if profile else None

    def get_all_profiles(self) -> list[dict[str, Any]]:
        return sorted(
            [p.to_dict() for p in self._profiles.values()],
            key=lambda p: -p["total_uses"],
        )

    def get_slow_tools(self, threshold_ms: float = 1000.0) -> list[str]:
        return [
            name for name, p in self._profiles.items()
            if p.avg_latency_ms > threshold_ms and p.total_uses >= 3
        ]

    def get_unreliable_tools(self, threshold: float = 0.5) -> list[str]:
        return [
            name for name, p in self._profiles.items()
            if p.reliability < threshold and p.total_uses >= 3
        ]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_tools": len(self._profiles),
            "total_uses": self._total_uses,
        }


tool_learner = ToolLearner()

__all__ = ["ToolLearner", "ToolProfile", "tool_learner"]
