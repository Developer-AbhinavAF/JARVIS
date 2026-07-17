"""Experience Database — Stores every interaction as structured experience.

Every experience stores:
  Timestamp, Event, Context, Reasoning, Decision,
  Result, Confidence, Outcome, Memory Reference

This becomes the AI's experience.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Outcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class ExperienceCategory(Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    ENVIRONMENTAL = "environmental"
    PROJECT = "project"
    CONVERSATION = "conversation"
    VISUAL = "visual"
    SPEECH = "speech"
    TOOL = "tool"
    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    ERROR = "error"
    WORKFLOW = "workflow"
    REASONING = "reasoning"


@dataclass
class Experience:
    """A single experience record."""
    experience_id: str = ""
    timestamp: float = field(default_factory=time.time)
    event: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    decision: str = ""
    result: Any = None
    confidence: float = 0.5
    outcome: Outcome = Outcome.UNKNOWN
    category: ExperienceCategory = ExperienceCategory.CONVERSATION
    memory_ref: str = ""
    tags: list[str] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "timestamp": self.timestamp,
            "event": self.event,
            "category": self.category.value,
            "outcome": self.outcome.value,
            "confidence": self.confidence,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "latency_ms": self.latency_ms,
        }


class ExperienceDB:
    """In-memory experience database with temporal indexing."""

    def __init__(self, max_experiences: int = 10000) -> None:
        self._experiences: list[Experience] = []
        self._max = max_experiences
        self._id_counter: int = 0
        self._category_index: dict[str, list[int]] = {}

    def store(self, experience: Experience) -> Experience:
        """Store an experience."""
        self._id_counter += 1
        experience.experience_id = f"exp_{self._id_counter:06d}"
        self._experiences.append(experience)

        cat = experience.category.value
        if cat not in self._category_index:
            self._category_index[cat] = []
        self._category_index[cat].append(len(self._experiences) - 1)

        if len(self._experiences) > self._max:
            self._prune()
        return experience

    def query(
        self,
        category: ExperienceCategory | None = None,
        outcome: Outcome | None = None,
        since: float = 0.0,
        limit: int = 100,
    ) -> list[Experience]:
        """Query experiences by filters."""
        results: list[Experience] = []
        for exp in reversed(self._experiences):
            if exp.timestamp < since:
                continue
            if category and exp.category != category:
                continue
            if outcome and exp.outcome != outcome:
                continue
            results.append(exp)
            if len(results) >= limit:
                break
        return results

    def get_recent(self, count: int = 10) -> list[Experience]:
        return list(reversed(self._experiences[-count:]))

    def get_by_id(self, exp_id: str) -> Experience | None:
        for exp in self._experiences:
            if exp.experience_id == exp_id:
                return exp
        return None

    def count(self, category: ExperienceCategory | None = None) -> int:
        if category:
            return len(self._category_index.get(category.value, []))
        return len(self._experiences)

    def success_rate(self, category: ExperienceCategory | None = None) -> float:
        """Calculate success rate across experiences."""
        exps = self.query(category=category, limit=1000)
        if not exps:
            return 0.0
        successes = sum(1 for e in exps if e.outcome == Outcome.SUCCESS)
        return successes / len(exps)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total": len(self._experiences),
            "categories": {k: len(v) for k, v in self._category_index.items()},
            "success_rate": round(self.success_rate(), 3),
        }

    def _prune(self) -> None:
        """Remove oldest experiences when over limit."""
        keep = self._max // 2
        self._experiences = self._experiences[-keep:]
        self._category_index.clear()
        for i, exp in enumerate(self._experiences):
            cat = exp.category.value
            if cat not in self._category_index:
                self._category_index[cat] = []
            self._category_index[cat].append(i)


experience_db = ExperienceDB()

__all__ = ["ExperienceDB", "Experience", "ExperienceCategory", "Outcome", "experience_db"]
