"""Habit & Routine Detection Engine for JARVIS NLP.

Detect repeated behavior patterns.
User always opens Chrome → GitHub → VS Code → Terminal
Automatically recognize "Programming Session"
Future: One command → Entire workflow.

Morning → News → Weather → Calendar
Night → Music → Coding → Notes
AI should learn naturally.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from collections import Counter


# ════════════════════════════════════════════════════════════════════
# HABIT & ROUTINE
# ════════════════════════════════════════════════════════════════════

@dataclass
class HabitPattern:
    """A detected habit pattern."""
    name: str = ""
    sequence: list[str] = field(default_factory=list)
    frequency: int = 0
    confidence: float = 0.0
    last_seen: float = 0.0
    time_of_day: str = ""  # morning, afternoon, evening, night
    day_of_week: str = ""  # weekday, weekend, any
    trigger_intent: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sequence": self.sequence,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 3),
            "last_seen": self.last_seen,
            "time_of_day": self.time_of_day,
            "description": self.description,
        }


@dataclass
class RoutinePattern:
    """A detected routine (daily/weekly pattern)."""
    name: str = ""
    time_range: str = ""  # "08:00-10:00", "evening", etc.
    actions: list[str] = field(default_factory=list)
    frequency: int = 0
    confidence: float = 0.0
    last_seen: float = 0.0
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "time_range": self.time_range,
            "actions": self.actions,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 3),
            "description": self.description,
        }


# ════════════════════════════════════════════════════════════════════
# HABIT DETECTOR
# ════════════════════════════════════════════════════════════════════

class HabitDetector:
    """Detects repeated behavior patterns and routines.

    Analyzes sequences of intents and entities to identify:
    - Repeated workflows (habits)
    - Time-based patterns (routines)
    - Session types (programming, research, etc.)
    """

    def __init__(self) -> None:
        self._intent_history: list[dict[str, Any]] = []
        self._detected_habits: dict[str, HabitPattern] = {}
        self._detected_routines: dict[str, RoutinePattern] = {}
        self._min_sequence_length: int = 2
        self._min_frequency: int = 3
        self._max_history: int = 500

    def record_action(
        self,
        intent: str,
        entities: dict[str, Any] | None = None,
        tool: str = "",
        success: bool = True,
    ) -> None:
        """Record a user action for habit detection."""
        now = time.time()
        hour = time.localtime(now).tm_hour
        wday = time.localtime(now).tm_wday

        time_of_day = self._get_time_of_day(hour)
        day_type = "weekend" if wday >= 5 else "weekday"

        entry = {
            "intent": intent,
            "entities": entities or {},
            "tool": tool,
            "success": success,
            "timestamp": now,
            "hour": hour,
            "time_of_day": time_of_day,
            "day_type": day_type,
        }

        self._intent_history.append(entry)

        # Trim history
        if len(self._intent_history) > self._max_history:
            self._intent_history = self._intent_history[-self._max_history:]

        # Detect patterns
        self._detect_sequences()
        self._detect_routines()

    def detect_habits(self) -> list[HabitPattern]:
        """Return all detected habit patterns."""
        return list(self._detected_habits.values())

    def detect_routines(self) -> list[RoutinePattern]:
        """Return all detected routines."""
        return list(self._detected_routines.values())

    def suggest_next_action(self, context: dict[str, Any] | None = None) -> str | None:
        """Suggest the next action based on detected patterns.

        Looks at recent actions and suggests what typically follows.
        """
        if len(self._intent_history) < 2:
            return None

        # Get last 2-3 intents as context
        recent = [e["intent"] for e in self._intent_history[-3:]]

        # Find habits that start with recent intents
        for habit in self._detected_habits.values():
            if len(habit.sequence) > len(recent):
                # Check if recent matches the beginning of the habit
                if habit.sequence[:len(recent)] == recent:
                    next_idx = len(recent)
                    if next_idx < len(habit.sequence):
                        return habit.sequence[next_idx]

        return None

    def get_session_type(self) -> str | None:
        """Detect the current session type based on recent actions."""
        if len(self._intent_history) < 3:
            return None

        recent_intents = [e["intent"] for e in self._intent_history[-5:]]

        # Programming session
        programming_intents = {
            "OPEN_VSCODE", "OPEN_TERMINAL", "PROGRAMMING",
            "VERSION_CONTROL", "RUN_CODE", "DEBUG_CODE",
        }
        if sum(1 for i in recent_intents if i in programming_intents) >= 2:
            return "programming_session"

        # Research session
        research_intents = {
            "SEARCH_WEB", "GET_NEWS", "OPEN_WEBSITE",
            "WEB_SEARCH", "DEFINITION",
        }
        if sum(1 for i in recent_intents if i in research_intents) >= 2:
            return "research_session"

        # Media session
        media_intents = {
            "PLAY_MUSIC", "PLAY_YOUTUBE", "PLAY_SPOTIFY",
            "PAUSE_MEDIA", "NEXT_TRACK",
        }
        if sum(1 for i in recent_intents if i in media_intents) >= 2:
            return "media_session"

        return None

    def get_stats(self) -> dict[str, Any]:
        """Return habit detection statistics."""
        return {
            "total_actions": len(self._intent_history),
            "detected_habits": len(self._detected_habits),
            "detected_routines": len(self._detected_routines),
            "session_type": self.get_session_type(),
        }

    # ── Internal detection ─────────────────────────────────────────

    def _detect_sequences(self) -> None:
        """Detect repeated intent sequences."""
        if len(self._intent_history) < self._min_sequence_length:
            return

        # Look for sequences of length 2-5
        for seq_len in range(self._min_sequence_length, min(6, len(self._intent_history) + 1)):
            for i in range(len(self._intent_history) - seq_len + 1):
                sequence = [e["intent"] for e in self._intent_history[i:i + seq_len]]
                seq_key = " → ".join(sequence)

                if seq_key not in self._detected_habits:
                    self._detected_habits[seq_key] = HabitPattern(
                        name=seq_key,
                        sequence=sequence,
                        frequency=1,
                        confidence=0.3,
                        last_seen=time.time(),
                        time_of_day=self._intent_history[i]["time_of_day"],
                        description=f"Sequence: {seq_key}",
                    )
                else:
                    habit = self._detected_habits[seq_key]
                    habit.frequency += 1
                    habit.confidence = min(1.0, habit.frequency / self._min_frequency)
                    habit.last_seen = time.time()

        # Remove low-confidence habits
        to_remove = [
            k for k, v in self._detected_habits.items()
            if v.frequency < self._min_frequency and v.confidence < 0.5
        ]
        for k in to_remove:
            del self._detected_habits[k]

    def _detect_routines(self) -> None:
        """Detect time-based routines."""
        if len(self._intent_history) < 5:
            return

        # Group actions by time of day
        time_groups: dict[str, list[str]] = {}
        for entry in self._intent_history:
            tod = entry["time_of_day"]
            if tod not in time_groups:
                time_groups[tod] = []
            time_groups[tod].append(entry["intent"])

        # Look for repeated patterns within time groups
        for tod, intents in time_groups.items():
            if len(intents) < 3:
                continue

            # Find the most common intent sequence
            for seq_len in range(2, min(4, len(intents) + 1)):
                for i in range(len(intents) - seq_len + 1):
                    seq = intents[i:i + seq_len]
                    seq_key = " → ".join(seq)

                    if seq_key not in self._detected_routines:
                        self._detected_routines[seq_key] = RoutinePattern(
                            name=seq_key,
                            time_range=tod,
                            actions=seq,
                            frequency=1,
                            confidence=0.3,
                            last_seen=time.time(),
                            description=f"{tod} routine: {seq_key}",
                        )
                    else:
                        routine = self._detected_routines[seq_key]
                        routine.frequency += 1
                        routine.confidence = min(1.0, routine.frequency / self._min_frequency)

        # Remove low-confidence routines
        to_remove = [
            k for k, v in self._detected_routines.items()
            if v.frequency < self._min_frequency
        ]
        for k in to_remove:
            del self._detected_routines[k]

    @staticmethod
    def _get_time_of_day(hour: int) -> str:
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

habit_detector = HabitDetector()
