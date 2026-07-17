"""Memory bridge between the NLP engine and JARVIS memory system.

Decides what to remember, prepares structured memory entries, and
provides recall/relevance scoring so the NLP pipeline can enrich
future interactions with historical context.

Memory categories:
- **preference**: User preferences (preferred apps, settings)
- **fact**: Important facts the user shared
- **command**: Frequently used commands
- **context**: Conversation context for follow-ups
- **correction**: User corrections ("actually, I meant…")
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from jarvis.nlp.utils import semantic_similarity, tokenize, remove_stop_words


# ════════════════════════════════════════════════════════════════════
# CONSTANTS
# ════════════════════════════════════════════════════════════════════

MEMORY_CATEGORIES = ("preference", "fact", "command", "context", "correction")

# Intents that are worth remembering
_REMEMBERABLE_INTENTS: set[str] = {
    "SAVE_MEMORY",
    "RECALL_MEMORY",
    "ADD_TODO",
    "ADD_NOTE",
    "OPEN_APP",
    "CLOSE_APP",
    "OPEN_WEBSITE",
    "SEARCH_WEB",
    "SEARCH_ON_PLATFORM",
    "PLAY_MUSIC",
    "PLAY_YOUTUBE",
    "PLAY_SPOTIFY",
    "GET_WEATHER",
    "GET_NEWS",
    "VOLUME_CONTROL",
    "BRIGHTNESS_CONTROL",
    "SYSTEM_POWER",
    "CALCULATOR",
    "TIMER",
    "SCREENSHOT",
    "FILE_MANAGEMENT",
    "OPEN_FOLDER",
    "STOCK_QUOTE",
    "PROGRAMMING",
    "OPEN_VSCODE",
    "OPEN_TERMINAL",
    "VERSION_CONTROL",
    "GIT_INIT",
    "GIT_CLONE",
    "GIT_COMMIT",
    "RUN_CODE",
    "DATABASE_QUERY",
    "CLOUD_UPLOAD",
    "TRAIN_MODEL",
    "SECURITY_SCAN",
    "AUTOMATE_TASK",
    "ANALYZE_DATA",
    "DEPLOY_APP",
    "RUN_TESTS",
}

# Intent → default category mapping
_INTENT_CATEGORIES: dict[str, str] = {
    "SAVE_MEMORY": "fact",
    "RECALL_MEMORY": "fact",
    "ADD_TODO": "command",
    "ADD_NOTE": "fact",
    "OPEN_APP": "command",
    "CLOSE_APP": "command",
    "OPEN_WEBSITE": "command",
    "SEARCH_WEB": "command",
    "SEARCH_ON_PLATFORM": "command",
    "PLAY_MUSIC": "command",
    "PLAY_YOUTUBE": "command",
    "PLAY_SPOTIFY": "command",
    "GET_WEATHER": "fact",
    "GET_NEWS": "fact",
    "VOLUME_CONTROL": "command",
    "BRIGHTNESS_CONTROL": "command",
    "SYSTEM_POWER": "command",
    "CALCULATOR": "command",
    "TIMER": "command",
    "SCREENSHOT": "command",
    "FILE_MANAGEMENT": "command",
    "OPEN_FOLDER": "command",
    "STOCK_QUOTE": "fact",
}

# Patterns that signal user corrections
_CORRECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bactually,?\s*(i meant|i want|i meant to)\b", re.IGNORECASE),
    re.compile(r"\bno,?\s*(i meant|i want|not that|use)\b", re.IGNORECASE),
    re.compile(r"\bwait,?\s*(i meant|not|use)\b", re.IGNORECASE),
    re.compile(r"\bsorry,?\s*(i meant|not|use)\b", re.IGNORECASE),
    re.compile(r"\bnot\s+\w+,?\s*(i meant|use|try)\b", re.IGNORECASE),
    re.compile(r"\bchange\s+(it|that|this)\s+to\b", re.IGNORECASE),
    re.compile(r"\bmake it\b", re.IGNORECASE),
]

# Patterns that signal facts about the user
_FACT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bmy\s+(favorite|fav|preferred)\s+\w+\s+is\b", re.IGNORECASE),
    re.compile(r"\bi\s+(like|love|prefer|hate|use)\s+\w+", re.IGNORECASE),
    re.compile(r"\bi\s+usually\s+\w+", re.IGNORECASE),
    re.compile(r"\bi\s+always\s+\w+", re.IGNORECASE),
    re.compile(r"\bremember\s+(that\s+)?my\b", re.IGNORECASE),
]


# ════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class MemoryEntry:
    """A single stored memory entry."""
    id: str = ""
    category: str = ""  # preference | fact | command | context | correction
    intent: str = ""
    text: str = ""
    entities: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    goal: str = ""
    timestamp: float = 0.0
    relevance_score: float = 0.0
    access_count: int = 0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "id": self.id,
            "category": self.category,
            "intent": self.intent,
            "text": self.text,
            "entities": self.entities,
            "context": self.context,
            "goal": self.goal,
            "timestamp": self.timestamp,
            "relevance_score": self.relevance_score,
            "access_count": self.access_count,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        """Deserialize from a dict."""
        return cls(
            id=data.get("id", ""),
            category=data.get("category", ""),
            intent=data.get("intent", ""),
            text=data.get("text", ""),
            entities=data.get("entities", {}),
            context=data.get("context", {}),
            goal=data.get("goal", ""),
            timestamp=data.get("timestamp", 0.0),
            relevance_score=data.get("relevance_score", 0.0),
            access_count=data.get("access_count", 0),
            tags=data.get("tags", []),
        )


# ════════════════════════════════════════════════════════════════════
# BRIDGE
# ════════════════════════════════════════════════════════════════════

class MemoryBridge:
    """Bridges the NLP engine to the long-term memory system.

    Responsibilities:
    - Decide whether an interaction should be remembered
    - Prepare structured memory entries from NLP output
    - Store and retrieve memories
    - Score relevance of stored memories to a query
    - Categorize memories automatically
    """

    def __init__(self, memory_manager: Any | None = None) -> None:
        """
        Args:
            memory_manager: Optional external memory manager with
                ``store()`` and ``search()`` methods.  When ``None``
                the bridge uses its own in-memory list.
        """
        self._memory_manager = memory_manager
        self._entries: list[MemoryEntry] = []
        self._next_id: int = 1
        self._category_counts: dict[str, int] = {cat: 0 for cat in MEMORY_CATEGORIES}

    # ── Core API ───────────────────────────────────────────────────

    def should_remember(
        self,
        intent: str,
        entities: dict[str, Any],
        goal: str = "",
    ) -> bool:
        """Decide if this interaction is worth storing in memory.

        Heuristics:
        - Always remember explicit save/recall intents
        - Always remember corrections
        - Remember commands if they have meaningful entities
        - Skip trivial intents (greetings, jokes, dice rolls)
        """
        # Explicit memory operations
        if intent in ("SAVE_MEMORY", "RECALL_MEMORY", "ADD_TODO", "ADD_NOTE"):
            return True

        # Corrections are always valuable
        if intent == "CORRECTION":
            return True

        # If the intent is not in our rememberable set, skip
        if intent not in _REMEMBERABLE_INTENTS:
            return False

        # For commands, only remember if there's something specific
        if intent in ("OPEN_APP", "CLOSE_APP"):
            return bool(entities.get("target"))
        if intent in ("OPEN_WEBSITE", "SEARCH_ON_PLATFORM"):
            return bool(entities.get("platform") or entities.get("target"))
        if intent == "SEARCH_WEB":
            return bool(entities.get("query"))
        if intent in ("PLAY_MUSIC", "PLAY_YOUTUBE", "PLAY_SPOTIFY"):
            return bool(entities.get("query") or entities.get("platform"))
        if intent == "GET_WEATHER":
            return bool(entities.get("city"))
        if intent == "STOCK_QUOTE":
            return bool(entities.get("symbol") or entities.get("query"))

        # Default: remember it if it's a known intent
        return True

    def prepare_memory_entry(
        self,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
        goal: str = "",
    ) -> dict[str, Any]:
        """Create a structured memory entry from NLP output.

        Returns a dict suitable for passing to :meth:`store`.
        """
        category = self._categorize_memory(intent, goal)
        text = self._build_entry_text(intent, entities, context)
        tags = self._extract_tags(intent, entities)

        entry = MemoryEntry(
            id=self._generate_id(),
            category=category,
            intent=intent,
            text=text,
            entities=entities,
            context=context,
            goal=goal,
            timestamp=time.time(),
            tags=tags,
        )
        return entry.to_dict()

    def store(self, entry: dict[str, Any]) -> str:
        """Store a memory entry and return its ID.

        Accepts either a dict (from :meth:`prepare_memory_entry`) or
        a :class:`MemoryEntry` converted via ``to_dict()``.
        """
        mem = MemoryEntry.from_dict(entry)

        if not mem.id:
            mem.id = self._generate_id()
        if mem.timestamp == 0.0:
            mem.timestamp = time.time()

        # Delegate to external manager if available
        if self._memory_manager is not None:
            try:
                self._memory_manager.store(mem.to_dict())
            except Exception:
                pass

        # Always keep a local copy
        self._entries.append(mem)
        self._category_counts[mem.category] = (
            self._category_counts.get(mem.category, 0) + 1
        )

        # Cap at 2000 entries
        if len(self._entries) > 2000:
            self._entries = self._entries[-2000:]

        return mem.id

    def recall(self, query: str) -> list[dict[str, Any]]:
        """Search memory for entries relevant to *query*.

        Returns matching entries sorted by relevance score descending.
        """
        if not query.strip():
            return []

        # Try external manager first
        if self._memory_manager is not None:
            try:
                results = self._memory_manager.search(query)
                if results:
                    return results
            except Exception:
                pass

        # Local search: score every entry
        scored: list[tuple[float, MemoryEntry]] = []
        for entry in self._entries:
            score = self._calculate_relevance_score(entry, query)
            if score > 0.05:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[dict[str, Any]] = []
        for score, entry in scored[:20]:
            entry.relevance_score = score
            entry.access_count += 1
            results.append(entry.to_dict())

        return results

    def get_relevant_context(self, query: str) -> dict[str, Any]:
        """Retrieve contextual information from memory for *query*.

        Returns a dict with:
        - ``relevant_entries``: top matching memories
        - ``user_preferences``: any preferences relevant to the query
        - ``recent_corrections``: recent corrections that may apply
        - ``suggested_intent``: intent suggested by past patterns
        - ``category_counts``: breakdown of stored memories
        """
        relevant = self.recall(query)

        # Extract preferences from relevant entries
        preferences = [
            e for e in self._entries
            if e.category == "preference" and self._calculate_relevance_score(e, query) > 0.1
        ]

        # Recent corrections (last 10 minutes)
        cutoff = time.time() - 600
        recent_corrections = [
            e.to_dict() for e in self._entries
            if e.category == "correction" and e.timestamp > cutoff
        ]

        # Suggest intent based on most common intent in relevant entries
        intent_suggestion = ""
        if relevant:
            intent_counts: dict[str, int] = {}
            for entry_dict in relevant:
                i = entry_dict.get("intent", "")
                intent_counts[i] = intent_counts.get(i, 0) + 1
            if intent_counts:
                intent_suggestion = max(intent_counts, key=intent_counts.get)  # type: ignore[arg-type]

        return {
            "relevant_entries": relevant[:5],
            "user_preferences": [p.to_dict() for p in preferences[:5]],
            "recent_corrections": recent_corrections,
            "suggested_intent": intent_suggestion,
            "category_counts": dict(self._category_counts),
        }

    # ── Categorization ─────────────────────────────────────────────

    def _categorize_memory(self, intent: str, goal: str = "") -> str:
        """Determine the memory category for an intent + goal pair."""
        # Explicit corrections
        if intent == "CORRECTION":
            return "correction"

        # Check the intent → category map
        if intent in _INTENT_CATEGORIES:
            return _INTENT_CATEGORIES[intent]

        # Fallback heuristics
        intent_lower = intent.lower()
        if "memory" in intent_lower or "save" in intent_lower or "recall" in intent_lower:
            return "fact"
        if "todo" in intent_lower or "note" in intent_lower:
            return "command"
        if "open" in intent_lower or "close" in intent_lower or "search" in intent_lower:
            return "command"

        return "context"

    def _is_correction(self, text: str) -> bool:
        """Check if the raw text is a user correction."""
        return any(p.search(text) for p in _CORRECTION_PATTERNS)

    def _is_fact(self, text: str) -> bool:
        """Check if the raw text contains a user fact."""
        return any(p.search(text) for p in _FACT_PATTERNS)

    # ── Relevance Scoring ──────────────────────────────────────────

    def _calculate_relevance_score(
        self,
        entry: MemoryEntry,
        query: str,
    ) -> float:
        """Score how relevant *entry* is to *query*.

        Uses a weighted combination of:
        1. Text similarity between entry text and query
        2. Entity overlap
        3. Recency decay
        4. Access frequency bonus
        """
        query_lower = query.lower().strip()
        entry_lower = entry.text.lower().strip()

        if not query_lower or not entry_lower:
            return 0.0

        # 1. Text similarity (semantic)
        text_sim = semantic_similarity(query_lower, entry_lower)

        # 2. Entity overlap
        entity_score = 0.0
        query_tokens = set(remove_stop_words(tokenize(query_lower)))
        for ent_value in entry.entities.values():
            ent_tokens = set(remove_stop_words(tokenize(str(ent_value).lower())))
            if ent_tokens and query_tokens:
                overlap = query_tokens & ent_tokens
                entity_score = max(entity_score, len(overlap) / max(len(query_tokens), 1))

        # 3. Recency decay — entries from the last hour score higher
        age_hours = (time.time() - entry.timestamp) / 3600.0
        recency = 1.0 / (1.0 + age_hours * 0.1)  # Slow decay

        # 4. Access frequency bonus
        access_bonus = min(entry.access_count * 0.02, 0.2)

        # Weighted combination
        score = (
            0.45 * text_sim
            + 0.30 * entity_score
            + 0.15 * recency
            + 0.10 * access_bonus
        )

        return min(round(score, 4), 1.0)

    # ── Helpers ────────────────────────────────────────────────────

    def _build_entry_text(
        self,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Build a human-readable text representation for the entry."""
        parts: list[str] = [intent]

        if entities.get("target"):
            parts.append(f"target={entities['target']}")
        if entities.get("query"):
            parts.append(f"query={entities['query']}")
        if entities.get("platform"):
            parts.append(f"platform={entities['platform']}")
        if entities.get("city"):
            parts.append(f"city={entities['city']}")
        if entities.get("symbol"):
            parts.append(f"symbol={entities['symbol']}")
        if context.get("source_text"):
            parts.append(f"raw=\"{context['source_text']}\"")

        return " | ".join(parts)

    def _extract_tags(self, intent: str, entities: dict[str, Any]) -> list[str]:
        """Extract searchable tags from intent and entities."""
        tags: list[str] = [intent.lower()]

        for key in ("target", "platform", "city", "symbol"):
            val = entities.get(key, "")
            if val:
                tags.append(str(val).lower())

        return tags

    def _generate_id(self) -> str:
        """Generate a unique memory entry ID."""
        entry_id = f"mem_{int(time.time())}_{self._next_id}"
        self._next_id += 1
        return entry_id

    # ── Stats ──────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return memory bridge statistics."""
        return {
            "total_entries": len(self._entries),
            "category_counts": dict(self._category_counts),
            "oldest_entry": (
                min(e.timestamp for e in self._entries) if self._entries else 0
            ),
            "newest_entry": (
                max(e.timestamp for e in self._entries) if self._entries else 0
            ),
        }

    def clear(self) -> None:
        """Clear all stored memory entries."""
        self._entries.clear()
        self._category_counts = {cat: 0 for cat in MEMORY_CATEGORIES}
        self._next_id = 1

    # ── Context Persistence (V3) ─────────────────────────────────

    def save_context(self, context: dict[str, Any], session_id: str = "") -> str:
        """Save conversation context for later restoration.

        Returns a context ID that can be used to restore the context.
        """
        context_entry = MemoryEntry(
            id=self._generate_id(),
            category="context",
            intent="CONTEXT_SAVE",
            text="conversation_context",
            entities=context,
            context={"session_id": session_id},
            timestamp=time.time(),
            tags=["context", "session", session_id] if session_id else ["context"],
        )
        return self.store(context_entry.to_dict())

    def load_context(self, session_id: str) -> dict[str, Any] | None:
        """Load previously saved context for a session.

        Returns the most recent context dict, or None if not found.
        """
        candidates = [
            e for e in self._entries
            if e.category == "context"
            and e.intent == "CONTEXT_SAVE"
            and e.context.get("session_id") == session_id
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda e: e.timestamp, reverse=True)
        return candidates[0].entities

    def get_recent_contexts(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get the most recent saved contexts."""
        context_entries = [
            e for e in self._entries
            if e.category == "context" and e.intent == "CONTEXT_SAVE"
        ]
        context_entries.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in context_entries[:limit]]
