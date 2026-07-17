"""Live Execution Dashboard — Expose planning progress through the UI.

Examples:
- Planning...
- Generating Task Graph...
- Analyzing Dependencies...
- Optimizing Workflow...
- Executing Step 3 of 12...
- Waiting for API...
- Learning in Background...
- Updating Knowledge...
- Completed.

Users should always know what the AI is doing.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# DASHBOARD PHASES
# ════════════════════════════════════════════════════════════════════

class DashboardPhase:
    IDLE = "idle"
    PLANNING = "planning"
    GENERATING_GRAPH = "generating_graph"
    ANALYZING_DEPENDENCIES = "analyzing_dependencies"
    OPTIMIZING = "optimizing"
    EXECUTING = "executing"
    WAITING = "waiting"
    PAUSED = "paused"
    RECOVERING = "recovering"
    LEARNING = "learning"
    COMPLETED = "completed"
    FAILED = "failed"

    # Phase → message template
    MESSAGES = {
        IDLE: "Ready.",
        PLANNING: "Planning...",
        GENERATING_GRAPH: "Generating task graph...",
        ANALYZING_DEPENDENCIES: "Analyzing dependencies...",
        OPTIMIZING: "Optimizing workflow...",
        EXECUTING: "Executing step {current} of {total}...",
        WAITING: "Waiting for {resource}...",
        PAUSED: "Paused — {reason}",
        RECOVERING: "Recovering from error...",
        LEARNING: "Learning in background...",
        COMPLETED: "Completed. {summary}",
        FAILED: "Failed: {error}",
    }


# ════════════════════════════════════════════════════════════════════
# DASHBOARD EVENT
# ════════════════════════════════════════════════════════════════════

@dataclass
class DashboardEvent:
    """A single dashboard update event."""
    phase: str = DashboardPhase.IDLE
    message: str = ""
    progress: float = 0.0       # 0-1
    current_step: int = 0
    total_steps: int = 0
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "message": self.message,
            "progress": round(self.progress, 3),
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "timestamp": self.timestamp,
        }


# ════════════════════════════════════════════════════════════════════
# EXECUTION DASHBOARD
# ════════════════════════════════════════════════════════════════════

class ExecutionDashboard:
    """Live progress dashboard for execution plans.

    Tracks the current phase, progress, and step information
    and broadcasts updates to the UI via callbacks.
    """

    def __init__(self) -> None:
        self._current_phase: str = DashboardPhase.IDLE
        self._progress: float = 0.0
        self._current_step: int = 0
        self._total_steps: int = 0
        self._callbacks: list[Callable[[DashboardEvent], None]] = []
        self._event_history: list[DashboardEvent] = []
        self._start_time: float = 0.0

    def update(
        self,
        phase: str,
        current_step: int = 0,
        total_steps: int = 0,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Update the dashboard with current progress."""
        self._current_phase = phase
        self._current_step = current_step
        self._total_steps = total_steps

        if total_steps > 0:
            self._progress = current_step / total_steps
        elif phase == DashboardPhase.COMPLETED:
            self._progress = 1.0

        # Build message
        if not message:
            template = DashboardPhase.MESSAGES.get(phase, phase)
            message = template.format(
                current=current_step,
                total=total_steps,
                resource=details.get("resource", "") if details else "",
                reason=details.get("reason", "") if details else "",
                error=details.get("error", "") if details else "",
                summary=details.get("summary", "") if details else "",
            )

        event = DashboardEvent(
            phase=phase,
            message=message,
            progress=self._progress,
            current_step=current_step,
            total_steps=total_steps,
            details=details or {},
        )

        self._event_history.append(event)
        if len(self._event_history) > 200:
            self._event_history = self._event_history[-100:]

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.debug("Dashboard callback error: %s", e)

    def start(self, total_steps: int = 0) -> None:
        """Start a new execution session."""
        self._start_time = time.time()
        self._total_steps = total_steps
        self._current_step = 0
        self._progress = 0.0
        self.update(DashboardPhase.PLANNING, total_steps=total_steps)

    def step(self, step: int, total: int = 0, message: str = "") -> None:
        """Report a step completion."""
        if total == 0:
            total = self._total_steps
        self.update(DashboardPhase.EXECUTING, step, total, message)

    def complete(self, summary: str = "") -> None:
        """Mark execution as complete."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        if not summary:
            summary = f"Done in {elapsed:.1f}s"
        self.update(DashboardPhase.COMPLETED, details={"summary": summary})

    def fail(self, error: str = "") -> None:
        """Mark execution as failed."""
        self.update(DashboardPhase.FAILED, details={"error": error})

    def on_update(self, callback: Callable[[DashboardEvent], None]) -> None:
        """Register a callback for dashboard updates."""
        self._callbacks.append(callback)

    def get_current(self) -> DashboardEvent:
        """Get the current dashboard state."""
        return DashboardEvent(
            phase=self._current_phase,
            progress=self._progress,
            current_step=self._current_step,
            total_steps=self._total_steps,
        )

    def get_history(self, limit: int = 50) -> list[DashboardEvent]:
        return self._event_history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "current_phase": self._current_phase,
            "progress": round(self._progress, 3),
            "total_events": len(self._event_history),
            "elapsed_ms": round((time.time() - self._start_time) * 1000, 1) if self._start_time else 0,
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

dashboard = ExecutionDashboard()
