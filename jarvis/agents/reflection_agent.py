"""Reflection Agent — Self-analysis, workflow improvement, and mistake detection."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class ReflectionAgent(AgentBase):
    """Analyzes past actions, detects mistakes, and generates optimizations."""

    def __init__(self) -> None:
        super().__init__("reflection", AgentPriority.LOW)
        self.add_capability(AgentCapability(
            name="reflection",
            intent_patterns=["REFLECT", "ANALYZE_PERFORMANCE", "IMPROVE"],
            keywords=["reflect", "analyze", "improve", "optimize", "mistake", "better"],
        ))
        self._reflections: list[dict] = []

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")

        result = self._reflect(text, intent)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "improvements": result.get("improvements", []),
            },
        )

    def _reflect(self, text: str, intent: str) -> dict:
        reflection = {
            "text": text,
            "timestamp": time.time(),
            "improvements": [],
        }
        self._reflections.append(reflection)
        return {
            "response": "Reflection recorded.",
            "improvements": reflection["improvements"],
        }


reflection_agent = ReflectionAgent()
