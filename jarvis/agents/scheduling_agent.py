"""Scheduling Agent — Reminders, recurring tasks, and background jobs."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class SchedulingAgent(AgentBase):
    """Handles reminders, recurring tasks, background jobs, and delayed execution."""

    def __init__(self) -> None:
        super().__init__("scheduling", AgentPriority.LOW)
        self.add_capability(AgentCapability(
            name="scheduling",
            intent_patterns=["SET_REMINDER", "SCHEDULE", "SET_TIMER", "RECURRING_TASK"],
            keywords=["remind", "schedule", "timer", "alarm", "every day", "recurring",
                     "daily", "weekly", "monthly"],
        ))
        self._schedules: list[dict] = []

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})

        result = self._schedule(text, intent, entities)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "schedule_id": result.get("schedule_id", ""),
                "schedules": result.get("schedules", []),
            },
        )

    def _schedule(self, text: str, intent: str, entities: dict) -> dict:
        schedule = {
            "text": text,
            "intent": intent,
            "entities": entities,
            "created_at": time.time(),
            "status": "active",
        }
        self._schedules.append(schedule)
        schedule_id = str(len(self._schedules))
        return {
            "response": f"Schedule created (ID: {schedule_id}).",
            "schedule_id": schedule_id,
            "schedules": [schedule],
        }


scheduling_agent = SchedulingAgent()
