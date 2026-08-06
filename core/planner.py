"""core/planner.py — Deterministic Planner & Confidence Engine for JARVIS vNext++.

Resides between Brain and Candidate Tool Search.
Responsibilities:
- Determine if memory, RAG, tools, or multi-step execution are required.
- Estimate decision confidence percentage.
- Select appropriate BrainProfile.
- Build structured ExecutionPlan.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from core.world_state import world_state_engine

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    step_id: int
    action_type: str  # memory, rag, tool, skill, response
    target: str
    args: Dict[str, Any] = field(default_factory=dict)
    confirmed: bool = True


@dataclass
class ExecutionPlan:
    goal: str
    profile: str = "NORMAL"
    requires_memory: bool = False
    requires_rag: bool = False
    requires_tools: bool = False
    top_k_rag: int = 2
    confidence: float = 0.95
    steps: List[ExecutionStep] = field(default_factory=list)


class PlannerEngine:
    """Planner and confidence calculation engine."""

    def __init__(self):
        pass

    def build_plan(self, query: str, context: Dict[str, Any] = None) -> ExecutionPlan:
        """Analyze query and build deterministic execution plan."""
        query_lower = query.lower().strip()
        state = world_state_engine.get_state()

        plan = ExecutionPlan(goal=query)

        # 1. Greetings & Simple Chat
        if any(word in query_lower for word in ["hello", "hi", "hey", "hii", "good morning", "how are you"]):
            plan.profile = "FAST"
            plan.confidence = 0.99
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="response", target="greeting"))
            return plan

        # 2. Coding & Debugging
        if any(word in query_lower for word in ["code", "python", "script", "function", "debug", "refactor", "bug", "error", "traceback"]):
            plan.profile = "CODING"
            plan.confidence = 0.90
            plan.requires_rag = True
            plan.top_k_rag = 4
            plan.steps.append(ExecutionStep(step_id=1, action_type="rag", target="coding_docs"))
            plan.steps.append(ExecutionStep(step_id=2, action_type="response", target="coding"))
            return plan

        # 3. Tool Actions (Open app, search web, etc.)
        if any(word in query_lower for word in ["open", "launch", "search", "close", "play", "run"]):
            plan.profile = "FAST"
            plan.requires_tools = True
            plan.confidence = 0.95
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="tool", target="tool_execution"))
            return plan

        # 4. Factual Memory Lookup
        if any(word in query_lower for word in ["who am i", "my name", "my age", "my preference", "what project"]):
            plan.profile = "MEMORY"
            plan.requires_memory = True
            plan.confidence = 0.98
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="memory", target="facts"))
            return plan

        # 5. General Questions / Research
        plan.profile = "NORMAL"
        plan.requires_rag = True
        plan.top_k_rag = 2
        plan.confidence = 0.85
        plan.steps.append(ExecutionStep(step_id=1, action_type="response", target="general_answer"))
        return plan


planner_engine = PlannerEngine()
