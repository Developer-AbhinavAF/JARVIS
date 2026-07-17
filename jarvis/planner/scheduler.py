"""Task Scheduler — Delayed, periodic, and persistent scheduling.

Examples:
- Remind me tomorrow
- Run backup every Sunday
- Index Downloads every night
- Learn new notes after school
- Check GitHub every morning

Tasks should persist across sessions.
"""

from __future__ import annotations

import json
import time
import logging
import threading
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_SCHEDULE_FILE = _DATA_DIR / "scheduled_tasks.json"


# ════════════════════════════════════════════════════════════════════
# SCHEDULED TASK
# ════════════════════════════════════════════════════════════════════

class ScheduleType(Enum):
    ONCE = "once"              # Run once at specific time
    DAILY = "daily"            # Run every day
    WEEKLY = "weekly"          # Run every week
    INTERVAL = "interval"      # Run every N seconds
    CRON = "cron"              # Cron-like pattern


@dataclass
class ScheduledTask:
    """A task scheduled for future or periodic execution."""
    task_id: str = ""
    name: str = ""
    description: str = ""

    # Schedule
    schedule_type: ScheduleType = ScheduleType.ONCE
    interval_seconds: float = 0.0
    next_run: float = 0.0        # Unix timestamp
    last_run: float = 0.0
    run_count: int = 0
    max_runs: int = -1           # -1 = unlimited

    # Execution
    intent: str = ""
    handler: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    text: str = ""               # Original user text

    # State
    enabled: bool = True
    paused: bool = False
    last_error: str = ""

    # Metadata
    created_at: float = 0.0
    created_by: str = "user"

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()

    @property
    def is_due(self) -> bool:
        """Check if this task is due to run."""
        if not self.enabled or self.paused:
            return False
        if self.max_runs > 0 and self.run_count >= self.max_runs:
            return False
        return time.time() >= self.next_run

    def mark_run(self) -> None:
        """Mark the task as having been run."""
        self.last_run = time.time()
        self.run_count += 1
        if self.schedule_type == ScheduleType.ONCE:
            self.enabled = False
        elif self.schedule_type == ScheduleType.INTERVAL:
            self.next_run = time.time() + self.interval_seconds
        elif self.schedule_type == ScheduleType.DAILY:
            self.next_run = time.time() + 86400
        elif self.schedule_type == ScheduleType.WEEKLY:
            self.next_run = time.time() + 604800

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "schedule_type": self.schedule_type.value,
            "interval_seconds": self.interval_seconds,
            "next_run": self.next_run,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "intent": self.intent,
            "text": self.text,
            "enabled": self.enabled,
            "paused": self.paused,
        }


# ════════════════════════════════════════════════════════════════════
# TASK SCHEDULER
# ════════════════════════════════════════════════════════════════════

class TaskScheduler:
    """Manages delayed and periodic task scheduling.

    - Stores scheduled tasks persistently
    - Runs a background loop to check for due tasks
    - Executes tasks when they're due
    - Supports one-time, daily, weekly, and interval schedules
    """

    def __init__(self) -> None:
        self._scheduled: dict[str, ScheduledTask] = {}
        self._executor: Callable | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._callbacks: dict[str, Callable] = {}
        self._load()

    def set_executor(self, executor: Callable) -> None:
        """Set the function to call when a scheduled task is due."""
        self._executor = executor

    def schedule(
        self,
        name: str,
        text: str,
        schedule_type: ScheduleType = ScheduleType.ONCE,
        next_run: float = 0.0,
        interval_seconds: float = 0.0,
        intent: str = "",
        handler: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> ScheduledTask:
        """Schedule a new task."""
        import uuid
        task = ScheduledTask(
            task_id=f"sched_{uuid.uuid4().hex[:8]}",
            name=name,
            description=text,
            schedule_type=schedule_type,
            next_run=next_run or time.time(),
            interval_seconds=interval_seconds,
            intent=intent,
            handler=handler,
            parameters=parameters or {},
            text=text,
        )
        self._scheduled[task.task_id] = task
        self._save()
        return task

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        task = self._scheduled.get(task_id)
        if task:
            task.enabled = False
            self._save()
            return True
        return False

    def pause(self, task_id: str) -> bool:
        task = self._scheduled.get(task_id)
        if task:
            task.paused = True
            self._save()
            return True
        return False

    def resume(self, task_id: str) -> bool:
        task = self._scheduled.get(task_id)
        if task:
            task.paused = False
            self._save()
            return True
        return False

    def get_due_tasks(self) -> list[ScheduledTask]:
        """Get all tasks that are due to run."""
        return [t for t in self._scheduled.values() if t.is_due]

    def get_all(self) -> list[ScheduledTask]:
        return list(self._scheduled.values())

    def start(self) -> None:
        """Start the scheduler loop in background."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        """Background loop checking for due tasks every 10 seconds."""
        while self._running:
            due = self.get_due_tasks()
            for task in due:
                self._execute_task(task)
            time.sleep(10)

    def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        if self._executor:
            try:
                self._executor(task)
                task.mark_run()
                self._save()
            except Exception as e:
                task.last_error = str(e)
                logger.error("Scheduled task failed: %s — %s", task.name, e)
        else:
            logger.warning("No executor set for scheduled tasks")

    def _save(self) -> None:
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "tasks": [t.to_dict() for t in self._scheduled.values()],
                "saved_at": time.time(),
            }
            _SCHEDULE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("Failed to save scheduled tasks: %s", e)

    def _load(self) -> None:
        try:
            if _SCHEDULE_FILE.exists():
                data = json.loads(_SCHEDULE_FILE.read_text())
                for t_data in data.get("tasks", []):
                    st = ScheduledTask(
                        task_id=t_data.get("task_id", ""),
                        name=t_data.get("name", ""),
                        description=t_data.get("description", ""),
                        schedule_type=ScheduleType(t_data.get("schedule_type", "once")),
                        interval_seconds=t_data.get("interval_seconds", 0),
                        next_run=t_data.get("next_run", 0),
                        last_run=t_data.get("last_run", 0),
                        run_count=t_data.get("run_count", 0),
                        intent=t_data.get("intent", ""),
                        text=t_data.get("text", ""),
                        enabled=t_data.get("enabled", True),
                        paused=t_data.get("paused", False),
                    )
                    self._scheduled[st.task_id] = st
        except Exception as e:
            logger.debug("Failed to load scheduled tasks: %s", e)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_scheduled": len(self._scheduled),
            "enabled": sum(1 for t in self._scheduled.values() if t.enabled),
            "paused": sum(1 for t in self._scheduled.values() if t.paused),
            "due_now": len(self.get_due_tasks()),
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

task_scheduler = TaskScheduler()
