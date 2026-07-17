"""Memory Optimization — Periodically improves memory quality.

Merge Similar Memories, Compress Memories, Delete Noise,
Rebuild Relationships, Optimize Retrieval, Reduce Redundancy.
Learning should improve memory quality.
"""

from __future__ import annotations

import time
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MemoryOptimizer:
    """Optimizes memory quality through periodic maintenance."""

    def __init__(self) -> None:
        self._optimize_count: int = 0
        self._total_merged: int = 0
        self._total_compressed: int = 0
        self._total_deleted: int = 0

    def optimize(self, memories: list[dict[str, Any]]) -> dict[str, Any]:
        """Run full memory optimization."""
        t0 = time.perf_counter()
        initial_count = len(memories)

        # 1. Remove duplicates
        deduped = self._deduplicate(memories)
        removed_dupes = len(memories) - len(deduped)

        # 2. Merge similar
        merged = self._merge_similar(deduped)
        merged_count = len(deduped) - len(merged)

        # 3. Compress old memories
        compressed = self._compress_old(merged)

        # 4. Remove noise (very low importance)
        cleaned = self._remove_noise(compressed)
        removed_noise = len(compressed) - len(cleaned)

        self._optimize_count += 1
        self._total_merged += merged_count
        self._total_deleted += removed_dupes + removed_noise

        ms = (time.perf_counter() - t0) * 1000
        return {
            "initial_count": initial_count,
            "final_count": len(cleaned),
            "merged": merged_count,
            "removed_duplicates": removed_dupes,
            "removed_noise": removed_noise,
            "latency_ms": round(ms, 1),
        }

    def _deduplicate(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for mem in memories:
            key = str(sorted(mem.items()))
            if key not in seen:
                seen.add(key)
                result.append(mem)
        return result

    def _merge_similar(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(memories) <= 1:
            return memories
        merged: list[dict[str, Any]] = [memories[0]]
        for mem in memories[1:]:
            is_similar = False
            for existing in merged:
                if self._are_similar(mem, existing):
                    is_similar = True
                    break
            if not is_similar:
                merged.append(mem)
        return merged

    def _compress_old(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compress old memories by removing verbose fields."""
        now = time.time()
        for mem in memories:
            age_days = (now - mem.get("timestamp", now)) / 86400
            if age_days > 30:
                for key in list(mem.keys()):
                    if key in ("detail", "raw_context", "metadata"):
                        mem.pop(key, None)
        return memories

    def _remove_noise(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove memories with very low importance."""
        return [
            m for m in memories
            if m.get("importance", 0.5) >= 0.1
        ]

    def _are_similar(self, a: dict[str, Any], b: dict[str, Any]) -> bool:
        """Check if two memories are similar enough to merge."""
        text_a = str(a.get("content", a.get("text", a.get("event", "")))).lower()
        text_b = str(b.get("content", b.get("text", b.get("event", "")))).lower()
        if not text_a or not text_b:
            return False
        words_a = set(text_a.split())
        words_b = set(text_b.split())
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
        return overlap > 0.8

    def get_stats(self) -> dict[str, Any]:
        return {
            "optimize_count": self._optimize_count,
            "total_merged": self._total_merged,
            "total_deleted": self._total_deleted,
        }


memory_optimizer = MemoryOptimizer()

__all__ = ["MemoryOptimizer", "memory_optimizer"]
