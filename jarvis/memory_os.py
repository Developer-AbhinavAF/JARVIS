"""Unified production memory store for the JARVIS Personal AI OS."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis import config

logger = logging.getLogger(__name__)


MEMORY_TYPES = {
    "conversation",
    "learning",
    "knowledge",
    "project",
    "research",
    "document",
    "preference",
    "reflection",
}


@dataclass
class OSMemory:
    id: str
    category: str
    importance: float
    timestamp: str
    source: str
    tags: list[str]
    summary: str
    content: str
    metadata: dict[str, Any]


class OSMemoryStore:
    """SQLite-first memory store with FTS search and graph edges."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or config.OS_DB_PATH)
        self._lock = threading.RLock()
        self._fts_available = False
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS os_memories (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 0.5,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'user',
                    tags TEXT NOT NULL DEFAULT '[]',
                    summary TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_os_mem_category_time ON os_memories(category, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_os_mem_importance ON os_memories(importance DESC)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            try:
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS os_memories_fts
                    USING fts5(id UNINDEXED, category, summary, content, tags)
                    """
                )
                self._fts_available = True
            except sqlite3.OperationalError:
                self._fts_available = False
                logger.warning("SQLite FTS5 unavailable; memory search will use LIKE fallback")
            conn.commit()

    def add(
        self,
        content: str,
        *,
        category: str = "knowledge",
        importance: float = 0.5,
        source: str = "user",
        tags: list[str] | None = None,
        summary: str | None = None,
        metadata: dict[str, Any] | None = None,
        memory_id: str | None = None,
    ) -> OSMemory:
        content = " ".join((content or "").split())
        if not content:
            raise ValueError("Memory content cannot be empty")
        category = category if category in MEMORY_TYPES else "knowledge"
        record = OSMemory(
            id=memory_id or f"osmem_{uuid.uuid4().hex}",
            category=category,
            importance=max(0.0, min(float(importance), 1.0)),
            timestamp=datetime.now().isoformat(),
            source=source,
            tags=tags or [],
            summary=summary or self._summarize(content),
            content=content,
            metadata=metadata or {},
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO os_memories
                (id, category, importance, timestamp, source, tags, summary, content, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.category,
                    record.importance,
                    record.timestamp,
                    record.source,
                    json.dumps(record.tags),
                    record.summary,
                    record.content,
                    json.dumps(record.metadata),
                ),
            )
            self._upsert_fts(conn, record)
            conn.commit()
        return record

    def remember_conversation(
        self,
        user_message: str,
        assistant_response: str,
        *,
        session_id: str = "default",
        importance: float = 0.35,
        metadata: dict[str, Any] | None = None,
    ) -> OSMemory:
        turn_id = f"turn_{uuid.uuid4().hex}"
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_turns
                (id, session_id, timestamp, user_message, assistant_response, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    turn_id,
                    session_id,
                    datetime.now().isoformat(),
                    user_message,
                    assistant_response,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
        return self.add(
            f"User: {user_message}\nAssistant: {assistant_response}",
            category="conversation",
            importance=importance,
            source=f"session:{session_id}",
            tags=["conversation"],
            summary=self._summarize(user_message),
            metadata={"turn_id": turn_id, **(metadata or {})},
        )

    def search(
        self,
        query: str,
        *,
        categories: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return self.list(category=categories[0] if categories and len(categories) == 1 else None, limit=limit)

        with self._lock, self._connect() as conn:
            if self._fts_available:
                rows = self._fts_search(conn, query, categories, limit)
                if rows:
                    return rows
            return self._like_search(conn, query, categories, limit)

    def list(self, *, category: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM os_memories WHERE category = ? ORDER BY importance DESC, timestamp DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM os_memories ORDER BY importance DESC, timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def update(self, memory_id: str, updates: dict[str, Any]) -> bool:
        allowed = {"category", "importance", "source", "tags", "summary", "content", "metadata"}
        filtered = {key: value for key, value in updates.items() if key in allowed}
        if not filtered:
            return False
        current = self.get(memory_id)
        if not current:
            return False
        current.update(filtered)
        if isinstance(current.get("tags"), str):
            current["tags"] = self._json_list(current["tags"])
        if isinstance(current.get("metadata"), str):
            current["metadata"] = self._json_dict(current["metadata"])
        record = OSMemory(
            id=memory_id,
            category=current.get("category", "knowledge"),
            importance=float(current.get("importance", 0.5)),
            timestamp=current.get("timestamp", datetime.now().isoformat()),
            source=current.get("source", "user"),
            tags=list(current.get("tags", [])),
            summary=current.get("summary", ""),
            content=current.get("content", ""),
            metadata=dict(current.get("metadata", {})),
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE os_memories
                SET category = ?, importance = ?, source = ?, tags = ?, summary = ?, content = ?, metadata = ?
                WHERE id = ?
                """,
                (
                    record.category,
                    record.importance,
                    record.source,
                    json.dumps(record.tags),
                    record.summary,
                    record.content,
                    json.dumps(record.metadata),
                    memory_id,
                ),
            )
            self._upsert_fts(conn, record)
            conn.commit()
            return conn.total_changes > 0

    def delete(self, memory_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM os_memories WHERE id = ?", (memory_id,))
            if self._fts_available:
                conn.execute("DELETE FROM os_memories_fts WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get(self, memory_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM os_memories WHERE id = ?", (memory_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        *,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        edge_id = f"edge_{uuid.uuid4().hex}"
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_edges
                (id, source_id, target_id, relation, weight, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge_id,
                    source_id,
                    target_id,
                    relation,
                    weight,
                    datetime.now().isoformat(),
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
        return edge_id

    def related(self, memory_id: str, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT e.*, m.summary, m.category
                FROM knowledge_edges e
                JOIN os_memories m ON m.id = e.target_id
                WHERE e.source_id = ?
                ORDER BY e.weight DESC
                LIMIT ?
                """,
                (memory_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def stats(self) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM os_memories").fetchone()[0]
            by_category = {
                row["category"]: row["count"]
                for row in conn.execute("SELECT category, COUNT(*) AS count FROM os_memories GROUP BY category")
            }
            graph_edges = conn.execute("SELECT COUNT(*) FROM knowledge_edges").fetchone()[0]
            turns = conn.execute("SELECT COUNT(*) FROM conversation_turns").fetchone()[0]
        return {
            "db_path": str(self.db_path),
            "total_memories": total,
            "conversation_turns": turns,
            "knowledge_graph_edges": graph_edges,
            "by_category": by_category,
            "fts_available": self._fts_available,
        }

    def dashboard(self, limit: int = 10) -> dict[str, Any]:
        return {
            "stats": self.stats(),
            "recent": self.list(limit=limit),
            "categories": sorted(MEMORY_TYPES),
        }

    def _upsert_fts(self, conn: sqlite3.Connection, record: OSMemory) -> None:
        if not self._fts_available:
            return
        conn.execute("DELETE FROM os_memories_fts WHERE id = ?", (record.id,))
        conn.execute(
            "INSERT INTO os_memories_fts (id, category, summary, content, tags) VALUES (?, ?, ?, ?, ?)",
            (record.id, record.category, record.summary, record.content, " ".join(record.tags)),
        )

    def _fts_search(
        self,
        conn: sqlite3.Connection,
        query: str,
        categories: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        match = self._fts_query(query)
        if not match:
            return []
        params: list[Any] = [match]
        category_sql = ""
        if categories:
            placeholders = ",".join("?" for _ in categories)
            category_sql = f" AND m.category IN ({placeholders})"
            params.extend(categories)
        params.append(limit)
        rows = conn.execute(
            f"""
            SELECT m.*, bm25(os_memories_fts) AS rank
            FROM os_memories_fts
            JOIN os_memories m ON m.id = os_memories_fts.id
            WHERE os_memories_fts MATCH ? {category_sql}
            ORDER BY rank, m.importance DESC, m.timestamp DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _like_search(
        self,
        conn: sqlite3.Connection,
        query: str,
        categories: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        tokens = self._tokens(query)[:6]
        if not tokens:
            return []
        clauses = []
        params: list[Any] = []
        for token in tokens:
            clauses.append("(summary LIKE ? OR content LIKE ? OR tags LIKE ?)")
            pattern = f"%{token}%"
            params.extend([pattern, pattern, pattern])
        category_sql = ""
        if categories:
            placeholders = ",".join("?" for _ in categories)
            category_sql = f" AND category IN ({placeholders})"
            params.extend(categories)
        params.append(limit)
        rows = conn.execute(
            f"""
            SELECT * FROM os_memories
            WHERE ({' OR '.join(clauses)}) {category_sql}
            ORDER BY importance DESC, timestamp DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["tags"] = self._json_list(item.get("tags", "[]"))
        item["metadata"] = self._json_dict(item.get("metadata", "{}"))
        return item

    def _summarize(self, text: str, max_chars: int = 220) -> str:
        cleaned = " ".join(text.split())
        return cleaned if len(cleaned) <= max_chars else cleaned[: max_chars - 3].rstrip() + "..."

    def _fts_query(self, query: str) -> str:
        tokens = self._tokens(query)
        return " OR ".join(tokens[:8])

    def _tokens(self, query: str) -> list[str]:
        return [token.lower() for token in re.findall(r"[A-Za-z0-9_]{2,}", query or "")]

    def _json_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        try:
            parsed = json.loads(value or "[]")
            return [str(item) for item in parsed] if isinstance(parsed, list) else []
        except Exception:
            return []

    def _json_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        try:
            parsed = json.loads(value or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}


os_memory = OSMemoryStore()
