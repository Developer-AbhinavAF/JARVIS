"""Lessons learned database for JARVIS self-improvement."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from jarvis import config


@dataclass
class Lesson:
    id: str
    lesson_type: str
    title: str
    description: str
    source: str
    confidence: float
    suggestion: str = ""
    resolved: bool = False
    pinned: bool = False
    timestamp: str = ""


class LessonsLearnedDB:
    """SQLite-backed log of mistakes and improvement ideas."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or str(config.LESSONS_DB_PATH)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    id TEXT PRIMARY KEY,
                    lesson_type TEXT,
                    title TEXT,
                    description TEXT,
                    source TEXT,
                    confidence REAL,
                    suggestion TEXT,
                    resolved INTEGER DEFAULT 0,
                    pinned INTEGER DEFAULT 0,
                    timestamp TEXT
                )
                """
            )
            conn.commit()

    def add_lesson(
        self,
        *,
        lesson_type: str,
        title: str,
        description: str,
        source: str,
        confidence: float,
        suggestion: str = "",
    ) -> str:
        lesson_id = f"lesson_{uuid.uuid4().hex}"
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO lessons
                (id, lesson_type, title, description, source, confidence, suggestion, resolved, pinned, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
                """,
                (
                    lesson_id,
                    lesson_type,
                    title,
                    description,
                    source,
                    confidence,
                    suggestion,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        return lesson_id

    def list_lessons(self, limit: int = 100, query: str | None = None) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            params: list[Any] = []
            sql = "SELECT * FROM lessons"
            if query:
                sql += " WHERE title LIKE ? OR description LIKE ? OR suggestion LIKE ?"
                pattern = f"%{query}%"
                params.extend([pattern, pattern, pattern])
            sql += " ORDER BY pinned DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def update_lesson(self, lesson_id: str, updates: dict[str, Any]) -> bool:
        allowed = {"title", "description", "suggestion", "resolved", "pinned", "confidence"}
        fields = [key for key in updates if key in allowed]
        if not fields:
            return False
        assignments = ", ".join(f"{field} = ?" for field in fields)
        values = [int(updates[field]) if field in {"resolved", "pinned"} else updates[field] for field in fields]
        values.append(lesson_id)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(f"UPDATE lessons SET {assignments} WHERE id = ?", values)
            conn.commit()
            return cur.rowcount > 0

    def delete_lesson(self, lesson_id: str) -> bool:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
            conn.commit()
            return cur.rowcount > 0

    def export_json(self) -> dict[str, Any]:
        return {
            "lessons": self.list_lessons(limit=1000),
            "exported_at": datetime.now().isoformat(),
        }


lessons_db = LessonsLearnedDB()
