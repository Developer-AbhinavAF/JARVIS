"""Self-Evaluation — Measures improvement over time.

Periodically ask internally:
  Am I improving?
  Are responses faster?
  Is reasoning better?
  Are tools more reliable?
  Is memory retrieval improving?
  Are users repeating themselves less?

Measure progress continuously.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetric:
    """A single evaluation metric."""
    name: str = ""
    current_value: float = 0.0
    previous_value: float = 0.0
    target_value: float = 1.0
    direction: str = "higher"     # higher is better, lower is better

    @property
    def improvement(self) -> float:
        if self.previous_value == 0:
            return 0.0
        return (self.current_value - self.previous_value) / abs(self.previous_value)

    @property
    def progress(self) -> float:
        if self.target_value == 0:
            return 0.0
        return min(1.0, self.current_value / self.target_value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "current": round(self.current_value, 4),
            "previous": round(self.previous_value, 4),
            "improvement": round(self.improvement, 4),
            "progress": round(self.progress, 3),
        }


class SelfEvaluator:
    """Evaluates JARVIS's own performance and improvement."""

    def __init__(self) -> None:
        self._metrics: dict[str, EvaluationMetric] = {}
        self._evaluation_count: int = 0
        self._evaluation_history: list[dict[str, Any]] = []

    def register_metric(
        self,
        name: str,
        target: float = 1.0,
        direction: str = "higher",
    ) -> None:
        """Register a metric to track."""
        self._metrics[name] = EvaluationMetric(
            name=name,
            target_value=target,
            direction=direction,
        )

    def update_metric(self, name: str, value: float) -> None:
        """Update a metric with a new value."""
        if name not in self._metrics:
            self.register_metric(name)
        metric = self._metrics[name]
        metric.previous_value = metric.current_value
        metric.current_value = value

    def evaluate(self) -> dict[str, Any]:
        """Run a full self-evaluation."""
        self._evaluation_count += 1
        results: dict[str, Any] = {
            "timestamp": time.time(),
            "evaluation_number": self._evaluation_count,
            "metrics": {},
            "improvements": [],
            "regressions": [],
        }

        for name, metric in self._metrics.items():
            results["metrics"][name] = metric.to_dict()
            if metric.improvement > 0.05:
                results["improvements"].append(name)
            elif metric.improvement < -0.05:
                results["regressions"].append(name)

        # Overall score
        if self._metrics:
            scores = [m.progress for m in self._metrics.values()]
            results["overall_score"] = round(sum(scores) / len(scores), 3)
        else:
            results["overall_score"] = 0.0

        self._evaluation_history.append(results)
        if len(self._evaluation_history) > 100:
            self._evaluation_history = self._evaluation_history[-50:]

        return results

    def get_trend(self, metric_name: str, count: int = 10) -> list[float]:
        """Get the trend of a metric over recent evaluations."""
        values: list[float] = []
        for eval_result in self._evaluation_history[-count:]:
            m = eval_result.get("metrics", {}).get(metric_name)
            if m:
                values.append(m["current"])
        return values

    def is_improving(self) -> bool:
        """Check if overall score is improving."""
        if len(self._evaluation_history) < 2:
            return True
        recent = self._evaluation_history[-1].get("overall_score", 0)
        previous = self._evaluation_history[-2].get("overall_score", 0)
        return recent >= previous

    def get_report(self) -> dict[str, Any]:
        """Get a summary report."""
        return {
            "evaluation_count": self._evaluation_count,
            "metrics_tracked": len(self._metrics),
            "is_improving": self.is_improving(),
            "latest": self._evaluation_history[-1] if self._evaluation_history else {},
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "evaluation_count": self._evaluation_count,
            "metrics_tracked": len(self._metrics),
        }


self_evaluator = SelfEvaluator()

__all__ = ["SelfEvaluator", "EvaluationMetric", "self_evaluator"]
