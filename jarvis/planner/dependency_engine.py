"""Dependency Engine — Resolves task dependencies and blocking.

Every task must know:
- Parent Task
- Child Tasks
- Required Resources
- Blocking Tasks
- Optional Tasks
- Estimated Time
- Priority
- Failure Recovery

The planner should never execute a dependent task before its prerequisite.
"""

from __future__ import annotations

import logging
from typing import Any

from .task_graph import TaskGraph, TaskNode, TaskState

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# DEPENDENCY ENGINE
# ════════════════════════════════════════════════════════════════════

class DependencyEngine:
    """Analyzes and resolves task dependencies.

    Responsibilities:
    - Validate dependency structure
    - Detect blocking chains
    - Determine execution readiness
    - Handle optional task failures
    - Propagate cancellation/skipping
    - Manage resource dependencies
    """

    def __init__(self) -> None:
        self._resource_locks: dict[str, str] = {}  # resource → task_id holding lock

    def resolve(self, graph: TaskGraph) -> dict[str, Any]:
        """Resolve all dependencies and return execution readiness info.

        Returns:
            Dict with ready_tasks, blocked_tasks, critical_path, etc.
        """
        ready = []
        blocked = []
        waiting = []

        for task in graph.get_all_tasks():
            if task.is_terminal or task.state == TaskState.RUNNING:
                continue

            status = self.check_readiness(graph, task)
            if status["ready"]:
                ready.append(task)
            elif status["waiting"]:
                waiting.append(task)
            else:
                blocked.append(task)

        critical_path = self.find_critical_path(graph)

        return {
            "ready": ready,
            "blocked": blocked,
            "waiting": waiting,
            "critical_path": critical_path,
            "total_ready": len(ready),
            "total_blocked": len(blocked),
            "total_waiting": len(waiting),
        }

    def check_readiness(self, graph: TaskGraph, task: TaskNode) -> dict[str, Any]:
        """Check if a task is ready to execute."""
        issues = []

        # Check dependency completion
        for dep_id in task.depends_on:
            dep_task = graph.get_task(dep_id)
            if dep_task is None:
                if not task.optional:
                    issues.append(f"Missing dependency: {dep_id}")
                continue
            if dep_task.state == TaskState.FAILED and not task.optional:
                issues.append(f"Dependency failed: {dep_id}")
            elif dep_task.state == TaskState.CANCELLED and not task.optional:
                issues.append(f"Dependency cancelled: {dep_id}")
            elif not dep_task.is_terminal and dep_task.state != TaskState.RUNNING:
                issues.append(f"Dependency not complete: {dep_id}")

        # Check resource availability
        resource_blocked = False
        for res in task.required_resources:
            holder = self._resource_locks.get(res)
            if holder and holder != task.task_id:
                issues.append(f"Resource locked: {res} (held by {holder})")
                resource_blocked = True

        return {
            "ready": len(issues) == 0,
            "waiting": resource_blocked and not issues,
            "issues": issues,
        }

    def on_task_complete(self, graph: TaskGraph, task: TaskNode) -> list[TaskNode]:
        """Handle task completion — return newly unblocked tasks."""
        newly_ready = []
        # Release resource locks
        for res in task.required_resources:
            if self._resource_locks.get(res) == task.task_id:
                del self._resource_locks[res]

        # Check children
        for child in graph.get_children(task.task_id):
            if child.state != TaskState.PENDING:
                continue
            status = self.check_readiness(graph, child)
            if status["ready"]:
                newly_ready.append(child)

        return newly_ready

    def on_task_fail(self, graph: TaskGraph, task: TaskNode) -> dict[str, Any]:
        """Handle task failure — determine impact on dependents."""
        affected = []
        skipped = []

        for child in graph.get_children(task.task_id):
            if task.optional:
                # Optional task failed — child can still proceed
                continue
            # Required task failed — check if child has alternatives
            if child.optional:
                child.skip()
                skipped.append(child)
            else:
                affected.append(child)

        return {
            "affected": affected,
            "skipped": skipped,
            "can_continue": len(affected) == 0,
        }

    def find_critical_path(self, graph: TaskGraph) -> list[str]:
        """Find the critical path (longest dependency chain)."""
        sorted_tasks = graph.topological_sort()
        end_times: dict[str, float] = {}
        path_map: dict[str, list[str]] = {}

        for task in sorted_tasks:
            dep_paths = []
            dep_ends = []
            for dep_id in task.depends_on:
                if dep_id in end_times:
                    dep_ends.append(end_times[dep_id])
                    dep_paths.append(path_map.get(dep_id, [dep_id]))

            start = max(dep_ends) if dep_ends else 0.0
            end_times[task.task_id] = start + task.estimated_duration_ms

            if dep_paths:
                # Extend the longest path
                longest = max(dep_paths, key=len)
                path_map[task.task_id] = longest + [task.task_id]
            else:
                path_map[task.task_id] = [task.task_id]

        if not path_map:
            return []

        longest_id = max(path_map, key=lambda k: end_times.get(k, 0))
        return path_map[longest_id]

    def lock_resource(self, resource: str, task_id: str) -> bool:
        """Try to lock a resource for a task."""
        if resource in self._resource_locks:
            return False
        self._resource_locks[resource] = task_id
        return True

    def unlock_resource(self, resource: str) -> None:
        """Release a resource lock."""
        self._resource_locks.pop(resource, None)

    def propagate_cancel(self, graph: TaskGraph, task_id: str) -> list[str]:
        """Cancel a task and all its dependents recursively."""
        cancelled = [task_id]
        task = graph.get_task(task_id)
        if task:
            task.cancel()

        for child in graph.get_children(task_id):
            if not child.is_terminal:
                child.cancel()
                cancelled.append(child.task_id)

        return cancelled

    def get_execution_layers(self, graph: TaskGraph) -> list[list[TaskNode]]:
        """Split graph into execution layers (topological levels).

        Each layer contains tasks that can potentially run in parallel.
        """
        sorted_tasks = graph.topological_sort()
        layers: list[list[TaskNode]] = []
        depth_cache: dict[str, int] = {}

        for task in sorted_tasks:
            depth = self._get_depth(graph, task.task_id, depth_cache)
            while len(layers) <= depth:
                layers.append([])
            layers[depth].append(task)

        return layers

    @staticmethod
    def _get_depth(graph: TaskGraph, task_id: str, memo: dict[str, int]) -> int:
        if task_id in memo:
            return memo[task_id]
        parents = graph.get_parents(task_id)
        if not parents:
            memo[task_id] = 0
            return 0
        max_d = max(
            DependencyEngine._get_depth(graph, p.task_id, memo)
            for p in parents
        )
        depth = max_d + 1
        memo[task_id] = depth
        return depth

    def get_stats(self) -> dict[str, Any]:
        return {
            "locked_resources": len(self._resource_locks),
            "resources": list(self._resource_locks.keys()),
        }
