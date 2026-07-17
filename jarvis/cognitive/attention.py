"""Attention System for JARVIS Cognitive Architecture.

Humans don't think about everything. Neither should JARVIS.

Focus only on:
- Current Goal
- Relevant Memory
- Relevant Context
- Relevant Applications
- Relevant Documents
- Relevant Conversation

Ignore unrelated information.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from jarvis.cognitive.perception import Situation

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# FOCUS MODEL
# ════════════════════════════════════════════════════════════════════

@dataclass
class Focus:
    """Filtered, relevant information for the current request."""
    # Core focus
    primary_goal: str = ""
    primary_intent: str = ""
    urgency: str = "normal"      # low, normal, high, urgent

    # Relevant context (filtered)
    relevant_history: list[dict[str, Any]] = field(default_factory=list)
    relevant_entities: dict[str, Any] = field(default_factory=dict)
    relevant_preferences: dict[str, str] = field(default_factory=dict)

    # Relevant state
    relevant_app: str = ""
    relevant_project: str = ""
    relevant_file: str = ""

    # Attention signals
    is_followup: bool = False
    is_correction: bool = False
    is_emotional: bool = False
    needs_immediate_attention: bool = False

    # Confidence
    attention_confidence: float = 0.8

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_goal": self.primary_goal,
            "primary_intent": self.primary_intent,
            "urgency": self.urgency,
            "is_followup": self.is_followup,
            "is_correction": self.is_correction,
            "is_emotional": self.is_emotional,
            "needs_immediate": self.needs_immediate_attention,
            "confidence": round(self.attention_confidence, 3),
        }


# ════════════════════════════════════════════════════════════════════
# ATTENTION SYSTEM
# ════════════════════════════════════════════════════════════════════

class AttentionSystem:
    """Filters the situation to focus on what matters.

    Takes a Situation and determines what's relevant to the current request.
    Ignores noise and unrelated context.
    """

    def __init__(self) -> None:
        self._attention_history: list[Focus] = []

    def focus(
        self,
        situation: Situation,
        intent: str = "",
        entities: dict[str, Any] | None = None,
    ) -> Focus:
        """Determine what to focus on for this request.

        Args:
            situation: The observed situation.
            intent: Detected intent (if any).
            entities: Extracted entities (if any).

        Returns:
            Focus object with filtered, relevant information.
        """
        entities = entities or {}

        focus = Focus(
            primary_intent=intent,
        )

        # Step 1: Determine primary goal from situation
        focus.primary_goal = self._determine_goal(situation, intent)

        # Step 2: Filter conversation history for relevance
        focus.relevant_history = self._filter_history(situation, intent)

        # Step 3: Filter entities for relevance
        focus.relevant_entities = self._filter_entities(entities, intent)

        # Step 4: Filter preferences for relevance
        focus.relevant_preferences = self._filter_preferences(
            situation.relevant_preferences, intent,
        )

        # Step 5: Determine context relevance
        focus.relevant_app = situation.current_app
        focus.relevant_project = situation.current_project
        focus.relevant_file = situation.current_file

        # Step 6: Detect attention signals
        focus.is_followup = situation.conversation_turn > 0
        focus.is_correction = self._is_correction(situation)
        focus.is_emotional = situation.user_emotion not in ("neutral", "calm")
        focus.needs_immediate_attention = self._needs_immediate(situation, intent)

        # Step 7: Determine urgency
        focus.urgency = self._determine_urgency(situation, intent)

        # Step 8: Calculate attention confidence
        focus.attention_confidence = self._calculate_confidence(focus, situation)

        self._attention_history.append(focus)
        if len(self._attention_history) > 50:
            self._attention_history = self._attention_history[-25:]

        return focus

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_focuses": len(self._attention_history),
        }

    # ── Private Methods ──

    @staticmethod
    def _determine_goal(situation: Situation, intent: str) -> str:
        """Determine the primary goal from situation and intent."""
        if intent:
            return intent
        if situation.user_activity == "coding":
            return "PROGRAMMING"
        if situation.user_activity == "browsing":
            return "INFORMATION"
        if situation.user_activity == "media":
            return "ENTERTAINMENT"
        if situation.user_emotion in ("frustrated", "angry"):
            return "ASSISTANCE"
        if situation.user_emotion in ("sad", "tired"):
            return "SUPPORT"
        return "GENERAL"

    @staticmethod
    def _filter_history(situation: Situation, intent: str) -> list[dict[str, Any]]:
        """Filter conversation history for relevance to current intent."""
        relevant = []
        for prev_intent in situation.previous_intents[-3:]:
            if prev_intent:
                relevant.append({"intent": prev_intent, "relevance": "recent"})
        return relevant

    @staticmethod
    def _filter_entities(entities: dict[str, Any], intent: str) -> dict[str, Any]:
        """Filter entities to only include those relevant to the intent."""
        # For now, return all entities (filtering can be enhanced later)
        return entities

    @staticmethod
    def _filter_preferences(
        preferences: dict[str, str], intent: str,
    ) -> dict[str, str]:
        """Filter user preferences relevant to the current intent."""
        if not preferences:
            return {}
        # Return preferences that match the intent domain
        relevant = {}
        intent_lower = intent.lower() if intent else ""
        for key, value in preferences.items():
            if not key or not value:
                continue
            # Simple relevance check: if any word from key is in intent
            key_words = set(key.lower().split("_"))
            intent_words = set(intent_lower.split("_"))
            if key_words & intent_words:
                relevant[key] = value
        return relevant

    @staticmethod
    def _is_correction(situation: Situation) -> bool:
        """Check if the current input is a correction."""
        text = situation.user_input.lower()
        correction_signals = [
            "actually", "i meant", "no, not", "wait, use",
            "change to", "make it", "instead of", "rather",
            "correct", "wrong", "fix",
        ]
        return any(s in text for s in correction_signals)

    @staticmethod
    def _needs_immediate(situation: Situation, intent: str) -> bool:
        """Check if the request needs immediate attention."""
        # Emotional distress
        if situation.user_emotion in ("angry", "frustrated", "sad"):
            return True
        # Urgent intents
        urgent_intents = {"SYSTEM_POWER", "SHUTDOWN", "RESTART", "EMERGENCY"}
        if intent in urgent_intents:
            return True
        # Correction needs immediate attention
        text = situation.user_input.lower()
        if any(s in text for s in ["urgent", "asap", "immediately", "now"]):
            return True
        return False

    @staticmethod
    def _determine_urgency(situation: Situation, intent: str) -> str:
        """Determine urgency level."""
        if situation.user_emotion in ("angry", "frustrated"):
            return "high"
        if situation.user_emotion in ("sad", "tired"):
            return "normal"
        urgent_intents = {"SYSTEM_POWER", "SHUTDOWN", "RESTART"}
        if intent in urgent_intents:
            return "high"
        if situation.user_emotion in ("excited", "happy"):
            return "low"
        return "normal"

    @staticmethod
    def _calculate_confidence(focus: Focus, situation: Situation) -> float:
        """Calculate confidence in the attention focus."""
        confidence = 0.7

        # Higher confidence if we have clear intent
        if focus.primary_intent:
            confidence += 0.15

        # Higher confidence if we have relevant context
        if situation.current_app or situation.current_project:
            confidence += 0.1

        # Higher confidence if followup (context is clearer)
        if focus.is_followup:
            confidence += 0.05

        return min(confidence, 1.0)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

attention_system = AttentionSystem()
