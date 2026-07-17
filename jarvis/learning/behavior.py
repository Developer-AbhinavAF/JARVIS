"""Behavior Adaptation — Changes behavior based on learning.

Examples:
  User prefers concise answers -> Reduce verbosity.
  User prefers speech mode -> Prioritize speech.
  User uses Python frequently -> Improve Python context retrieval.

Adapt intelligently.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Adaptation:
    """A behavior adaptation."""
    adaptation_id: str = ""
    category: str = ""
    setting: str = ""
    old_value: Any = None
    new_value: Any = None
    reason: str = ""
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptation_id": self.adaptation_id,
            "category": self.category,
            "setting": self.setting,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
        }


class BehaviorAdapter:
    """Adapts JARVIS behavior based on learned patterns."""

    def __init__(self) -> None:
        self._adaptations: list[Adaptation] = []
        self._settings: dict[str, Any] = {
            "response_verbosity": "medium",
            "prefer_speech": False,
            "technical_depth": "adaptive",
            "greeting_style": "friendly",
            "context_retrieval_depth": "normal",
            "parallel_execution": True,
            "auto_learn": True,
        }
        self._adapt_counter: int = 0
        self._adapt_count: int = 0

    def adapt(self, setting: str, value: Any, reason: str = "") -> bool:
        """Apply a behavior adaptation."""
        old_value = self._settings.get(setting)
        if old_value == value:
            return False

        self._settings[setting] = value
        self._adapt_counter += 1
        adaptation = Adaptation(
            adaptation_id=f"adapt_{self._adapt_counter:04d}",
            setting=setting,
            old_value=old_value,
            new_value=value,
            reason=reason,
        )
        self._adaptations.append(adaptation)
        self._adapt_count += 1
        logger.info("Behavior adapted: %s = %s (was %s)", setting, value, old_value)
        return True

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def get_all_settings(self) -> dict[str, Any]:
        return dict(self._settings)

    def get_recent_adaptations(self, count: int = 10) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._adaptations[-count:]]

    def analyze_and_adapt(self, preferences: dict[str, Any], habits: dict[str, Any]) -> list[str]:
        """Analyze preferences/habits and apply adaptations."""
        applied: list[str] = []

        # Adapt verbosity based on preference
        if preferences.get("verbosity") == "concise":
            if self.adapt("response_verbosity", "short", "User prefers concise"):
                applied.append("verbosity -> short")
        elif preferences.get("verbosity") == "verbose":
            if self.adapt("response_verbosity", "long", "User prefers detailed"):
                applied.append("verbosity -> long")

        # Adapt speech preference
        if habits.get("voice_mode_ratio", 0) > 0.7:
            if self.adapt("prefer_speech", True, "User frequently uses voice"):
                applied.append("prefer_speech -> true")

        return applied

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_adaptations": len(self._adaptations),
            "adapt_count": self._adapt_count,
            "current_settings": len(self._settings),
        }


behavior_adapter = BehaviorAdapter()

__all__ = ["BehaviorAdapter", "Adaptation", "behavior_adapter"]
