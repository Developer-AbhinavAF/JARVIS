"""Self-Optimizer — Post-execution analysis & learning.

After execution, evaluate:
- Was the plan efficient?
- Could tasks run in parallel?
- Were unnecessary steps included?
- Could latency be reduced?
- Should future plans change?

Store improvements.
"""

from __future__ import annotations

import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from .task_graph import ExecutionPlan, TaskNode, TaskState

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_OPTIMIZATION_LOG = _DATA_DIR / "planner_optimizations.json"


# ════════════════════════════════════════════════════════════════════
# OPTIMIZATION INSIGHT
# ════════════════════════════════════════════════════════════════════

@dataclass
class OptimizationInsight:
    """A single insight from plan analysis."""
    insight_type: str = ""      # efficiency, parallelism, redundancy, latency, etc.
    description: str = ""
    severity: str = "info"      # info, warning, critical
    impact: float = 0.0         # Estimated improvement (0-1)
    recommendation: str = ""
    intent: str = ""
    tool: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ════════════════════════════════════════════════════════════════════
# SELF OPTIMIZER
# ════════════════════════════════════════════════════════════════════

class SelfOptimizer:
    """Analyzes completed plans to improve future planning.

    Identifies inefficiencies, redundant steps, missed parallelism,
    and other optimization opportunities.
    """

    def __init__(self) -> None:
        self._insights: list[OptimizationInsight] = []
        self._learned_rules: list[dict[str, Any]] = []
        self._load()

    def analyze_plan(self, plan: ExecutionPlan) -> list[OptimizationInsight]:
        """Analyze a completed plan and generate insights."""
        insights = []

        # Check execution time
        insights.extend(self._analyze_timing(plan))

        # Check parallelism opportunities
        insights.extend(self._analyze_parallelism(plan))

        # Check for redundant tasks
        insights.extend(self._analyze_redundancy(plan))

        # Check failure patterns
        insights.extend(self._analyze_failures(plan))

        # Check task ordering
        insights.extend(self._analyze_ordering(plan))

        # Store insights
        self._insights.extend(insights)
        self._extract_rules(insights)

        return insights

    def _analyze_timing(self, plan: ExecutionPlan) -> list[OptimizationInsight]:
        """Analyze execution timing."""
        insights = []

        # Check for slow tasks
        for task in plan.tasks:
            if task.actual_duration_ms > 0 and task.estimated_duration_ms > 0:
                ratio = task.actual_duration_ms / task.estimated_duration_ms
                if ratio > 2.0:
                    insights.append(OptimizationInsight(
                        insight_type="timing",
                        description=f"Task '{task.name}' took {ratio:.1f}x longer than estimated",
                        severity="warning",
                        impact=0.1,
                        recommendation=f"Increase estimate for {task.intent} to {task.actual_duration_ms * 0.8:.0f}ms",
                        intent=task.intent,
                        tool=task.tool,
                    ))
                elif ratio < 0.3:
                    insights.append(OptimizationInsight(
                        insight_type="timing",
                        description=f"Task '{task.name}' was {ratio:.1f}x faster than estimated",
                        severity="info",
                        impact=0.05,
                        recommendation=f"Decrease estimate for {task.intent} to {task.actual_duration_ms * 1.2:.0f}ms",
                        intent=task.intent,
                        tool=task.tool,
                    ))

        # Check total plan time
        if plan.total_estimated_ms > 0:
            actual = sum(t.actual_duration_ms for t in plan.tasks)
            if actual > 0:
                total_ratio = actual / plan.total_estimated_ms
                if total_ratio > 1.5:
                    insights.append(OptimizationInsight(
                        insight_type="timing",
                        description=f"Total plan took {total_ratio:.1f}x longer than estimated",
                        severity="warning",
                        impact=0.15,
                        recommendation="Review estimation model for these task types",
                    ))

        return insights

    def _analyze_parallelism(self, plan: ExecutionPlan) -> list[OptimizationInsight]:
        """Check if independent tasks could have been parallelized."""
        insights = []
        # Simple check: if tasks in the same phase ran sequentially
        # that could have been parallel
        if len(plan.phases) > 0:
            for i, phase in enumerate(plan.phases):
                if len(phase) > 1:
                    # These were identified as parallel-capable
                    # Check if they actually ran in parallel
                    pass  # Would need execution tracking data

        return insights

    def _analyze_redundancy(self, plan: ExecutionPlan) -> list[OptimizationInsight]:
        """Check for redundant tasks."""
        insights = []
        seen_handlers: dict[str, int] = {}
        for task in plan.tasks:
            if task.state == TaskState.COMPLETED and task.handler:
                seen_handlers[task.handler] = seen_handlers.get(task.handler, 0) + 1

        for handler, count in seen_handlers.items():
            if count > 2:
                insights.append(OptimizationInsight(
                    insight_type="redundancy",
                    description=f"Handler '{handler}' was used {count} times",
                    severity="info",
                    impact=0.1,
                    recommendation="Consider caching or merging repeated calls",
                ))

        return insights

    def _analyze_failures(self, plan: ExecutionPlan) -> list[OptimizationInsight]:
        """Analyze task failures."""
        insights = []
        failed = [t for t in plan.tasks if t.state == TaskState.FAILED]
        for task in failed:
            insights.append(OptimizationInsight(
                insight_type="failure",
                description=f"Task '{task.name}' failed: {task.error}",
                severity="critical",
                impact=0.2,
                recommendation=f"Review recovery chain for {task.intent}",
                intent=task.intent,
                tool=task.tool,
            ))
        return insights

    def _analyze_ordering(self, plan: ExecutionPlan) -> list[OptimizationInsight]:
        """Check if task ordering could be improved."""
        insights = []
        # Check if quick tasks were delayed by slow dependencies
        for task in plan.tasks:
            if task.estimated_duration_ms < 100 and task.depends_on:
                for dep_id in task.depends_on:
                    dep = plan.get_task(dep_id)
                    if dep and dep.estimated_duration_ms > 5000:
                        insights.append(OptimizationInsight(
                            insight_type="ordering",
                            description=f"Quick task '{task.name}' blocked by slow '{dep.name}'",
                            severity="info",
                            impact=0.05,
                            recommendation="Consider extracting quick prerequisites",
                        ))
        return insights

    def _extract_rules(self, insights: list[OptimizationInsight]) -> None:
        """Extract learned rules from insights."""
        for insight in insights:
            if insight.impact > 0.1:
                rule = {
                    "type": insight.insight_type,
                    "intent": insight.intent,
                    "recommendation": insight.recommendation,
                    "impact": insight.impact,
                    "learned_at": time.time(),
                }
                # Avoid duplicates
                if not any(
                    r.get("recommendation") == rule["recommendation"]
                    for r in self._learned_rules
                ):
                    self._learned_rules.append(rule)

        if len(self._learned_rules) > 100:
            self._learned_rules = self._learned_rules[-50:]

    def get_recommendations(self, intent: str = "") -> list[str]:
        """Get optimization recommendations for an intent."""
        relevant = self._learned_rules
        if intent:
            relevant = [r for r in relevant if r.get("intent") == intent]
        return [r["recommendation"] for r in relevant[:5]]

    def get_insights(self, limit: int = 20) -> list[OptimizationInsight]:
        return self._insights[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_insights": len(self._insights),
            "learned_rules": len(self._learned_rules),
            "insight_types": list(set(i.insight_type for i in self._insights)),
        }

    def _save(self) -> None:
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "rules": self._learned_rules,
                "saved_at": time.time(),
            }
            _OPTIMIZATION_LOG.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("Failed to save optimization log: %s", e)

    def _load(self) -> None:
        try:
            if _OPTIMIZATION_LOG.exists():
                data = json.loads(_OPTIMIZATION_LOG.read_text())
                self._learned_rules = data.get("rules", [])
        except Exception as e:
            logger.debug("Failed to load optimization log: %s", e)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

self_optimizer = SelfOptimizer()
