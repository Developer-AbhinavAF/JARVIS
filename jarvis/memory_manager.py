"""Intelligent long-term learning memory for JARVIS.

Conversation memory remains SQLite in ``jarvis.memory``. This module manages
learning memory in ChromaDB, with a SQLite fallback so the app still runs when
Chroma is not installed yet.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis import config

logger = logging.getLogger(__name__)


MEMORY_CATEGORIES = {
    "preferences": "Preferences",
    "projects": "Projects",
    "skills": "Skills",
    "interests": "Interests",
    "personal_knowledge": "Personal Knowledge",
    "educational_content": "Educational Content",
    "learned_procedures": "Learned Procedures",
}


@dataclass
class LearningMemoryRecord:
    id: str
    category: str
    timestamp: str
    importance_score: float
    source: str
    summary: str
    content: str
    pinned: bool = False


class HashEmbeddingFunction:
    """Small deterministic embedding function for ChromaDB.

    This avoids automatic model downloads and keeps retrieval usable on local
    8GB systems. It is not semantic like a transformer, but works well enough
    for keyword-rich personal memory and can be swapped later.
    """

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def __call__(self, input: list[str]) -> list[list[float]]:  # Chroma expects this name.
        return [self._embed(text) for text in input]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = [token.strip(".,;:!?()[]{}\"'").lower() for token in text.split()]
        for token in tokens:
            if not token:
                continue
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class IntelligentMemoryManager:
    """Memory validation, categorization, storage, and retrieval."""

    def __init__(self, chroma_dir: Path | None = None) -> None:
        self.chroma_dir = Path(chroma_dir or config.CHROMA_DIR)
        self.sqlite_path = config.DATA_DIR / "learning_memory_fallback.db"
        self._lock = threading.Lock()
        self._client = None
        self._collections: dict[str, Any] = {}
        self._embedding = HashEmbeddingFunction()
        self._init_storage()

    @property
    def backend(self) -> str:
        return "chromadb" if self._client is not None else "sqlite"

    def _init_storage(self) -> None:
        try:
            import chromadb

            self._client = chromadb.PersistentClient(path=str(self.chroma_dir))
            for key in MEMORY_CATEGORIES:
                self._collections[key] = self._client.get_or_create_collection(
                    name=f"learning_{key}",
                    embedding_function=self._embedding,
                    metadata={"description": MEMORY_CATEGORIES[key]},
                )
            logger.info("ChromaDB learning memory initialized at %s", self.chroma_dir)
        except Exception as exc:
            self._client = None
            logger.warning("ChromaDB unavailable; using SQLite learning memory fallback: %s", exc)
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_memories (
                    id TEXT PRIMARY KEY,
                    category TEXT,
                    timestamp TEXT,
                    importance_score REAL,
                    source TEXT,
                    summary TEXT,
                    content TEXT,
                    pinned INTEGER DEFAULT 0
                )
                """
            )
            conn.commit()

    def should_remember(self, text: str, explicit: bool = False) -> tuple[bool, float, str]:
        normalized = (text or "").strip().lower()
        if explicit:
            return True, 0.95, "Explicit user instruction"

        if len(normalized) < 12 or normalized in {"hello", "hi", "thanks", "thank you", "ok", "okay"}:
            return False, 0.05, "Low-value chatter"

        signals = {
            "i prefer": 0.78,
            "my preference": 0.82,
            "remember": 0.9,
            "important": 0.85,
            "my project": 0.8,
            "my goal": 0.8,
            "always": 0.7,
            "never": 0.7,
            "actually": 0.68,
            "correction": 0.82,
        }
        score = max((value for marker, value in signals.items() if marker in normalized), default=0.25)
        return score >= config.MEMORY_IMPORTANCE_THRESHOLD, score, "Heuristic memory relevance"

    def categorize(self, text: str) -> str:
        normalized = text.lower()
        if any(word in normalized for word in ["prefer", "preference", "like", "dislike", "always", "never"]):
            return "preferences"
        if any(word in normalized for word in ["project", "repo", "jarvis", "build", "architecture"]):
            return "projects"
        if any(word in normalized for word in ["skill", "procedure", "steps", "workflow", "how i"]):
            return "learned_procedures"
        if any(word in normalized for word in ["learn", "study", "course", "lecture", "concept", "topic"]):
            return "educational_content"
        if any(word in normalized for word in ["interest", "hobby", "curious"]):
            return "interests"
        return "personal_knowledge"

    def summarize(self, text: str, max_chars: int = 220) -> str:
        cleaned = " ".join((text or "").split())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 3].rstrip() + "..."

    def remember(
        self,
        content: str,
        *,
        category: str | None = None,
        source: str = "user",
        importance_score: float | None = None,
        explicit: bool = False,
        summary: str | None = None,
    ) -> LearningMemoryRecord | None:
        should_save, score, _reason = self.should_remember(content, explicit=explicit)
        if not should_save:
            return None

        record = LearningMemoryRecord(
            id=f"mem_{uuid.uuid4().hex}",
            category=category or self.categorize(content),
            timestamp=datetime.now().isoformat(),
            importance_score=importance_score if importance_score is not None else score,
            source=source,
            summary=summary or self.summarize(content),
            content=content,
        )
        self.add_record(record)
        return record

    def add_record(self, record: LearningMemoryRecord) -> None:
        if record.category not in MEMORY_CATEGORIES:
            record.category = "personal_knowledge"

        with self._lock:
            if self._client is not None:
                collection = self._collections[record.category]
                metadata = asdict(record)
                metadata["pinned"] = int(record.pinned)
                collection.upsert(
                    ids=[record.id],
                    documents=[record.content],
                    metadatas=[metadata],
                )
            else:
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO learning_memories
                        (id, category, timestamp, importance_score, source, summary, content, pinned)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record.id,
                            record.category,
                            record.timestamp,
                            record.importance_score,
                            record.source,
                            record.summary,
                            record.content,
                            int(record.pinned),
                        ),
                    )
                    conn.commit()

    def search(self, query: str, *, limit: int = 5, category: str | None = None) -> list[dict[str, Any]]:
        if not query:
            return self.list_memories(limit=limit, category=category)

        if self._client is not None:
            categories = [category] if category in self._collections else list(self._collections)
            results: list[dict[str, Any]] = []
            for key in categories:
                collection = self._collections[key]
                data = collection.query(query_texts=[query], n_results=limit)
                ids = data.get("ids", [[]])[0]
                documents = data.get("documents", [[]])[0]
                metadatas = data.get("metadatas", [[]])[0]
                distances = data.get("distances", [[]])[0] if data.get("distances") else []
                for index, memory_id in enumerate(ids):
                    metadata = metadatas[index] or {}
                    item = {
                        **metadata,
                        "id": memory_id,
                        "content": documents[index] if index < len(documents) else metadata.get("content", ""),
                        "distance": distances[index] if index < len(distances) else None,
                        "pinned": bool(metadata.get("pinned")),
                    }
                    results.append(item)
            results.sort(key=lambda item: (not item.get("pinned", False), item.get("distance", 1.0)))
            return results[:limit]

        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            pattern = f"%{query}%"
            params: list[Any] = [pattern, pattern]
            sql = """
                SELECT * FROM learning_memories
                WHERE (summary LIKE ? OR content LIKE ?)
            """
            if category:
                sql += " AND category = ?"
                params.append(category)
            sql += " ORDER BY pinned DESC, importance_score DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def list_memories(self, *, limit: int = 50, category: str | None = None) -> list[dict[str, Any]]:
        if self._client is not None:
            categories = [category] if category in self._collections else list(self._collections)
            items: list[dict[str, Any]] = []
            for key in categories:
                data = self._collections[key].get(limit=limit, include=["documents", "metadatas"])
                for index, memory_id in enumerate(data.get("ids", [])):
                    metadata = data.get("metadatas", [])[index] or {}
                    document = data.get("documents", [])[index]
                    items.append({
                        **metadata,
                        "id": memory_id,
                        "content": document,
                        "pinned": bool(metadata.get("pinned")),
                    })
            items.sort(key=lambda item: (not item.get("pinned", False), item.get("timestamp", "")), reverse=False)
            return items[:limit]

        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            params: list[Any] = []
            sql = "SELECT * FROM learning_memories"
            if category:
                sql += " WHERE category = ?"
                params.append(category)
            sql += " ORDER BY pinned DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def update_memory(self, memory_id: str, updates: dict[str, Any]) -> bool:
        item = self.get_memory(memory_id)
        if not item:
            return False
        item.update({k: v for k, v in updates.items() if k in {"summary", "content", "category", "importance_score", "pinned"}})
        record = LearningMemoryRecord(
            id=item["id"],
            category=item.get("category", "personal_knowledge"),
            timestamp=item.get("timestamp", datetime.now().isoformat()),
            importance_score=float(item.get("importance_score", 0.5)),
            source=item.get("source", "user"),
            summary=item.get("summary", ""),
            content=item.get("content", ""),
            pinned=bool(item.get("pinned", False)),
        )
        self.add_record(record)
        return True

    def pin_memory(self, memory_id: str, pinned: bool = True) -> bool:
        return self.update_memory(memory_id, {"pinned": pinned})

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        for item in self.list_memories(limit=1000):
            if item.get("id") == memory_id:
                return item
        return None

    def delete_memory(self, memory_id: str) -> bool:
        item = self.get_memory(memory_id)
        if not item:
            return False

        with self._lock:
            if self._client is not None:
                category = item.get("category", "personal_knowledge")
                if category in self._collections:
                    self._collections[category].delete(ids=[memory_id])
            else:
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.execute("DELETE FROM learning_memories WHERE id = ?", (memory_id,))
                    conn.commit()
        return True

    def export_json(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "categories": MEMORY_CATEGORIES,
            "memories": self.list_memories(limit=1000),
            "exported_at": datetime.now().isoformat(),
        }


intelligent_memory = IntelligentMemoryManager()
