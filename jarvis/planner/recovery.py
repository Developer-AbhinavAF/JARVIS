"""Failure Planner — Recovery paths BEFORE execution.

Every task should have recovery paths:
Primary Tool → Alternative Tool → Alternative API →
Alternative Strategy → Cached Result → Ask User

Recovery planning happens before execution begins.
"""

from __future__ import annotations

import logging
from typing import Any

from .task_graph import TaskNode, TaskType

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# RECOVERY CHAINS
# ════════════════════════════════════════════════════════════════════

# Intent → list of fallback strategies (in order)
_RECOVERY_CHAINS: dict[str, list[dict[str, Any]]] = {
    "OPEN_APP": [
        {"handler": "jarvis.tools.open_app", "description": "Open with primary handler"},
        {"handler": "jarvis.tools.web_search", "description": "Search for app download"},
        {"handler": "os.startfile", "description": "Direct OS launch"},
    ],
    "WEB_SEARCH": [
        {"handler": "jarvis.tools.web_search", "description": "Web search"},
        {"handler": "jarvis.tools.search_on_platform", "description": "Platform search"},
        {"handler": "jarvis.tools.open_website", "description": "Open Google directly"},
    ],
    "SEARCH_ON_PLATFORM": [
        {"handler": "jarvis.tools.search_on_platform", "description": "Platform search"},
        {"handler": "jarvis.tools.web_search", "description": "General web search"},
        {"handler": "jarvis.tools.open_website", "description": "Open platform website"},
    ],
    "PLAY_MUSIC": [
        {"handler": "jarvis.tools.play_music", "description": "Play on default platform"},
        {"handler": "jarvis.tools.search_youtube", "description": "Search YouTube"},
        {"handler": "jarvis.tools.open_website", "description": "Open music website"},
    ],
    "GET_WEATHER": [
        {"handler": "jarvis.tools.get_weather", "description": "Weather API"},
        {"handler": "jarvis.tools.web_search", "description": "Search weather online"},
    ],
    "PROGRAMMING": [
        {"handler": "jarvis.tools.programming", "description": "Programming tool"},
        {"handler": "jarvis.tools.web_search", "description": "Search Stack Overflow"},
        {"handler": "jarvis.tools.open_vscode", "description": "Open in VS Code"},
    ],
    "FILE_MANAGEMENT": [
        {"handler": "jarvis.tools.file_management", "description": "File manager"},
        {"handler": "jarvis.tools.open_terminal", "description": "Terminal file ops"},
    ],
    "GET_NEWS": [
        {"handler": "jarvis.tools.get_news", "description": "News API"},
        {"handler": "jarvis.tools.search_on_platform", "description": "Search news sites"},
        {"handler": "jarvis.tools.web_search", "description": "General news search"},
    ],
    "SYSTEM_STATUS": [
        {"handler": "jarvis.tools.system_status", "description": "System status"},
        {"handler": "jarvis.tools.open_terminal", "description": "Terminal commands"},
    ],
    "SAVE_MEMORY": [
        {"handler": "jarvis.tools.save_memory", "description": "Memory save"},
        {"handler": "jarvis.tools.create_file", "description": "Save to file"},
    ],
}


# ════════════════════════════════════════════════════════════════════
# FAILURE PLANNER
# ════════════════════════════════════════════════════════════════════

class FailurePlanner:
    """Plans recovery paths before execution begins.

    For each task in the plan, attaches a recovery chain so that
    if execution fails, the system already knows what to try next.
    """

    def __init__(self) -> None:
        self._custom_chains: dict[str, list[dict[str, Any]]] = {}

    def plan_recovery(self, task: TaskNode) -> TaskNode:
        """Attach recovery chain to a task.

        Returns the task with recovery_chain populated.
        """
        intent = task.intent or task.name
        chain = self._custom_chains.get(intent) or _RECOVERY_CHAINS.get(intent, [])

        if not chain:
            # Default chain
            chain = [
                {"handler": task.handler, "description": "Primary handler"},
                {"handler": "jarvis.tools.web_search", "description": "Web search fallback"},
            ]

        task.recovery_chain = chain

        # Set fallback handler
        if len(chain) > 1:
            task.fallback_handler = chain[1].get("handler", "")

        return task

    def plan_all(self, tasks: list[TaskNode]) -> list[TaskNode]:
        """Plan recovery for all tasks."""
        for task in tasks:
            self.plan_recovery(task)
        return tasks

    def get_next_fallback(self, task: TaskNode) -> dict[str, Any] | None:
        """Get the next fallback strategy for a failed task."""
        current_handler = task.handler
        for i, step in enumerate(task.recovery_chain):
            if step.get("handler") == current_handler and i + 1 < len(task.recovery_chain):
                return task.recovery_chain[i + 1]
        return None

    def add_custom_chain(self, intent: str, chain: list[dict[str, Any]]) -> None:
        """Add a custom recovery chain for an intent."""
        self._custom_chains[intent] = chain

    def get_chain(self, intent: str) -> list[dict[str, Any]]:
        """Get the recovery chain for an intent."""
        return self._custom_chains.get(intent) or _RECOVERY_CHAINS.get(intent, [])

    def get_stats(self) -> dict[str, Any]:
        return {
            "builtin_chains": len(_RECOVERY_CHAINS),
            "custom_chains": len(self._custom_chains),
        }
