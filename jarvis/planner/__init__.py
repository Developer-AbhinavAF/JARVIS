"""Planning Engine — The executive planner for JARVIS AI.

Transforms user goals into optimized execution graphs.

Pipeline:
  User Goal
    → Intent Analysis
    → Context Collection
    → Memory Retrieval
    → Task Generation
    → Dependency Analysis
    → Execution Graph
    → Risk Analysis
    → Optimization
    → Scheduling
    → Execution
    → Monitoring
    → Verification
    → Reflection

The AI should never directly execute a command after understanding it.
Every request must first become a structured plan.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable

from .task_graph import (
    TaskGraph, TaskNode, TaskState, TaskPriority, TaskType, ExecutionPlan,
)
from .dependency_engine import DependencyEngine
from .priority_engine import PriorityEngine
from .resource_monitor import ResourceMonitor
from .estimation import EstimationEngine
from .optimizer import PlanOptimizer
from .recovery import FailurePlanner
from .replanner import DynamicReplanner
from .scheduler import TaskScheduler, task_scheduler, ScheduleType
from .project_manager import ProjectManager, project_manager
from .dashboard import ExecutionDashboard, dashboard, DashboardPhase
from .self_optimizer import SelfOptimizer, self_optimizer

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# INTENT → TASK TEMPLATES
# ════════════════════════════════════════════════════════════════════

# Maps intents to task decomposition templates
_TASK_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "OPEN_WEBSITE": [
        {"name": "open_browser", "handler": "jarvis.tools.open_website", "type": "action"},
    ],
    "WEB_SEARCH": [
        {"name": "search_web", "handler": "jarvis.tools.web_search", "type": "action"},
    ],
    "SEARCH_ON_PLATFORM": [
        {"name": "search_platform", "handler": "jarvis.tools.search_on_platform", "type": "action"},
    ],
    "PLAY_MUSIC": [
        {"name": "play_music", "handler": "jarvis.tools.play_music", "type": "action"},
    ],
    "SEARCH_YOUTUBE": [
        {"name": "search_youtube", "handler": "jarvis.tools.search_youtube", "type": "action"},
    ],
    "GET_NEWS": [
        {"name": "get_news", "handler": "jarvis.tools.get_news", "type": "action"},
    ],
    "GET_WEATHER": [
        {"name": "get_weather", "handler": "jarvis.tools.get_weather", "type": "action"},
    ],
    "STOCK_QUOTE": [
        {"name": "get_stock", "handler": "jarvis.tools.stock_quote", "type": "action"},
    ],
    "OPEN_APP": [
        {"name": "open_app", "handler": "jarvis.tools.open_app", "type": "action"},
    ],
    "CLOSE_APP": [
        {"name": "close_app", "handler": "jarvis.tools.close_app", "type": "action"},
    ],
    "PROGRAMMING": [
        {"name": "program", "handler": "jarvis.tools.programming", "type": "action"},
    ],
    "VERSION_CONTROL": [
        {"name": "git_op", "handler": "jarvis.tools.version_control", "type": "action"},
    ],
    "FILE_MANAGEMENT": [
        {"name": "file_op", "handler": "jarvis.tools.file_management", "type": "action"},
    ],
    "SYSTEM_STATUS": [
        {"name": "sys_status", "handler": "jarvis.tools.system_status", "type": "action"},
    ],
    "SYSTEM_POWER": [
        {"name": "power_op", "handler": "jarvis.tools.system_power", "type": "action",
         "risk": 0.8},
    ],
    "SAVE_MEMORY": [
        {"name": "save_mem", "handler": "jarvis.tools.save_memory", "type": "action"},
    ],
    "VOLUME_CONTROL": [
        {"name": "volume", "handler": "jarvis.tools.volume_control", "type": "action"},
    ],
    "BRIGHTNESS_CONTROL": [
        {"name": "brightness", "handler": "jarvis.tools.brightness_control", "type": "action"},
    ],
    "SCREENSHOT": [
        {"name": "screenshot", "handler": "jarvis.tools.screenshot", "type": "action"},
    ],
    "CLIPBOARD": [
        {"name": "clipboard", "handler": "jarvis.tools.clipboard", "type": "action"},
    ],
    "OPEN_VSCODE": [
        {"name": "open_vscode", "handler": "jarvis.tools.open_vscode", "type": "action"},
    ],
    "OPEN_TERMINAL": [
        {"name": "open_terminal", "handler": "jarvis.tools.open_terminal", "type": "action"},
    ],
}

# Compound intent patterns — maps multi-intent goals to task sequences
_COMPOUND_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "research_and_explain": [
        {"name": "search_info", "handler": "jarvis.tools.web_search",
         "type": "action", "intent": "WEB_SEARCH"},
        {"name": "analyze", "handler": "analyze_result",
         "type": "analysis", "depends_on": ["search_info"]},
        {"name": "explain", "handler": "generate_explanation",
         "type": "action", "depends_on": ["analyze"]},
    ],
    "download_and_analyze": [
        {"name": "download", "handler": "jarvis.tools.web_search",
         "type": "action", "intent": "WEB_SEARCH"},
        {"name": "read_structure", "handler": "read_project_structure",
         "type": "analysis", "depends_on": ["download"]},
        {"name": "analyze_code", "handler": "analyze_codebase",
         "type": "analysis", "depends_on": ["read_structure"]},
        {"name": "generate_summary", "handler": "generate_summary",
         "type": "action", "depends_on": ["analyze_code"]},
    ],
}


# ════════════════════════════════════════════════════════════════════
# PLANNING ENGINE
# ════════════════════════════════════════════════════════════════════

class PlanningEngine:
    """The executive planner.

    Orchestrates the full planning pipeline:
    1. Analyze intent and decompose into tasks
    2. Build dependency graph
    3. Score priorities
    4. Estimate costs
    5. Plan recovery paths
    6. Optimize the plan
    7. Monitor system resources
    8. Execute with dashboard updates
    9. Reflect and learn
    """

    def __init__(self) -> None:
        self.dependencies = DependencyEngine()
        self.priorities = PriorityEngine()
        self.resources = ResourceMonitor()
        self.estimation = EstimationEngine()
        self.optimizer = PlanOptimizer()
        self.failure_planner = FailurePlanner()
        self.replanner = DynamicReplanner()
        self.scheduler = task_scheduler
        self.projects = project_manager
        self.dashboard = dashboard
        self.self_optimizer = self_optimizer

        self._plan_count = 0
        self._active_plans: dict[str, ExecutionPlan] = {}

    def create_plan(
        self,
        text: str,
        intent: str,
        entities: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        """Create an execution plan for a user request.

        This is the core planning method. It decomposes the user's goal
        into a structured execution graph.
        """
        entities = entities or {}
        context = context or {}
        self._plan_count += 1

        # ── Step 1: Generate tasks ──
        self.dashboard.update(DashboardPhase.GENERATING_GRAPH)
        tasks = self._generate_tasks(text, intent, entities, context)

        if not tasks:
            # Fallback: single task for the intent
            tasks = [TaskNode(
                name=f"execute_{intent}",
                description=text,
                task_type=TaskType.ACTION,
                intent=intent,
                handler=f"jarvis.tools.{intent.lower()}",
                parameters=entities,
            )]

        # ── Step 2: Build graph ──
        graph = TaskGraph()
        for task in tasks:
            graph.add_task(task)

        # ── Step 3: Analyze dependencies ──
        self.dashboard.update(DashboardPhase.ANALYZING_DEPENDENCIES)
        self._analyze_dependencies(graph, intent, context)

        # ── Step 4: Estimate costs ──
        for task in graph.get_all_tasks():
            self.estimation.estimate_task(task)

        # ── Step 5: Score priorities ──
        # Use lightweight load estimate (skip heavy PowerShell calls)
        system_load = 0.3  # Default moderate load
        for task in graph.get_all_tasks():
            score = self.priorities.score_task(
                task, text, graph.size, system_load,
            )
            task.priority = self.priorities.assign_priority_level(score)

        # ── Step 6: Plan recovery paths ──
        for task in graph.get_all_tasks():
            self.failure_planner.plan_recovery(task)

        # ── Step 7: Optimize ──
        self.dashboard.update(DashboardPhase.OPTIMIZING)
        graph = self.optimizer.optimize(graph)

        # ── Step 8: Build execution plan ──
        execution_layers = self.dependencies.get_execution_layers(graph)
        plan = ExecutionPlan(
            goal=text,
            intent=intent,
            tasks=graph.get_all_tasks(),
            phases=[[t.task_id for t in layer] for layer in execution_layers],
            total_estimated_ms=graph.estimated_total_ms,
            total_tasks=graph.size,
            parallel_groups=sum(1 for layer in execution_layers if len(layer) > 1),
        )

        # ── Step 9: Validate ──
        issues = graph.validate()
        if issues:
            logger.warning("Plan validation issues: %s", issues)

        self._active_plans[plan.plan_id] = plan
        return plan

    def execute_plan(
        self,
        plan: ExecutionPlan,
        action_executor: Callable | None = None,
    ) -> ExecutionPlan:
        """Execute a plan step by step with dashboard updates."""
        self.dashboard.start(plan.total_tasks)

        # Build graph for dependency tracking
        exec_graph = TaskGraph()
        for task in plan.tasks:
            exec_graph.add_task(task)

        for phase_idx, phase_ids in enumerate(plan.phases):
            plan.current_phase = phase_idx
            phase_tasks = [plan.get_task(tid) for tid in phase_ids]
            phase_tasks = [t for t in phase_tasks if t is not None]

            for i, task in enumerate(phase_tasks):
                self.dashboard.step(
                    i + 1, plan.total_tasks,
                    f"Executing: {task.name}",
                )

                task.start()

                if action_executor:
                    try:
                        result = action_executor(task)
                        task.complete(result)
                    except Exception as e:
                        task.fail(str(e))
                        # Try recovery
                        fallback = self.failure_planner.get_next_fallback(task)
                        if fallback and task.can_retry:
                            task.handler = fallback.get("handler", task.handler)
                            task.retry_count += 1
                            task.state = TaskState.PENDING
                            try:
                                result = action_executor(task)
                                task.complete(result)
                            except Exception as e2:
                                task.fail(str(e2))
                else:
                    # No executor — just mark complete
                    task.complete(None)

            # Check newly unblocked tasks after each phase
            for task in phase_tasks:
                newly_ready = self.dependencies.on_task_complete(exec_graph, task)
                for ready_task in newly_ready:
                    if ready_task not in phase_tasks:
                        pass

        plan.completed_at = time.time()
        plan.is_complete = True

        self.dashboard.complete(
            f"Completed {plan.total_tasks} tasks "
            f"({plan.success_rate * 100:.0f}% success)"
        )

        # Post-execution analysis
        insights = self.self_optimizer.analyze_plan(plan)

        return plan

    def replan_on_change(
        self,
        change_type: str,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle a condition change and replan."""
        graph = TaskGraph()
        for task in plan.tasks:
            graph.add_task(task)

        return self.replanner.handle_change(change_type, graph, context)

    def schedule_task(
        self,
        name: str,
        text: str,
        schedule_type: str = "once",
        next_run: float = 0.0,
        interval_seconds: float = 0.0,
    ) -> dict[str, Any]:
        """Schedule a task for future execution."""
        st = ScheduleType(schedule_type)
        task = self.scheduler.schedule(
            name=name, text=text,
            schedule_type=st, next_run=next_run,
            interval_seconds=interval_seconds,
        )
        return task.to_dict()

    def get_plan(self, plan_id: str) -> ExecutionPlan | None:
        return self._active_plans.get(plan_id)

    def get_active_plans(self) -> list[ExecutionPlan]:
        return list(self._active_plans.values())

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_plans_created": self._plan_count,
            "active_plans": len(self._active_plans),
            "dependencies": self.dependencies.get_stats(),
            "priorities": self.priorities.get_stats(),
            "resources": self.resources.get_stats(),
            "estimation": self.estimation.get_stats(),
            "optimizer": self.optimizer.get_stats(),
            "recovery": self.failure_planner.get_stats(),
            "replanner": self.replanner.get_stats(),
            "scheduler": self.scheduler.get_stats(),
            "projects": self.projects.get_stats(),
            "dashboard": self.dashboard.get_stats(),
            "self_optimizer": self.self_optimizer.get_stats(),
        }

    # ── Private Methods ──

    def _generate_tasks(
        self,
        text: str,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
    ) -> list[TaskNode]:
        """Generate task nodes from user intent."""
        tasks: list[TaskNode] = []

        # Check for compound templates
        template = _TASK_TEMPLATES.get(intent, [])

        if template:
            for step in template:
                task = TaskNode(
                    name=step["name"],
                    description=step.get("description", text),
                    task_type=TaskType(step.get("type", "action")),
                    intent=intent,
                    handler=step.get("handler", ""),
                    parameters={**entities, **step.get("parameters", {})},
                    estimated_risk=step.get("risk", 0.1),
                )
                # Handle dependencies
                dep_names = step.get("depends_on", [])
                task.depends_on = dep_names
                tasks.append(task)
        else:
            # Generic single task
            tasks.append(TaskNode(
                name=f"execute_{intent.lower()}",
                description=text,
                task_type=TaskType.ACTION,
                intent=intent,
                handler=f"jarvis.tools.{intent.lower()}",
                parameters=entities,
            ))

        return tasks

    def _analyze_dependencies(
        self,
        graph: TaskGraph,
        intent: str,
        context: dict[str, Any],
    ) -> None:
        """Analyze and set task dependencies."""
        tasks = graph.get_all_tasks()

        # Simple heuristic: if tasks share the same handler,
        # make later ones depend on earlier ones
        handler_first_seen: dict[str, str] = {}
        for task in tasks:
            if task.handler in handler_first_seen:
                if task.task_id not in task.depends_on:
                    task.depends_on.append(handler_first_seen[task.handler])
            else:
                handler_first_seen[task.handler] = task.task_id

        # Ensure no circular dependencies
        issues = graph.validate()
        if issues:
            logger.debug("Dependency issues found: %s", issues)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

planning_engine = PlanningEngine()

__all__ = [
    "PlanningEngine",
    "planning_engine",
    "TaskGraph",
    "TaskNode",
    "TaskState",
    "TaskPriority",
    "TaskType",
    "ExecutionPlan",
    "ScheduleType",
]
