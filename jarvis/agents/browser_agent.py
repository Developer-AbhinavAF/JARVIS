"""Browser Agent — Web navigation, search, and automation."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class BrowserAgent(AgentBase):
    """Handles web search, navigation, tab management, and web extraction."""

    def __init__(self) -> None:
        super().__init__("browser", AgentPriority.MEDIUM)
        self.add_capability(AgentCapability(
            name="web_browse",
            intent_patterns=["WEB_SEARCH", "BROWSE", "NAVIGATE", "OPEN_URL"],
            keywords=["search", "browse", "google", "website", "url", "http", "www",
                     "open site", "go to", "visit"],
        ))

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})

        result = self._browse(text, intent, entities)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "url": result.get("url", ""),
                "title": result.get("title", ""),
            },
        )

    def _browse(self, text: str, intent: str, entities: dict) -> dict:
        query = entities.get("query") or text
        url = entities.get("url", "")

        if url:
            return {"response": f"Navigating to {url}", "url": url}

        return {"response": f"Searching the web for: {query}", "query": query}


browser_agent = BrowserAgent()
