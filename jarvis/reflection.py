"""Post-interaction reflection and memory gating."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from jarvis import config
from jarvis.memory_manager import intelligent_memory
from jarvis.nlp_pipeline import nlp_pipeline

logger = logging.getLogger(__name__)


@dataclass
class Reflection:
    learned: str
    should_remember: bool
    confidence: float
    suggested_category: str
    stored_memory_id: str | None = None


class ReflectionManager:
    """Reflect after important interactions and store validated memories."""

    def reflect_interaction(self, user_message: str, assistant_response: str) -> Reflection:
        nlp = nlp_pipeline.process(user_message)
        explicit = nlp.intent == "remember"
        content = self._extract_memory_content(user_message)
        category = intelligent_memory.categorize(content)

        should_save = explicit or nlp.memory_relevance >= config.MEMORY_REFLECTION_THRESHOLD
        stored_id = None
        if should_save:
            record = intelligent_memory.remember(
                content,
                category=category,
                source="reflection",
                importance_score=nlp.memory_relevance,
                explicit=explicit,
            )
            stored_id = record.id if record else None

        return Reflection(
            learned=content,
            should_remember=should_save,
            confidence=nlp.memory_relevance,
            suggested_category=category,
            stored_memory_id=stored_id,
        )

    def _extract_memory_content(self, text: str) -> str:
        cleaned = text.strip()
        prefixes = [
            "remember this",
            "remember that",
            "learn this",
            "save this",
            "save this for later",
            "this is important",
        ]
        lower = cleaned.lower()
        for prefix in prefixes:
            if lower.startswith(prefix):
                return cleaned[len(prefix):].strip(" :-") or cleaned
        return cleaned

    def reflect_tool_failure(self, tool_name: str, error: str) -> None:
        try:
            from jarvis.lessons import lessons_db

            lessons_db.add_lesson(
                lesson_type="tool_failure",
                title=f"Tool failed: {tool_name}",
                description=error,
                source=tool_name,
                confidence=0.85,
                suggestion="Review validation, dependencies, and fallback behavior before changing code.",
            )
        except Exception:
            logger.debug("Could not record tool failure reflection", exc_info=True)


reflection_manager = ReflectionManager()
