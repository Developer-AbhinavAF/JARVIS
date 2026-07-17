"""Plan Optimizer — Before execution, optimize the plan.

Optimizations:
- Remove Duplicate Tasks
- Merge Similar Tasks
- Reuse Existing Resources
- Reuse Open Applications
- Reuse Existing Browser Tabs
- Avoid Redundant Searches
- Minimize API Calls

Optimize for speed.
"""

from __future__ import annotations

import logging
from typing import Any

from .task_graph import TaskGraph, TaskNode, TaskState, TaskPriority

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# PLAN OPTIMIZER
# ════════════════════════════════════════════════════════════════════

class PlanOptimizer:
    """Optimizes execution plans before execution.

    Applies multiple optimization passes to reduce execution time,
    eliminate redundancy, and improve efficiency.
    """

    def __init__(self) -> None:
        self._optimizations_applied: list[str] = []

    def optimize(self, graph: TaskGraph) -> TaskGraph:
        """Run all optimization passes on the graph.

        Returns the optimized graph.
        """
        self._optimizations_applied = []

        # Pass 1: Remove duplicates
        self._remove_duplicates(graph)

        # Pass 2: Merge similar consecutive tasks
        self._merge_similar(graph)

        # Pass 3: Eliminate unnecessary optional tasks
        self._prune_optional(graph)

        # Pass 4: Reorder for quick wins
        self._optimize_order(graph)

        # Pass 5: Minimize resource conflicts
        self._minimize_contention(graph)

        logger.debug("Applied optimizations: %s", self._optimizations_applied)
        return graph

    def _remove_duplicates(self, graph: TaskGraph) -> None:
        """Remove tasks that do the same thing."""
        seen: dict[str, str] = {}  # signature → task_id
        to_remove: list[str] = []

        for task in graph.get_all_tasks():
            sig = self._task_signature(task)
            if sig in seen:
                # Duplicate found — keep the one with higher priority
                existing = graph.get_task(seen[sig])
                if existing and task.priority.value > existing.priority.value:
                    to_remove.append(seen[sig])
                    seen[sig] = task.task_id
                else:
                    to_remove.append(task.task_id)
            else:
                seen[sig] = task.task_id

        for tid in to_remove:
            task = graph.get_task(tid)
            if task:
                # Redirect dependents to non-duplicate
                graph.remove_task(tid)
                self._optimizations_applied.append(f"Removed duplicate: {task.name}")

    def _merge_similar(self, graph: TaskGraph) -> None:
        """Merge consecutive tasks with same handler."""
        tasks = graph.topological_sort()
        merge_candidates: list[tuple[str, str]] = []

        for i in range(len(tasks) - 1):
            t1, t2 = tasks[i], tasks[i + 1]
            if (t1.handler == t2.handler and t1.handler
                    and t2.task_id in [c.task_id for c in graph.get_children(t1.task_id)]):
                merge_candidates.append((t1.task_id, t2.task_id))

        for t1_id, t2_id in merge_candidates:
            t1 = graph.get_task(t1_id)
            t2 = graph.get_task(t2_id)
            if t1 and t2:
                # Merge t2 into t1
                t1.parameters = {**t1.parameters, **t2.parameters}
                t1.description += f" + {t2.description}"
                graph.remove_task(t2_id)
                self._optimizations_applied.append(f"Merged: {t1.name} + {t2.name}")

    def _prune_optional(self, graph: TaskGraph) -> None:
        """Remove optional tasks that don't contribute to the critical path."""
        for task in graph.get_all_tasks():
            if task.optional and task.state == TaskState.PENDING:
                children = graph.get_children(task.task_id)
                # If no children depend on this optional task, remove it
                if not children:
                    graph.remove_task(task.task_id)
                    self._optimizations_applied.append(f"Pruned optional: {task.name}")

    def _optimize_order(self, graph: TaskGraph) -> None:
        """Reorder tasks to prioritize quick wins."""
        for task in graph.get_all_tasks():
            if task.state == TaskState.PENDING and task.estimated_duration_ms <= 200:
                if task.priority.value < TaskPriority.HIGH.value:
                    task.priority = TaskPriority.HIGH

    def _minimize_contention(self, graph: TaskGraph) -> None:
        """Reduce resource contention by spreading resource-heavy tasks."""
        resource_tasks: dict[str, list[TaskNode]] = {}
        for task in graph.get_all_tasks():
            for res in task.required_resources:
                if res not in resource_tasks:
                    resource_tasks[res] = []
                resource_tasks[res].append(task)

        for res, tasks in resource_tasks.items():
            if len(tasks) > 2:
                # Mark some as sequential to reduce contention
                for i, task in enumerate(tasks):
                    if i > 0:
                        task.depends_on.append(tasks[i - 1].task_id)

    @staticmethod
    def _task_signature(task: TaskNode) -> str:
        """Create a signature for duplicate detection."""
        params_str = str(sorted(task.parameters.items()))
        return f"{task.handler}:{task.intent}:{params_str}"

    def get_optimizations(self) -> list[str]:
        return list(self._optimizations_applied)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_optimizations": len(self._optimizations_applied),
            "optimizations": self._optimizations_applied,
        }
