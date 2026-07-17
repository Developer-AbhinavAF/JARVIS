"""Estimation Engine — Predict task cost before execution.

Estimates:
- Execution Time
- Memory Usage
- Network Usage
- Expected Accuracy
- Risk
- Confidence

Display estimates when useful.
"""

from __future__ import annotations

import logging
from typing import Any

from .task_graph import TaskNode, TaskType

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# TASK ESTIMATES
# ════════════════════════════════════════════════════════════════════

# Baseline estimates by task type (intent → {duration_ms, memory_mb, risk})
_TASK_ESTIMATES: dict[str, dict[str, float]] = {
    # Quick actions (< 500ms)
    "GREETING": {"duration_ms": 50, "memory_mb": 10, "risk": 0.0},
    "DATETIME": {"duration_ms": 20, "memory_mb": 5, "risk": 0.0},
    "CALCULATOR": {"duration_ms": 100, "memory_mb": 10, "risk": 0.0},
    "FLIP_COIN": {"duration_ms": 20, "memory_mb": 5, "risk": 0.0},
    "DICE_ROLL": {"duration_ms": 20, "memory_mb": 5, "risk": 0.0},
    "SCREENSHOT": {"duration_ms": 300, "memory_mb": 50, "risk": 0.1},

    # App operations (200ms - 3s)
    "OPEN_APP": {"duration_ms": 1000, "memory_mb": 50, "risk": 0.1},
    "CLOSE_APP": {"duration_ms": 500, "memory_mb": 20, "risk": 0.1},
    "VOLUME_CONTROL": {"duration_ms": 200, "memory_mb": 10, "risk": 0.05},
    "BRIGHTNESS_CONTROL": {"duration_ms": 200, "memory_mb": 10, "risk": 0.05},
    "WINDOW_CONTROL": {"duration_ms": 300, "memory_mb": 20, "risk": 0.05},
    "SYSTEM_POWER": {"duration_ms": 500, "memory_mb": 10, "risk": 0.8},

    # Web operations (1-10s)
    "WEB_SEARCH": {"duration_ms": 3000, "memory_mb": 100, "risk": 0.1},
    "SEARCH_ON_PLATFORM": {"duration_ms": 4000, "memory_mb": 100, "risk": 0.1},
    "SEARCH_YOUTUBE": {"duration_ms": 5000, "memory_mb": 150, "risk": 0.1},
    "GET_NEWS": {"duration_ms": 4000, "memory_mb": 100, "risk": 0.1},
    "GET_WEATHER": {"duration_ms": 2000, "memory_mb": 50, "risk": 0.05},
    "OPEN_WEBSITE": {"duration_ms": 2000, "memory_mb": 100, "risk": 0.1},

    # Media (2-5s)
    "PLAY_MUSIC": {"duration_ms": 3000, "memory_mb": 200, "risk": 0.1},
    "PAUSE_MUSIC": {"duration_ms": 500, "memory_mb": 50, "risk": 0.05},
    "NEXT_TRACK": {"duration_ms": 500, "memory_mb": 50, "risk": 0.05},
    "STOCK_QUOTE": {"duration_ms": 3000, "memory_mb": 50, "risk": 0.05},

    # File operations (500ms - 5s)
    "FILE_MANAGEMENT": {"duration_ms": 1000, "memory_mb": 50, "risk": 0.3},
    "CREATE_FILE": {"duration_ms": 500, "memory_mb": 20, "risk": 0.2},
    "DELETE_FILE": {"duration_ms": 500, "memory_mb": 20, "risk": 0.6},
    "OPEN_FILE": {"duration_ms": 1000, "memory_mb": 100, "risk": 0.1},

    # Programming (5-30s)
    "PROGRAMMING": {"duration_ms": 10000, "memory_mb": 500, "risk": 0.3},
    "VERSION_CONTROL": {"duration_ms": 5000, "memory_mb": 200, "risk": 0.2},
    "OPEN_VSCODE": {"duration_ms": 3000, "memory_mb": 300, "risk": 0.1},
    "OPEN_TERMINAL": {"duration_ms": 1000, "memory_mb": 50, "risk": 0.1},

    # System (1-10s)
    "SYSTEM_STATUS": {"duration_ms": 2000, "memory_mb": 50, "risk": 0.05},
    "CLIPBOARD": {"duration_ms": 200, "memory_mb": 10, "risk": 0.05},

    # Memory (100ms - 1s)
    "SAVE_MEMORY": {"duration_ms": 200, "memory_mb": 20, "risk": 0.05},
    "RECALL_MEMORY": {"duration_ms": 300, "memory_mb": 20, "risk": 0.0},
}


# ════════════════════════════════════════════════════════════════════
# ESTIMATION ENGINE
# ════════════════════════════════════════════════════════════════════

class EstimationEngine:
    """Estimates task cost and feasibility before execution.

    Uses historical data and task characteristics to predict:
    - How long a task will take
    - How much memory it needs
    - Whether it's likely to succeed
    - What the risk level is
    """

    def __init__(self) -> None:
        self._history: dict[str, list[dict[str, float]]] = {}  # intent → [past estimates]

    def estimate_task(self, task: TaskNode) -> TaskNode:
        """Estimate and populate task cost fields.

        Returns the task with estimates filled in.
        """
        intent = task.intent or task.name

        # Get baseline estimate
        baseline = _TASK_ESTIMATES.get(intent, {
            "duration_ms": 2000.0,
            "memory_mb": 100.0,
            "risk": 0.2,
        })

        # Adjust with historical data
        historical = self._history.get(intent, [])
        if historical:
            avg_duration = sum(h["duration_ms"] for h in historical) / len(historical)
            avg_risk = sum(h.get("risk", 0.2) for h in historical) / len(historical)
            # Blend: 60% baseline, 40% historical
            task.estimated_duration_ms = baseline["duration_ms"] * 0.6 + avg_duration * 0.4
            task.estimated_risk = baseline["risk"] * 0.6 + avg_risk * 0.4
        else:
            task.estimated_duration_ms = baseline["duration_ms"]
            task.estimated_risk = baseline["risk"]

        task.estimated_memory_mb = baseline["memory_mb"]
        task.confidence = self._estimate_confidence(task)

        return task

    def estimate_plan(self, tasks: list[TaskNode]) -> dict[str, Any]:
        """Estimate total plan cost."""
        total_duration = 0.0
        total_memory = 0.0
        max_risk = 0.0
        critical_path_ms = 0.0

        for task in tasks:
            total_duration += task.estimated_duration_ms
            total_memory = max(total_memory, task.estimated_memory_mb)
            max_risk = max(max_risk, task.estimated_risk)

        # Rough critical path (actual requires DAG analysis)
        critical_path_ms = total_duration * 0.7  # Heuristic

        return {
            "total_tasks": len(tasks),
            "total_estimated_ms": round(total_duration, 1),
            "critical_path_ms": round(critical_path_ms, 1),
            "max_memory_mb": round(total_memory, 0),
            "max_risk": round(max_risk, 2),
            "estimated_accuracy": self._overall_accuracy(tasks),
        }

    def record_actual(self, intent: str, duration_ms: float, risk: float = 0.0) -> None:
        """Record actual execution for future estimation."""
        if intent not in self._history:
            self._history[intent] = []
        self._history[intent].append({"duration_ms": duration_ms, "risk": risk})
        if len(self._history[intent]) > 50:
            self._history[intent] = self._history[intent][-30:]

    def _estimate_confidence(self, task: TaskNode) -> float:
        """Estimate confidence that the task will succeed."""
        confidence = 0.7  # Base

        # Historical success improves confidence
        history = self._history.get(task.intent or task.name, [])
        if history:
            confidence = min(0.95, confidence + len(history) * 0.02)

        # Risk reduces confidence
        confidence *= (1.0 - task.estimated_risk * 0.3)

        # Complex tasks are less certain
        if task.task_type == TaskType.RESEARCH:
            confidence *= 0.85
        elif task.task_type == TaskType.ANALYSIS:
            confidence *= 0.9

        return max(0.3, min(0.95, confidence))

    def _overall_accuracy(self, tasks: list[TaskNode]) -> float:
        """Estimate overall plan accuracy."""
        if not tasks:
            return 1.0
        return sum(t.confidence for t in tasks) / len(tasks)

    def get_stats(self) -> dict[str, Any]:
        return {
            "intents_tracked": len(self._history),
            "total_records": sum(len(v) for v in self._history.values()),
        }
