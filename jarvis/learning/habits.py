"""Habit Learning — Detects patterns in user behavior.

Wake Time, Sleep Time, Study Time, Work Time, Gaming Time,
Coding Sessions, Break Patterns.

Example:
  Every day 7 PM -> Opens VS Code -> Starts Python -> Plays Spotify
  Infer: Coding Session.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Habit:
    """A detected habit pattern."""
    habit_id: str = ""
    name: str = ""
    pattern: list[str] = field(default_factory=list)    # sequence of actions
    time_range: str = ""                                 # e.g. "19:00-22:00"
    frequency: int = 1                                   # how often observed
    confidence: float = 0.3
    last_observed: float = field(default_factory=time.time)
    category: str = ""                                   # coding, work, leisure, etc.

    def to_dict(self) -> dict[str, Any]:
        return {
            "habit_id": self.habit_id,
            "name": self.name,
            "pattern": self.pattern,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 3),
            "category": self.category,
            "time_range": self.time_range,
        }


class HabitLearner:
    """Detects behavioral habits from observed actions."""

    def __init__(self, min_occurrences: int = 3) -> None:
        self._habits: dict[str, Habit] = {}
        self._observations: list[dict[str, Any]] = []
        self._min_occurrences = min_occurrences
        self._habit_counter: int = 0
        self._detect_count: int = 0

    def observe(self, action: str, context: dict[str, Any] | None = None) -> None:
        """Record an action observation."""
        ctx = context or {}
        hour = datetime.now().hour
        self._observations.append({
            "action": action,
            "time": time.time(),
            "hour": hour,
            **ctx,
        })
        if len(self._observations) > 500:
            self._observations = self._observations[-250:]

    def detect(self) -> list[Habit]:
        """Analyze observations to detect habits."""
        if len(self._observations) < self._min_occurrences:
            return []

        detected: list[Habit] = []

        # Detect action frequency
        action_counts: dict[str, int] = {}
        action_hours: dict[str, list[int]] = {}
        for obs in self._observations[-100:]:
            action = obs["action"]
            action_counts[action] = action_counts.get(action, 0) + 1
            action_hours.setdefault(action, []).append(obs.get("hour", 12))

        for action, count in action_counts.items():
            if count >= self._min_occurrences:
                hours = action_hours[action]
                avg_hour = sum(hours) / len(hours) if hours else 12
                time_range = f"{int(avg_hour):02d}:00-{(int(avg_hour) + 2) % 24:02d}:00"

                confidence = min(1.0, count / (self._min_occurrences * 3))
                habit_key = f"action:{action}"

                if habit_key in self._habits:
                    habit = self._habits[habit_key]
                    habit.frequency = count
                    habit.confidence = confidence
                    habit.last_observed = time.time()
                else:
                    self._habit_counter += 1
                    habit = Habit(
                        habit_id=f"habit_{self._habit_counter:04d}",
                        name=f"Uses {action}",
                        pattern=[action],
                        time_range=time_range,
                        frequency=count,
                        confidence=confidence,
                        category=self._categorize_action(action),
                    )
                    self._habits[habit_key] = habit
                    detected.append(habit)

        # Detect sequences (A -> B patterns)
        for i in range(len(self._observations) - 1):
            a = self._observations[i]["action"]
            b = self._observations[i + 1]["action"]
            seq_key = f"seq:{a}->{b}"
            if seq_key not in self._habits:
                self._habit_counter += 1
                habit = Habit(
                    habit_id=f"habit_{self._habit_counter:04d}",
                    name=f"{a} then {b}",
                    pattern=[a, b],
                    frequency=1,
                    confidence=0.2,
                    category="workflow",
                )
                self._habits[seq_key] = habit
            else:
                h = self._habits[seq_key]
                h.frequency += 1
                h.confidence = min(1.0, h.frequency / (self._min_occurrences * 2))

        self._detect_count += 1
        return detected

    def get_habits(self, min_confidence: float = 0.3) -> list[dict[str, Any]]:
        """Get detected habits above confidence threshold."""
        habits = [
            h.to_dict() for h in self._habits.values()
            if h.confidence >= min_confidence
        ]
        return sorted(habits, key=lambda h: -h["confidence"])

    def get_habit(self, habit_id: str) -> dict[str, Any] | None:
        for h in self._habits.values():
            if h.habit_id == habit_id:
                return h.to_dict()
        return None

    def predict_next(self, last_action: str) -> str | None:
        """Predict the most likely next action."""
        best_seq = None
        best_conf = 0.0
        for key, habit in self._habits.items():
            if key.startswith("seq:") and habit.pattern[0] == last_action:
                if habit.confidence > best_conf:
                    best_conf = habit.confidence
                    best_seq = habit.pattern[1] if len(habit.pattern) > 1 else None
        return best_seq

    def _categorize_action(self, action: str) -> str:
        coding_kw = ["code", "vscode", "terminal", "python", "git", "build"]
        work_kw = ["browser", "email", "slack", "zoom", "docs"]
        leisure_kw = ["spotify", "youtube", "discord", "game", "music"]
        action_lower = action.lower()
        if any(k in action_lower for k in coding_kw):
            return "coding"
        if any(k in action_lower for k in work_kw):
            return "work"
        if any(k in action_lower for k in leisure_kw):
            return "leisure"
        return "general"

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_habits": len(self._habits),
            "observations": len(self._observations),
            "detect_count": self._detect_count,
        }


habit_learner = HabitLearner()

__all__ = ["HabitLearner", "Habit", "habit_learner"]
