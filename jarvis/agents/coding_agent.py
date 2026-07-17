"""Coding Agent — Code generation, debugging, and repository analysis."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class CodingAgent(AgentBase):
    """Handles code generation, debugging, architecture analysis, and testing."""

    def __init__(self) -> None:
        super().__init__("coding", AgentPriority.MEDIUM)
        self.add_capability(AgentCapability(
            name="coding",
            intent_patterns=["CODE_GENERATE", "DEBUG", "REFACTOR", "CODE_ANALYSIS",
                           "TEST_GENERATE", "PROGRAMMING"],
            keywords=["code", "program", "script", "debug", "refactor", "test",
                     "function", "class", "bug", "error", "fix", "write code"],
        ))

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})

        result = self._code_operation(text, intent, entities)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "code": result.get("code", ""),
                "language": result.get("language", ""),
            },
        )

    def _code_operation(self, text: str, intent: str, entities: dict) -> dict:
        language = entities.get("language", "python")

        if "debug" in text.lower() or intent == "DEBUG":
            return {"response": "Analyzing code for issues.", "language": language}
        elif "refactor" in text.lower() or intent == "REFACTOR":
            return {"response": "Refactoring code.", "language": language}
        elif "test" in text.lower() or intent == "TEST_GENERATE":
            return {"response": "Generating tests.", "language": language}
        else:
            return {"response": f"Processing code request ({language}).", "language": language}


coding_agent = CodingAgent()
