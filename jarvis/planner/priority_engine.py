"""Priority Engine — Multi-factor priority scoring.

Each task receives a priority score based on:
- User Goal alignment
- Urgency
- Dependencies (blocking others)
- Execution Time
- System Resources
- Background Tasks
- User Preferences

High priority tasks execute first.
"""

from __future__ import annotations

import logging
from typing import Any

from .task_graph import TaskNode, TaskPriority, TaskState

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# PRIORITY FACTORS
# ════════════════════════════════════════════════════════════════════

class PriorityFactor:
    """Individual scoring factors with weights."""
    GOAL_ALIGNMENT = ("goal_alignment", 0.20)      # How aligned with user goal
    URGENCY = ("urgency", 0.15)                      # Time sensitivity
    DEPENDENCY_IMPACT = ("dependency_impact", 0.20)  # How many tasks it blocks
    ESTIMATED_DURATION = ("estimated_duration", 0.10)  # Shorter = higher priority
    RISK = ("risk", 0.10)                            # Lower risk = higher priority
    CONFIDENCE = ("confidence", 0.10)                # Higher confidence = higher
    USER_PREFERENCE = ("user_preference", 0.10)      # Learned preference
    RESOURCE_CONTENTION = ("resource_contention", 0.05)  # Low resource use = higher


# ════════════════════════════════════════════════════════════════════
# PRIORITY ENGINE
# ════════════════════════════════════════════════════════════════════

class PriorityEngine:
    """Calculates and manages task priorities.

    Assigns a composite score (0-100) to each task based on multiple factors.
    Re-ranks tasks dynamically as conditions change.
    """

    def __init__(self) -> None:
        self._weight_overrides: dict[str, float] = {}
        self._priority_history: list[dict[str, Any]] = []

    def score_task(
        self,
        task: TaskNode,
        goal: str = "",
        total_tasks: int = 1,
        system_load: float = 0.0,
    ) -> float:
        """Calculate priority score for a task (0-100).

        Args:
            task: The task to score.
            goal: The user's overall goal.
            total_tasks: Total number of tasks in the plan.
            system_load: Current system load (0-1).

        Returns:
            Priority score from 0 (lowest) to 100 (highest).
        """
        scores = {}

        # Goal alignment
        scores["goal_alignment"] = self._score_goal_alignment(task, goal)

        # Urgency
        scores["urgency"] = self._score_urgency(task)

        # Dependency impact
        scores["dependency_impact"] = self._score_dependency_impact(task, total_tasks)

        # Duration (shorter tasks get priority for quick wins)
        scores["estimated_duration"] = self._score_duration(task)

        # Risk (lower risk = higher priority)
        scores["risk"] = self._score_risk(task)

        # Confidence
        scores["confidence"] = task.confidence * 100

        # User preference — look up from memory/settings, default to 50
        pref_score = 50.0
        try:
            from jarvis.memory import JarvisMemory
            mem = JarvisMemory()
            prefs = mem.get_all_preferences("task_priority")
            task_key = f"priority_{task.task_type}"
            if task_key in prefs:
                pref_score = float(prefs[task_key])
            elif task.task_type in prefs:
                pref_score = float(prefs[task.task_type])
        except Exception:
            pass
        scores["user_preference"] = pref_score

        # Resource contention
        scores["resource_contention"] = max(0, 100 - system_load * 100)

        # Weighted sum
        total_score = 0.0
        total_weight = 0.0
        for val in PriorityFactor.__dict__.values():
            if isinstance(val, tuple) and len(val) == 2:
                name, w = val
                override = self._weight_overrides.get(name, w)
                score = scores.get(name, 50.0)
                total_score += score * override
                total_weight += override

        final_score = total_score / total_weight if total_weight > 0 else 50.0
        return min(100.0, max(0.0, final_score))

    def rank_tasks(
        self,
        tasks: list[TaskNode],
        goal: str = "",
        system_load: float = 0.0,
    ) -> list[TaskNode]:
        """Rank tasks by priority score (highest first)."""
        total = len(tasks)
        scored = []
        for task in tasks:
            score = self.score_task(task, goal, total, system_load)
            scored.append((score, task))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [task for _, task in scored]

    def assign_priority_level(self, score: float) -> TaskPriority:
        """Convert numeric score to priority level."""
        if score >= 85:
            return TaskPriority.CRITICAL
        if score >= 65:
            return TaskPriority.HIGH
        if score >= 40:
            return TaskPriority.NORMAL
        if score >= 20:
            return TaskPriority.LOW
        return TaskPriority.BACKGROUND

    def re_rank_after_completion(
        self,
        completed_task: TaskNode,
        remaining_tasks: list[TaskNode],
        goal: str = "",
    ) -> list[TaskNode]:
        """Re-rank remaining tasks after a task completes.

        Tasks that were blocked by the completed task may now be ready
        and should get a priority boost.
        """
        # Boost tasks that depend on the completed task
        boosted = []
        for task in remaining_tasks:
            if completed_task.task_id in task.depends_on:
                task.priority = TaskPriority.HIGH
                boosted.append(task)

        # Re-rank everything
        return self.rank_tasks(remaining_tasks, goal)

    def set_weight(self, factor_name: str, weight: float) -> None:
        """Override a priority factor weight."""
        self._weight_overrides[factor_name] = max(0.0, min(1.0, weight))

    def _score_goal_alignment(self, task: TaskNode, goal: str) -> float:
        """Score how well the task aligns with the user's goal."""
        if not goal:
            return 50.0
        goal_lower = goal.lower()
        task_text = f"{task.name} {task.description} {task.intent}".lower()
        # Simple keyword overlap
        goal_words = set(goal_lower.split())
        task_words = set(task_text.split())
        if not goal_words:
            return 50.0
        overlap = len(goal_words & task_words)
        return min(100.0, (overlap / len(goal_words)) * 100)

    @staticmethod
    def _score_urgency(task: TaskNode) -> float:
        """Score urgency based on task type and metadata."""
        if task.task_type.value == "decision":
            return 80.0  # Decisions often block everything
        if task.priority == TaskPriority.CRITICAL:
            return 95.0
        if task.priority == TaskPriority.HIGH:
            return 75.0
        if task.priority == TaskPriority.LOW:
            return 25.0
        return 50.0

    @staticmethod
    def _score_dependency_impact(task: TaskNode, total_tasks: int) -> float:
        """Score based on how many downstream tasks this blocks."""
        if total_tasks <= 1:
            return 50.0
        blocking_count = len(task.blocks)
        impact = (blocking_count / max(total_tasks - 1, 1)) * 100
        return min(100.0, impact + 30)  # Base 30 + impact

    @staticmethod
    def _score_duration(task: TaskNode) -> float:
        """Shorter tasks get priority (quick wins)."""
        ms = task.estimated_duration_ms
        if ms <= 100:
            return 90.0
        if ms <= 500:
            return 75.0
        if ms <= 2000:
            return 50.0
        if ms <= 10000:
            return 30.0
        return 15.0

    @staticmethod
    def _score_risk(task: TaskNode) -> float:
        """Lower risk = higher priority score."""
        return max(0.0, (1.0 - task.estimated_risk) * 100)

    def get_stats(self) -> dict[str, Any]:
        return {
            "weight_overrides": self._weight_overrides,
            "history_count": len(self._priority_history),
        }
