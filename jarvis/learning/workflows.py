"""Workflow Learning — Learns sequences of user actions.

Observe sequences like:
  Open Browser -> Open GitHub -> Open VS Code -> Open Terminal -> Run Python
  Learn: Development Workflow.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Workflow:
    """A learned workflow pattern."""
    workflow_id: str = ""
    name: str = ""
    steps: list[str] = field(default_factory=list)
    frequency: int = 1
    confidence: float = 0.3
    avg_duration_seconds: float = 0.0
    category: str = ""
    last_observed: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "steps": self.steps,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 3),
            "category": self.category,
        }


class WorkflowLearner:
    """Learns multi-step workflow patterns."""

    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}
        self._current_session: list[dict[str, Any]] = []
        self._wf_counter: int = 0
        self._learn_count: int = 0

    def start_session(self) -> None:
        """Start observing a new workflow session."""
        self._current_session = []

    def record_step(self, action: str, tool: str = "", metadata: dict | None = None) -> None:
        """Record a step in the current session."""
        self._current_session.append({
            "action": action,
            "tool": tool,
            "time": time.time(),
            **(metadata or {}),
        })

    def end_session(self) -> Workflow | None:
        """End session and learn from the observed workflow."""
        if len(self._current_session) < 2:
            return None

        steps = [s["action"] for s in self._current_session]
        duration = self._current_session[-1]["time"] - self._current_session[0]["time"]

        wf_key = "->".join(steps)
        if wf_key in self._workflows:
            wf = self._workflows[wf_key]
            wf.frequency += 1
            wf.confidence = min(1.0, wf.frequency / 10)
            wf.avg_duration_seconds = (wf.avg_duration_seconds + duration) / 2
            wf.last_observed = time.time()
        else:
            self._wf_counter += 1
            wf = Workflow(
                workflow_id=f"wf_{self._wf_counter:04d}",
                name=f"Workflow: {steps[0]} -> ... -> {steps[-1]}",
                steps=steps,
                frequency=1,
                confidence=0.1,
                avg_duration_seconds=duration,
                category=self._categorize(steps),
            )
            self._workflows[wf_key] = wf

        self._learn_count += 1
        self._current_session = []
        return wf

    def get_workflows(self, min_confidence: float = 0.2) -> list[dict[str, Any]]:
        return sorted(
            [w.to_dict() for w in self._workflows.values() if w.confidence >= min_confidence],
            key=lambda w: -w["confidence"],
        )

    def suggest_next_step(self, current_steps: list[str]) -> str | None:
        """Suggest the next step based on learned workflows."""
        prefix = "->".join(current_steps)
        best_match = None
        best_conf = 0.0
        for key, wf in self._workflows.items():
            if key.startswith(prefix + "->"):
                remaining = key[len(prefix) + 2:].split("->")
                if remaining and wf.confidence > best_conf:
                    best_conf = wf.confidence
                    best_match = remaining[0]
        return best_match

    def _categorize(self, steps: list[str]) -> str:
        text = " ".join(steps).lower()
        if any(k in text for k in ["code", "git", "terminal", "build", "test"]):
            return "development"
        if any(k in text for k in ["browser", "search", "browse"]):
            return "research"
        if any(k in text for k in ["email", "slack", "meeting"]):
            return "communication"
        return "general"

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_workflows": len(self._workflows),
            "learn_count": self._learn_count,
        }


workflow_learner = WorkflowLearner()

__all__ = ["WorkflowLearner", "Workflow", "workflow_learner"]
