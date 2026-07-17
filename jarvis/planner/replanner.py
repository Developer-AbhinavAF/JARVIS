"""Dynamic Replanner — Adapts when conditions change.

If conditions change:
- Internet Lost → Choose Offline Strategy
- API Limit Reached → Switch Provider
- Repository Deleted → Search Mirror
- File Missing → Search Entire Disk

The planner should automatically adapt.
"""

from __future__ import annotations

import logging
from typing import Any

from .task_graph import TaskGraph, TaskNode, TaskState

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# CONDITION CHANGES
# ════════════════════════════════════════════════════════════════════

class ConditionChange:
    """Represents a change in execution conditions."""
    INTERNET_LOST = "internet_lost"
    INTERNET_RESTORED = "internet_restored"
    API_LIMIT = "api_limit"
    FILE_NOT_FOUND = "file_not_found"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    TOOL_FAILED = "tool_failed"
    USER_CANCELLED = "user_cancelled"
    SYSTEM_BUSY = "system_busy"
    PRIORITY_CHANGED = "priority_changed"
    DEADLINE_APPROACHING = "deadline_approaching"


# ════════════════════════════════════════════════════════════════════
# DYNAMIC REPLANNER
# ════════════════════════════════════════════════════════════════════

class DynamicReplanner:
    """Adapts execution plans when conditions change.

    Monitors for condition changes and automatically modifies
    the execution plan to handle new realities.
    """

    def __init__(self) -> None:
        self._adaptation_history: list[dict[str, Any]] = []
        self._adaptation_rules: dict[str, list[dict[str, Any]]] = {
            ConditionChange.INTERNET_LOST: [
                {"action": "switch_to_offline", "description": "Use offline tools"},
                {"action": "pause_network_tasks", "description": "Pause tasks needing internet"},
                {"action": "notify_user", "description": "Inform user of limitation"},
            ],
            ConditionChange.API_LIMIT: [
                {"action": "switch_provider", "description": "Try alternative API"},
                {"action": "use_cached", "description": "Use cached results"},
                {"action": "queue_for_later", "description": "Queue when limit resets"},
            ],
            ConditionChange.FILE_NOT_FOUND: [
                {"action": "search_disk", "description": "Search entire disk"},
                {"action": "check_recycle", "description": "Check recycle bin"},
                {"action": "ask_user", "description": "Ask user for file location"},
            ],
            ConditionChange.TOOL_FAILED: [
                {"action": "use_fallback", "description": "Use recovery chain"},
                {"action": "try_alternative", "description": "Try alternative approach"},
                {"action": "skip_optional", "description": "Skip if optional"},
            ],
            ConditionChange.SYSTEM_BUSY: [
                {"action": "defer_heavy", "description": "Defer heavy tasks"},
                {"action": "prioritize_quick", "description": "Prioritize quick tasks"},
                {"action": "move_to_background", "description": "Move to background"},
            ],
            ConditionChange.USER_CANCELLED: [
                {"action": "pause_running", "description": "Pause running tasks"},
                {"action": "cancel_pending", "description": "Cancel pending tasks"},
                {"action": "save_state", "description": "Save current state"},
            ],
        }

    def handle_change(
        self,
        change_type: str,
        graph: TaskGraph,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle a condition change and replan.

        Returns:
            Dict with adaptations applied and new plan state.
        """
        context = context or {}
        rules = self._adaptation_rules.get(change_type, [])

        adaptations = []
        for rule in rules:
            action = rule["action"]
            result = self._apply_adaptation(action, graph, change_type, context)
            if result:
                adaptations.append(result)

        self._adaptation_history.append({
            "change": change_type,
            "adaptations": len(adaptations),
            "context": context,
        })

        return {
            "change_type": change_type,
            "adaptations": adaptations,
            "plan_modified": len(adaptations) > 0,
            "tasks_affected": sum(a.get("tasks_affected", 0) for a in adaptations),
        }

    def _apply_adaptation(
        self,
        action: str,
        graph: TaskGraph,
        change_type: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Apply a single adaptation action."""
        tasks_affected = 0

        if action == "switch_to_offline":
            for task in graph.get_all_tasks():
                if task.state == TaskState.PENDING and self._needs_internet(task):
                    task.handler = "offline_mode"
                    tasks_affected += 1

        elif action == "pause_network_tasks":
            for task in graph.get_all_tasks():
                if task.state == TaskState.RUNNING and self._needs_internet(task):
                    task.pause()
                    tasks_affected += 1

        elif action == "use_fallback":
            for task in graph.get_all_tasks():
                if task.state == TaskState.FAILED and task.recovery_chain:
                    next_fallback = task.recovery_chain[1] if len(task.recovery_chain) > 1 else None
                    if next_fallback:
                        task.handler = next_fallback.get("handler", task.handler)
                        task.state = TaskState.PENDING
                        task.retry_count += 1
                        tasks_affected += 1

        elif action == "defer_heavy":
            for task in graph.get_all_tasks():
                if (task.state == TaskState.PENDING
                        and task.estimated_duration_ms > 5000):
                    task.priority = TaskPriority.LOW
                    tasks_affected += 1

        elif action == "skip_optional":
            for task in graph.get_all_tasks():
                if task.state == TaskState.PENDING and task.optional:
                    task.skip()
                    tasks_affected += 1

        elif action == "cancel_pending":
            for task in graph.get_all_tasks():
                if task.state in (TaskState.PENDING, TaskState.READY):
                    task.cancel()
                    tasks_affected += 1

        elif action == "pause_running":
            for task in graph.get_all_tasks():
                if task.state == TaskState.RUNNING:
                    task.pause()
                    tasks_affected += 1

        elif action == "save_state":
            # State saving is handled externally
            tasks_affected = 0

        elif action == "notify_user":
            tasks_affected = 0

        if tasks_affected > 0:
            return {
                "action": action,
                "description": f"Applied: {action}",
                "tasks_affected": tasks_affected,
            }
        return None

    @staticmethod
    def _needs_internet(task: TaskNode) -> bool:
        """Check if a task requires internet."""
        internet_intents = {
            "WEB_SEARCH", "SEARCH_ON_PLATFORM", "SEARCH_YOUTUBE",
            "GET_NEWS", "GET_WEATHER", "OPEN_WEBSITE", "STOCK_QUOTE",
            "PLAY_MUSIC", "OPEN_APP",
        }
        return task.intent in internet_intents

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_adaptations": len(self._adaptation_history),
            "adaptation_rules": len(self._adaptation_rules),
        }


# Import TaskPriority here to avoid circular imports
from .task_graph import TaskPriority
