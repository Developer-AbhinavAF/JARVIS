"""Reasoning Engine for JARVIS NLP.

Before execution, ask internally:
- What does the user actually want?
- Is there a better way?
- Do I already know this?
- Should I search? Should I ask? Should I execute? Should I plan? Should I remember?

Reason internally before action.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# REASONING TYPES
# ════════════════════════════════════════════════════════════════════

class ReasoningType:
    DIRECT_EXECUTE = "direct_execute"      # Simple, clear command
    CLARIFY = "clarify"                    # Need more info
    SEARCH = "search"                      # Need to look up
    PLAN = "plan"                          # Multi-step, need planning
    REMEMBER = "remember"                  # Should store this
    ASK = "ask"                            # Need user input
    FALLBACK_LLM = "fallback_llm"          # Use LLM knowledge
    SUGGEST = "suggest"                    # Offer options
    CORRECT = "correct"                    # User is correcting
    CHITCHAT = "chitchat"                  # Social conversation


# ════════════════════════════════════════════════════════════════════
# REASONING RESULT
# ════════════════════════════════════════════════════════════════════

@dataclass
class ReasoningResult:
    """Result of internal reasoning."""
    reasoning_type: str = ReasoningType.DIRECT_EXECUTE
    confidence: float = 0.8
    reasoning: str = ""
    suggested_action: str = ""
    should_search: bool = False
    should_ask: bool = False
    should_remember: bool = False
    should_plan: bool = False
    alternative_intents: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reasoning_type": self.reasoning_type,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "suggested_action": self.suggested_action,
            "should_search": self.should_search,
            "should_ask": self.should_ask,
            "should_remember": self.should_remember,
            "should_plan": self.should_plan,
        }


# ════════════════════════════════════════════════════════════════════
# QUESTION ROUTING
# ════════════════════════════════════════════════════════════════════

QUESTION_CATEGORIES: dict[str, dict[str, Any]] = {
    "general": {
        "keywords": ["what is", "how does", "explain", "tell me about"],
        "strategy": "llm_first",
        "search_if": "recent events, specific data",
    },
    "programming": {
        "keywords": ["code", "function", "error", "bug", "debug", "compile", "python", "javascript"],
        "strategy": "search_first",
        "search_if": "always for specific errors, llm for concepts",
    },
    "math": {
        "keywords": ["calculate", "solve", "equation", "formula", "compute"],
        "strategy": "llm_first",
        "search_if": "complex proofs",
    },
    "science": {
        "keywords": ["physics", "chemistry", "biology", "research", "study"],
        "strategy": "search_first",
        "search_if": "recent discoveries, specific data",
    },
    "history": {
        "keywords": ["when did", "who was", "history", "ancient", "war"],
        "strategy": "llm_first",
        "search_if": "obscure events",
    },
    "current_affairs": {
        "keywords": ["today", "latest", "recent", "news", "happening", "2024", "2025", "2026"],
        "strategy": "search_always",
        "search_if": "always",
    },
    "technical_support": {
        "keywords": ["error", "fix", "problem", "issue", "not working", "broken"],
        "strategy": "search_first",
        "search_if": "always for specific errors",
    },
    "research": {
        "keywords": ["paper", "study", "research", "arxiv", "scholar"],
        "strategy": "search_always",
        "search_if": "always",
    },
}


# ════════════════════════════════════════════════════════════════════
# INTERNET DECISION
# ════════════════════════════════════════════════════════════════════

class InternetDecision:
    """Decides whether to use LLM knowledge or internet search.

    Never search unnecessarily. Use LLM for general knowledge,
    internet for current/recent/specific data.
    """

    def should_search(self, intent: str, entities: dict[str, Any], context: dict[str, Any]) -> bool:
        """Determine if internet search is needed.

        Returns True if search is preferred, False for LLM knowledge.
        """
        intent_lower = intent.lower()

        # Always search for these intents
        always_search = {
            "GET_NEWS", "GET_WEATHER", "SEARCH_WEB", "STOCK_QUOTE",
            "GET_STOCK_PRICE", "GET_CRYPTO_PRICE",
        }
        if intent in always_search:
            return True

        # Check question category
        text = context.get("raw_text", "").lower()
        for category, config in QUESTION_CATEGORIES.items():
            if any(kw in text for kw in config["keywords"]):
                strategy = config["strategy"]
                if strategy == "search_always":
                    return True
                if strategy == "search_first":
                    return True
                # LLM first, but search if specific conditions met
                if strategy == "llm_first":
                    return self._should_search_for_llm_category(text, config)

        # Check for temporal keywords (indicates need for current info)
        temporal_keywords = [
            "today", "latest", "recent", "now", "current",
            "this week", "this month", "this year", "2024", "2025", "2026",
        ]
        if any(kw in text for kw in temporal_keywords):
            return True

        # Check for specific data requests
        specific_keywords = ["price", "stock", "forecast", "statistics", "data"]
        if any(kw in text for kw in specific_keywords):
            return True

        return False

    def _should_search_for_llm_category(self, text: str, config: dict[str, Any]) -> bool:
        """Check if search is needed for an LLM-first category."""
        # Search if the query is about recent events
        recent_keywords = ["latest", "recent", "new", "update", "change"]
        if any(kw in text for kw in recent_keywords):
            return True

        # Search if the query asks for specific data
        specific_keywords = ["how many", "how much", "percentage", "statistics"]
        if any(kw in text for kw in specific_keywords):
            return True

        return False

    def choose_platform(
        self,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Choose the best platform for search.

        Returns platform name (google, github, arxiv, etc.)
        """
        text = context.get("raw_text", "").lower()

        # Programming → GitHub, Docs, Stack Overflow
        programming_keywords = ["code", "function", "error", "library", "api", "programming"]
        if any(kw in text for kw in programming_keywords):
            return "github"

        # Academic → Arxiv, Google Scholar
        academic_keywords = ["paper", "research", "study", "arxiv", "scholar", "academic"]
        if any(kw in text for kw in academic_keywords):
            return "arxiv"

        # News → News APIs
        if intent in ("GET_NEWS",):
            return "news_api"

        # General → Google
        return "google"


# ════════════════════════════════════════════════════════════════════
# REASONING ENGINE
# ════════════════════════════════════════════════════════════════════

class ReasoningEngine:
    """Internal reasoning engine that decides how to handle user requests.

    Before execution, reasons about:
    - What does the user actually want?
    - Is there a better way?
    - Do I already know this?
    - Should I search? Ask? Execute? Plan? Remember?
    """

    def __init__(self) -> None:
        self.internet = InternetDecision()

    def reason(
        self,
        text: str,
        intent: str,
        entities: dict[str, Any],
        confidence: float,
        context: dict[str, Any],
    ) -> ReasoningResult:
        """Perform internal reasoning before action.

        This is the "thinking" step before execution.
        """
        result = ReasoningResult()

        # 1. What does the user actually want?
        actual_desire = self._infer_actual_desire(text, intent, entities, context)
        result.metadata["actual_desire"] = actual_desire

        # 2. Is this a clarification/correction?
        if self._is_correction(text, context):
            result.reasoning_type = ReasoningType.CORRECT
            result.reasoning = "User is correcting a previous action"
            result.confidence = 0.9
            return result

        # 3. Is this chitchat?
        if self._is_chitchat(text, intent):
            result.reasoning_type = ReasoningType.CHITCHAT
            result.reasoning = "Social conversation, no tool needed"
            result.confidence = 0.8
            return result

        # 4. Should I ask for clarification?
        if confidence < 0.4 and not self._has_sufficient_entities(entities, intent):
            result.reasoning_type = ReasoningType.CLARIFY
            result.should_ask = True
            result.reasoning = "Low confidence and insufficient entities"
            result.confidence = 0.7
            return result

        # 5. Should I search the internet?
        if self.internet.should_search(intent, entities, context):
            result.should_search = True
            platform = self.internet.choose_platform(intent, entities, context)
            result.suggested_action = f"search_{platform}"
            result.reasoning = f"Internet search needed, platform: {platform}"

        # 6. Should I plan (multi-step)?
        if self._needs_planning(text, intent, entities):
            result.should_plan = True
            result.reasoning = "Multi-step task detected"

        # 7. Should I remember this?
        if self._should_remember(text, intent, entities):
            result.should_remember = True
            result.reasoning = "This interaction should be stored"

        # 8. Default: direct execution
        if not result.should_search and not result.should_plan:
            result.reasoning_type = ReasoningType.DIRECT_EXECUTE
            result.reasoning = "Clear command, direct execution"

        result.confidence = confidence
        return result

    # ── Internal analysis ──────────────────────────────────────────

    def _infer_actual_desire(
        self,
        text: str,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Infer what the user actually wants (beyond literal meaning)."""
        text_lower = text.lower()

        # "I need to watch something" → wants entertainment
        if any(phrase in text_lower for phrase in ["need to watch", "want to watch", "watch something"]):
            return "entertainment"

        # "I feel like coding" → wants to code
        if any(phrase in text_lower for phrase in ["feel like coding", "want to code", "need coding"]):
            return "programming"

        # "My PC feels slow" → wants system diagnosis
        if any(phrase in text_lower for phrase in ["feels slow", "is slow", "running slow"]):
            return "system_diagnosis"

        # "I forgot where I kept that PDF" → wants file search
        if any(phrase in text_lower for phrase in ["forgot where", "can't find", "lost"]):
            return "file_search"

        return intent

    def _is_correction(self, text: str, context: dict[str, Any]) -> bool:
        """Check if the user is correcting a previous action."""
        correction_phrases = [
            "actually", "i meant", "no, not", "wait, use",
            "change to", "make it", "instead of", "rather",
        ]
        return any(phrase in text.lower() for phrase in correction_phrases)

    def _is_chitchat(self, text: str, intent: str) -> bool:
        """Check if the input is social conversation."""
        chitchat_intents = {"GREETING", "CHAT", "FAREWELL", "THANKS", "HOW_ARE_YOU"}
        if intent in chitchat_intents:
            return True

        chitchat_phrases = [
            "how are you", "what's up", "hello", "hi",
            "good morning", "good night", "thanks", "bye",
        ]
        return any(phrase in text.lower() for phrase in chitchat_phrases)

    def _has_sufficient_entities(self, entities: dict[str, Any], intent: str) -> bool:
        """Check if we have enough entities to execute the intent."""
        required_entities = {
            "OPEN_APP": ["app"],
            "OPEN_WEBSITE": ["url", "website"],
            "SEARCH_WEB": ["query"],
            "PLAY_MUSIC": ["query", "song"],
            "SET_REMINDER": ["reminder", "time"],
            "SEND_EMAIL": ["email", "recipient"],
        }
        required = required_entities.get(intent, [])
        return any(entities.get(r) for r in required)

    def _needs_planning(self, text: str, intent: str, entities: dict[str, Any]) -> bool:
        """Check if the task needs multi-step planning."""
        planning_keywords = [
            "and then", "after that", "first", "then",
            "step by step", "workflow", "automate",
        ]
        return any(kw in text.lower() for kw in planning_keywords)

    def _should_remember(self, text: str, intent: str, entities: dict[str, Any]) -> bool:
        """Check if this interaction should be stored in memory."""
        remember_intents = {"SAVE_MEMORY", "RECALL_MEMORY", "ADD_NOTE", "ADD_TODO"}
        if intent in remember_intents:
            return True

        remember_phrases = [
            "remember", "don't forget", "note that", "save this",
            "my preference", "i always", "i usually",
        ]
        return any(phrase in text.lower() for phrase in remember_phrases)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

reasoning_engine = ReasoningEngine()
