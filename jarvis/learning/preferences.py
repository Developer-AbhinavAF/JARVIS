"""Preference Learning — Learns user preferences over time.

Preferred Browser, IDE, Voice, Search Engine, Music Platform,
Coding Style, Language, UI Theme, Response Style.

Every interaction becomes training data.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

from .experience_db import experience_db, Experience, ExperienceCategory, Outcome

logger = logging.getLogger(__name__)


@dataclass
class Preference:
    """A learned user preference."""
    category: str = ""
    key: str = ""
    value: Any = None
    score: float = 0.5        # 0.0-1.0 confidence
    count: int = 1
    last_used: float = field(default_factory=time.time)
    first_seen: float = field(default_factory=time.time)

    @property
    def recency(self) -> float:
        age_hours = (time.time() - self.last_used) / 3600
        return max(0.0, 1.0 - age_hours / (24 * 30))

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "key": self.key,
            "value": self.value,
            "score": round(self.score, 3),
            "count": self.count,
        }


class PreferenceLearner:
    """Learns and retrieves user preferences."""

    def __init__(self) -> None:
        self._preferences: dict[str, Preference] = {}
        self._learn_count: int = 0

    def learn(self, category: str, key: str, value: Any) -> None:
        """Learn or strengthen a preference."""
        pref_key = f"{category}:{key}"
        if pref_key in self._preferences:
            pref = self._preferences[pref_key]
            pref.count += 1
            pref.last_used = time.time()
            pref.score = min(1.0, pref.score + 0.05 * (1.0 - pref.score))
            if value != pref.value:
                pref.value = value
        else:
            self._preferences[pref_key] = Preference(
                category=category,
                key=key,
                value=value,
                score=0.5,
            )
        self._learn_count += 1

    def get(self, category: str, key: str) -> Any | None:
        """Get a preference value."""
        pref = self._preferences.get(f"{category}:{key}")
        if pref and pref.score > 0.3:
            return pref.value
        return None

    def get_preferred(self, category: str) -> Any | None:
        """Get the highest-scored value in a category."""
        candidates = [
            p for p in self._preferences.values()
            if p.category == category and p.score > 0.3
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda p: (-p.score, -p.count))
        return candidates[0].value

    def get_category(self, category: str) -> list[dict[str, Any]]:
        """Get all preferences in a category."""
        return [
            p.to_dict() for p in self._preferences.values()
            if p.category == category
        ]

    def strengthen(self, category: str, key: str, amount: float = 0.1) -> None:
        """Strengthen an existing preference."""
        pref = self._preferences.get(f"{category}:{key}")
        if pref:
            pref.score = min(1.0, pref.score + amount)
            pref.count += 1

    def weaken(self, category: str, key: str, amount: float = 0.1) -> None:
        """Weaken a preference."""
        pref = self._preferences.get(f"{category}:{key}")
        if pref:
            pref.score = max(0.0, pref.score - amount)

    def remove(self, category: str, key: str) -> bool:
        return self._preferences.pop(f"{category}:{key}", None) is not None

    def get_all(self) -> list[dict[str, Any]]:
        return sorted(
            [p.to_dict() for p in self._preferences.values()],
            key=lambda d: -d["score"],
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_preferences": len(self._preferences),
            "learn_count": self._learn_count,
            "categories": list(set(p.category for p in self._preferences.values())),
        }


preference_learner = PreferenceLearner()

__all__ = ["PreferenceLearner", "Preference", "preference_learner"]
