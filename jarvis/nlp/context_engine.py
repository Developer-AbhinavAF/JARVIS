"""Conversation context engine for JARVIS NLP.

Tracks per-session conversational state, resolves pronoun / deictic
references (``"it"``, ``"that"``, ``"again"``, …), and provides
contextual hints so downstream modules can disambiguate multi-turn
inputs without calling the LLM.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class ConversationState:
    """Mutable state that is updated after every interaction turn."""

    # Last-turn metadata
    last_intent: str = ""
    last_entities: dict[str, Any] = field(default_factory=dict)
    last_target: str = ""
    last_platform: str = ""
    last_query: str = ""

    # Current focus – the "active" entity the user is working with
    current_app: str = ""
    current_website: str = ""
    current_folder: str = ""
    current_file: str = ""
    current_song: str = ""
    current_video: str = ""

    # Current search / task state
    current_search: str = ""
    current_goal: str = ""
    current_task: str = ""
    current_topic: str = ""
    current_window: str = ""
    current_browser_tab: str = ""

    # Programming context
    current_programming_project: str = ""
    current_repository: str = ""
    current_programming_language: str = ""

    # User state tracking
    current_user_emotion: str = "neutral"
    current_user_activity: str = ""  # idle, working, browsing, coding, etc.
    current_user_focus: str = ""  # high, medium, low

    # History & timing
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    session_start_time: float = field(default_factory=time.time)
    last_turn_time: float = 0.0

    # Learned user preferences (key → value, grows over session)
    user_preferences: dict[str, str] = field(default_factory=dict)


# ════════════════════════════════════════════════════════════════════
# CONTEXT ENGINE
# ════════════════════════════════════════════════════════════════════

# Pronouns / deictic tokens that should be resolved from context.
_PRONOUNS: dict[str, str] = {
    "it": "last_target",
    "this": "last_target",
    "that": "last_target",
    "them": "last_target",
    "same": "last_target",
    "again": "last_target",
    "next": "last_target",
    "back": "last_target",
    "there": "last_target",
}

# Maps intent prefixes → the state field that "owns" focus.
_INTENT_FOCUS_MAP: dict[str, str] = {
    "open_app": "current_app",
    "close_app": "current_app",
    "launch_app": "current_app",
    "switch_app": "current_app",
    "open_website": "current_website",
    "visit_site": "current_website",
    "search_web": "current_search",
    "search_on_platform": "current_search",
    "browse": "current_search",
    "open_folder": "current_folder",
    "open_file": "current_file",
    "open_path": "current_file",
    "navigate": "current_folder",
    "play_song": "current_song",
    "play_music": "current_song",
    "search_music": "current_song",
    "programming": "current_programming_project",
    "open_vscode": "current_programming_project",
    "open_terminal": "current_programming_project",
    "version_control": "current_repository",
    "git_init": "current_repository",
    "git_clone": "current_repository",
    "play_video": "current_video",
}

# Suggested follow-ups keyed by the intent that just completed.
_FOLLOWUP_SUGGESTIONS: dict[str, list[str]] = {
    "open_app": [
        "Open another app",
        "Switch to browser",
        "Close the app",
    ],
    "search_web": [
        "Open the first result",
        "Search on YouTube instead",
        "Refine the search",
    ],
    "open_folder": [
        "Open a file in the folder",
        "Go to Downloads",
        "Create a new folder",
    ],
    "play_song": [
        "Pause the song",
        "Play the next track",
        "Add to playlist",
    ],
    "open_website": [
        "Search on the site",
        "Bookmark the page",
        "Open in incognito",
    ],
}


class ContextEngine:
    """Tracks conversational state and resolves references across turns.

    Example::

        ctx = ContextEngine()
        ctx.update("search_web", {"query": "python async"}, None, True)
        ctx.resolve_references("open it")
        # → "open https://www.google.com/search?q=python async"
    """

    TIMEOUT_SECONDS: float = 300.0  # 5 minutes

    def __init__(self) -> None:
        self.state = ConversationState()

    # ── public API ──────────────────────────────────────────────────

    def update(
        self,
        intent: str,
        entities: dict[str, Any],
        tool_result: Any,
        success: bool,
    ) -> None:
        """Update state after a completed interaction.

        Parameters
        ----------
        intent:
            The classified intent string.
        entities:
            Extracted entity dict (values may be :class:`Entity` objects
            or plain dicts/strings).
        tool_result:
            Raw result returned by the tool executor (may be ``None``).
        success:
            Whether the tool executed successfully.
        """
        self.state.turn_count += 1
        self.state.last_turn_time = time.time()
        self.state.last_intent = intent

        # Store normalised entity values
        resolved: dict[str, str] = {}
        for key, ent in entities.items():
            if hasattr(ent, "value"):
                resolved[key] = ent.value
            elif isinstance(ent, dict):
                resolved[key] = ent.get("value", str(ent))
            else:
                resolved[key] = str(ent)
        self.state.last_entities = resolved

        # Update focus fields based on intent
        focus_key = self._focus_key_for_intent(intent)
        if focus_key:
            primary = self._primary_entity_value(entities)
            if primary:
                setattr(self.state, focus_key, primary)
                self.state.last_target = primary

        # Extract commonly-used fields
        self.state.last_query = resolved.get("query", "")
        self.state.last_platform = resolved.get("platform", "")
        self.state.last_target = (
            resolved.get("query")
            or resolved.get("website")
            or resolved.get("app")
            or resolved.get("path")
            or resolved.get("platform")
            or self.state.last_target
        )

        # Append to history (keep last 20 turns)
        self.state.conversation_history.append({
            "turn": self.state.turn_count,
            "intent": intent,
            "entities": resolved,
            "success": success,
            "timestamp": self.state.last_turn_time,
        })
        self.state.conversation_history = (
            self.state.conversation_history[-20:]
        )

    # Memory-related verbs after which "this"/"that" should NOT be resolved.
    # "remember this important fact" → "this" is the object, not a reference.
    _MEMORY_VERBS = frozenset({
        "remember", "recall", "note", "save", "store", "forget",
        "memorize", "log", "record",
    })

    def resolve_references(self, text: str) -> str:
        """Replace pronouns and deictic tokens with concrete entities.

        Only resolves when the context is still valid (within timeout).

        Returns the text with pronouns substituted, or the original
        text if context has expired or no resolution is possible.
        """
        if not self.should_use_context():
            return text

        words = text.lower().split()
        resolved_words: list[str] = []
        changed = False

        for i, word in enumerate(words):
            clean = word.strip(".,!?;:'\"")
            if clean in _PRONOUNS:
                # Skip resolution for "this"/"that" after memory verbs
                # e.g. "remember this important fact" — "this" is not a reference
                if clean in ("this", "that") and i > 0:
                    prev = words[i - 1].strip(".,!?;:'\"")
                    if prev in self._MEMORY_VERBS:
                        resolved_words.append(word)
                        continue

                target_field = _PRONOUNS[clean]
                replacement = getattr(self.state, target_field, "")
                if replacement:
                    resolved_words.append(replacement)
                    changed = True
                else:
                    resolved_words.append(word)
            else:
                resolved_words.append(word)

        return " ".join(resolved_words) if changed else text

    def get_context_for_intent(self, intent: str) -> dict[str, Any]:
        """Return a context dict relevant for *intent*.

        Contains the current focus entity, recent history, and any
        learned preferences that may affect execution.
        """
        if not self.should_use_context():
            return {}

        focus_key = self._focus_key_for_intent(intent)
        context: dict[str, Any] = {
            "turn_count": self.state.turn_count,
            "last_intent": self.state.last_intent,
            "last_target": self.state.last_target,
            "last_query": self.state.last_query,
            "last_platform": self.state.last_platform,
            "recent_history": self.state.conversation_history[-5:],
            "preferences": dict(self.state.user_preferences),
        }

        if focus_key:
            context["current_focus"] = getattr(self.state, focus_key, "")
        if self.state.current_app:
            context["current_app"] = self.state.current_app
        if self.state.current_website:
            context["current_website"] = self.state.current_website
        if self.state.current_search:
            context["current_search"] = self.state.current_search
        if self.state.current_folder:
            context["current_folder"] = self.state.current_folder
        if self.state.current_programming_project:
            context["current_programming_project"] = self.state.current_programming_project
        if self.state.current_repository:
            context["current_repository"] = self.state.current_repository
        if self.state.current_programming_language:
            context["current_programming_language"] = self.state.current_programming_language
        if self.state.current_video:
            context["current_video"] = self.state.current_video
        if self.state.current_user_emotion and self.state.current_user_emotion != "neutral":
            context["current_user_emotion"] = self.state.current_user_emotion
        if self.state.current_user_activity:
            context["current_user_activity"] = self.state.current_user_activity

        return context

    def should_use_context(self) -> bool:
        """Return ``True`` if the conversation context is still fresh.

        Context is considered expired if more than ``TIMEOUT_SECONDS``
        have elapsed since the last interaction.
        """
        if self.state.last_turn_time == 0.0:
            return False
        elapsed = time.time() - self.state.last_turn_time
        return elapsed <= self.TIMEOUT_SECONDS

    def get_followup_suggestion(self) -> str | None:
        """Suggest a likely next action based on the last intent.

        Returns ``None`` when no suggestion is available or context has
        expired.
        """
        if not self.should_use_context():
            return None

        suggestions = _FOLLOWUP_SUGGESTIONS.get(self.state.last_intent)
        if suggestions and self.state.turn_count > 0:
            # Rotate through suggestions based on turn count
            idx = self.state.turn_count % len(suggestions)
            return suggestions[idx]
        return None

    def clear(self) -> None:
        """Reset all conversation state."""
        self.state = ConversationState()

    def snapshot(self) -> dict[str, Any]:
        """Serialise the current state to a plain dict.

        Useful for logging, debugging, or persisting state across
        sessions.
        """
        return {
            "last_intent": self.state.last_intent,
            "last_entities": self.state.last_entities,
            "last_target": self.state.last_target,
            "last_platform": self.state.last_platform,
            "last_query": self.state.last_query,
            "current_app": self.state.current_app,
            "current_website": self.state.current_website,
            "current_folder": self.state.current_folder,
            "current_file": self.state.current_file,
            "current_song": self.state.current_song,
            "current_video": self.state.current_video,
            "current_search": self.state.current_search,
            "current_goal": self.state.current_goal,
            "current_task": self.state.current_task,
            "current_topic": self.state.current_topic,
            "current_window": self.state.current_window,
            "current_browser_tab": self.state.current_browser_tab,
            "current_programming_project": self.state.current_programming_project,
            "current_repository": self.state.current_repository,
            "current_programming_language": self.state.current_programming_language,
            "current_user_emotion": self.state.current_user_emotion,
            "current_user_activity": self.state.current_user_activity,
            "current_user_focus": self.state.current_user_focus,
            "turn_count": self.state.turn_count,
            "session_start_time": self.state.session_start_time,
            "last_turn_time": self.state.last_turn_time,
            "history_length": len(self.state.conversation_history),
            "preferences": dict(self.state.user_preferences),
        }

    # ── private helpers ─────────────────────────────────────────────

    @staticmethod
    def _focus_key_for_intent(intent: str) -> str | None:
        """Map an intent to the ConversationState field it updates."""
        for prefix, field_name in _INTENT_FOCUS_MAP.items():
            if intent.startswith(prefix):
                return field_name
        return None

    @staticmethod
    def _primary_entity_value(entities: dict[str, Any]) -> str:
        """Return the most salient entity value from a dict."""
        # Priority order for the "primary" value
        priority = [
            "app", "website", "path", "folder", "file",
            "query", "platform", "url", "song", "video",
            "project", "repository", "language",
        ]
        for key in priority:
            ent = entities.get(key)
            if ent is not None:
                if hasattr(ent, "value"):
                    return ent.value
                if isinstance(ent, dict):
                    return ent.get("value", "")
                return str(ent)
        return ""
