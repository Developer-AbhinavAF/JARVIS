"""Background Learning — Runs learning tasks without interrupting interaction.

Analyzing User Habits...
Compressing Memories...
Optimizing Knowledge Graph...
Learning Repository...
Improving Workflow Models...
Updating Preferences...

These tasks should never interrupt interaction.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LearningTask:
    """A background learning task."""
    task_id: str = ""
    name: str = ""
    category: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0


class BackgroundLearningCoordinator:
    """Coordinates background learning tasks."""

    def __init__(self, max_concurrent: int = 2) -> None:
        self._max_concurrent = max_concurrent
        self._tasks: dict[str, LearningTask] = {}
        self._task_counter: int = 0
        self._lock = threading.Lock()

    def submit(
        self,
        name: str,
        func: Callable[[], dict[str, Any]],
        category: str = "general",
    ) -> LearningTask:
        """Submit a learning task for background execution."""
        self._task_counter += 1
        task = LearningTask(
            task_id=f"blt_{self._task_counter:04d}",
            name=name,
            category=category,
        )
        self._tasks[task.task_id] = task

        thread = threading.Thread(
            target=self._run_task,
            args=(task, func),
            daemon=True,
            name=f"learn-{task.task_id}",
        )
        thread.start()
        return task

    def _run_task(self, task: LearningTask, func: Callable) -> None:
        """Execute a learning task in a background thread."""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        try:
            result = func()
            task.result = result if isinstance(result, dict) else {}
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error("Background learning task failed: %s", e)
        task.completed_at = time.time()

    def get_task(self, task_id: str) -> LearningTask | None:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[dict[str, Any]]:
        return [
            {
                "task_id": t.task_id,
                "name": t.name,
                "category": t.category,
                "status": t.status.value,
                "progress": t.progress,
            }
            for t in self._tasks.values()
        ]

    def get_active_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_tasks": len(self._tasks),
            "active": self.get_active_count(),
            "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED),
        }


background_coordinator = BackgroundLearningCoordinator()

__all__ = ["BackgroundLearningCoordinator", "LearningTask", "TaskStatus", "background_coordinator"]
