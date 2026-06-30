"""Fast retrieval context builder for the JARVIS Personal AI OS.

Optimized: skips retrieval for trivial queries, dedupes layers, measures latency.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from jarvis import config
from jarvis.memory_os import os_memory
from jarvis.fast_path import is_trivial

logger = logging.getLogger(__name__)


@dataclass
class RAGItem:
    source: str
    category: str
    summary: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGContext:
    query: str
    context_text: str
    items: list[RAGItem]
    latency_ms: float


class RAGContextBuilder:
    """Searches memory layers and injects only compact relevant context."""

    def __init__(self, max_chars: int | None = None, max_results: int | None = None) -> None:
        self.max_chars = max_chars or config.RAG_CONTEXT_MAX_CHARS
        self.max_results = max_results or config.RAG_MAX_RESULTS

    def build(self, query: str, *, categories: list[str] | None = None) -> RAGContext:
        started = time.time()

        if is_trivial(query) or len(query.strip()) < 3:
            return RAGContext(query=query, context_text="", items=[], latency_ms=(time.time() - started) * 1000)

        items = self._search_all(query, categories=categories)
        context_text = self._pack(items)
        return RAGContext(query=query, context_text=context_text, items=items, latency_ms=(time.time() - started) * 1000)

    def _search_all(self, query: str, *, categories: list[str] | None) -> list[RAGItem]:
        candidates: list[RAGItem] = []

        # Primary: os_memory with FTS5 (fastest, most relevant)
        for item in os_memory.search(query, categories=categories, limit=self.max_results):
            candidates.append(
                RAGItem(
                    source=item.get("source", "os_memory"),
                    category=item.get("category", "knowledge"),
                    summary=item.get("summary", ""),
                    content=item.get("content", ""),
                    score=float(item.get("importance", 0.5)),
                    metadata={"id": item.get("id"), "layer": "os_memory"},
                )
            )

        # Secondary: only if os_memory returned few results, query legacy stores
        if len(candidates) < 3:
            try:
                from jarvis.memory_manager import intelligent_memory
                for item in intelligent_memory.search(query, limit=max(2, self.max_results // 2)):
                    candidates.append(
                        RAGItem(
                            source=item.get("source", "learning_memory"),
                            category=item.get("category", "learning"),
                            summary=item.get("summary", ""),
                            content=item.get("content", ""),
                            score=float(item.get("importance_score", 0.5)),
                            metadata={"id": item.get("id"), "layer": "learning_memory"},
                        )
                    )
            except Exception:
                pass

            try:
                from jarvis.memory import memory
                for item in memory.search_conversations(query, limit=2):
                    candidates.append(
                        RAGItem(
                            source="conversation_memory", category="conversation",
                            summary=item.get("summary", ""), content=item.get("summary", ""),
                            score=float(item.get("importance", 1)) / 5.0,
                            metadata={"id": item.get("id"), "layer": "legacy_conversation"},
                        )
                    )
                for item in memory.search_notes(query):
                    candidates.append(
                        RAGItem(
                            source="notes", category="document",
                            summary=item.get("title", "Note"), content=item.get("content", ""),
                            score=0.55,
                            metadata={"id": item.get("id"), "layer": "legacy_notes"},
                        )
                    )
            except Exception:
                pass

        # Deduplicate and rank
        deduped: dict[str, RAGItem] = {}
        for item in candidates:
            key = (item.summary or item.content[:120]).lower()
            existing = deduped.get(key)
            if existing is None or item.score > existing.score:
                deduped[key] = item

        ranked = list(deduped.values())
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[: self.max_results]

    def _pack(self, items: list[RAGItem]) -> str:
        if not items:
            return ""
        chunks: list[str] = []
        used = 0
        for index, item in enumerate(items, 1):
            content = " ".join((item.content or item.summary).split())
            if len(content) > 700:
                content = content[:697].rstrip() + "..."
            block = f"[{index}] {item.category} from {item.source}: {item.summary}\n{content}"
            if used + len(block) > self.max_chars:
                break
            chunks.append(block)
            used += len(block)
        return "\n\n".join(chunks)


rag_builder = RAGContextBuilder()
