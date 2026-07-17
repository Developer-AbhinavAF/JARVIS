"""Planner Agent — Task decomposition and execution planning."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class PlannerAgent(AgentBase):
    """Decomposes complex tasks into executable sub-tasks with dependency graphs."""

    def __init__(self) -> None:
        super().__init__("planner", AgentPriority.CRITICAL)
        self.add_capability(AgentCapability(
            name="planning",
            intent_patterns=["PLAN", "SCHEDULE", "ORGANIZE", "PREPARE", "COMPLEX_TASK"],
            keywords=["plan", "schedule", "organize", "steps", "break down", "how to", "approach"],
        ))

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})

        # Decompose the task
        tasks = self._decompose(text, intent, entities)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": f"Decomposed into {len(tasks)} sub-tasks",
                "tasks": tasks,
                "task_count": len(tasks),
            },
        )

    def _decompose(self, text: str, intent: str, entities: dict) -> list[dict]:
        tasks = []
        tasks.append({
            "step": 1,
            "action": "analyze",
            "description": f"Analyze request: {text[:80]}",
            "agent": "reasoning",
            "dependencies": [],
        })

        if any(kw in text.lower() for kw in ("search", "find", "look up", "research")):
            tasks.append({
                "step": 2,
                "action": "research",
                "description": "Gather information",
                "agent": "research",
                "dependencies": [1],
            })

        if any(kw in text.lower() for kw in ("code", "program", "script", "debug")):
            tasks.append({
                "step": 2,
                "action": "code",
                "description": "Generate or modify code",
                "agent": "coding",
                "dependencies": [1],
            })

        if any(kw in text.lower() for kw in ("remember", "memory", "recall")):
            tasks.append({
                "step": 2,
                "action": "memory",
                "description": "Access memory system",
                "agent": "memory",
                "dependencies": [],
            })

        tasks.append({
            "step": max(t["step"] for t in tasks) + 1 if tasks else 2,
            "action": "respond",
            "description": "Generate final response",
            "agent": "reasoning",
            "dependencies": [t["step"] for t in tasks if t["step"] > 1][:1],
        })

        return tasks


planner_agent = PlannerAgent()
