"""Memory Agent — Memory retrieval, updates, and knowledge management."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class MemoryAgent(AgentBase):
    """Manages memory retrieval, updates, importance scoring, and knowledge graph."""

    def __init__(self) -> None:
        super().__init__("memory", AgentPriority.CRITICAL)
        self.add_capability(AgentCapability(
            name="memory_retrieval",
            intent_patterns=["RECALL_MEMORY", "REMEMBER", "SAVE_MEMORY", "FORGET"],
            keywords=["remember", "recall", "memory", "forgot", "forget", "saved", "note"],
        ))
        self._memory_store: dict[str, Any] = {}
        self._importance_scores: dict[str, float] = {}

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})

        if intent == "SAVE_MEMORY":
            result = self._save(text, entities)
        elif intent in ("RECALL_MEMORY", "REMEMBER"):
            result = self._recall(text, entities)
        elif intent == "FORGET":
            result = self._forget(entities)
        else:
            result = self._search(text)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "memories": result.get("memories", []),
                "importance": result.get("importance", 0.5),
            },
        )

    def _save(self, text: str, entities: dict) -> dict:
        key = str(hash(text))
        content = entities.get("content") or text
        self._memory_store[key] = {
            "text": content,
            "timestamp": time.time(),
            "entities": entities,
        }
        importance = self._score_importance(content)
        self._importance_scores[key] = importance
        return {"response": "Saved to memory.", "importance": importance}

    def _recall(self, text: str, entities: dict) -> dict:
        query = entities.get("query") or text
        matches = []
        for key, mem in self._memory_store.items():
            if any(kw in mem["text"].lower() for kw in query.lower().split()):
                matches.append({
                    "text": mem["text"],
                    "importance": self._importance_scores.get(key, 0.5),
                    "timestamp": mem["timestamp"],
                })
        matches.sort(key=lambda m: -m["importance"])

        if matches:
            return {
                "response": matches[0]["text"],
                "memories": matches[:5],
            }
        return {"response": "No relevant memories found.", "memories": []}

    def _forget(self, entities: dict) -> dict:
        query = entities.get("query", "")
        removed = 0
        for key in list(self._memory_store.keys()):
            if query.lower() in self._memory_store[key]["text"].lower():
                del self._memory_store[key]
                self._importance_scores.pop(key, None)
                removed += 1
        return {"response": f"Forget {removed} memories." if removed else "Nothing to forget."}

    def _search(self, text: str) -> dict:
        return self._recall(text, {"query": text})

    def _score_importance(self, text: str) -> float:
        score = 0.5
        important_words = ["important", "critical", "always", "never", "password", "key"]
        if any(w in text.lower() for w in important_words):
            score += 0.3
        if len(text) > 50:
            score += 0.1
        return min(1.0, score)


memory_agent = MemoryAgent()
