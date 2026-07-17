"""Knowledge Ranking — Score and rank knowledge for retrieval.

Every piece of knowledge receives:
- Importance
- Confidence
- Recency
- Frequency
- Source Reliability
- Relationship Score

Knowledge should be ranked before retrieval.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# SOURCE RELIABILITY
# ════════════════════════════════════════════════════════════════════

SOURCE_RELIABILITY: dict[str, float] = {
    "official_documentation": 0.95,
    "research_paper": 0.93,
    "book": 0.90,
    "verified_source": 0.88,
    "wikipedia": 0.80,
    "github": 0.78,
    "technical_blog": 0.72,
    "stackoverflow": 0.68,
    "reddit": 0.55,
    "forum": 0.50,
    "user_input": 0.70,
    "learned": 0.65,
    "default": 0.60,
}


@dataclass
class RankedKnowledge:
    """A piece of knowledge with its ranking score."""
    content: str = ""
    source: str = ""
    importance: float = 0.5
    confidence: float = 0.8
    recency: float = 0.5
    frequency: float = 0.0
    source_reliability: float = 0.6
    relationship_score: float = 0.0
    final_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content[:200],
            "source": self.source,
            "final_score": round(self.final_score, 3),
            "importance": round(self.importance, 3),
            "confidence": round(self.confidence, 3),
            "recency": round(self.recency, 3),
        }


class KnowledgeRanker:
    """Rank knowledge pieces for optimal retrieval."""

    def __init__(self) -> None:
        self._weights = {
            "importance": 0.25,
            "confidence": 0.20,
            "recency": 0.15,
            "frequency": 0.10,
            "source_reliability": 0.20,
            "relationship_score": 0.10,
        }
        self._access_counts: dict[str, int] = {}

    def rank(
        self,
        candidates: list[dict[str, Any]],
        query: str = "",
        top_k: int = 10,
    ) -> list[RankedKnowledge]:
        """Rank a list of knowledge candidates."""
        ranked: list[RankedKnowledge] = []

        for candidate in candidates:
            rk = self._score_candidate(candidate)
            ranked.append(rk)

        ranked.sort(key=lambda r: -r.final_score)
        return ranked[:top_k]

    def _score_candidate(self, candidate: dict[str, Any]) -> RankedKnowledge:
        content = candidate.get("content", "")
        source = candidate.get("source", "default")
        importance = candidate.get("importance", 0.5)
        confidence = candidate.get("confidence", 0.8)
        timestamp = candidate.get("timestamp", time.time())
        access_count = candidate.get("access_count", 0)

        recency = self._calc_recency(timestamp)
        frequency = min(1.0, access_count / 10)
        source_rel = SOURCE_RELIABILITY.get(source, SOURCE_RELIABILITY["default"])
        rel_score = candidate.get("relationship_score", 0.0)

        final = (
            self._weights["importance"] * importance +
            self._weights["confidence"] * confidence +
            self._weights["recency"] * recency +
            self._weights["frequency"] * frequency +
            self._weights["source_reliability"] * source_rel +
            self._weights["relationship_score"] * rel_score
        )

        return RankedKnowledge(
            content=content,
            source=source,
            importance=importance,
            confidence=confidence,
            recency=recency,
            frequency=frequency,
            source_reliability=source_rel,
            relationship_score=rel_score,
            final_score=final,
        )

    def _calc_recency(self, timestamp: float) -> float:
        age_hours = (time.time() - timestamp) / 3600
        if age_hours < 1:
            return 1.0
        if age_hours < 24:
            return 0.9
        if age_hours < 24 * 7:
            return 0.7
        if age_hours < 24 * 30:
            return 0.5
        return max(0.1, 1.0 - age_hours / (24 * 365))

    def update_weights(self, weights: dict[str, float]) -> None:
        self._weights.update(weights)

    def get_stats(self) -> dict[str, Any]:
        return {
            "weights": dict(self._weights),
            "source_reliability_count": len(SOURCE_RELIABILITY),
        }


knowledge_ranker = KnowledgeRanker()

__all__ = ["KnowledgeRanker", "RankedKnowledge", "knowledge_ranker", "SOURCE_RELIABILITY"]
