"""Failure Memory & Tool Reliability Tracking for JARVIS NLP.

Remember failures. Tool A failed three times → prefer Tool B next time.
System continuously improves.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# FAILURE RECORD
# ════════════════════════════════════════════════════════════════════

@dataclass
class FailureRecord:
    """A single tool failure record."""
    tool_name: str
    error_type: str = ""
    error_message: str = ""
    intent: str = ""
    timestamp: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)
    alternative_used: str = ""
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "intent": self.intent,
            "timestamp": self.timestamp,
            "alternative_used": self.alternative_used,
            "resolved": self.resolved,
        }


# ════════════════════════════════════════════════════════════════════
# FAILURE MEMORY
# ════════════════════════════════════════════════════════════════════

class FailureMemory:
    """Tracks tool failures and suggests alternatives.

    When a tool fails multiple times, the system automatically
    prefers alternative tools for the same task.
    """

    def __init__(self) -> None:
        self._failures: list[FailureRecord] = []
        self._tool_reliability: dict[str, dict[str, Any]] = {}
        self._failure_threshold: int = 3  # Failures before deprioritizing
        self._window_hours: float = 24.0  # Consider failures from last 24h

    def record_failure(
        self,
        tool_name: str,
        error_type: str = "",
        error_message: str = "",
        intent: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record a tool failure."""
        record = FailureRecord(
            tool_name=tool_name,
            error_type=error_type,
            error_message=error_message,
            intent=intent,
            context=context or {},
        )
        self._failures.append(record)
        self._update_reliability(tool_name)

    def record_success(self, tool_name: str) -> None:
        """Record a tool success (improves reliability)."""
        if tool_name not in self._tool_reliability:
            self._tool_reliability[tool_name] = {
                "total_calls": 0,
                "total_failures": 0,
                "recent_failures": 0,
                "reliability_score": 1.0,
            }
        stats = self._tool_reliability[tool_name]
        stats["total_calls"] += 1
        stats["reliability_score"] = min(1.0, stats["reliability_score"] + 0.05)

    def record_alternative(self, failed_tool: str, alternative: str) -> None:
        """Record that an alternative tool was used after failure."""
        for record in reversed(self._failures):
            if record.tool_name == failed_tool and not record.alternative_used:
                record.alternative_used = alternative
                break

    def should_avoid(self, tool_name: str) -> bool:
        """Check if a tool should be avoided due to recent failures."""
        recent_failures = self._get_recent_failures(tool_name)
        return len(recent_failures) >= self._failure_threshold

    def get_reliability(self, tool_name: str) -> float:
        """Get the reliability score for a tool (0.0-1.0)."""
        stats = self._tool_reliability.get(tool_name)
        if not stats:
            return 1.0  # Unknown tools get neutral score
        return stats["reliability_score"]

    def suggest_alternative(
        self,
        failed_tool: str,
        capability: str,
        available_tools: list[str] | None = None,
    ) -> str | None:
        """Suggest an alternative tool for a failed tool.

        Uses past success patterns to recommend the best alternative.
        """
        # Check past alternatives used
        alternatives: dict[str, int] = {}
        for record in self._failures:
            if record.tool_name == failed_tool and record.alternative_used:
                alt = record.alternative_used
                alternatives[alt] = alternatives.get(alt, 0) + 1

        if alternatives:
            # Return most-used alternative
            return max(alternatives, key=alternatives.get)  # type: ignore

        return None

    def get_tool_stats(self, tool_name: str) -> dict[str, Any]:
        """Get failure statistics for a specific tool."""
        stats = self._tool_reliability.get(tool_name, {
            "total_calls": 0,
            "total_failures": 0,
            "recent_failures": 0,
            "reliability_score": 1.0,
        })
        recent = self._get_recent_failures(tool_name)
        stats["recent_failures"] = len(recent)
        return stats

    def get_all_stats(self) -> dict[str, Any]:
        """Get overall failure memory statistics."""
        return {
            "total_failures": len(self._failures),
            "tools_tracked": len(self._tool_reliability),
            "unreliable_tools": [
                name for name, stats in self._tool_reliability.items()
                if stats["reliability_score"] < 0.5
            ],
        }

    def clear_old(self, hours: float = 48.0) -> int:
        """Clear failures older than specified hours."""
        cutoff = time.time() - hours * 3600
        old_count = len(self._failures)
        self._failures = [r for r in self._failures if r.timestamp > cutoff]
        return old_count - len(self._failures)

    # ── Internal helpers ───────────────────────────────────────────

    def _get_recent_failures(self, tool_name: str) -> list[FailureRecord]:
        cutoff = time.time() - self._window_hours * 3600
        return [
            r for r in self._failures
            if r.tool_name == tool_name and r.timestamp > cutoff
        ]

    def _update_reliability(self, tool_name: str) -> None:
        if tool_name not in self._tool_reliability:
            self._tool_reliability[tool_name] = {
                "total_calls": 0,
                "total_failures": 0,
                "recent_failures": 0,
                "reliability_score": 1.0,
            }
        stats = self._tool_reliability[tool_name]
        stats["total_calls"] += 1
        stats["total_failures"] += 1

        # Decay reliability based on failure rate
        if stats["total_calls"] > 0:
            failure_rate = stats["total_failures"] / stats["total_calls"]
            stats["reliability_score"] = max(0.0, 1.0 - failure_rate)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

failure_memory = FailureMemory()
