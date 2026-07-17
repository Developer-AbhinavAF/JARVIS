"""Tool Learning System for JARVIS.

Continuously improves tool usage by tracking:
- Execution time
- Failure rate
- User satisfaction
- Preferred tool per intent
- Recovery success
- Average latency
- Health score

Future executions should become faster.
"""

from __future__ import annotations

import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_LEARNING_FILE = _DATA_DIR / "tool_learning.json"


# ════════════════════════════════════════════════════════════════════
# TOOL PERFORMANCE PROFILE
# ════════════════════════════════════════════════════════════════════

@dataclass
class ToolPerformance:
    """Performance profile for a single tool."""
    tool_name: str = ""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    success_rate: float = 1.0
    failure_rate: float = 0.0
    last_used: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    user_satisfaction: float = 0.5  # 0.0 to 1.0
    health_score: float = 1.0      # 0.0 to 1.0

    def record_execution(self, success: bool, latency_ms: float) -> None:
        """Record a single execution."""
        self.total_executions += 1
        self.last_used = time.time()

        if success:
            self.successful_executions += 1
            self.last_success = time.time()
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            self.user_satisfaction = min(1.0, self.user_satisfaction + 0.02)
        else:
            self.failed_executions += 1
            self.last_failure = time.time()
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            self.user_satisfaction = max(0.0, self.user_satisfaction - 0.05)

        # Update latency stats
        if latency_ms > 0:
            self.total_latency_ms += latency_ms
            self.avg_latency_ms = self.total_latency_ms / self.total_executions
            self.min_latency_ms = min(self.min_latency_ms, latency_ms)
            self.max_latency_ms = max(self.max_latency_ms, latency_ms)

        # Update rates
        self.success_rate = self.successful_executions / self.total_executions
        self.failure_rate = self.failed_executions / self.total_executions

        # Update health score
        self._update_health()

    def _update_health(self) -> None:
        """Update health score based on recent performance."""
        # Base health from success rate
        health = self.success_rate

        # Penalty for consecutive failures
        if self.consecutive_failures >= 5:
            health *= 0.3
        elif self.consecutive_failures >= 3:
            health *= 0.6
        elif self.consecutive_failures >= 1:
            health *= 0.85

        # Bonus for recent success
        if self.consecutive_successes >= 3:
            health = min(1.0, health * 1.1)

        # Latency penalty (slow tools are less healthy)
        if self.avg_latency_ms > 5000:
            health *= 0.7
        elif self.avg_latency_ms > 2000:
            health *= 0.85

        self.health_score = max(0.0, min(1.0, health))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "total_executions": self.total_executions,
            "success_rate": round(self.success_rate, 4),
            "failure_rate": round(self.failure_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "min_latency_ms": round(self.min_latency_ms, 1) if self.min_latency_ms != float("inf") else 0,
            "max_latency_ms": round(self.max_latency_ms, 1),
            "health_score": round(self.health_score, 4),
            "user_satisfaction": round(self.user_satisfaction, 4),
            "consecutive_failures": self.consecutive_failures,
        }


# ════════════════════════════════════════════════════════════════════
# INTENT-TO-TOOL LEARNING
# ════════════════════════════════════════════════════════════════════

@dataclass
class IntentToolPreference:
    """Learned preference for which tool to use for an intent."""
    intent: str = ""
    tool_name: str = ""
    usage_count: int = 0
    success_count: int = 0
    avg_latency_ms: float = 0.0
    preference_score: float = 0.5

    def record(self, success: bool, latency_ms: float = 0.0) -> None:
        self.usage_count += 1
        if success:
            self.success_count += 1
        if latency_ms > 0:
            self.avg_latency_ms = (self.avg_latency_ms * (self.usage_count - 1) + latency_ms) / self.usage_count
        self.preference_score = (self.success_count / self.usage_count) * 0.7 + (1.0 - min(self.avg_latency_ms / 5000, 1.0)) * 0.3


# ════════════════════════════════════════════════════════════════════
# TOOL LEARNING ENGINE
# ════════════════════════════════════════════════════════════════════

class ToolLearner:
    """Learns from tool executions to improve future performance.

    Tracks per-tool performance and per-intent tool preferences.
    Provides recommendations for tool selection.
    """

    def __init__(self) -> None:
        self._tool_profiles: dict[str, ToolPerformance] = {}
        self._intent_preferences: dict[str, dict[str, IntentToolPreference]] = {}
        self._load()

    def record_execution(
        self,
        intent: str,
        tool_name: str,
        success: bool,
        latency_ms: float = 0.0,
    ) -> None:
        """Record a tool execution for learning."""
        # Update tool performance
        if tool_name not in self._tool_profiles:
            self._tool_profiles[tool_name] = ToolPerformance(tool_name=tool_name)
        self._tool_profiles[tool_name].record_execution(success, latency_ms)

        # Update intent-tool preference
        if intent not in self._intent_preferences:
            self._intent_preferences[intent] = {}
        if tool_name not in self._intent_preferences[intent]:
            self._intent_preferences[intent][tool_name] = IntentToolPreference(
                intent=intent, tool_name=tool_name,
            )
        self._intent_preferences[intent][tool_name].record(success, latency_ms)

        # Periodic save
        if sum(p.total_executions for p in self._tool_profiles.values()) % 10 == 0:
            self._save()

    def get_preferred_tool(self, intent: str, candidates: list[str]) -> str | None:
        """Get the best tool for an intent based on learned preferences."""
        if intent not in self._intent_preferences:
            return None

        prefs = self._intent_preferences[intent]
        best_tool = None
        best_score = -1.0

        for tool_name in candidates:
            if tool_name in prefs:
                score = prefs[tool_name].preference_score
                # Bonus for health
                profile = self._tool_profiles.get(tool_name)
                if profile:
                    score *= profile.health_score
                if score > best_score:
                    best_score = score
                    best_tool = tool_name

        return best_tool

    def get_tool_profile(self, tool_name: str) -> ToolPerformance | None:
        """Get performance profile for a tool."""
        return self._tool_profiles.get(tool_name)

    def get_tool_health(self, tool_name: str) -> float:
        """Get health score for a tool (0.0 to 1.0)."""
        profile = self._tool_profiles.get(tool_name)
        return profile.health_score if profile else 1.0

    def get_tool_rankings(self) -> list[dict[str, Any]]:
        """Get tools ranked by overall performance."""
        rankings = []
        for name, profile in self._tool_profiles.items():
            rankings.append({
                "tool": name,
                "executions": profile.total_executions,
                "success_rate": round(profile.success_rate, 3),
                "avg_latency": round(profile.avg_latency_ms, 1),
                "health": round(profile.health_score, 3),
                "satisfaction": round(profile.user_satisfaction, 3),
            })
        return sorted(rankings, key=lambda x: x["health"], reverse=True)

    def get_recommendations(self, intent: str) -> list[dict[str, Any]]:
        """Get tool recommendations for an intent."""
        if intent not in self._intent_preferences:
            return []

        prefs = self._intent_preferences[intent]
        recs = []
        for tool_name, pref in prefs.items():
            recs.append({
                "tool": tool_name,
                "preference_score": round(pref.preference_score, 3),
                "usage_count": pref.usage_count,
                "avg_latency": round(pref.avg_latency_ms, 1),
            })
        return sorted(recs, key=lambda x: x["preference_score"], reverse=True)

    def get_stats(self) -> dict[str, Any]:
        """Get learning statistics."""
        total_exec = sum(p.total_executions for p in self._tool_profiles.values())
        total_success = sum(p.successful_executions for p in self._tool_profiles.values())
        return {
            "tools_tracked": len(self._tool_profiles),
            "intents_tracked": len(self._intent_preferences),
            "total_executions": total_exec,
            "overall_success_rate": round(total_success / max(total_exec, 1), 4),
        }

    def _save(self) -> None:
        """Save learning data to disk."""
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "tools": {k: v.to_dict() for k, v in self._tool_profiles.items()},
                "saved_at": time.time(),
            }
            _LEARNING_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("Failed to save tool learning: %s", e)

    def _load(self) -> None:
        """Load learning data from disk."""
        try:
            if _LEARNING_FILE.exists():
                data = json.loads(_LEARNING_FILE.read_text())
                for name, profile_data in data.get("tools", {}).items():
                    profile = ToolPerformance(tool_name=name)
                    profile.total_executions = profile_data.get("total_executions", 0)
                    profile.successful_executions = int(profile.total_executions * profile_data.get("success_rate", 1.0))
                    profile.failed_executions = profile.total_executions - profile.successful_executions
                    profile.avg_latency_ms = profile_data.get("avg_latency_ms", 0)
                    profile.health_score = profile_data.get("health_score", 1.0)
                    profile.user_satisfaction = profile_data.get("user_satisfaction", 0.5)
                    self._tool_profiles[name] = profile
        except Exception as e:
            logger.debug("Failed to load tool learning: %s", e)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

tool_learner = ToolLearner()
