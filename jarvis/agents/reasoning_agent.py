"""Reasoning Agent — Decision making and goal prediction."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class ReasoningAgent(AgentBase):
    """Handles decision making, goal prediction, solution generation, and confidence scoring."""

    def __init__(self) -> None:
        super().__init__("reasoning", AgentPriority.CRITICAL)
        self.add_capability(AgentCapability(
            name="reasoning",
            intent_patterns=["REASON", "ANALYZE", "DECIDE", "EVALUATE", "EXPLAIN"],
            keywords=["why", "how", "because", "reason", "explain", "analyze", "decide", "evaluate"],
        ))
        self.add_capability(AgentCapability(
            name="greeting",
            intent_patterns=["GREETING"],
            keywords=["hello", "hi", "hey", "good morning"],
        ))
        self.add_capability(AgentCapability(
            name="datetime",
            intent_patterns=["DATETIME", "TIME", "DATE"],
            keywords=["time", "date", "day", "hour", "when"],
        ))

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})

        response = self._generate_response(text, intent, entities)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": response,
                "intent": intent,
                "confidence": 0.85,
                "reasoning": f"Processed {intent} intent",
            },
        )

    def _generate_response(self, text: str, intent: str, entities: dict) -> str:
        lower = text.lower().strip()

        if intent == "GREETING" or any(kw in lower for kw in ("hello", "hi", "hey")):
            return "Hello! How can I help you?"

        if intent == "DATETIME" or any(kw in lower for kw in ("time", "date", "what time")):
            from datetime import datetime
            now = datetime.now()
            return f"Current time: {now.strftime('%I:%M %p')}. Today is {now.strftime('%A, %B %d, %Y')}."

        if intent == "WEATHER":
            location = entities.get("location", "your area")
            return f"Let me check the weather for {location}."

        if intent == "OPEN_APP":
            app = entities.get("app_name") or entities.get("application") or "the application"
            return f"Opening {app}."

        if intent == "CLOSE_APP":
            app = entities.get("app_name") or entities.get("application") or "the application"
            return f"Closing {app}."

        if intent == "PLAY_MUSIC":
            query = entities.get("query") or text
            return f"Playing: {query}"

        if intent == "WEB_SEARCH":
            query = entities.get("query") or text
            return f"Searching for: {query}"

        if intent == "SAVE_MEMORY" or intent == "REMEMBER":
            return "I'll remember that."

        if intent == "RECALL_MEMORY":
            return "Let me check my memory."

        return f"I understand you want to {intent.lower().replace('_', ' ') if intent else 'do something'}."

    def _calculate_confidence(self, intent: str, entities: dict) -> float:
        base = 0.7
        if entities:
            base += 0.1
        if intent in ("GREETING", "DATETIME", "TIME", "DATE"):
            base += 0.15
        return min(1.0, base)


reasoning_agent = ReasoningAgent()
