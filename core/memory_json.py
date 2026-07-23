"""memory_json — JSON-based persistent memory system.

Implements the required memory files with an in-memory cache for fast reads:
- memories.json: User facts (name, age, dream, interests)
- mistakes.json: Learning from corrections
- knowledge.json: Document storage
- conversation_history.json: Full conversation log
"""

from __future__ import annotations

import os
import json
import time
import logging
from pathlib import Path
from typing import Any
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class JSONMemoryStore:
    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        self._memories_file = self._data_dir / "memories.json"
        self._mistakes_file = self._data_dir / "mistakes.json"
        self._knowledge_file = self._data_dir / "knowledge.json"
        self._conversation_file = self._data_dir / "conversation_history.json"
        
        self._memories_cache: dict[str, dict] = {}
        self._init_files()
        self._load_cache()

    def _init_files(self) -> None:
        """Initialize JSON files if they don't exist."""
        for file_path in [self._memories_file, self._mistakes_file, self._knowledge_file, self._conversation_file]:
            if not file_path.exists():
                file_path.write_text("{}", encoding="utf-8")
        if not self._conversation_file.exists() or self._conversation_file.read_text().strip() == "{}":
             self._conversation_file.write_text("[]", encoding="utf-8")

    def _load_cache(self) -> None:
        """Load memories into memory for fast read."""
        self._memories_cache = self._load_json(self._memories_file)

    def _load_json(self, file_path: Path) -> dict | list:
        """Load JSON file safely."""
        try:
            if file_path.exists():
                return json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load {file_path}: {e}")
        return {}

    def _save_json(self, file_path: Path, data: dict | list) -> bool:
        """Save JSON file safely."""
        try:
            file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to save {file_path}: {e}")
            return False

    # --- Memories (User Facts) ---

    def save_memory(self, key: str, value: str, confidence: float = 0.95) -> bool:
        """Save a user fact to memory."""
        self._memories_cache[key] = {
            "value": value,
            "confidence": confidence,
            "updated_at": datetime.now().isoformat(),
            "access_count": self._memories_cache.get(key, {}).get("access_count", 0),
        }
        return self._save_json(self._memories_file, self._memories_cache)

    def get_memory(self, key: str) -> dict[str, Any] | None:
        """Get a specific memory."""
        if key in self._memories_cache:
            # Update access count
            self._memories_cache[key]["access_count"] = self._memories_cache[key].get("access_count", 0) + 1
            self._memories_cache[key]["last_accessed"] = datetime.now().isoformat()
            # Fire and forget save, don't strictly block on access count update
            self._save_json(self._memories_file, self._memories_cache)
            return self._memories_cache[key]
        return None

    def get_all_memories(self) -> dict[str, Any]:
        """Get all user memories."""
        return self._memories_cache.copy()
        
    def get_profile(self) -> str:
        """Return a formatted string of all user facts for prompt injection."""
        if not self._memories_cache:
            return "No profile data stored."
        lines = []
        for k, v in self._memories_cache.items():
            lines.append(f"{k}: {v.get('value', '')}")
        return "\n".join(lines)

    def delete_memory(self, key: str) -> bool:
        """Delete a specific memory."""
        if key in self._memories_cache:
            del self._memories_cache[key]
            return self._save_json(self._memories_file, self._memories_cache)
        return False

    def search_memories(self, query: str) -> list[dict[str, Any]]:
        """Search memories by key or value."""
        query_lower = query.lower()
        results = []
        for key, data in self._memories_cache.items():
            if query_lower in key.lower() or query_lower in str(data.get("value", "")).lower():
                results.append({"key": key, **data})
        return results

    # --- Mistakes (Learning from Corrections) ---

    def record_mistake(self, input_text: str, expected: str, actual: str) -> bool:
        mistakes = self._load_json(self._mistakes_file)
        if not isinstance(mistakes, dict):
             mistakes = {}
        
        mistake_id = f"mistake_{int(time.time() * 1000)}"
        mistakes[mistake_id] = {
            "input": input_text,
            "expected": expected,
            "actual": actual,
            "timestamp": datetime.now().isoformat(),
            "learned": False,
        }
        
        return self._save_json(self._mistakes_file, mistakes)

    def get_mistakes(self, limit: int = 20) -> list[dict[str, Any]]:
        mistakes = self._load_json(self._mistakes_file)
        if not isinstance(mistakes, dict): return []
        mistake_list = [{"id": k, **v} for k, v in mistakes.items()]
        mistake_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return mistake_list[:limit]

    def mark_mistake_learned(self, mistake_id: str) -> bool:
        mistakes = self._load_json(self._mistakes_file)
        if isinstance(mistakes, dict) and mistake_id in mistakes:
            mistakes[mistake_id]["learned"] = True
            mistakes[mistake_id]["learned_at"] = datetime.now().isoformat()
            return self._save_json(self._mistakes_file, mistakes)
        return False

    # --- Knowledge (Document Storage) ---

    def add_knowledge(self, content: str, source: str = "", metadata: dict[str, Any] | None = None) -> str:
        knowledge = self._load_json(self._knowledge_file)
        if not isinstance(knowledge, dict): knowledge = {}
        
        entry_id = f"knowledge_{int(time.time() * 1000)}"
        knowledge[entry_id] = {
            "content": content,
            "source": source,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        
        self._save_json(self._knowledge_file, knowledge)
        return entry_id

    def search_knowledge(self, query: str) -> list[dict[str, Any]]:
        knowledge = self._load_json(self._knowledge_file)
        if not isinstance(knowledge, dict): return []
        query_lower = query.lower()
        
        results = []
        for entry_id, data in knowledge.items():
            content = data.get("content", "")
            if query_lower in content.lower():
                results.append({"id": entry_id, **data})
        return results

    def get_knowledge(self, entry_id: str) -> dict[str, Any] | None:
        knowledge = self._load_json(self._knowledge_file)
        if isinstance(knowledge, dict):
            return knowledge.get(entry_id)
        return None

    # --- Conversation History ---

    def add_conversation_entry(self, role: str, content: str, intent: str = "", tool: str = "") -> bool:
        history = self._load_json(self._conversation_file)
        if not isinstance(history, list):
            history = []
        
        entry = {
            "role": role,
            "content": content,
            "intent": intent,
            "tool": tool,
            "timestamp": datetime.now().isoformat(),
        }
        
        history.append(entry)
        if len(history) > 100:
            history = history[-100:]
        
        return self._save_json(self._conversation_file, history)

    def get_conversation_history(self, limit: int = 20) -> list[dict[str, Any]]:
        history = self._load_json(self._conversation_file)
        if not isinstance(history, list):
            history = []
        return history[-limit:] if history else []

    def get_recent_context(self, n: int = 3) -> str:
        history = self.get_conversation_history(n)
        lines = []
        for entry in history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            if content:
                lines.append(f"{role.title()}: {content}")
        return "\n".join(lines)

    def clear_conversation_history(self) -> bool:
        return self._save_json(self._conversation_file, [])


# Singleton instance
json_memory = JSONMemoryStore()
