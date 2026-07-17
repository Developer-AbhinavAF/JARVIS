"""Learning Agent — Habit detection, preference learning, and continuous improvement."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class LearningAgent(AgentBase):
    """Handles habit detection, preference learning, workflow learning, and behavior analysis."""

    def __init__(self) -> None:
        super().__init__("learning", AgentPriority.LOW)
        self.add_capability(AgentCapability(
            name="learning",
            intent_patterns=["LEARN", "PREFERENCE", "HABIT"],
            keywords=["prefer", "like", "always", "usually", "habit", "pattern"],
        ))
        self._learnings: list[dict] = []

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})

        result = self._learn(text, intent, entities)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "learnings": result.get("learnings", []),
            },
        )

    def _learn(self, text: str, intent: str, entities: dict) -> dict:
        learning = {
            "text": text,
            "intent": intent,
            "entities": entities,
            "timestamp": time.time(),
        }
        self._learnings.append(learning)
        return {
            "response": "Learning recorded.",
            "learnings": [learning],
        }


learning_agent = LearningAgent()
