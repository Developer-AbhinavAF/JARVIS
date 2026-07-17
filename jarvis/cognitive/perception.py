"""Perception Layer for JARVIS Cognitive Architecture.

The AI must first understand the situation.

Observe:
- Current Conversation
- Current Time
- Current User Activity
- Current Application
- Current Project
- Current Background Tasks
- Current User Goal

Never execute immediately. Always observe first.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# SITUATION MODEL
# ════════════════════════════════════════════════════════════════════

@dataclass
class Situation:
    """A complete snapshot of the current situation."""
    # Time context
    timestamp: float = 0.0
    time_of_day: str = ""       # morning, afternoon, evening, night
    day_of_week: str = ""       # monday, tuesday, ...
    is_weekend: bool = False

    # Conversation context
    user_input: str = ""
    conversation_turn: int = 0
    previous_intents: list[str] = field(default_factory=list)
    previous_emotions: list[str] = field(default_factory=list)

    # User state
    user_emotion: str = "neutral"
    user_activity: str = "idle"  # idle, coding, browsing, researching, media
    user_focus: str = ""         # what the user is focused on

    # Application context
    current_app: str = ""
    current_website: str = ""
    current_file: str = ""
    current_folder: str = ""

    # Project context
    current_project: str = ""
    current_language: str = ""
    current_repository: str = ""

    # Task context
    active_tasks: int = 0
    background_tasks: list[str] = field(default_factory=list)

    # Memory context
    recent_memories: list[str] = field(default_factory=list)
    relevant_preferences: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_of_day": self.time_of_day,
            "day_of_week": self.day_of_week,
            "is_weekend": self.is_weekend,
            "user_input": self.user_input[:100],
            "conversation_turn": self.conversation_turn,
            "user_emotion": self.user_emotion,
            "user_activity": self.user_activity,
            "current_app": self.current_app,
            "current_project": self.current_project,
            "active_tasks": self.active_tasks,
        }


# ════════════════════════════════════════════════════════════════════
# PERCEPTION LAYER
# ════════════════════════════════════════════════════════════════════

class PerceptionLayer:
    """Observes the current situation before any action.

    Builds a comprehensive Situation object from all available signals:
    - Time, conversation history, user state, applications, projects
    - Never executes directly; only observes and reports.
    """

    def __init__(self) -> None:
        self._situation_history: list[Situation] = []
        self._max_history: int = 50

    def observe(
        self,
        user_input: str = "",
        context: dict[str, Any] | None = None,
        emotion: str = "neutral",
        intent: str = "",
    ) -> Situation:
        """Observe and build a complete situation snapshot.

        Args:
            user_input: The current user input.
            context: Context from the context engine.
            emotion: Detected user emotion.
            intent: Detected intent (if any).

        Returns:
            Situation object with all observed state.
        """
        context = context or {}
        now = time.time()

        situation = Situation(
            timestamp=now,
            time_of_day=self._get_time_of_day(now),
            day_of_week=self._get_day_of_week(now),
            is_weekend=self._is_weekend(now),
            user_input=user_input,
            conversation_turn=context.get("turn_count", 0),
            previous_intents=self._extract_previous_intents(context),
            previous_emotions=self._extract_previous_emotions(context),
            user_emotion=emotion,
            user_activity=self._detect_user_activity(context),
            user_focus=self._detect_user_focus(context),
            current_app=context.get("current_app", ""),
            current_website=context.get("current_website", ""),
            current_file=context.get("current_file", ""),
            current_folder=context.get("current_folder", ""),
            current_project=context.get("current_programming_project", ""),
            current_language=context.get("current_programming_language", ""),
            current_repository=context.get("current_repository", ""),
            active_tasks=context.get("active_tasks", 0),
            background_tasks=context.get("background_tasks", []),
            recent_memories=self._extract_recent_memories(context),
            relevant_preferences=context.get("user_preferences", {}),
        )

        self._situation_history.append(situation)
        if len(self._situation_history) > self._max_history:
            self._situation_history = self._situation_history[-self._max_history:]

        return situation

    def get_recent_situations(self, limit: int = 5) -> list[Situation]:
        """Get recent situation history."""
        return self._situation_history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_observations": len(self._situation_history),
        }

    # ── Private Methods ──

    @staticmethod
    def _get_time_of_day(timestamp: float) -> str:
        import datetime
        hour = datetime.datetime.fromtimestamp(timestamp).hour
        if 5 <= hour < 12:
            return "morning"
        if 12 <= hour < 17:
            return "afternoon"
        if 17 <= hour < 21:
            return "evening"
        return "night"

    @staticmethod
    def _get_day_of_week(timestamp: float) -> str:
        import datetime
        return datetime.datetime.fromtimestamp(timestamp).strftime("%A").lower()

    @staticmethod
    def _is_weekend(timestamp: float) -> bool:
        import datetime
        return datetime.datetime.fromtimestamp(timestamp).weekday() >= 5

    @staticmethod
    def _extract_previous_intents(context: dict[str, Any]) -> list[str]:
        history = context.get("conversation_history", [])
        return [h.get("intent", "") for h in history[-5:] if h.get("intent")]

    @staticmethod
    def _extract_previous_emotions(context: dict[str, Any]) -> list[str]:
        history = context.get("conversation_history", [])
        return [h.get("emotion", "") for h in history[-5:] if h.get("emotion")]

    @staticmethod
    def _detect_user_activity(context: dict[str, Any]) -> str:
        current_app = context.get("current_app", "").lower()
        if any(w in current_app for w in ["code", "pycharm", "cursor", "terminal"]):
            return "coding"
        if any(w in current_app for w in ["chrome", "firefox", "edge", "browser"]):
            return "browsing"
        if any(w in current_app for w in ["spotify", "youtube", "vlc", "media"]):
            return "media"
        if context.get("current_search"):
            return "researching"
        return "idle"

    @staticmethod
    def _detect_user_focus(context: dict[str, Any]) -> str:
        for key in ("current_file", "current_project", "current_website", "current_song"):
            val = context.get(key, "")
            if val:
                return val
        return ""

    @staticmethod
    def _extract_recent_memories(context: dict[str, Any]) -> list[str]:
        history = context.get("conversation_history", [])
        return [h.get("tool_result", "") for h in history[-3:] if h.get("tool_result")]


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

perception_layer = PerceptionLayer()
