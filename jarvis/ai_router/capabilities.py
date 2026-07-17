"""Capabilities — Detects what a request needs.

Capability Detection → Model Selection.
"""

from __future__ import annotations

import re
from typing import Any
from dataclasses import dataclass

from .models import Capability


VISION_KEYWORDS = {
    "screenshot", "see", "look at", "describe",
    "vision", "ocr", "read", "visual", "diagram", "chart", "graph",
    "painting", "illustration", "poster", "logo",
}

SPEECH_KEYWORDS = {
    "say", "speak", "voice", "speech", "talk", "read aloud",
    "pronounce", "tts", "stt", "transcribe", "audio", "listen",
}

SEARCH_KEYWORDS = {
    "search", "find", "lookup", "google", "web", "online",
    "latest", "current", "news", "recent", "what is", "who is",
    "where is", "how to", "when did",
}

CODING_KEYWORDS = {
    "code", "program", "function", "class", "method", "variable",
    "debug", "fix", "error", "compile", "run", "execute", "script",
    "import", "api", "endpoint", "algorithm", "database", "sql",
    "git", "commit", "deploy", "test", "refactor", "lint",
}

IMAGE_GEN_KEYWORDS = {
    "generate", "create image", "draw", "paint", "illustrate",
    "design", "make a picture", "render", "visualize", "make an image",
    "create a picture", "generate an image", "picture of",
}

EMBEDDING_KEYWORDS = {
    "embeddings", "embedding", "vector", "similarity", "semantic",
    "compare meaning", "related", "cluster",
}

REASONING_KEYWORDS = {
    "think", "reason", "analyze", "explain why", "prove",
    "step by step", "logic", "deduce", "infer", "evaluate",
    "consider", "weigh", "compare and contrast", "critique",
}

TOOL_KEYWORDS = {
    "open", "launch", "start", "close", "click", "type",
    "send email", "schedule", "create file", "run command",
    "browse", "navigate", "scroll",
}


@dataclass
class CapabilityResult:
    """Result of capability detection."""
    primary: Capability = Capability.CHAT
    secondary: list[Capability] | None = None
    confidence: float = 0.8
    reasoning: str = ""

    def __post_init__(self):
        if self.secondary is None:
            self.secondary = []


class CapabilityDetector:
    """Detects what capabilities a request needs.

    Usage:
        detector = CapabilityDetector()
        result = detector.detect("Describe this screenshot")
        # result.primary = Capability.VISION
    """

    def detect(self, text: str, context: dict[str, Any] | None = None) -> CapabilityResult:
        text_lower = text.lower().strip()
        scores: dict[Capability, float] = {}

        # Keyword scoring
        scores[Capability.VISION] = self._score_keywords(text_lower, VISION_KEYWORDS)
        scores[Capability.SPEECH] = self._score_keywords(text_lower, SPEECH_KEYWORDS)
        scores[Capability.SEARCH] = self._score_keywords(text_lower, SEARCH_KEYWORDS)
        scores[Capability.CODING] = self._score_keywords(text_lower, CODING_KEYWORDS)
        scores[Capability.IMAGE_GENERATION] = self._score_keywords(text_lower, IMAGE_GEN_KEYWORDS)
        scores[Capability.EMBEDDINGS] = self._score_keywords(text_lower, EMBEDDING_KEYWORDS)
        scores[Capability.REASONING] = self._score_keywords(text_lower, REASONING_KEYWORDS)
        scores[Capability.TOOL_USE] = self._score_keywords(text_lower, TOOL_KEYWORDS)

        # Boost chat score slightly as baseline
        scores[Capability.CHAT] = 0.1

        # Context boost
        if context:
            if context.get("has_image"):
                scores[Capability.VISION] += 0.5
            if context.get("has_file"):
                scores[Capability.CODING] += 0.2
            if context.get("needs_search"):
                scores[Capability.SEARCH] += 0.3

        # Find primary and secondary
        sorted_caps = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_caps[0][0]
        primary_score = sorted_caps[0][1]

        secondary = [cap for cap, score in sorted_caps[1:4] if score > 0.3]

        confidence = min(1.0, 0.5 + primary_score * 0.5) if primary_score > 0 else 0.5

        return CapabilityResult(
            primary=primary,
            secondary=secondary,
            confidence=confidence,
            reasoning=f"top={primary.value}({primary_score:.2f})",
        )

    def _score_keywords(self, text: str, keywords: set[str]) -> float:
        score = 0.0
        for kw in keywords:
            if " " in kw:
                if kw in text:
                    score += 1.0
            else:
                if re.search(r'\b' + re.escape(kw) + r'\b', text):
                    score += 0.5
        return min(score, 2.0)


# Global instance
detector = CapabilityDetector()

__all__ = ["CapabilityDetector", "CapabilityResult", "detector"]
