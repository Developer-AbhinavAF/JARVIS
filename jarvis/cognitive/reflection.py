"""Reflection Engine for JARVIS Cognitive Architecture.

After every important task, reflect:
- Was this optimal?
- Could another tool be faster?
- Should memory update?
- Should workflow improve?
- Should preference change?

Reflection creates new experience.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# REFLECTION MODEL
# ════════════════════════════════════════════════════════════════════

@dataclass
class Reflection:
    """Post-task reflection insights."""
    task_id: str = ""
    intent: str = ""
    tool_used: str = ""
    success: bool = True
    latency_ms: float = 0.0

    # Reflection insights
    was_optimal: bool = True
    optimal_score: float = 0.8      # How optimal was the execution (0-1)
    could_use_faster_tool: bool = False
    suggested_alternative: str = ""
    should_update_memory: bool = False
    should_update_preference: bool = False
    should_improve_workflow: bool = False

    # Analysis
    issues_found: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    learning_points: list[str] = field(default_factory=list)

    # Metadata
    timestamp: float = 0.0
    context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "tool": self.tool_used,
            "success": self.success,
            "latency_ms": round(self.latency_ms, 1),
            "was_optimal": self.was_optimal,
            "optimal_score": round(self.optimal_score, 3),
            "suggested_alternative": self.suggested_alternative,
            "issues": self.issues_found,
            "improvements": self.improvements,
            "learning_points": self.learning_points,
        }


# ════════════════════════════════════════════════════════════════════
# REFLECTION ENGINE
# ════════════════════════════════════════════════════════════════════

class ReflectionEngine:
    """Reflects on task execution to improve future performance.

    After every important task, analyzes:
    - Was the execution optimal?
    - Could a different approach be better?
    - What should be remembered?
    - What patterns are emerging?
    """

    def __init__(self) -> None:
        self._reflections: list[Reflection] = []
        self._max_reflections: int = 500

    def reflect(
        self,
        intent: str,
        tool_used: str,
        success: bool,
        latency_ms: float = 0.0,
        response: str = "",
        context: dict[str, Any] | None = None,
        tool_health: float = 1.0,
    ) -> Reflection:
        """Reflect on a completed task.

        Args:
            intent: The intent that was executed.
            tool_used: The tool that was used.
            success: Whether execution succeeded.
            latency_ms: How long execution took.
            response: The response text.
            context: Execution context.
            tool_health: Health of the tool used.

        Returns:
            Reflection with insights and improvement suggestions.
        """
        context = context or {}

        reflection = Reflection(
            intent=intent,
            tool_used=tool_used,
            success=success,
            latency_ms=latency_ms,
            context=context,
        )

        # Analyze optimality
        reflection.optimal_score = self._score_optimality(
            intent, tool_used, success, latency_ms, tool_health,
        )
        reflection.was_optimal = reflection.optimal_score > 0.7

        # Check for faster alternatives
        reflection.could_use_faster_tool, reflection.suggested_alternative = (
            self._check_faster_alternative(tool_used, latency_ms)
        )

        # Check if memory should be updated
        reflection.should_update_memory = self._should_update_memory(
            intent, response, context,
        )

        # Check if preferences should be updated
        reflection.should_update_preference = self._should_update_preference(
            intent, tool_used, success,
        )

        # Check if workflow should be improved
        reflection.should_improve_workflow = self._should_improve_workflow(
            intent, tool_used, success, latency_ms,
        )

        # Identify issues
        reflection.issues_found = self._identify_issues(
            intent, tool_used, success, latency_ms, response,
        )

        # Generate improvements
        reflection.improvements = self._generate_improvements(
            reflection.issues_found, intent, tool_used,
        )

        # Extract learning points
        reflection.learning_points = self._extract_learning(
            intent, tool_used, success, latency_ms, reflection,
        )

        self._reflections.append(reflection)
        if len(self._reflections) > self._max_reflections:
            self._reflections = self._reflections[-self._max_reflections // 2:]

        return reflection

    def get_recent_reflections(self, limit: int = 10) -> list[Reflection]:
        """Get recent reflections."""
        return self._reflections[-limit:]

    def get_improvement_trend(self) -> dict[str, Any]:
        """Analyze improvement trend over time."""
        if len(self._reflections) < 2:
            return {"trend": "insufficient_data"}

        recent = self._reflections[-20:]
        older = self._reflections[-40:-20] if len(self._reflections) >= 40 else self._reflections[:20]

        recent_avg = sum(r.optimal_score for r in recent) / len(recent)
        older_avg = sum(r.optimal_score for r in older) / len(older) if older else recent_avg

        return {
            "trend": "improving" if recent_avg > older_avg else "stable" if recent_avg == older_avg else "declining",
            "recent_avg_score": round(recent_avg, 3),
            "older_avg_score": round(older_avg, 3),
            "total_reflections": len(self._reflections),
        }

    def get_stats(self) -> dict[str, Any]:
        if not self._reflections:
            return {"total_reflections": 0}
        return {
            "total_reflections": len(self._reflections),
            "optimal_rate": round(
                sum(1 for r in self._reflections if r.was_optimal) / len(self._reflections), 3,
            ),
            "avg_optimal_score": round(
                sum(r.optimal_score for r in self._reflections) / len(self._reflections), 3,
            ),
            "memory_update_suggestions": sum(1 for r in self._reflections if r.should_update_memory),
            "workflow_improvements": sum(1 for r in self._reflections if r.should_improve_workflow),
        }

    # ── Private Methods ──

    @staticmethod
    def _score_optimality(
        intent: str, tool: str, success: bool, latency_ms: float, health: float,
    ) -> float:
        """Score how optimal the execution was."""
        score = 0.5

        if success:
            score += 0.2
        else:
            score -= 0.2

        # Latency score
        if latency_ms < 100:
            score += 0.15
        elif latency_ms < 500:
            score += 0.1
        elif latency_ms > 2000:
            score -= 0.1

        # Health score
        score += health * 0.15

        return max(0.0, min(1.0, score))

    @staticmethod
    def _check_faster_alternative(tool: str, latency_ms: float) -> tuple[bool, str]:
        """Check if a faster alternative exists."""
        if latency_ms > 1000:
            # Suggest faster alternatives for slow tools
            faster_map = {
                "web_search": "direct_url",
                "play_music": "local_playlist",
                "open_app": "shortcut",
            }
            if tool in faster_map:
                return True, faster_map[tool]
        return False, ""

    @staticmethod
    def _should_update_memory(intent: str, response: str, context: dict) -> bool:
        """Check if memory should be updated based on the task."""
        # Remember successful searches
        if intent in ("WEB_SEARCH", "SEARCH_ON_PLATFORM") and response:
            return True
        # Remember user preferences expressed
        if intent in ("SAVE_MEMORY", "ADD_NOTE"):
            return True
        return False

    @staticmethod
    def _should_update_preference(intent: str, tool: str, success: bool) -> bool:
        """Check if user preferences should be updated."""
        # If a tool consistently works, prefer it
        return success and intent in (
            "OPEN_APP", "PLAY_MUSIC", "WEB_SEARCH", "OPEN_WEBSITE",
        )

    @staticmethod
    def _should_improve_workflow(intent: str, tool: str, success: bool, latency: float) -> bool:
        """Check if workflow should be improved."""
        if not success:
            return True
        if latency > 3000:
            return True
        return False

    @staticmethod
    def _identify_issues(
        intent: str, tool: str, success: bool, latency_ms: float, response: str,
    ) -> list[str]:
        """Identify issues in the execution."""
        issues = []
        if not success:
            issues.append(f"Tool {tool} failed for {intent}")
        if latency_ms > 2000:
            issues.append(f"Slow execution: {latency_ms:.0f}ms")
        if not response and success:
            issues.append("Empty response despite success")
        if len(response) > 500:
            issues.append("Response too long")
        return issues

    @staticmethod
    def _generate_improvements(
        issues: list[str], intent: str, tool: str,
    ) -> list[str]:
        """Generate improvement suggestions based on issues."""
        improvements = []
        for issue in issues:
            if "failed" in issue:
                improvements.append(f"Consider alternative tool for {intent}")
            elif "Slow" in issue:
                improvements.append(f"Optimize {tool} execution or use cache")
            elif "Empty response" in issue:
                improvements.append(f"Add fallback response for {intent}")
        return improvements

    @staticmethod
    def _extract_learning(
        intent: str, tool: str, success: bool, latency_ms: float, reflection: Reflection,
    ) -> list[str]:
        """Extract learning points from the reflection."""
        points = []
        if success and latency_ms < 100:
            points.append(f"Fast execution: {tool} for {intent} ({latency_ms:.0f}ms)")
        if reflection.could_use_faster_tool:
            points.append(f"Consider {reflection.suggested_alternative} for better performance")
        if reflection.should_update_preference:
            points.append(f"User prefers {tool} for {intent}")
        return points


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

reflection_engine = ReflectionEngine()
