"""Shared utilities for the JARVIS NLP engine.

Provides data structures, constants, and helper functions used across
all NLP modules.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ════════════════════════════════════════════════════════════════════
# ENUMS
# ════════════════════════════════════════════════════════════════════

class Language(Enum):
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hi-en"
    UNKNOWN = "unknown"


class ExecutionMode(Enum):
    AUTO = "auto"           # Execute immediately
    CONFIRM = "confirm"     # Ask user confirmation
    FALLBACK_LLM = "llm"    # Use LLM as fallback
    CLARIFY = "clarify"     # Ask for clarification


class GoalCategory(Enum):
    ENTERTAINMENT = "entertainment"
    PRODUCTIVITY = "productivity"
    PROGRAMMING = "programming"
    COMMUNICATION = "communication"
    INFORMATION = "information"
    SHOPPING = "shopping"
    SYSTEM = "system"
    MEDIA = "media"
    FINANCE = "finance"
    EDUCATION = "education"
    HEALTH = "health"
    SOCIAL = "social"
    UNKNOWN = "unknown"


# ════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class NLPInput:
    """Raw input to the NLP pipeline."""
    text: str
    source: str = "text"  # text | voice
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""


@dataclass
class NLPOutput:
    """Complete output from the NLP pipeline. Never exposed to user."""
    raw_text: str = ""
    normalized_text: str = ""
    language: Language = Language.ENGLISH
    intent: str = ""
    intent_confidence: float = 0.0
    intent_reason: str = ""
    goal: GoalCategory = GoalCategory.UNKNOWN
    entities: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    planner: list[dict[str, Any]] = field(default_factory=list)
    tool: str = ""
    handler: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.AUTO
    confidence_score: float = 0.0
    confidence_level: str = ""
    memory_update: dict[str, Any] = field(default_factory=dict)
    execution_priority: int = 0
    requires_clarification: bool = False
    clarification_message: str = ""
    is_multi_intent: bool = False
    sub_intents: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    match_method: str = ""  # semantic | pattern | context | fallback

    # V3 Cognitive fields
    emotion: str = "neutral"
    emotion_confidence: float = 0.0
    emotion_valence: float = 0.0
    emotion_arousal: float = 0.0
    conversation_type: str = ""  # command | statement | implicit_request | correction | confirm | chitchat
    conversation_behavior: str = ""  # execute | suggest | acknowledge | respond | clarify | correct | confirm | cancel
    conversation_confidence: float = 0.0
    implicit_intent: str = ""
    implicit_confidence: float = 0.0
    implicit_goal: str = ""
    adaptive_plan: dict[str, Any] = field(default_factory=dict)
    safety_level: str = ""  # SAFE | LOW_RISK | MEDIUM_RISK | HIGH_RISK | BLOCKED
    safety_message: str = ""
    safety_risks: list[str] = field(default_factory=list)
    confidence_signals: dict[str, float] = field(default_factory=dict)
    knowledge_sources: list[dict[str, str]] = field(default_factory=list)
    knowledge_domain: str = ""
    knowledge_platform: str = ""
    knowledge_context: str = ""
    knowledge_sources_found: list[dict[str, Any]] = field(default_factory=list)
    response_text: str = ""
    response_style: str = ""
    vocab_match: dict[str, Any] = field(default_factory=dict)
    user_profile_summary: str = ""
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    execution_phases: list[str] = field(default_factory=list)

    @property
    def should_execute(self) -> bool:
        return self.execution_mode == ExecutionMode.AUTO and self.tool

    @property
    def should_fallback_to_llm(self) -> bool:
        return self.execution_mode == ExecutionMode.FALLBACK_LLM or not self.tool


@dataclass
class Entity:
    """A single extracted entity."""
    name: str
    value: str
    raw_value: str = ""
    confidence: float = 1.0
    entity_type: str = ""  # app, website, query, path, url, number, etc.
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentCandidate:
    """A candidate intent with score."""
    intent: str
    score: float
    reason: str = ""
    entities: dict[str, Any] = field(default_factory=dict)
    goal: GoalCategory = GoalCategory.UNKNOWN
    required_capability: str = ""
    execution_mode: ExecutionMode = ExecutionMode.AUTO


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    step_id: int
    intent: str
    tool: str
    handler: str
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: list[int] = field(default_factory=list)
    description: str = ""


# ════════════════════════════════════════════════════════════════════
# SEMANTIC SIMILARITY HELPERS
# ════════════════════════════════════════════════════════════════════

# Common English stop words (lightweight set)
STOP_WORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out",
    "off", "over", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "that",
    "this", "it", "its", "i", "me", "my", "we", "our", "you", "your",
    "he", "him", "his", "she", "her", "they", "them", "their", "what",
    "which", "who", "whom",
}


def tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens."""
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())


def remove_stop_words(tokens: list[str]) -> list[str]:
    """Remove stop words from token list."""
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


# Platform prepositions that are meaningful for intent detection
PLATFORM_PREPOSITIONS: set[str] = {"on", "in", "at", "to", "for"}


def remove_stop_words_platform_aware(tokens: list[str]) -> list[str]:
    """Remove stop words but preserve platform prepositions (on, in, at)."""
    return [t for t in tokens if (t not in STOP_WORDS or t in PLATFORM_PREPOSITIONS) and len(t) > 1]


def word_overlap_score(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Compute Jaccard-like overlap score between two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def weighted_token_score(
    input_tokens: list[str],
    reference_tokens: list[str],
    input_weights: dict[str, float] | None = None,
) -> float:
    """Compute weighted overlap score.

    input_weights: optional dict mapping token -> weight (0.0-1.0).
    Tokens with higher weights contribute more to the score.
    """
    if not input_tokens or not reference_tokens:
        return 0.0

    ref_set = set(reference_tokens)
    total_weight = 0.0
    matched_weight = 0.0

    for token in input_tokens:
        w = (input_weights or {}).get(token, 1.0)
        total_weight += w
        if token in ref_set:
            matched_weight += w

    return matched_weight / total_weight if total_weight > 0 else 0.0


def ngram_overlap(tokens_a: list[str], tokens_b: list[str], n: int = 2) -> float:
    """Compute n-gram overlap between two token lists."""
    if len(tokens_a) < n or len(tokens_b) < n:
        return 0.0

    ngrams_a = set(zip(*[tokens_a[i:] for i in range(n)]))
    ngrams_b = set(zip(*[tokens_b[i:] for i in range(n)]))

    if not ngrams_a or not ngrams_b:
        return 0.0

    intersection = ngrams_a & ngrams_b
    union = ngrams_a | ngrams_b
    return len(intersection) / len(union) if union else 0.0


def semantic_similarity(text_a: str, text_b: str) -> float:
    """Compute semantic similarity between two texts.

    Uses a combination of:
    1. Token overlap (Jaccard)
    2. N-gram overlap (bigram)
    3. Exact phrase matching bonus
    4. Length normalization
    """
    tokens_a = remove_stop_words(tokenize(text_a))
    tokens_b = remove_stop_words(tokenize(text_b))

    if not tokens_a or not tokens_b:
        return 0.0

    # Component scores
    token_score = word_overlap_score(tokens_a, tokens_b)
    bigram_score = ngram_overlap(tokens_a, tokens_b, 2)

    # Exact phrase bonus
    phrase_bonus = 0.0
    if text_a.lower().strip() == text_b.lower().strip():
        phrase_bonus = 0.3
    elif text_a.lower() in text_b.lower() or text_b.lower() in text_a.lower():
        phrase_bonus = 0.15

    # Length normalization: penalize large length differences
    len_ratio = min(len(tokens_a), len(tokens_b)) / max(len(tokens_a), len(tokens_b))
    length_factor = 0.7 + 0.3 * len_ratio  # 0.7 to 1.0

    # Weighted combination
    score = (
        0.40 * token_score +
        0.25 * bigram_score +
        0.35 * phrase_bonus
    ) * length_factor

    return min(score, 1.0)
