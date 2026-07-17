"""Implicit intent detection for JARVIS NLP.

Infers goals from user statements when they never directly ask.
"My laptop is slow" → Performance Diagnosis
"My code isn't working" → Code Analysis
"I need ideas" → Brainstorm

Never waits for explicit commands. Infers goals naturally.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from jarvis.nlp.utils import GoalCategory


# ════════════════════════════════════════════════════════════════════
# IMPLICIT INTENT DEFINITIONS
# ════════════════════════════════════════════════════════════════════

_IMPLICIT_INTENTS: dict[str, dict[str, Any]] = {
    "PERFORMANCE_DIAGNOSIS": {
        "patterns": [
            re.compile(r"\blaptop\s+is\s+slow\b", re.IGNORECASE),
            re.compile(r"\bcomputer\s+is\s+slow\b", re.IGNORECASE),
            re.compile(r"\bpc\s+is\s+slow\b", re.IGNORECASE),
            re.compile(r"\b(system|machine|device)\s+is\s+(slow|lag|hang)", re.IGNORECASE),
            re.compile(r"\btoo\s+slow\b", re.IGNORECASE),
            re.compile(r"\bfreez(e|ing)\b", re.IGNORECASE),
            re.compile(r"\b(lag|laggy|lagging)\b", re.IGNORECASE),
            re.compile(r"\bnot\s+responding\b", re.IGNORECASE),
            re.compile(r"\bhanging\b", re.IGNORECASE),
        ],
        "goal": GoalCategory.SYSTEM,
        "suggested_action": "system_status",
        "response_template": "Let me check your system performance.",
        "confidence": 0.8,
    },
    "VISUAL_ANALYSIS": {
        "patterns": [
            re.compile(r"\bwhat\s+(is|'s|does)\s+(this|it|the\s+screen)\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+(am\s+i|are\s+we)\s+looking\s+at\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+(error|problem|issue)\s+(is\s+)?(shown|displayed|visible|on)\b", re.IGNORECASE),
            re.compile(r"\b(read|explain|describe|analyze)\s+(this|the|screen|window)\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+(do\s+you\s+)?see\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+(is|'s)\s+(on\s+)?(my\s+)?screen\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+(app|application|program)\s+is\s+(active|open|running|showing)\b", re.IGNORECASE),
            re.compile(r"\bwhich\s+(app|application|program)\s+is\s+(active|open|running|focused)\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+is\s+(open|running|showing|displayed|visible)\b", re.IGNORECASE),
            re.compile(r"\bfind\s+(the\s+)?(button|element|link|text|error)\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+does\s+this\s+(say|mean|show)\b", re.IGNORECASE),
            re.compile(r"\bsummarize\s+(this\s+)?(screen|window|page)\b", re.IGNORECASE),
            re.compile(r"\bwh?at'?s\s+on\s+(the\s+)?screen\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+(is|'s)\s+this\s+(error|message|problem)\b", re.IGNORECASE),
            re.compile(r"\bexplain\s+(the\s+)?(error|message|problem)\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+(is\s+)?(happening|going\s+on)\s+(on|here)\b", re.IGNORECASE),
            re.compile(r"\blook\s+(at|into)\s+(this|that|the\s+screen)\b", re.IGNORECASE),
            re.compile(r"\bsee\s+(this|that|what)\b", re.IGNORECASE),
        ],
        "goal": GoalCategory.INFORMATION,
        "suggested_action": "visual_analysis",
        "response_template": "Let me analyze what's on your screen.",
        "confidence": 0.85,
    },

    "SECURITY_SCAN": {
        "patterns": [
            re.compile(r"\bthink\s+i\s+have\s+(malware|virus|trojan)\b", re.IGNORECASE),
            re.compile(r"\bcomputer\s+(might|may|could)\s+be\s+(hack|infected)\b", re.IGNORECASE),
            re.compile(r"\bsecurity\s+(issue|problem|concern|breach)\b", re.IGNORECASE),
            re.compile(r"\bstrange\s+(behavior|activity|pop.?ups?)\b", re.IGNORECASE),
            re.compile(r"\bunusual\s+(activity|behavior)\b", re.IGNORECASE),
        ],
        "goal": GoalCategory.SYSTEM,
        "suggested_action": "security_check",
        "response_template": "I'll help you check for security issues.",
        "confidence": 0.75,
    },
    "FILE_SEARCH": {
        "patterns": [
            re.compile(r"\bcan'?t\s+find\s+(my|the|a)\b", re.IGNORECASE),
            re.compile(r"\bcannot\s+find\s+(my|the|a)\b", re.IGNORECASE),
            re.compile(r"\bforgot\s+where\s+(i|we)\s+(saved|put|stored)\b", re.IGNORECASE),
            re.compile(r"\blost\s+(my|the|a)\b", re.IGNORECASE),
            re.compile(r"\bwhere\s+is\s+(my|the|a)\b", re.IGNORECASE),
            re.compile(r"\blooking\s+for\s+(my|the|a)\b", re.IGNORECASE),
            re.compile(r"\bneed\s+to\s+find\b", re.IGNORECASE),
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "suggested_action": "search_files",
        "response_template": "Let me search for that file.",
        "confidence": 0.7,
    },
    "CODE_ANALYSIS": {
        "patterns": [
            re.compile(r"\bcode\s+(is\s+)?not\s+working\b", re.IGNORECASE),
            re.compile(r"\bcode\s+is\s+broken\b", re.IGNORECASE),
            re.compile(r"\bmy\s+code\s+(is|has)\s+(bug|error|issue|problem)\b", re.IGNORECASE),
            re.compile(r"\b(bug|error|issue)\s+in\s+(my|the)\s+code\b", re.IGNORECASE),
            re.compile(r"\bdebug\s+(this|my|the)\b", re.IGNORECASE),
            re.compile(r"\b(explain|fix)\s+(this\s+)?error\b", re.IGNORECASE),
            re.compile(r"\bwhy\s+(is|does|do)\s+(this|my)\s+code\b", re.IGNORECASE),
        ],
        "goal": GoalCategory.PROGRAMMING,
        "suggested_action": "code_analysis",
        "response_template": "Let me look at your code and help debug it.",
        "confidence": 0.8,
    },
    "BRAINSTORM": {
        "patterns": [
            re.compile(r"\bneed\s+ideas?\b", re.IGNORECASE),
            re.compile(r"\bbrainstorm\b", re.IGNORECASE),
            re.compile(r"\bhelp\s+me\s+(think|decide|come\s+up)\b", re.IGNORECASE),
            re.compile(r"\bwhat\s+should\s+i\s+(do|make|build|create|name)\b", re.IGNORECASE),
            re.compile(r"\bsuggest\s+(something|ideas?|ways?)\b", re.IGNORECASE),
            re.compile(r"\brecommend\s+(something|ideas?|ways?)\b", re.IGNORECASE),
            re.compile(r"\bneed\s+inspiration\b", re.IGNORECASE),
        ],
        "goal": GoalCategory.EDUCATION,
        "suggested_action": "brainstorm",
        "response_template": "Let me brainstorm some ideas for you.",
        "confidence": 0.7,
    },
    "ENTERTAINMENT": {
        "patterns": [
            re.compile(r"\bi'?m\s+bored\b", re.IGNORECASE),
            re.compile(r"\bnothing\s+to\s+do\b", re.IGNORECASE),
            re.compile(r"\bbored\b", re.IGNORECASE),
            re.compile(r"\bentertain\s+me\b", re.IGNORECASE),
            re.compile(r"\bneed\s+entertainment\b", re.IGNORECASE),
            re.compile(r"\bsomething\s+fun\b", re.IGNORECASE),
        ],
        "goal": GoalCategory.ENTERTAINMENT,
        "suggested_action": "suggest_entertainment",
        "response_template": "Let me find something entertaining for you.",
        "confidence": 0.75,
    },
    "STUDY_ASSISTANT": {
        "patterns": [
            re.compile(r"\bhave\s+exam\b", re.IGNORECASE),
            re.compile(r"\bneed\s+to\s+study\b", re.IGNORECASE),
            re.compile(r"\bexam\s+(tomorrow|soon|next\s+week|next\s+month)\b", re.IGNORECASE),
            re.compile(r"\bstudying\s+for\b", re.IGNORECASE),
            re.compile(r"\bhelp\s+me\s+study\b", re.IGNORECASE),
            re.compile(r"\bprepare\s+for\s+(exam|test)\b", re.IGNORECASE),
        ],
        "goal": GoalCategory.EDUCATION,
        "suggested_action": "study_assist",
        "response_template": "Let me help you prepare for your exam.",
        "confidence": 0.7,
    },
    "CREATIVE_HELP": {
        "patterns": [
            re.compile(r"\bneed\s+(to\s+)?(write|create|design|make)\b", re.IGNORECASE),
            re.compile(r"\bhelp\s+me\s+(write|create|design|make)\b", re.IGNORECASE),
            re.compile(r"\bworking\s+on\s+(a\s+)?(project|essay|paper|article|blog)\b", re.IGNORECASE),
            re.compile(r"\bneed\s+help\s+with\s+(writing|design|creative)\b", re.IGNORECASE),
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "suggested_action": "creative_assist",
        "response_template": "I'd be happy to help with your creative work.",
        "confidence": 0.65,
    },
}


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

@dataclass
class ImplicitIntentResult:
    """Result of implicit intent detection."""
    detected: bool
    intent: str
    goal: GoalCategory
    confidence: float
    suggested_action: str
    response_template: str
    signals: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected": self.detected,
            "intent": self.intent,
            "goal": self.goal.value if hasattr(self.goal, 'value') else str(self.goal),
            "confidence": round(self.confidence, 3),
            "suggested_action": self.suggested_action,
            "response_template": self.response_template,
            "signals": self.signals,
        }


class ImplicitIntentDetector:
    """Detects implicit goals from user statements.

    When a user says something like "I'm bored" or "my code isn't
    working", this module infers the underlying intent and suggests
    appropriate actions.
    """

    def detect(
        self,
        text: str,
        explicit_intent: str = "",
        context: dict[str, Any] | None = None,
    ) -> ImplicitIntentResult:
        """Detect implicit intent in *text*.

        Parameters
        ----------
        text:
            Raw user input.
        explicit_intent:
            Intent already detected by the main intent engine. If
            non-empty, implicit detection may skip to avoid conflicts.
        context:
            Optional conversation context.

        Returns
        -------
        ImplicitIntentResult with detected intent and suggested action.
        """
        # If explicit intent is already high-confidence, skip implicit detection
        if explicit_intent and explicit_intent not in ("GREETING", "CHITCHAT", ""):
            return self._no_result()

        text_lower = text.lower().strip()

        # Check each implicit intent
        for intent_name, config in _IMPLICIT_INTENTS.items():
            for pattern in config["patterns"]:
                if pattern.search(text):
                    return ImplicitIntentResult(
                        detected=True,
                        intent=intent_name,
                        goal=config["goal"],
                        confidence=config["confidence"],
                        suggested_action=config["suggested_action"],
                        response_template=config["response_template"],
                        signals=[f"pattern match: {intent_name}"],
                    )

        return self._no_result()

    def should_override_explicit(
        self,
        implicit: ImplicitIntentResult,
        explicit_confidence: float,
    ) -> bool:
        """Determine if implicit intent should override explicit.

        Returns True when:
        - Implicit intent is detected with high confidence
        - Explicit confidence is low
        - The implicit intent is more specific than the explicit one
        """
        if not implicit.detected:
            return False
        if explicit_confidence >= 0.7:
            return False
        if implicit.confidence >= 0.75:
            return True
        return False

    @staticmethod
    def _no_result() -> ImplicitIntentResult:
        return ImplicitIntentResult(
            detected=False,
            intent="",
            goal=GoalCategory.UNKNOWN,
            confidence=0.0,
            suggested_action="",
            response_template="",
            signals=[],
        )
