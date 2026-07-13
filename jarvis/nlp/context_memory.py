"""Context memory for JARVIS NLP pipeline.

Tracks conversation state to resolve follow-up commands and pronouns.
Supports:
- Last intent tracking
- Entity persistence across turns
- Pronoun resolution (this, it, that, them)
- Follow-up command inference
- Topic tracking
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    timestamp: float
    raw_text: str
    normalized_text: str
    intent: str
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    tool_name: str = ""
    tool_result: str = ""
    success: bool = True


@dataclass
class ContextState:
    """Current conversation context."""
    last_intent: str = ""
    last_entities: dict[str, Any] = field(default_factory=dict)
    last_tool_name: str = ""
    last_target: str = ""
    last_platform: str = ""
    last_query: str = ""
    last_topic: str = ""
    last_success: bool = True
    turn_count: int = 0
    last_turn_time: float = 0.0

    # Pronoun resolution
    this_target: str = ""  # What "this" refers to
    it_target: str = ""    # What "it" refers to
    that_target: str = ""  # What "that" refers to


# Pronouns that need resolution
_PRONOUNS = {"this", "it", "that", "them", "those", "there"}

# Follow-up intent mappings: (last_intent, current_intent) -> inferred intent
_FOLLOWUP_INTENTS: dict[tuple[str, str], str] = {
    # After opening something, "search" means search within that context
    ("OPEN_WEBSITE", "SEARCH_WEB"): "SEARCH_ON_PLATFORM",
    ("OPEN_APP", "SEARCH_WEB"): "SEARCH_WEB",
    # After opening a platform, "search" means search that platform
    ("OPEN_WEBSITE", "PLAY_MUSIC"): "PLAY_YOUTUBE",
    # After opening a folder, file operations apply to that folder
    ("OPEN_FOLDER", "DELETE_FILE"): "DELETE_FILE",
    ("OPEN_FOLDER", "COPY_FILE"): "COPY_FILE",
    ("OPEN_FOLDER", "RENAME_FILE"): "RENAME_FILE",
}

# Context-dependent intent inference from minimal input
_CONTEXTUAL_INTENTS: dict[str, dict[str, str]] = {
    # If last intent was a website and current input is a search query
    "OPEN_WEBSITE": {
        "intent": "SEARCH_ON_PLATFORM",
        "confidence": 0.80,
    },
    # If last intent was a music player
    "PLAY_MUSIC": {
        "intent": "PLAY_MUSIC",
        "confidence": 0.75,
    },
    "PLAY_YOUTUBE": {
        "intent": "SEARCH_YOUTUBE",
        "confidence": 0.80,
    },
    "PLAY_SPOTIFY": {
        "intent": "SEARCH_ON_PLATFORM",
        "confidence": 0.80,
    },
}


class ContextMemory:
    """Tracks conversation state for follow-up command resolution.

    Features:
    - Remembers last intent, entities, and targets
    - Resolves pronouns (this, it, that) to last mentioned entity
    - Infers intent from context when input is ambiguous
    - Maintains conversation history for pattern learning
    - Auto-clears after timeout (5 minutes)
    """

    def __init__(self, timeout_seconds: float = 300.0) -> None:
        self.state = ContextState()
        self.history: list[ConversationTurn] = []
        self.timeout_seconds = timeout_seconds

    def update(
        self,
        raw_text: str,
        normalized_text: str,
        intent: str,
        confidence: float,
        entities: dict[str, Any] | None = None,
        tool_name: str = "",
        tool_result: str = "",
        success: bool = True,
    ) -> None:
        """Update context with a new conversation turn."""
        now = time.time()

        # Auto-clear if timeout exceeded
        if self.state.turn_count > 0 and (now - self.state.last_turn_time) > self.timeout_seconds:
            self.clear()

        # Record turn
        turn = ConversationTurn(
            timestamp=now,
            raw_text=raw_text,
            normalized_text=normalized_text,
            intent=intent,
            confidence=confidence,
            entities=entities or {},
            tool_name=tool_name,
            tool_result=tool_result,
            success=success,
        )
        self.history.append(turn)

        # Keep only last 50 turns
        if len(self.history) > 50:
            self.history = self.history[-50:]

        # Update state
        self.state.last_intent = intent
        self.state.last_entities = entities or {}
        self.state.last_tool_name = tool_name
        self.state.last_success = success
        self.state.turn_count += 1
        self.state.last_turn_time = now

        # Extract and remember targets
        if entities:
            if "target" in entities:
                target = str(entities["target"])
                self.state.last_target = target
                self.state.this_target = target
                self.state.it_target = target
                self.state.that_target = target
            if "platform" in entities:
                self.state.last_platform = str(entities["platform"])
            if "query" in entities:
                self.state.last_query = str(entities["query"])
            if "city" in entities:
                self.state.last_topic = str(entities["city"])

    def resolve_pronouns(self, text: str) -> str:
        """Resolve pronouns in text to their referenced entities.

        Example:
            "search AI" after "open youtube" → "search AI on youtube"
            "delete it" after "open file.txt" → "delete file.txt"
        """
        words = text.split()
        resolved = []
        for word in words:
            if word.lower() == "this" and self.state.this_target:
                resolved.append(self.state.this_target)
            elif word.lower() == "it" and self.state.it_target:
                resolved.append(self.state.it_target)
            elif word.lower() == "that" and self.state.that_target:
                resolved.append(self.state.that_target)
            elif word.lower() == "them" and self.state.it_target:
                resolved.append(self.state.it_target)
            else:
                resolved.append(word)
        return " ".join(resolved)

    def infer_followup_intent(self, text: str, current_intent: str) -> str | None:
        """Infer intent from context when input is ambiguous.

        Returns the inferred intent if context suggests a follow-up,
        or None if the current intent is clear.
        """
        if not self.state.last_intent:
            return None

        # Check explicit follow-up mappings
        key = (self.state.last_intent, current_intent)
        if key in _FOLLOWUP_INTENTS:
            return _FOLLOWUP_INTENTS[key]

        # Check if input is too short and context can fill in
        words = text.strip().split()
        if len(words) <= 3 and self.state.last_intent in _CONTEXTUAL_INTENTS:
            ctx = _CONTEXTUAL_INTENTS[self.state.last_intent]
            # Only use context if the input looks like a search query
            if current_intent in ("SEARCH_WEB", "SEARCH_ON_PLATFORM", "SEARCH_YOUTUBE", "PLAY_MUSIC"):
                return ctx["intent"]

        return None

    def should_use_context(self) -> bool:
        """Check if context should be used for resolution."""
        if self.state.turn_count == 0:
            return False
        # Only use context within timeout window
        elapsed = time.time() - self.state.last_turn_time
        return elapsed < self.timeout_seconds

    def get_last_target(self) -> str:
        """Get the last mentioned target (app, website, file, etc.)."""
        return self.state.last_target

    def get_last_platform(self) -> str:
        """Get the last mentioned platform."""
        return self.state.last_platform

    def get_last_query(self) -> str:
        """Get the last search query."""
        return self.state.last_query

    def clear(self) -> None:
        """Clear all conversation state."""
        self.state = ContextState()

    def get_stats(self) -> dict[str, Any]:
        """Get context memory statistics."""
        return {
            "turn_count": self.state.turn_count,
            "last_intent": self.state.last_intent,
            "last_target": self.state.last_target,
            "last_platform": self.state.last_platform,
            "history_length": len(self.history),
        }


# Global instance
context_memory = ContextMemory()
