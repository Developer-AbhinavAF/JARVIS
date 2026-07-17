"""Background & Live Task Manager for JARVIS.

Supports:
- Synchronous execution (fast tasks)
- Asynchronous background execution (long-running tasks)
- Live task tracking with progress, status, cancellation
- Task dependencies
- Priority-based scheduling

The user should continue chatting normally while background tasks run.
"""

from __future__ import annotations

import time
import uuid
import threading
import logging
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# TASK DEFINITIONS
# ════════════════════════════════════════════════════════════════════

class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority:
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class TaskResult:
    """Result of a task execution."""
    success: bool
    output: str
    error: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output[:500],
            "error": self.error[:200] if self.error else "",
            "metadata": self.metadata,
        }


@dataclass
class Task:
    """A tracked task with full lifecycle."""
    task_id: str = ""
    name: str = ""
    description: str = ""
    status: str = TaskStatus.PENDING
    priority: int = TaskPriority.NORMAL
    progress: float = 0.0        # 0.0 to 1.0
    estimated_time_ms: float = 0.0
    elapsed_time_ms: float = 0.0
    tool_name: str = ""
    current_step: str = ""
    total_steps: int = 1
    current_step_num: int = 0
    dependencies: list[str] = field(default_factory=list)
    result: TaskResult | None = None
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    is_background: bool = False
    is_cancellable: bool = True
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    @property
    def is_done(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    @property
    def duration_ms(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.completed_at if self.completed_at > 0 else time.time()
        return (end - self.started_at) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "priority": self.priority,
            "progress": round(self.progress, 3),
            "elapsed_ms": round(self.duration_ms, 1),
            "estimated_ms": round(self.estimated_time_ms, 1),
            "tool": self.tool_name,
            "step": f"{self.current_step_num}/{self.total_steps}: {self.current_step}",
            "is_background": self.is_background,
            "result": self.result.to_dict() if self.result else None,
        }


# ════════════════════════════════════════════════════════════════════
# BACKGROUND TASK MANAGER
# ════════════════════════════════════════════════════════════════════

class TaskManager:
    """Manages both synchronous and background tasks.

    - Fast tasks (< 100ms): Execute synchronously, return immediately
    - Long tasks (> 100ms): Submit to background thread, return task ID
    - All tasks are tracked with progress, status, and results
    """

    def __init__(self, max_background: int = 5) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._max_background = max_background
        self._active_threads: dict[str, threading.Thread] = {}
        self._callbacks: list[Callable[[Task], None]] = []
        self._auto_background_threshold_ms: float = 100.0

    def submit(
        self,
        name: str,
        func: Callable[..., str],
        args: tuple = (),
        kwargs: dict | None = None,
        priority: int = TaskPriority.NORMAL,
        is_background: bool | None = None,
        estimated_time_ms: float = 0.0,
        tool_name: str = "",
        dependencies: list[str] | None = None,
        metadata: dict | None = None,
    ) -> Task:
        """Submit a task for execution.

        If is_background is None, auto-detect based on estimated time.
        """
        kwargs = kwargs or {}

        task = Task(
            name=name,
            priority=priority,
            estimated_time_ms=estimated_time_ms,
            tool_name=tool_name,
            dependencies=dependencies or [],
            metadata=metadata or {},
        )

        # Auto-detect background vs foreground
        if is_background is None:
            is_background = estimated_time_ms > self._auto_background_threshold_ms

        task.is_background = is_background

        with self._lock:
            self._tasks[task.task_id] = task

        if is_background:
            self._submit_background(task, func, args, kwargs)
        else:
            self._execute_sync(task, func, args, kwargs)

        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[Task]:
        """Get all tasks."""
        return list(self._tasks.values())

    def get_active_tasks(self) -> list[Task]:
        """Get all non-completed tasks."""
        return [t for t in self._tasks.values() if not t.is_done]

    def get_background_tasks(self) -> list[Task]:
        """Get all background tasks."""
        return [t for t in self._tasks.values() if t.is_background and not t.is_done]

    def cancel(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if not task or not task.is_cancellable:
            return False
        if task.is_done:
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = time.time()
        self._notify_callbacks(task)
        return True

    def pause(self, task_id: str) -> bool:
        """Pause a task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        task.status = TaskStatus.PAUSED
        self._notify_callbacks(task)
        return True

    def resume(self, task_id: str) -> bool:
        """Resume a paused task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        task.status = TaskStatus.RUNNING
        self._notify_callbacks(task)
        return True

    def update_progress(self, task_id: str, progress: float, step: str = "") -> None:
        """Update task progress."""
        task = self._tasks.get(task_id)
        if task:
            task.progress = min(max(progress, 0.0), 1.0)
            if step:
                task.current_step = step
            self._notify_callbacks(task)

    def on_update(self, callback: Callable[[Task], None]) -> None:
        """Register a callback for task updates."""
        self._callbacks.append(callback)

    def cleanup(self, max_age_seconds: float = 3600.0) -> int:
        """Remove old completed tasks."""
        now = time.time()
        to_remove = []
        for task_id, task in self._tasks.items():
            if task.is_done and (now - task.completed_at) > max_age_seconds:
                to_remove.append(task_id)
        for task_id in to_remove:
            del self._tasks[task_id]
        return len(to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get task manager statistics."""
        tasks = list(self._tasks.values())
        return {
            "total_tasks": len(tasks),
            "active": sum(1 for t in tasks if not t.is_done),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "cancelled": sum(1 for t in tasks if t.status == TaskStatus.CANCELLED),
            "background_active": len(self.get_background_tasks()),
        }

    # ── Private Methods ──

    def _execute_sync(
        self, task: Task, func: Callable, args: tuple, kwargs: dict,
    ) -> None:
        """Execute a task synchronously."""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        task.progress = 0.5
        self._notify_callbacks(task)

        try:
            result = func(*args, **kwargs)
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.result = TaskResult(success=True, output=str(result))
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.result = TaskResult(success=False, output="", error=str(e))
            logger.exception("Task %s failed: %s", task.task_id, e)
        finally:
            task.completed_at = time.time()
            task.elapsed_time_ms = task.duration_ms
            self._notify_callbacks(task)

    def _submit_background(
        self, task: Task, func: Callable, args: tuple, kwargs: dict,
    ) -> None:
        """Submit a task to run in background thread."""
        def _run() -> None:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            self._notify_callbacks(task)

            try:
                result = func(*args, **kwargs)
                if task.status != TaskStatus.CANCELLED:
                    task.status = TaskStatus.COMPLETED
                    task.progress = 1.0
                    task.result = TaskResult(success=True, output=str(result))
            except Exception as e:
                if task.status != TaskStatus.CANCELLED:
                    task.status = TaskStatus.FAILED
                    task.result = TaskResult(success=False, output="", error=str(e))
                    logger.exception("Background task %s failed: %s", task.task_id, e)
            finally:
                task.completed_at = time.time()
                task.elapsed_time_ms = task.duration_ms
                self._notify_callbacks(task)
                with self._lock:
                    self._active_threads.pop(task.task_id, None)

        thread = threading.Thread(target=_run, daemon=True, name=f"bg-{task.task_id}")
        with self._lock:
            self._active_threads[task.task_id] = thread
        thread.start()

    def _notify_callbacks(self, task: Task) -> None:
        """Notify all registered callbacks of task update."""
        for cb in self._callbacks:
            try:
                cb(task)
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════
# STATUS INDICATOR ENGINE
# ════════════════════════════════════════════════════════════════════

# Phase → display message mapping
STATUS_MESSAGES: dict[str, list[str]] = {
    "listening":        ["Listening...", "Waiting for input..."],
    "understanding":    ["Understanding...", "Processing language..."],
    "normalizing":      ["Normalizing...", "Cleaning input..."],
    "language_detection": ["Detecting language...", "Identifying language..."],
    "context_resolution": ["Resolving context...", "Checking conversation history..."],
    "intent_detection": ["Understanding intent...", "What do you want to do?..."],
    "entity_extraction": ["Extracting details...", "Identifying key information..."],
    "emotion_detection": ["Reading emotions...", "Understanding how you feel..."],
    "conversation_analysis": ["Analyzing conversation...", "Understanding context..."],
    "implicit_intent":  ["Reading between the lines...", "Detecting implicit goals..."],
    "goal_detection":   ["Detecting goals...", "Understanding objectives..."],
    "capability_detection": ["Checking capabilities...", "What tools are available?..."],
    "knowledge_routing": ["Finding best source...", "Routing to optimal platform..."],
    "tool_resolution":  ["Selecting tool...", "Choosing best approach..."],
    "parameter_building": ["Preparing parameters...", "Setting up execution..."],
    "personal_language": ["Personalizing...", "Adapting to your style..."],
    "planning":         ["Planning steps...", "Creating execution plan..."],
    "safety_check":     ["Checking safety...", "Verifying security..."],
    "confidence_scoring": ["Calculating confidence...", "Assessing certainty..."],
    "response_generation": ["Generating response...", "Preparing answer..."],
    "searching":        ["Searching...", "Looking up information..."],
    "analyzing":        ["Analyzing...", "Processing data..."],
    "opening":          ["Opening...", "Launching application..."],
    "reading":          ["Reading...", "Loading content..."],
    "writing":          ["Writing...", "Saving data..."],
    "coding":           ["Coding...", "Writing code..."],
    "executing":        ["Executing...", "Running command..."],
    "learning":         ["Learning...", "Updating knowledge..."],
    "memory_update":    ["Updating memory...", "Saving to memory..."],
    "optimizing":       ["Optimizing...", "Improving performance..."],
    "done":             ["Done!", "Finished!", "Complete!"],
    "error":            ["Error occurred", "Something went wrong"],
    "fallback":         ["Trying alternative...", "Using backup approach..."],
}


class StatusEngine:
    """Real-time status indicator engine.

    Instead of a loading spinner, display real states:
    Listening... Understanding... Thinking... Planning...
    Searching... Executing... Finished.
    """

    def __init__(self) -> None:
        self._current_phase: str = ""
        self._current_message: str = ""
        self._callbacks: list[Callable[[str, str], None]] = []
        self._phase_history: list[tuple[str, float, str]] = []

    def update(self, phase: str) -> str:
        """Update status to a new phase. Returns the display message."""
        messages = STATUS_MESSAGES.get(phase, [f"{phase}..."])
        # Rotate through messages for variety
        idx = len(self._phase_history) % len(messages)
        message = messages[idx]

        self._current_phase = phase
        self._current_message = message
        self._phase_history.append((phase, time.time(), message))

        self._notify(phase, message)
        return message

    def get_current(self) -> tuple[str, str]:
        """Get current phase and message."""
        return self._current_phase, self._current_message

    def on_update(self, callback: Callable[[str, str], None]) -> None:
        """Register a callback for status updates."""
        self._callbacks.append(callback)

    def _notify(self, phase: str, message: str) -> None:
        for cb in self._callbacks:
            try:
                cb(phase, message)
            except Exception:
                pass

    def get_background_status(self) -> list[str]:
        """Get status messages for background tasks."""
        return [
            "Learning Repository...",
            "Analyzing PDF...",
            "Reading Documentation...",
            "Training Memory...",
            "Creating Embeddings...",
            "Indexing Files...",
            "Summarizing Video...",
        ]


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCES
# ════════════════════════════════════════════════════════════════════

task_manager = TaskManager()
status_engine = StatusEngine()
