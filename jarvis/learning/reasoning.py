"""Reasoning Learning — Tracks reasoning paths and outcomes.

Track: Reasoning Path, Decision, Outcome, Confidence, Success, Failure
Learn which reasoning strategies work best.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ReasoningPath:
    """A recorded reasoning path."""
    path_id: str = ""
    steps: list[str] = field(default_factory=list)
    decision: str = ""
    outcome: str = ""          # success, failure
    confidence: float = 0.5
    latency_ms: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id,
            "steps": self.steps,
            "decision": self.decision,
            "outcome": self.outcome,
            "confidence": round(self.confidence, 3),
        }


class ReasoningLearner:
    """Learns from reasoning outcomes."""

    def __init__(self) -> None:
        self._paths: list[ReasoningPath] = []
        self._strategy_scores: dict[str, dict[str, float]] = {}
        self._path_counter: int = 0

    def record(
        self,
        steps: list[str],
        decision: str,
        outcome: str,
        confidence: float = 0.5,
        latency_ms: float = 0.0,
        context: dict | None = None,
    ) -> ReasoningPath:
        """Record a reasoning path and outcome."""
        self._path_counter += 1
        path = ReasoningPath(
            path_id=f"rp_{self._path_counter:04d}",
            steps=steps,
            decision=decision,
            outcome=outcome,
            confidence=confidence,
            latency_ms=latency_ms,
            context=context or {},
        )
        self._paths.append(path)

        # Update strategy scores
        strategy = steps[0] if steps else "unknown"
        if strategy not in self._strategy_scores:
            self._strategy_scores[strategy] = {"success": 0, "failure": 0, "total": 0}
        self._strategy_scores[strategy]["total"] += 1
        if outcome == "success":
            self._strategy_scores[strategy]["success"] += 1
        else:
            self._strategy_scores[strategy]["failure"] += 1

        if len(self._paths) > 2000:
            self._paths = self._paths[-1000:]
        return path

    def get_strategy_score(self, strategy: str) -> float:
        """Get success rate for a reasoning strategy."""
        scores = self._strategy_scores.get(strategy)
        if not scores or scores["total"] == 0:
            return 0.5
        return scores["success"] / scores["total"]

    def best_strategy(self) -> str | None:
        """Get the highest performing strategy."""
        best = None
        best_score = 0.0
        for strategy, scores in self._strategy_scores.items():
            if scores["total"] >= 2:
                score = scores["success"] / scores["total"]
                if score > best_score:
                    best_score = score
                    best = strategy
        return best

    def get_recent(self, count: int = 10) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._paths[-count:]]

    def get_stats(self) -> dict[str, Any]:
        total = len(self._paths)
        successes = sum(1 for p in self._paths if p.outcome == "success")
        return {
            "total_paths": total,
            "success_rate": round(successes / max(1, total), 3),
            "strategies": len(self._strategy_scores),
        }


reasoning_learner = ReasoningLearner()

__all__ = ["ReasoningLearner", "ReasoningPath", "reasoning_learner"]
