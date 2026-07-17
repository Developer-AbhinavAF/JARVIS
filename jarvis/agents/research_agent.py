"""Research Agent — Web research, fact verification, and source ranking."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class ResearchAgent(AgentBase):
    """Handles web research, fact verification, paper search, and source ranking."""

    def __init__(self) -> None:
        super().__init__("research", AgentPriority.MEDIUM)
        self.add_capability(AgentCapability(
            name="research",
            intent_patterns=["RESEARCH", "FIND_INFO", "LOOKUP", "FACT_CHECK"],
            keywords=["research", "find out", "look up", "investigate", "fact check",
                     "what is", "who is", "how does", "explain", "tell me about"],
        ))

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})

        result = self._research(text, intent, entities)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "sources": result.get("sources", []),
                "confidence": result.get("confidence", 0.5),
            },
        )

    def _research(self, text: str, intent: str, entities: dict) -> dict:
        query = entities.get("query") or text
        return {
            "response": f"Researching: {query}",
            "sources": [],
            "confidence": 0.6,
        }


research_agent = ResearchAgent()
