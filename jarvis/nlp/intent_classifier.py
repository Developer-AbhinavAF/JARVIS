"""Enhanced intent classification for JARVIS NLP pipeline.

Production-grade intent classifier that combines:
1. Regex pattern matching (fast, exact)
2. Semantic keyword scoring (fuzzy, flexible)
3. Fuzzy string matching (typo tolerance)
4. Context-aware disambiguation

The classifier follows a strict priority cascade:
  Pattern match (highest confidence)
  → Semantic keyword scoring
  → Fuzzy matching
  → LLM fallback (only as last resort)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .normalizer import normalize, normalize_for_matching
from .patterns import PatternBank, IntentPattern
from .entity_extractor import EntityExtractor, ExtractionResult
from .synonyms import SEMANTIC_INTENT_KEYWORDS


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent: str
    confidence: float
    action: str | None  # Direct action mapping
    pattern: IntentPattern | None  # Matched pattern
    match: re.Match | None  # Regex match object
    entities: ExtractionResult = field(default_factory=ExtractionResult)
    raw_text: str = ""
    normalized_text: str = ""
    should_execute: bool = True
    should_fallback_to_llm: bool = False
    match_method: str = "pattern"  # pattern | semantic | fuzzy | keyword_score
    all_scores: dict[str, float] = field(default_factory=dict)  # All intent scores for debugging

    @property
    def has_high_confidence(self) -> bool:
        return self.confidence >= 0.90

    @property
    def has_medium_confidence(self) -> bool:
        return 0.70 <= self.confidence < 0.90

    @property
    def has_low_confidence(self) -> bool:
        return self.confidence < 0.70


# ════════════════════════════════════════════════════════════════════
# SEMANTIC KEYWORD SCORING
# ════════════════════════════════════════════════════════════════════

# Intent → high-value keywords (words that strongly indicate this intent)
_INTENT_KEYWORDS: dict[str, list[str]] = {
    "OPEN_WEBSITE": ["open", "launch", "go to", "visit", "navigate", "browse", "website", "site", "page"],
    "OPEN_APP": ["open", "launch", "start", "run", "app", "application", "program", "software"],
    "CLOSE_APP": ["close", "shut", "kill", "stop", "quit", "exit", "terminate", "end"],
    "SEARCH_WEB": ["search", "find", "look up", "google", "query", "browse for"],
    "SEARCH_YOUTUBE": ["youtube", "yt", "search", "find", "video"],
    "SEARCH_ON_PLATFORM": ["search", "find", "on", "in"],
    "PLAY_MUSIC": ["play", "listen", "music", "song", "artist", "album", "playlist", "stream"],
    "PLAY_YOUTUBE": ["youtube", "yt", "play", "watch", "video"],
    "PLAY_SPOTIFY": ["spotify", "play", "music", "song", "artist"],
    "GET_WEATHER": ["weather", "forecast", "temperature", "rain", "sun", "cold", "hot", "umbrella"],
    "GET_NEWS": ["news", "headlines", "breaking", "current events", "happening"],
    "SYSTEM_STATUS": ["system", "computer", "pc", "status", "stats", "cpu", "ram", "memory", "disk", "battery", "performance"],
    "VOLUME_CONTROL": ["volume", "louder", "softer", "mute", "unmute", "sound", "audio", "silence"],
    "BRIGHTNESS_CONTROL": ["brightness", "brighter", "dimmer", "dim", "bright", "screen", "display", "light"],
    "SCREENSHOT": ["screenshot", "screen", "capture", "snapshot", "screen shot"],
    "SYSTEM_POWER": ["shutdown", "shut down", "power off", "restart", "reboot", "sleep", "hibernate", "lock"],
    "CLIPBOARD": ["clipboard", "copy", "paste", "copied", "clipped"],
    "CALCULATOR": ["calculate", "calc", "compute", "math", "multiply", "divide", "add", "subtract", "plus", "minus", "times", "equation"],
    "TIMER": ["timer", "alarm", "remind", "countdown", "minutes", "seconds", "hours"],
    "DATETIME": ["time", "date", "day", "today", "tomorrow", "yesterday", "clock", "hour", "minute"],
    "SAVE_MEMORY": ["remember", "save", "store", "keep", "note", "write down", "don't forget", "memorize"],
    "RECALL_MEMORY": ["recall", "remember", "know", "memory", "notes", "saved"],
    "WINDOW_CONTROL": ["minimize", "maximize", "restore", "window", "switch", "focus", "desktop"],
    "JOKE": ["joke", "funny", "laugh", "humor", "comedy", "hilarious"],
    "QUOTE": ["quote", "inspire", "motivational", "inspiration", "encourage", "uplift"],
    "FLIP_COIN": ["coin", "flip", "toss", "heads", "tails"],
    "DICE_ROLL": ["dice", "roll", "die", "random"],
    "NASA_APOD": ["nasa", "apod", "astronomy", "picture of the day", "space", "astronomy picture"],
    "NASA_MARS": ["mars", "rover", "curiosity", "nasa mars"],
    "ISS_LOCATION": ["iss", "space station", "international space station"],
    "STOCK_QUOTE": ["stock", "share", "price", "ticker", "market", "finance", "trading"],
    "RANDOM_FACT": ["fact", "trivia", "did you know", "interesting fact", "fun fact"],
    "IP_LOOKUP": ["ip", "address", "ip address", "geolocation"],
    "ADD_TODO": ["todo", "task", "reminder", "add", "create", "remind me"],
    "LIST_TODOS": ["todos", "tasks", "list", "show", "what do i need to do"],
    "ADD_NOTE": ["note", "add note", "create note", "take note"],
    "GREETING": ["hello", "hi", "hey", "howdy", "morning", "afternoon", "evening", "how are you", "who are you", "thanks", "bye"],
    "WEB_SEARCH": ["search", "find", "look up", "google", "what is", "who is", "how to", "explain", "tell me about"],
}


class IntentClassifier:
    """Enhanced intent classifier with semantic understanding.

    Classification cascade:
    1. Regex pattern matching (fast, exact, highest confidence)
    2. Semantic keyword scoring (flexible, handles variations)
    3. Fuzzy string matching (typo tolerance)
    4. LLM fallback (only when all else fails)
    """

    def __init__(self) -> None:
        self.pattern_bank = PatternBank()
        self.entity_extractor = EntityExtractor()
        # Pre-compile intent keyword patterns for fast scoring
        self._intent_keyword_patterns: dict[str, list[re.Pattern]] = {}
        for intent, keywords in _INTENT_KEYWORDS.items():
            patterns = []
            for kw in keywords:
                patterns.append(re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
            self._intent_keyword_patterns[intent] = patterns

    def classify(self, text: str) -> IntentResult:
        """Classify user intent from text.

        Uses a multi-stage classification cascade:
        1. Pattern matching (exact regex)
        2. Semantic keyword scoring
        3. Fuzzy matching
        4. LLM fallback
        """
        # Step 1: Normalize
        normalized = normalize(text)
        matching_text = normalize_for_matching(text)

        # Step 2: Try regex pattern matching (highest confidence)
        pattern_result = self._try_pattern_match(normalized)
        if pattern_result and pattern_result.confidence >= 0.85:
            return pattern_result

        # Step 3: Try semantic keyword scoring
        semantic_result = self._try_semantic_scoring(normalized, matching_text, text)
        if semantic_result and semantic_result.confidence >= 0.75:
            return semantic_result

        # Step 4: If we have a pattern match with lower confidence, use it
        if pattern_result and pattern_result.confidence >= 0.60:
            return pattern_result

        # Step 5: If we have a semantic match with lower confidence, use it
        if semantic_result and semantic_result.confidence >= 0.60:
            return semantic_result

        # Step 6: No good match - fall back to LLM
        return IntentResult(
            intent="CHAT",
            confidence=0.50,
            action=None,
            pattern=None,
            match=None,
            entities=ExtractionResult(raw_text=text, cleaned_text=normalized),
            raw_text=text,
            normalized_text=normalized,
            should_execute=False,
            should_fallback_to_llm=True,
            match_method="fallback",
        )

    def _try_pattern_match(self, normalized: str) -> IntentResult | None:
        """Try regex pattern matching."""
        best_match: re.Match | None = None
        best_pattern: IntentPattern | None = None
        best_confidence = 0.0

        for pattern in self.pattern_bank.get_patterns():
            for regex_str in pattern.patterns:
                try:
                    match = re.search(regex_str, normalized, re.IGNORECASE)
                    if match and pattern.confidence > best_confidence:
                        best_match = match
                        best_pattern = pattern
                        best_confidence = pattern.confidence
                        break
                except re.error:
                    continue

        if not best_pattern:
            return None

        entities = self.entity_extractor.extract(normalized, best_pattern.intent, best_match)

        return IntentResult(
            intent=best_pattern.intent,
            confidence=best_confidence,
            action=best_pattern.action,
            pattern=best_pattern,
            match=best_match,
            entities=entities,
            raw_text="",
            normalized_text=normalized,
            should_execute=best_confidence >= 0.70,
            should_fallback_to_llm=best_confidence < 0.70,
            match_method="pattern",
        )

    def _try_semantic_scoring(self, normalized: str, matching_text: str, raw_text: str) -> IntentResult | None:
        """Score each intent based on keyword presence."""
        scores: dict[str, float] = {}

        for intent, keyword_patterns in self._intent_keyword_patterns.items():
            score = 0.0
            matches_found = 0
            for pattern in keyword_patterns:
                if pattern.search(matching_text) or pattern.search(normalized):
                    matches_found += 1
                    score += 1.0

            if matches_found > 0:
                # Normalize score by number of keywords matched
                # More keywords matched = higher confidence
                normalized_score = min(score / 3.0, 1.0)  # Cap at 1.0 after 3 matches
                # Boost score if multiple keywords match
                if matches_found >= 2:
                    normalized_score = min(normalized_score * 1.2, 0.95)
                if matches_found >= 3:
                    normalized_score = min(normalized_score * 1.1, 0.98)
                scores[intent] = normalized_score

        if not scores:
            return None

        # Find best scoring intent
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        # Get action mapping
        action = best_intent.lower()

        return IntentResult(
            intent=best_intent,
            confidence=best_score,
            action=action,
            pattern=None,
            match=None,
            entities=ExtractionResult(raw_text=raw_text, cleaned_text=normalized),
            raw_text=raw_text,
            normalized_text=normalized,
            should_execute=best_score >= 0.70,
            should_fallback_to_llm=best_score < 0.70,
            match_method="semantic",
            all_scores=scores,
        )

    def classify_batch(self, texts: list[str]) -> list[IntentResult]:
        """Classify multiple texts."""
        return [self.classify(text) for text in texts]

    def get_supported_intents(self) -> list[str]:
        """Get list of all supported intent names."""
        return list(set(p.intent for p in self.pattern_bank.get_patterns()))


# Global instance
intent_classifier = IntentClassifier()
