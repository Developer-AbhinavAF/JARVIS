"""Conversation analyzer for JARVIS NLP.

Recognizes non-command statements like "I'm hungry", "I'm tired",
"I have to finish my project" and maps them to appropriate assistant
behaviors (suggest, assist, acknowledge, etc.).

Distinguishes between:
- Direct commands ("open chrome")
- Questions ("what time is it")
- State statements ("I'm tired")
- Implicit requests ("my laptop is slow")
- General conversation ("hello")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


# ════════════════════════════════════════════════════════════════════
# CONVERSATION TYPES
# ════════════════════════════════════════════════════════════════════

class ConversationType:
    COMMAND = "command"           # Direct actionable command
    QUESTION = "question"         # Information-seeking question
    STATEMENT = "statement"       # User sharing their state
    IMPLICIT_REQUEST = "implicit" # Goal implied, not stated
    GREETING = "greeting"         # Social interaction
    CORRECTION = "correction"     # User correcting previous action
    CONFIRMATION = "confirmation" # Yes/no response
    CHITCHAT = "chitchat"        # Casual conversation


@dataclass
class ConversationAnalysis:
    """Result of conversation analysis."""
    conversation_type: str
    is_actionable: bool
    suggested_behavior: str  # execute, suggest, acknowledge, respond, clarify
    confidence: float
    state_signals: list[str]
    suggested_intents: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_type": self.conversation_type,
            "is_actionable": self.is_actionable,
            "suggested_behavior": self.suggested_behavior,
            "confidence": round(self.confidence, 3),
            "state_signals": self.state_signals,
            "suggested_intents": self.suggested_intents,
        }


# ════════════════════════════════════════════════════════════════════
# STATE PATTERNS
# ════════════════════════════════════════════════════════════════════

_STATE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "hungry": [
        re.compile(r"\bi'?m\s+hungry\b", re.IGNORECASE),
        re.compile(r"\bi\s+(want|need)\s+(to\s+)?eat\b", re.IGNORECASE),
        re.compile(r"\bfeeling\s+hungry\b", re.IGNORECASE),
        re.compile(r"\bfood\b.*\b(hungry|want|need)\b", re.IGNORECASE),
    ],
    "tired": [
        re.compile(r"\bi'?m\s+tired\b", re.IGNORECASE),
        re.compile(r"\bso\s+tired\b", re.IGNORECASE),
        re.compile(r"\bexhausted\b", re.IGNORECASE),
        re.compile(r"\bneed\s+(to\s+)?sleep\b", re.IGNORECASE),
        re.compile(r"\bneed\s+(to\s+)?rest\b", re.IGNORECASE),
        re.compile(r"\bno\s+energy\b", re.IGNORECASE),
    ],
    "bored": [
        re.compile(r"\bi'?m\s+bored\b", re.IGNORECASE),
        re.compile(r"\bnothing\s+to\s+do\b", re.IGNORECASE),
        re.compile(r"\bbored\b", re.IGNORECASE),
    ],
    "stressed": [
        re.compile(r"\bstress(ed)?\b", re.IGNORECASE),
        re.compile(r"\boverwhelmed\b", re.IGNORECASE),
        re.compile(r"\btoo\s+much\b", re.IGNORECASE),
        re.compile(r"\bdeadline\b", re.IGNORECASE),
    ],
    "frustrated": [
        re.compile(r"\bfrustrat(ed|ing|ion)\b", re.IGNORECASE),
        re.compile(r"\bannoy(ed|ing|ance)\b", re.IGNORECASE),
        re.compile(r"\birritat(ed|ing)\b", re.IGNORECASE),
    ],
    "sad": [
        re.compile(r"\bi'?m\s+sad\b", re.IGNORECASE),
        re.compile(r"\bfeeling\s+sad\b", re.IGNORECASE),
        re.compile(r"\bunhappy\b", re.IGNORECASE),
        re.compile(r"\bdepressed\b", re.IGNORECASE),
        re.compile(r"\bdown\b", re.IGNORECASE),
    ],
    "happy": [
        re.compile(r"\bi'?m\s+(happy|glad|great|excellent)\b", re.IGNORECASE),
        re.compile(r"\bfeeling\s+(happy|good|great)\b", re.IGNORECASE),
        re.compile(r"\bso\s+happy\b", re.IGNORECASE),
    ],
    "programming": [
        re.compile(r"\bcode\b", re.IGNORECASE),
        re.compile(r"\bcoding\b", re.IGNORECASE),
        re.compile(r"\bprogram(ming)?\b", re.IGNORECASE),
        re.compile(r"\bdevelop(er|ment)?\b", re.IGNORECASE),
        re.compile(r"\bfinish\s+(my\s+)?project\b", re.IGNORECASE),
        re.compile(r"\b(debug|compile|build|deploy)\b", re.IGNORECASE),
    ],
    "file_search": [
        re.compile(r"\b(can'?t|cannot|can not)\s+find\b", re.IGNORECASE),
        re.compile(r"\bwhere\s+(did\s+)?(i|we)\s+(save|put|store)\b", re.IGNORECASE),
        re.compile(r"\bforgot\s+where\b", re.IGNORECASE),
        re.compile(r"\blost\s+(my|the|a)\b", re.IGNORECASE),
        re.compile(r"\blooking\s+for\b", re.IGNORECASE),
    ],
    "performance": [
        re.compile(r"\blaptop\s+is\s+slow\b", re.IGNORECASE),
        re.compile(r"\bcomputer\s+is\s+slow\b", re.IGNORECASE),
        re.compile(r"\b(pcs?|system)\s+(is\s+)?lag(gy)?\b", re.IGNORECASE),
        re.compile(r"\btoo\s+slow\b", re.IGNORECASE),
        re.compile(r"\bfreez(e|ing)\b", re.IGNORECASE),
    ],
    "security": [
        re.compile(r"\bmalware\b", re.IGNORECASE),
        re.compile(r"\bvirus\b", re.IGNORECASE),
        re.compile(r"\bhack(ed|er|ing)?\b", re.IGNORECASE),
        re.compile(r"\bsecurity\s+(issue|problem|breach)\b", re.IGNORECASE),
    ],
    "learning": [
        re.compile(r"\bi\s+(want|need)\s+to\s+learn\b", re.IGNORECASE),
        re.compile(r"\bteach\s+me\b", re.IGNORECASE),
        re.compile(r"\bhow\s+(do|does|can|to)\b", re.IGNORECASE),
        re.compile(r"\b(learn|study|understand)\b", re.IGNORECASE),
    ],
    "ideas": [
        re.compile(r"\bneed\s+ideas?\b", re.IGNORECASE),
        re.compile(r"\bbrainstorm\b", re.IGNORECASE),
        re.compile(r"\bwhat\s+should\s+i\b", re.IGNORECASE),
        re.compile(r"\bsuggest\b", re.IGNORECASE),
        re.compile(r"\brecommend\b", re.IGNORECASE),
    ],
}

# Correction patterns
_CORRECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bactually,?\s*(i meant|i want|use)\b", re.IGNORECASE),
    re.compile(r"\bno,?\s*(i meant|not that|use)\b", re.IGNORECASE),
    re.compile(r"\bwait,?\s*(i meant|not|use)\b", re.IGNORECASE),
    re.compile(r"\bnot\s+\w+,?\s*(i meant|use|try)\b", re.IGNORECASE),
    re.compile(r"\bchange\s+(it|that|this)\s+to\b", re.IGNORECASE),
    re.compile(r"\bmake it\b", re.IGNORECASE),
]

# Confirmation patterns
_CONFIRMATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(yes|yeah|yep|yup|sure|ok|okay|confirm|proceed|do it|go ahead)\s*[.!]*$", re.IGNORECASE),
    re.compile(r"^(no|nope|nah|cancel|nevermind|stop|abort)\s*[.!]*$", re.IGNORECASE),
]

# Question patterns
_QUESTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(what|who|where|when|why|how|which|whose)\b", re.IGNORECASE),
    re.compile(r"\?\s*$"),
    re.compile(r"\b(can|could|would|should|do|does|did|is|are|was|were)\s+\w+", re.IGNORECASE),
]

# Implicit request patterns (statements that imply a request)
_IMPLICIT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "PERFORMANCE_DIAGNOSIS": [
        re.compile(r"\blaptop\s+is\s+slow\b", re.IGNORECASE),
        re.compile(r"\bcomputer\s+is\s+slow\b", re.IGNORECASE),
        re.compile(r"\btoo\s+slow\b", re.IGNORECASE),
    ],
    "SECURITY_SCAN": [
        re.compile(r"\bthink\s+i\s+have\s+(malware|virus)\b", re.IGNORECASE),
        re.compile(r"\bmight\s+be\s+hack(ed)?\b", re.IGNORECASE),
    ],
    "FILE_SEARCH": [
        re.compile(r"\bcan'?t\s+find\s+(my|the)\b", re.IGNORECASE),
        re.compile(r"\bforgot\s+where\b", re.IGNORECASE),
        re.compile(r"\blost\s+(my|the)\b", re.IGNORECASE),
    ],
    "CODE_ANALYSIS": [
        re.compile(r"\bcode\s+(is\s+)?not\s+working\b", re.IGNORECASE),
        re.compile(r"\bcode\s+is\s+broken\b", re.IGNORECASE),
        re.compile(r"\bbug\s+in\b", re.IGNORECASE),
    ],
    "BRAINSTORM": [
        re.compile(r"\bneed\s+ideas?\b", re.IGNORECASE),
        re.compile(r"\bhelp\s+me\s+(think|decide)\b", re.IGNORECASE),
    ],
    "ENTERTAINMENT": [
        re.compile(r"\b(bored|boring)\b", re.IGNORECASE),
        re.compile(r"\bnothing\s+to\s+do\b", re.IGNORECASE),
    ],
    "STUDY_ASSISTANT": [
        re.compile(r"\bhave\s+exam\b", re.IGNORECASE),
        re.compile(r"\bneed\s+to\s+study\b", re.IGNORECASE),
        re.compile(r"\bexam\s+(tomorrow|soon|next)\b", re.IGNORECASE),
    ],
}


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

class ConversationAnalyzer:
    """Analyzes conversation type and suggests assistant behavior.

    Distinguishes commands from questions, state statements, implicit
    requests, corrections, and casual conversation. Provides behavior
    guidance for the response generator.
    """

    def analyze(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> ConversationAnalysis:
        """Analyze the conversation type of *text*.

        Parameters
        ----------
        text:
            Raw user input.
        context:
            Optional conversation context for disambiguation.

        Returns
        -------
        ConversationAnalysis with type, behavior suggestion, and signals.
        """
        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        # Check correction patterns first
        if any(p.search(text_stripped) for p in _CORRECTION_PATTERNS):
            return ConversationAnalysis(
                conversation_type=ConversationType.CORRECTION,
                is_actionable=True,
                suggested_behavior="correct",
                confidence=0.85,
                state_signals=["correction pattern detected"],
                suggested_intents=["CORRECTION"],
            )

        # Check confirmation patterns
        if any(p.search(text_stripped) for p in _CONFIRMATION_PATTERNS):
            is_yes = bool(re.match(
                r"^(yes|yeah|yep|yup|sure|ok|okay|confirm|proceed|do it|go ahead)",
                text_lower,
            ))
            return ConversationAnalysis(
                conversation_type=ConversationType.CONFIRMATION,
                is_actionable=True,
                suggested_behavior="confirm" if is_yes else "cancel",
                confidence=0.9,
                state_signals=["confirmation pattern detected"],
                suggested_intents=[],
            )

        # Check for implicit requests (before questions/commands)
        implicit = self._detect_implicit_request(text_stripped)
        if implicit:
            return ConversationAnalysis(
                conversation_type=ConversationType.IMPLICIT_REQUEST,
                is_actionable=True,
                suggested_behavior="suggest",
                confidence=0.7,
                state_signals=[f"implicit request: {implicit}"],
                suggested_intents=[implicit],
            )

        # Check for state statements
        state = self._detect_state(text_stripped)
        if state:
            return ConversationAnalysis(
                conversation_type=ConversationType.STATEMENT,
                is_actionable=False,
                suggested_behavior="acknowledge",
                confidence=0.75,
                state_signals=[f"state detected: {state}"],
                suggested_intents=[],
            )

        # Check for questions
        is_question = any(p.search(text_stripped) for p in _QUESTION_PATTERNS)
        if is_question:
            return ConversationAnalysis(
                conversation_type=ConversationType.QUESTION,
                is_actionable=True,
                suggested_behavior="respond",
                confidence=0.8,
                state_signals=["question pattern detected"],
                suggested_intents=["SEARCH_WEB", "CALCULATOR", "DATETIME"],
            )

        # Check for greetings
        greeting_words = {
            "hello", "hi", "hey", "howdy", "good morning", "good evening",
            "good afternoon", "good night", "greetings", "sup", "yo",
        }
        if text_lower in greeting_words or any(
            text_lower.startswith(g) for g in greeting_words
        ):
            return ConversationAnalysis(
                conversation_type=ConversationType.GREETING,
                is_actionable=False,
                suggested_behavior="respond",
                confidence=0.9,
                state_signals=["greeting detected"],
                suggested_intents=["GREETING"],
            )

        # Check context for chitchat vs command
        if context and context.get("last_intent") in ("GREETING", "CHITCHAT"):
            # After a greeting, follow-up might be chitchat
            word_count = len(text_lower.split())
            if word_count <= 5:
                return ConversationAnalysis(
                    conversation_type=ConversationType.CHITCHAT,
                    is_actionable=False,
                    suggested_behavior="respond",
                    confidence=0.5,
                    state_signals=["short follow-up after greeting"],
                    suggested_intents=[],
                )

        # Default: treat as command (will be classified by intent engine)
        return ConversationAnalysis(
            conversation_type=ConversationType.COMMAND,
            is_actionable=True,
            suggested_behavior="execute",
            confidence=0.6,
            state_signals=["default command classification"],
            suggested_intents=[],
        )

    def _detect_state(self, text: str) -> str | None:
        """Detect if the text is a state statement."""
        for state_name, patterns in _STATE_PATTERNS.items():
            if any(p.search(text) for p in patterns):
                return state_name
        return None

    def _detect_implicit_request(self, text: str) -> str | None:
        """Detect implicit requests from statements."""
        for intent, patterns in _IMPLICIT_PATTERNS.items():
            if any(p.search(text) for p in patterns):
                return intent
        return None

    def get_suggested_response(self, analysis: ConversationAnalysis) -> str:
        """Get a suggested response template based on the analysis."""
        templates = {
            "execute": "",  # No template — execute the command
            "suggest": "Here are some things I can help with:",
            "acknowledge": "",  # Acknowledge silently, no template
            "respond": "",  # Generate natural response
            "clarify": "Could you clarify what you mean?",
            "correct": "Let me fix that for you.",
            "confirm": "Got it.",
            "cancel": "Cancelled.",
        }
        return templates.get(analysis.suggested_behavior, "")
