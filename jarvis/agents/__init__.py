"""JARVIS Multi-Agent Framework.

Coordinates multiple specialized agents through a central Orchestrator.

Architecture:
  User -> NLP -> Reasoning -> Planner -> Orchestrator -> Agents

Usage:
    from jarvis.agents import get_orchestrator, execute

    # Simple execution
    result = execute("hello")

    # With intent context
    result = execute("open chrome", intent="OPEN_APP")

    # Direct orchestrator access
    orch = get_orchestrator()
    agents = orch.select_agents(text="what time is it")
"""

from __future__ import annotations

import logging
from typing import Any

from .base import (
    AgentBase, AgentMessage, AgentHealth,
    AgentPriority, AgentStatus, MessageType, AgentCapability,
)
from .orchestrator import Orchestrator, orchestrator, TaskNode, ExecutionPlan

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# LAZY AGENT REGISTRATION
# ════════════════════════════════════════════════════════════════════

_agents_registered = False


def _register_all_agents() -> None:
    """Register all agents with the orchestrator."""
    global _agents_registered
    if _agents_registered:
        return

    from .planner_agent import planner_agent
    from .reasoning_agent import reasoning_agent
    from .memory_agent import memory_agent
    from .tool_agent import tool_agent
    from .vision_agent import vision_agent
    from .speech_agent import speech_agent
    from .browser_agent import browser_agent
    from .desktop_agent import desktop_agent
    from .research_agent import research_agent
    from .coding_agent import coding_agent
    from .learning_agent import learning_agent
    from .knowledge_agent import knowledge_agent
    from .reflection_agent import reflection_agent
    from .scheduling_agent import scheduling_agent
    from .environment_agent import environment_agent

    agents = [
        planner_agent,      # CRITICAL
        reasoning_agent,     # CRITICAL
        memory_agent,        # CRITICAL
        tool_agent,          # CRITICAL
        vision_agent,        # HIGH
        speech_agent,        # HIGH
        desktop_agent,       # HIGH
        browser_agent,       # MEDIUM
        research_agent,      # MEDIUM
        coding_agent,        # MEDIUM
        knowledge_agent,     # MEDIUM
        learning_agent,      # LOW
        reflection_agent,    # LOW
        scheduling_agent,    # LOW
        environment_agent,   # LOW
    ]

    for agent in agents:
        orchestrator.register_agent(agent)

    _agents_registered = True
    logger.info("Registered %d agents with orchestrator", len(agents))


def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator (registers agents on first call)."""
    _register_all_agents()
    return orchestrator


def execute(
    text: str,
    intent: str = "",
    entities: dict | None = None,
    context: dict | None = None,
) -> dict[str, Any]:
    """Execute a user request through the multi-agent system.

    Returns:
        {
            "response": str,
            "agents_used": list[str],
            "latency_ms": float,
            "task_id": str,
        }
    """
    orch = get_orchestrator()
    return orch.execute(text, intent, entities, context)


def get_agent_health() -> dict[str, dict]:
    """Get health status of all agents."""
    orch = get_orchestrator()
    return orch.get_all_health()


# ════════════════════════════════════════════════════════════════════
# EXPORTS
# ════════════════════════════════════════════════════════════════════

__all__ = [
    # Base
    "AgentBase", "AgentMessage", "AgentHealth",
    "AgentPriority", "AgentStatus", "MessageType", "AgentCapability",
    # Orchestrator
    "Orchestrator", "orchestrator", "TaskNode", "ExecutionPlan",
    # Functions
    "get_orchestrator", "execute", "get_agent_health",
    # Agents (lazy — import from submodules)
    "planner_agent", "reasoning_agent", "memory_agent", "tool_agent",
    "vision_agent", "speech_agent", "browser_agent", "desktop_agent",
    "research_agent", "coding_agent", "learning_agent", "knowledge_agent",
    "reflection_agent", "scheduling_agent", "environment_agent",
]
