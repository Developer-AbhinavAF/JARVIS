"""Personality Learning — Adapts conversation style.

Learn: Conversation Style, Preferred Tone, Preferred Response Length,
Preferred Communication Style, Technical Depth

Do not imitate. Do not become another person.
Adapt naturally while remaining JARVIS.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PersonalityProfile:
    """Learned personality adaptation settings."""
    tone: str = "friendly"              # friendly, formal, casual, professional
    response_length: str = "medium"      # short, medium, long, adaptive
    technical_depth: str = "adaptive"    # basic, intermediate, advanced, adaptive
    humor_level: float = 0.3            # 0.0-1.0
    formality: float = 0.4             # 0.0-1.0
    verbosity: float = 0.5             # 0.0-1.0
    emoji_usage: float = 0.0           # 0.0-1.0
    preferred_greeting: str = ""
    preferred_farewell: str = ""
    communication_style: str = ""       # direct, explanatory, Socratic
    examples_seen: int = 0
    last_adapted: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tone": self.tone,
            "response_length": self.response_length,
            "technical_depth": self.technical_depth,
            "humor_level": round(self.humor_level, 2),
            "formality": round(self.formality, 2),
            "verbosity": round(self.verbosity, 2),
            "communication_style": self.communication_style,
        }


class PersonalityLearner:
    """Adapts JARVIS's conversation style to the user."""

    def __init__(self) -> None:
        self._profile = PersonalityProfile()
        self._observations: list[dict[str, Any]] = []
        self._adapt_count: int = 0

    def observe_response_preference(
        self,
        preferred_length: str = "",
        preferred_tone: str = "",
        technical: bool | None = None,
    ) -> None:
        """Observe a user response preference."""
        self._observations.append({
            "length": preferred_length,
            "tone": preferred_tone,
            "technical": technical,
            "time": time.time(),
        })
        self._adapt()

    def observe_user_message(self, message: str) -> None:
        """Observe a user message to adapt style."""
        self._observations.append({"message": message, "time": time.time()})
        words = len(message.split())
        if words < 5:
            self._profile.verbosity = max(0.1, self._profile.verbosity - 0.02)
        elif words > 30:
            self._profile.verbosity = min(0.9, self._profile.verbosity + 0.02)

        if message.endswith("!") or message.endswith("!!"):
            self._profile.humor_level = min(1.0, self._profile.humor_level + 0.01)
        if "?" in message and message.count("?") > 1:
            self._profile.formality = max(0.0, self._profile.formality - 0.02)

    def _adapt(self) -> None:
        """Adapt personality based on observations."""
        if not self._observations:
            return
        recent = self._observations[-20:]

        lengths = [o["length"] for o in recent if o["length"]]
        if lengths:
            from collections import Counter
            most_common = Counter(lengths).most_common(1)[0][0]
            self._profile.response_length = most_common

        tones = [o["tone"] for o in recent if o["tone"]]
        if tones:
            from collections import Counter
            most_common = Counter(tones).most_common(1)[0][0]
            self._profile.tone = most_common

        self._profile.examples_seen = len(self._observations)
        self._profile.last_adapted = time.time()
        self._adapt_count += 1

    def get_profile(self) -> dict[str, Any]:
        return self._profile.to_dict()

    def set_profile(self, **kwargs: Any) -> None:
        """Manually set personality traits."""
        for key, value in kwargs.items():
            if hasattr(self._profile, key):
                setattr(self._profile, key, value)

    def get_stats(self) -> dict[str, Any]:
        return {
            "observations": len(self._observations),
            "adapt_count": self._adapt_count,
        }


personality_learner = PersonalityLearner()

__all__ = ["PersonalityLearner", "PersonalityProfile", "personality_learner"]
