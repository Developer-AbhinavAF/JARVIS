"""Task Graph — The foundational DAG for all planning.

Every request becomes a directed acyclic graph of tasks.
Tasks have dependencies, priorities, states, and recovery paths.

This is the data structure everything else operates on.
"""

from __future__ import annotations

import time
import uuid
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# TASK STATE
# ════════════════════════════════════════════════════════════════════

class TaskState(Enum):
    PENDING = "pending"
    READY = "ready"            # All dependencies met
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    WAITING = "waiting"        # Waiting for external resource
    RETRYING = "retrying"


class TaskPriority(Enum):
    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    BACKGROUND = 10


class TaskType(Enum):
    ACTION = "action"          # Execute a tool/command
    DECISION = "decision"      # Make a choice
    RESEARCH = "research"      # Gather information
    ANALYSIS = "analysis"      # Analyze data
    WAIT = "wait"              # Wait for condition
    PARALLEL = "parallel"      # Group of parallel tasks
    FALLBACK = "fallback"      # Recovery/alternative path


# ════════════════════════════════════════════════════════════════════
# TASK NODE
# ════════════════════════════════════════════════════════════════════

@dataclass
class TaskNode:
    """A single task in the execution graph."""
    task_id: str = ""
    name: str = ""
    description: str = ""
    task_type: TaskType = TaskType.ACTION
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = TaskPriority.NORMAL

    # Execution
    handler: str = ""               # Dotted module path or tool name
    parameters: dict[str, Any] = field(default_factory=dict)
    intent: str = ""
    tool: str = ""

    # Dependencies
    depends_on: list[str] = field(default_factory=list)   # Task IDs
    blocks: list[str] = field(default_factory=list)        # Tasks this blocks
    required_resources: list[str] = field(default_factory=list)
    optional: bool = False           # Can be skipped without failing parent

    # Estimation
    estimated_duration_ms: float = 0.0
    estimated_memory_mb: float = 0.0
    estimated_risk: float = 0.0      # 0-1, higher = riskier
    confidence: float = 0.5

    # Recovery
    fallback_handler: str = ""
    fallback_parameters: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 2
    retry_count: int = 0
    recovery_chain: list[dict[str, Any]] = field(default_factory=list)

    # Execution result
    result: Any = None
    error: str = ""
    actual_duration_ms: float = 0.0

    # Metadata
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Parallel group
    parallel_group: str = ""        # Group ID for parallel tasks
    is_parallel: bool = False

    def __post_init__(self) -> None:
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    @property
    def is_terminal(self) -> bool:
        """Task is in a final state."""
        return self.state in (
            TaskState.COMPLETED, TaskState.FAILED,
            TaskState.SKIPPED, TaskState.CANCELLED,
        )

    @property
    def is_ready(self) -> bool:
        """Task is ready to execute (all deps met, not yet started)."""
        return self.state == TaskState.PENDING and not self.depends_on

    @property
    def can_retry(self) -> bool:
        """Task can be retried."""
        return self.retry_count < self.max_retries

    @property
    def duration_ms(self) -> float:
        """Actual or estimated duration."""
        if self.actual_duration_ms > 0:
            return self.actual_duration_ms
        return self.estimated_duration_ms

    def start(self) -> None:
        """Mark task as started."""
        self.state = TaskState.RUNNING
        self.started_at = time.time()

    def complete(self, result: Any = None) -> None:
        """Mark task as completed."""
        self.state = TaskState.COMPLETED
        self.result = result
        self.completed_at = time.time()
        if self.started_at > 0:
            self.actual_duration_ms = (self.completed_at - self.started_at) * 1000

    def fail(self, error: str = "") -> None:
        """Mark task as failed."""
        self.state = TaskState.FAILED
        self.error = error
        self.completed_at = time.time()

    def pause(self) -> None:
        """Pause the task."""
        if self.state == TaskState.RUNNING:
            self.state = TaskState.PAUSED

    def resume(self) -> None:
        """Resume the task."""
        if self.state == TaskState.PAUSED:
            self.state = TaskState.PENDING

    def cancel(self) -> None:
        """Cancel the task."""
        self.state = TaskState.CANCELLED
        self.completed_at = time.time()

    def skip(self) -> None:
        """Skip the task."""
        self.state = TaskState.SKIPPED
        self.completed_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.task_id,
            "name": self.name,
            "type": self.task_type.value,
            "state": self.state.value,
            "priority": self.priority.value,
            "handler": self.handler,
            "intent": self.intent,
            "tool": self.tool,
            "depends_on": self.depends_on,
            "optional": self.optional,
            "estimated_ms": round(self.estimated_duration_ms, 1),
            "actual_ms": round(self.actual_duration_ms, 1),
            "retries": f"{self.retry_count}/{self.max_retries}",
            "error": self.error,
            "is_parallel": self.is_parallel,
            "parallel_group": self.parallel_group,
        }


# ════════════════════════════════════════════════════════════════════
# EXECUTION PLAN
# ════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionPlan:
    """A complete execution plan with ordered phases."""
    plan_id: str = ""
    goal: str = ""
    intent: str = ""

    # Tasks
    tasks: list[TaskNode] = field(default_factory=list)

    # Phases (ordered groups of parallel-capable tasks)
    phases: list[list[str]] = field(default_factory=list)  # List of task ID groups

    # Metadata
    total_estimated_ms: float = 0.0
    total_tasks: int = 0
    parallel_groups: int = 0
    created_at: float = 0.0
    completed_at: float = 0.0

    # State
    current_phase: int = 0
    is_complete: bool = False

    def __post_init__(self) -> None:
        if not self.plan_id:
            self.plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def get_task(self, task_id: str) -> TaskNode | None:
        """Get a task by ID."""
        for t in self.tasks:
            if t.task_id == task_id:
                return t
        return None

    def get_ready_tasks(self) -> list[TaskNode]:
        """Get all tasks that are ready to execute."""
        ready = []
        for task in self.tasks:
            if task.state != TaskState.PENDING:
                continue
            # Check if all dependencies are completed
            deps_met = all(
                self._dep_completed(dep_id)
                for dep_id in task.depends_on
            )
            if deps_met:
                ready.append(task)
        return ready

    def get_phase_tasks(self, phase_index: int) -> list[TaskNode]:
        """Get tasks for a specific phase."""
        if phase_index >= len(self.phases):
            return []
        return [
            self.get_task(tid)
            for tid in self.phases[phase_index]
            if self.get_task(tid) is not None
        ]

    def advance_phase(self) -> bool:
        """Advance to next phase. Returns True if there are more phases."""
        if self.current_phase < len(self.phases) - 1:
            self.current_phase += 1
            return True
        return False

    def _dep_completed(self, dep_id: str) -> bool:
        task = self.get_task(dep_id)
        return task is not None and task.state == TaskState.COMPLETED

    @property
    def progress(self) -> float:
        """Overall progress 0.0 - 1.0."""
        if not self.tasks:
            return 1.0
        done = sum(1 for t in self.tasks if t.is_terminal)
        return done / len(self.tasks)

    @property
    def success_rate(self) -> float:
        """Fraction of tasks that completed successfully."""
        done = [t for t in self.tasks if t.is_terminal]
        if not done:
            return 1.0
        return sum(1 for t in done if t.state == TaskState.COMPLETED) / len(done)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "intent": self.intent,
            "total_tasks": len(self.tasks),
            "total_estimated_ms": round(self.total_estimated_ms, 1),
            "current_phase": self.current_phase,
            "total_phases": len(self.phases),
            "progress": round(self.progress, 3),
            "tasks": [t.to_dict() for t in self.tasks],
        }


# ════════════════════════════════════════════════════════════════════
# TASK GRAPH
# ════════════════════════════════════════════════════════════════════

class TaskGraph:
    """Directed Acyclic Graph of tasks.

    Manages the structure, traversal, and validation of task dependencies.
    Everything else (priorities, scheduling, optimization) operates on this.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}
        self._adjacency: dict[str, list[str]] = {}  # task_id → [dependent IDs]
        self._reverse: dict[str, list[str]] = {}     # task_id → [dependency IDs]

    def add_task(self, task: TaskNode) -> None:
        """Add a task to the graph."""
        self._nodes[task.task_id] = task
        if task.task_id not in self._adjacency:
            self._adjacency[task.task_id] = []
        if task.task_id not in self._reverse:
            self._reverse[task.task_id] = []

        # Register dependencies
        for dep_id in task.depends_on:
            if dep_id not in self._adjacency:
                self._adjacency[dep_id] = []
            self._adjacency[dep_id].append(task.task_id)

            if task.task_id not in self._reverse:
                self._reverse[task.task_id] = []
            self._reverse[task.task_id].append(dep_id)

    def remove_task(self, task_id: str) -> None:
        """Remove a task and clean up references."""
        if task_id in self._nodes:
            del self._nodes[task_id]
        # Clean adjacency
        self._adjacency.pop(task_id, None)
        self._reverse.pop(task_id, None)
        for dep_list in self._adjacency.values():
            while task_id in dep_list:
                dep_list.remove(task_id)
        for dep_list in self._reverse.values():
            while task_id in dep_list:
                dep_list.remove(task_id)

    def get_task(self, task_id: str) -> TaskNode | None:
        return self._nodes.get(task_id)

    def get_all_tasks(self) -> list[TaskNode]:
        return list(self._nodes.values())

    def get_children(self, task_id: str) -> list[TaskNode]:
        """Get tasks that depend on this task."""
        return [
            self._nodes[cid]
            for cid in self._adjacency.get(task_id, [])
            if cid in self._nodes
        ]

    def get_parents(self, task_id: str) -> list[TaskNode]:
        """Get tasks that this task depends on."""
        return [
            self._nodes[pid]
            for pid in self._reverse.get(task_id, [])
            if pid in self._nodes
        ]

    def get_root_tasks(self) -> list[TaskNode]:
        """Get tasks with no dependencies (entry points)."""
        return [
            t for t in self._nodes.values()
            if not t.depends_on
        ]

    def get_leaf_tasks(self) -> list[TaskNode]:
        """Get tasks with no dependents (exit points)."""
        return [
            t for t in self._nodes.values()
            if not self._adjacency.get(t.task_id, [])
        ]

    def topological_sort(self) -> list[TaskNode]:
        """Kahn's algorithm with cycle detection."""
        in_degree: dict[str, int] = {tid: 0 for tid in self._nodes}
        for tid, deps in self._reverse.items():
            if tid in in_degree:
                in_degree[tid] = len([d for d in deps if d in self._nodes])

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result: list[TaskNode] = []

        while queue:
            tid = queue.pop(0)
            result.append(self._nodes[tid])
            for child_id in self._adjacency.get(tid, []):
                if child_id in in_degree:
                    in_degree[child_id] -= 1
                    if in_degree[child_id] == 0:
                        queue.append(child_id)

        if len(result) != len(self._nodes):
            logger.warning("Cycle detected in task graph!")
            # Return what we can, skip cyclic nodes
            seen = {t.task_id for t in result}
            for t in self._nodes.values():
                if t.task_id not in seen:
                    result.append(t)

        return result

    def detect_parallel_groups(self) -> list[list[str]]:
        """Detect groups of tasks that can run in parallel.

        Tasks are in the same parallel group if they have the same
        dependency depth and no inter-dependencies.
        """
        sorted_tasks = self.topological_sort()
        levels: dict[int, list[str]] = {}

        for task in sorted_tasks:
            depth = self._get_depth(task.task_id)
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(task.task_id)

        return [ids for ids in levels.values() if len(ids) > 1]

    def _get_depth(self, task_id: str, memo: dict[str, int] | None = None) -> int:
        """Get the depth (longest path from root) of a task."""
        if memo is None:
            memo = {}
        if task_id in memo:
            return memo[task_id]

        parents = self._reverse.get(task_id, [])
        if not parents:
            memo[task_id] = 0
            return 0

        max_parent_depth = max(
            self._get_depth(pid, memo)
            for pid in parents
            if pid in self._nodes
        ) if any(pid in self._nodes for pid in parents) else 0

        depth = max_parent_depth + 1
        memo[task_id] = depth
        return depth

    def validate(self) -> list[str]:
        """Validate the graph structure. Returns list of issues."""
        issues = []
        for task in self._nodes.values():
            for dep_id in task.depends_on:
                if dep_id not in self._nodes:
                    issues.append(f"Task {task.task_id} depends on missing task {dep_id}")
        # Check cycles via topological sort
        sorted_tasks = self.topological_sort()
        if len(sorted_tasks) != len(self._nodes):
            issues.append("Graph contains cycles")
        return issues

    @property
    def size(self) -> int:
        return len(self._nodes)

    @property
    def estimated_total_ms(self) -> float:
        """Critical path length estimate."""
        if not self._nodes:
            return 0.0
        sorted_tasks = self.topological_sort()
        # Longest path considering dependencies
        end_times: dict[str, float] = {}
        for task in sorted_tasks:
            dep_ends = [
                end_times[pid]
                for pid in task.depends_on
                if pid in end_times
            ]
            start = max(dep_ends) if dep_ends else 0.0
            end_times[task.task_id] = start + task.estimated_duration_ms
        return max(end_times.values()) if end_times else 0.0
