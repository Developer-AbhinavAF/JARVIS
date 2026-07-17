"""Memory Manager with Importance Scoring & Decay for JARVIS NLP.

Every memory gets:
- Importance (how important is this memory?)
- Confidence (how confident are we in this memory?)
- Frequency (how often is this accessed?)
- Recency (when was it last accessed?)
- Relationship (what other memories does it relate to?)
- Decay Rate (how fast should this memory fade?)

Old useless memories fade naturally. Important memories remain.
"""

from __future__ import annotations

import time
import math
import json
import os
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path


# ════════════════════════════════════════════════════════════════════
# MEMORY TYPES
# ════════════════════════════════════════════════════════════════════

class MemoryType:
    WORKING = "working"          # Short-term, current task
    EPISODIC = "episodic"        # Events and experiences
    SEMANTIC = "semantic"        # Facts and knowledge
    PROCEDURAL = "procedural"    # How to do things
    PREFERENCE = "preference"    # User preferences
    SKILL = "skill"              # Learned skills
    FAILURE = "failure"          # Tool/system failures
    TOOL = "tool"                # Tool usage patterns
    CONVERSATION = "conversation"  # Conversation history
    PROJECT = "project"          # Project-specific knowledge


# ════════════════════════════════════════════════════════════════════
# MEMORY ENTRY
# ════════════════════════════════════════════════════════════════════

@dataclass
class MemoryEntry:
    """A single memory with importance scoring."""
    id: str = ""
    content: str = ""
    memory_type: str = MemoryType.EPISODIC
    category: str = ""

    # Importance scoring
    importance: float = 0.5       # 0.0 (trivial) to 1.0 (critical)
    confidence: float = 0.8       # 0.0 (uncertain) to 1.0 (certain)
    frequency: int = 0            # Access count
    recency: float = 0.0          # Last access timestamp
    created_at: float = 0.0       # Creation timestamp

    # Decay
    decay_rate: float = 0.01      # How fast this memory fades
    last_decay_check: float = 0.0

    # Relationships
    related_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # Context
    entities: dict[str, Any] = field(default_factory=dict)
    intent: str = ""
    tool_used: str = ""
    success: bool = True
    context: dict[str, Any] = field(default_factory=dict)

    def effective_importance(self) -> float:
        """Calculate effective importance considering decay and access patterns."""
        now = time.time()
        age_hours = (now - self.created_at) / 3600.0 if self.created_at else 0

        # Base importance
        base = self.importance

        # Frequency boost (logarithmic, capped)
        freq_boost = min(math.log(self.frequency + 1) * 0.1, 0.3)

        # Recency boost (more recent = higher)
        recency_boost = 0.0
        if self.recency > 0:
            hours_since_access = (now - self.recency) / 3600.0
            recency_boost = max(0, 0.2 - hours_since_access * 0.001)

        # Decay penalty
        decay_penalty = age_hours * self.decay_rate * 0.01

        # Confidence factor
        confidence_factor = self.confidence

        # Calculate final effective importance
        effective = (base + freq_boost + recency_boost - decay_penalty) * confidence_factor
        return max(0.0, min(1.0, effective))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "category": self.category,
            "importance": round(self.importance, 3),
            "confidence": round(self.confidence, 3),
            "frequency": self.frequency,
            "recency": self.recency,
            "created_at": self.created_at,
            "decay_rate": self.decay_rate,
            "related_ids": self.related_ids,
            "tags": self.tags,
            "entities": self.entities,
            "intent": self.intent,
            "tool_used": self.tool_used,
            "success": self.success,
            "effective_importance": round(self.effective_importance(), 3),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ════════════════════════════════════════════════════════════════════
# MEMORY MANAGER
# ════════════════════════════════════════════════════════════════════

class MemoryManager:
    """Advanced memory system with importance scoring, decay, and persistence.

    Memories are scored by importance, confidence, frequency, recency,
    and relationships. Old useless memories fade naturally.
    Important memories remain.
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self._memories: dict[str, MemoryEntry] = {}
        self._next_id: int = 1
        self._data_dir = Path(data_dir) if data_dir else None
        self._max_memories: int = 10000
        self._auto_decay_enabled: bool = True
        self._last_decay_run: float = 0.0
        self._decay_interval: float = 3600.0  # Run decay every hour

    # ── Core API ───────────────────────────────────────────────────

    def store(
        self,
        content: str,
        memory_type: str = MemoryType.EPISODIC,
        importance: float = 0.5,
        confidence: float = 0.8,
        tags: list[str] | None = None,
        entities: dict[str, Any] | None = None,
        intent: str = "",
        tool_used: str = "",
        success: bool = True,
        context: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a new memory with importance scoring.

        Args:
            content: The memory content.
            memory_type: Type of memory (episodic, semantic, etc.).
            importance: Initial importance (0.0-1.0).
            confidence: Confidence in the memory (0.0-1.0).
            tags: Searchable tags.
            entities: Associated entities.
            intent: The intent that created this memory.
            tool_used: The tool that was used.
            success: Whether the action was successful.
            context: Additional context.

        Returns:
            The stored MemoryEntry.
        """
        now = time.time()
        entry = MemoryEntry(
            id=self._generate_id(),
            content=content,
            memory_type=memory_type,
            importance=importance,
            confidence=confidence,
            frequency=1,
            recency=now,
            created_at=now,
            last_decay_check=now,
            tags=tags or [],
            entities=entities or {},
            intent=intent,
            tool_used=tool_used,
            success=success,
            context=context or {},
        )

        self._memories[entry.id] = entry

        # Auto-decay if enabled
        if self._auto_decay_enabled:
            self._maybe_run_decay()

        # Enforce memory limit
        self._enforce_limit()

        return entry

    def retrieve(
        self,
        query: str = "",
        memory_type: str | None = None,
        tags: list[str] | None = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Retrieve memories matching criteria.

        Returns memories sorted by effective importance (highest first).
        """
        candidates: list[MemoryEntry] = []

        for entry in self._memories.values():
            # Filter by type
            if memory_type and entry.memory_type != memory_type:
                continue

            # Filter by tags
            if tags and not any(t in entry.tags for t in tags):
                continue

            # Filter by importance
            if entry.effective_importance() < min_importance:
                continue

            # Filter by query (simple content match)
            if query and query.lower() not in entry.content.lower():
                # Also check tags and entities
                tag_match = any(query.lower() in t.lower() for t in entry.tags)
                entity_match = any(
                    query.lower() in str(v).lower()
                    for v in entry.entities.values()
                )
                if not tag_match and not entity_match:
                    continue

            candidates.append(entry)

        # Sort by effective importance
        candidates.sort(key=lambda e: e.effective_importance(), reverse=True)

        # Update access patterns
        now = time.time()
        for entry in candidates[:limit]:
            entry.frequency += 1
            entry.recency = now

        return candidates[:limit]

    def update_importance(
        self,
        memory_id: str,
        importance_delta: float = 0.0,
        confidence_delta: float = 0.0,
    ) -> bool:
        """Adjust the importance or confidence of a memory."""
        entry = self._memories.get(memory_id)
        if not entry:
            return False

        entry.importance = max(0.0, min(1.0, entry.importance + importance_delta))
        entry.confidence = max(0.0, min(1.0, entry.confidence + confidence_delta))
        return True

    def link_memories(self, id_a: str, id_b: str) -> bool:
        """Create a bidirectional link between two memories."""
        a = self._memories.get(id_a)
        b = self._memories.get(id_b)
        if not a or not b:
            return False

        if id_b not in a.related_ids:
            a.related_ids.append(id_b)
        if id_a not in b.related_ids:
            b.related_ids.append(id_a)
        return True

    def get_related(self, memory_id: str, limit: int = 5) -> list[MemoryEntry]:
        """Get memories related to a given memory."""
        entry = self._memories.get(memory_id)
        if not entry:
            return []

        related = [
            self._memories[rid]
            for rid in entry.related_ids
            if rid in self._memories
        ]

        related.sort(key=lambda e: e.effective_importance(), reverse=True)
        return related[:limit]

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        if memory_id not in self._memories:
            return False
        del self._memories[memory_id]
        return True

    def clear(self, memory_type: str | None = None) -> int:
        """Clear memories, optionally filtered by type."""
        if memory_type is None:
            count = len(self._memories)
            self._memories.clear()
            return count

        to_delete = [
            mid for mid, entry in self._memories.items()
            if entry.memory_type == memory_type
        ]
        for mid in to_delete:
            del self._memories[mid]
        return len(to_delete)

    # ── Decay ──────────────────────────────────────────────────────

    def run_decay(self) -> int:
        """Run decay on all memories. Returns number of memories removed."""
        now = time.time()
        self._last_decay_run = now

        to_remove: list[str] = []
        for mid, entry in self._memories.items():
            entry.last_decay_check = now
            # Remove memories with very low effective importance
            if entry.effective_importance() < 0.01 and entry.memory_type != MemoryType.PREFERENCE:
                to_remove.append(mid)

        for mid in to_remove:
            del self._memories[mid]

        return len(to_remove)

    def get_decay_stats(self) -> dict[str, Any]:
        """Get statistics about memory decay."""
        entries = list(self._memories.values())
        if not entries:
            return {"total": 0, "avg_importance": 0, "avg_effective": 0}

        return {
            "total": len(entries),
            "avg_importance": sum(e.importance for e in entries) / len(entries),
            "avg_effective": sum(e.effective_importance() for e in entries) / len(entries),
            "high_importance": sum(1 for e in entries if e.effective_importance() > 0.7),
            "low_importance": sum(1 for e in entries if e.effective_importance() < 0.2),
        }

    # ── Persistence ────────────────────────────────────────────────

    def save(self, filepath: str | Path | None = None) -> None:
        """Save memories to disk."""
        if filepath is None:
            if self._data_dir is None:
                return
            filepath = self._data_dir / "memory_manager.json"
        else:
            filepath = Path(filepath)

        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "next_id": self._next_id,
            "memories": {mid: entry.to_dict() for mid, entry in self._memories.items()},
        }
        filepath.write_text(json.dumps(data, indent=2, default=str))

    def load(self, filepath: str | Path | None = None) -> None:
        """Load memories from disk."""
        if filepath is None:
            if self._data_dir is None:
                return
            filepath = self._data_dir / "memory_manager.json"
        else:
            filepath = Path(filepath)

        if not filepath.exists():
            return

        data = json.loads(filepath.read_text())
        self._next_id = data.get("next_id", 1)
        self._memories = {
            mid: MemoryEntry.from_dict(entry_data)
            for mid, entry_data in data.get("memories", {}).items()
        }

    # ── Stats ──────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return memory manager statistics."""
        entries = list(self._memories.values())
        type_counts: dict[str, int] = {}
        for e in entries:
            type_counts[e.memory_type] = type_counts.get(e.memory_type, 0) + 1

        return {
            "total_memories": len(entries),
            "type_distribution": type_counts,
            "avg_importance": sum(e.importance for e in entries) / len(entries) if entries else 0,
            "avg_confidence": sum(e.confidence for e in entries) / len(entries) if entries else 0,
            "total_accesses": sum(e.frequency for e in entries),
        }

    # ── Internal helpers ───────────────────────────────────────────

    def _generate_id(self) -> str:
        mem_id = f"mem_{int(time.time())}_{self._next_id}"
        self._next_id += 1
        return mem_id

    def _maybe_run_decay(self) -> None:
        now = time.time()
        if now - self._last_decay_run >= self._decay_interval:
            self.run_decay()

    def _enforce_limit(self) -> None:
        if len(self._memories) <= self._max_memories:
            return

        # Remove least important memories
        entries = sorted(
            self._memories.items(),
            key=lambda x: x[1].effective_importance(),
        )
        to_remove = len(self._memories) - self._max_memories
        for mid, _ in entries[:to_remove]:
            del self._memories[mid]


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

memory_manager = MemoryManager()
