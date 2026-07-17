"""Knowledge Learning — Learns from various sources.

Repositories, PDFs, YouTube, Research Papers, Documentation,
Websites, Study Notes, Books.
Everything contributes to future intelligence.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeItem:
    """A learned knowledge item."""
    item_id: str = ""
    source_type: str = ""          # repository, pdf, youtube, paper, docs, website, note, book
    title: str = ""
    url: str = ""
    summary: str = ""
    key_concepts: list[str] = field(default_factory=list)
    entities_learned: list[str] = field(default_factory=list)
    usefulness_score: float = 0.5
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    learned_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_type": self.source_type,
            "title": self.title,
            "usefulness_score": round(self.usefulness_score, 3),
            "access_count": self.access_count,
        }


class KnowledgeLearner:
    """Tracks learned knowledge sources."""

    def __init__(self) -> None:
        self._items: dict[str, KnowledgeItem] = {}
        self._item_counter: int = 0
        self._total_learned: int = 0

    def learn(
        self,
        source_type: str,
        title: str,
        url: str = "",
        summary: str = "",
        key_concepts: list[str] | None = None,
        entities: list[str] | None = None,
    ) -> KnowledgeItem:
        """Record a knowledge item."""
        item_key = f"{source_type}:{title.lower()[:50]}"
        if item_key in self._items:
            item = self._items[item_key]
            item.access_count += 1
            item.last_accessed = time.time()
            item.usefulness_score = min(1.0, item.usefulness_score + 0.05)
            return item

        self._item_counter += 1
        item = KnowledgeItem(
            item_id=f"kl_{self._item_counter:04d}",
            source_type=source_type,
            title=title,
            url=url,
            summary=summary,
            key_concepts=key_concepts or [],
            entities_learned=entities or [],
        )
        self._items[item_key] = item
        self._total_learned += 1
        return item

    def access(self, source_type: str, title: str) -> None:
        """Record access to a knowledge item."""
        item_key = f"{source_type}:{title.lower()[:50]}"
        item = self._items.get(item_key)
        if item:
            item.access_count += 1
            item.last_accessed = time.time()

    def get_by_type(self, source_type: str) -> list[dict[str, Any]]:
        return [
            i.to_dict() for i in self._items.values()
            if i.source_type == source_type
        ]

    def get_useful(self, min_score: float = 0.5) -> list[dict[str, Any]]:
        return sorted(
            [i.to_dict() for i in self._items.values() if i.usefulness_score >= min_score],
            key=lambda i: -i["usefulness_score"],
        )

    def get_stats(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for item in self._items.values():
            by_type[item.source_type] = by_type.get(item.source_type, 0) + 1
        return {
            "total_items": len(self._items),
            "total_learned": self._total_learned,
            "by_type": by_type,
        }


knowledge_learner = KnowledgeLearner()

__all__ = ["KnowledgeLearner", "KnowledgeItem", "knowledge_learner"]
