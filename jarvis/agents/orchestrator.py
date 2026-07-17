"""Orchestrator — The brain that coordinates all agents.

The Orchestrator never performs work itself. It only:
- Selects agents for tasks
- Distributes work
- Manages parallel execution
- Resolves conflicts
- Aggregates results
- Monitors agent health

Architecture:
  User -> NLP -> Reasoning -> Planner -> Orchestrator -> Agents
"""

from __future__ import annotations

import time
import uuid
import logging
import asyncio
import threading
from typing import Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed, Future

from .base import (
    AgentBase, AgentMessage, AgentHealth,
    AgentPriority, AgentStatus, MessageType,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# TASK GRAPH
# ════════════════════════════════════════════════════════════════════

@dataclass
class TaskNode:
    """A single task in the execution graph."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    intent: str = ""
    text: str = ""
    entities: dict[str, Any] = field(default_factory=dict)
    priority: AgentPriority = AgentPriority.MEDIUM
    assigned_agent: str = ""
    dependencies: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    latency_ms: float = 0.0
    error: str = ""


@dataclass
class ExecutionPlan:
    """Complete plan for executing a user request."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tasks: list[TaskNode] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    final_response: str = ""


# ════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ════════════════════════════════════════════════════════════════════

class Orchestrator:
    """Central coordinator for all JARVIS agents.

    Responsibilities:
    - Agent selection based on capabilities
    - Task distribution and scheduling
    - Parallel execution management
    - Conflict resolution
    - Result aggregation
    - Health monitoring
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._agents: dict[str, AgentBase] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="orchestrator",
        )
        self._plans: dict[str, ExecutionPlan] = {}
        self._total_tasks: int = 0
        self._total_success: int = 0
        self._total_failures: int = 0
        self._total_latency_ms: float = 0.0
        self._lock = threading.Lock()
        self._active_futures: dict[str, Future] = {}

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    # ── Agent Registration ─────────────────────────────────────────

    def register_agent(self, agent: AgentBase) -> None:
        """Register an agent with the orchestrator."""
        self._agents[agent.name] = agent
        logger.info("Registered agent: %s (priority=%s)", agent.name, agent.priority.name)

    def unregister_agent(self, name: str) -> None:
        self._agents.pop(name, None)

    def get_agent(self, name: str) -> AgentBase | None:
        return self._agents.get(name)

    def get_agents(self) -> dict[str, AgentBase]:
        return dict(self._agents)

    # ── Agent Selection ────────────────────────────────────────────

    def select_agents(
        self,
        intent: str = "",
        entities: dict | None = None,
        text: str = "",
        top_k: int = 3,
    ) -> list[tuple[AgentBase, float]]:
        """Select the best agents for a given request.

        Returns list of (agent, score) sorted by score descending.
        """
        scored: list[tuple[AgentBase, float]] = []
        for agent in self._agents.values():
            if not agent.is_available:
                continue
            score = agent.can_handle(intent, entities, text)
            if score > 0:
                scored.append((agent, score))

        scored.sort(key=lambda x: (-x[1], x[0].priority.value))
        return scored[:top_k]

    def select_primary_agent(
        self,
        intent: str = "",
        entities: dict | None = None,
        text: str = "",
    ) -> AgentBase | None:
        """Select the single best agent."""
        results = self.select_agents(intent, entities, text, top_k=1)
        return results[0][0] if results else None

    # ── Task Execution ─────────────────────────────────────────────

    def execute(
        self,
        text: str,
        intent: str = "",
        entities: dict | None = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Execute a user request through the agent system.

        Returns aggregated result with response, agents used, timing.
        """
        t0 = time.perf_counter()
        task_id = str(uuid.uuid4())[:8]

        # Select agents
        selected = self.select_agents(intent, entities, text)
        if not selected:
            return {
                "response": "",
                "agents_used": [],
                "latency_ms": 0,
                "task_id": task_id,
                "error": "No agents available",
            }

        # Build task
        task = TaskNode(
            task_id=task_id,
            intent=intent,
            text=text,
            entities=entities or {},
            assigned_agent=selected[0][0].name,
            status="running",
        )

        # Execute on selected agents
        results: list[dict[str, Any]] = []
        agents_used: list[str] = []

        if len(selected) == 1:
            # Single agent — direct execution
            agent = selected[0][0]
            msg = self._build_message(agent.name, task)
            agent_result = agent.process_sync(msg)
            results.append({
                "agent": agent.name,
                "score": selected[0][1],
                "result": agent_result.payload,
            })
            agents_used.append(agent.name)
        else:
            # Multiple agents — parallel execution
            results = self._execute_parallel(selected, task)
            agents_used = [r["agent"] for r in results]

        # Aggregate results
        response = self._aggregate_results(results, text)

        ms = (time.perf_counter() - t0) * 1000

        with self._lock:
            self._total_tasks += 1
            self._total_latency_ms += ms
            if not any(r.get("result", {}).get("error") for r in results):
                self._total_success += 1
            else:
                self._total_failures += 1

        return {
            "response": response,
            "agents_used": agents_used,
            "results": results,
            "latency_ms": round(ms, 1),
            "task_id": task_id,
        }

    def execute_task(self, task: TaskNode) -> dict[str, Any]:
        """Execute a single TaskNode."""
        if not task.assigned_agent:
            return {"error": "No agent assigned"}

        agent = self._agents.get(task.assigned_agent)
        if not agent:
            return {"error": f"Agent not found: {task.assigned_agent}"}

        msg = self._build_message(agent.name, task)
        result = agent.process_sync(msg)
        return result.payload

    def execute_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Execute a full ExecutionPlan with dependency resolution."""
        plan.status = "executing"
        completed: dict[str, dict] = {}
        task_map = {t.task_id: t for t in plan.tasks}

        # Process parallel groups in order
        for group in plan.parallel_groups:
            group_tasks = [task_map[tid] for tid in group if tid in task_map]

            # Check dependencies
            ready = []
            for task in group_tasks:
                deps_met = all(d in completed for d in task.dependencies)
                if deps_met:
                    ready.append(task)

            if not ready:
                continue

            # Execute ready tasks in parallel
            futures: dict[Future, TaskNode] = {}
            for task in ready:
                future = self._executor.submit(self.execute_task, task)
                futures[future] = task

            # Collect results
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result(timeout=30.0)
                    task.result = result
                    task.status = "completed"
                    completed[task.task_id] = result
                except Exception as e:
                    task.status = "failed"
                    task.error = str(e)
                    completed[task.task_id] = {"error": str(e)}

        plan.status = "completed"
        return plan

    # ── Health Monitoring ──────────────────────────────────────────

    def get_all_health(self) -> dict[str, dict]:
        """Get health status of all agents."""
        return {name: agent.get_health() for name, agent in self._agents.items()}

    def get_healthy_agents(self) -> list[str]:
        """Get names of agents that are available and healthy."""
        return [name for name, agent in self._agents.items() if agent.is_available]

    def get_unhealthy_agents(self) -> list[str]:
        """Get names of agents that are unavailable or failed."""
        return [name for name, agent in self._agents.items() if not agent.is_available]

    # ── Internal Helpers ───────────────────────────────────────────

    def _build_message(self, target: str, task: TaskNode) -> AgentMessage:
        return AgentMessage(
            source_agent="orchestrator",
            target_agent=target,
            task_id=task.task_id,
            message_type=MessageType.TASK,
            payload={
                "text": task.text,
                "intent": task.intent,
                "entities": task.entities,
                "priority": task.priority.value,
            },
            priority=task.priority,
        )

    def _execute_parallel(
        self,
        selected: list[tuple[AgentBase, float]],
        task: TaskNode,
    ) -> list[dict[str, Any]]:
        """Execute task on multiple agents in parallel."""
        futures: dict[Future, tuple[AgentBase, float]] = {}

        for agent, score in selected:
            msg = self._build_message(agent.name, task)
            future = self._executor.submit(agent.process_sync, msg)
            futures[future] = (agent, score)

        results: list[dict[str, Any]] = []
        for future in as_completed(futures, timeout=30.0):
            agent, score = futures[future]
            try:
                result = future.result(timeout=5.0)
                results.append({
                    "agent": agent.name,
                    "score": score,
                    "result": result.payload,
                })
            except Exception as e:
                results.append({
                    "agent": agent.name,
                    "score": score,
                    "result": {"error": str(e)},
                })

        return results

    def _aggregate_results(
        self,
        results: list[dict[str, Any]],
        original_text: str,
    ) -> str:
        """Aggregate results from multiple agents into a single response."""
        if not results:
            return ""

        # Sort by score
        results.sort(key=lambda r: -r.get("score", 0))

        # Use highest-scoring result
        best = results[0]
        payload = best.get("result", {})

        # Try to extract response from payload
        for key in ("response", "text", "output", "result"):
            if key in payload and payload[key]:
                return str(payload[key])

        # Check if any agent returned a useful response
        for r in results:
            p = r.get("result", {})
            for key in ("response", "text", "output", "result"):
                if key in p and p[key]:
                    return str(p[key])

        return ""

    def get_stats(self) -> dict[str, Any]:
        return {
            "agent_count": self.agent_count,
            "total_tasks": self._total_tasks,
            "total_success": self._total_success,
            "total_failures": self._total_failures,
            "avg_latency_ms": (
                round(self._total_latency_ms / self._total_tasks, 1)
                if self._total_tasks > 0 else 0
            ),
            "agents": {name: agent.get_health() for name, agent in self._agents.items()},
        }

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


# ════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════

orchestrator = Orchestrator()

__all__ = ["Orchestrator", "orchestrator", "TaskNode", "ExecutionPlan"]
