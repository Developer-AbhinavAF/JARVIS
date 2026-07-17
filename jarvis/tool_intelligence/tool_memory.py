"""Tool Memory System for JARVIS.

Remembers:
- Frequently opened apps
- Frequently opened websites
- Frequently used commands
- Favorite directories
- Favorite projects
- Recent files
- Recent downloads
- Recent searches

Improves execution speed by remembering patterns.
"""

from __future__ import annotations

import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
from collections import Counter

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_MEMORY_FILE = _DATA_DIR / "tool_memory.json"


# ════════════════════════════════════════════════════════════════════
# MEMORY ENTRY
# ════════════════════════════════════════════════════════════════════

@dataclass
class MemoryEntry:
    """A single memory entry."""
    key: str = ""
    category: str = ""        # "app", "website", "command", "directory", "project", "file", "search"
    value: str = ""
    use_count: int = 0
    last_used: float = 0.0
    first_used: float = 0.0
    avg_frequency: float = 0.0  # Uses per day
    metadata: dict = field(default_factory=dict)

    def record_use(self) -> None:
        now = time.time()
        self.use_count += 1
        self.last_used = now
        if self.first_used == 0:
            self.first_used = now
        # Calculate average frequency (uses per day)
        days = max((now - self.first_used) / 86400, 0.01)
        self.avg_frequency = self.use_count / days

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "category": self.category,
            "value": self.value,
            "use_count": self.use_count,
            "last_used": self.last_used,
            "avg_frequency": round(self.avg_frequency, 4),
        }


# ════════════════════════════════════════════════════════════════════
# TOOL MEMORY SYSTEM
# ════════════════════════════════════════════════════════════════════

class ToolMemory:
    """Remembers frequently used tools, apps, websites, and patterns.

    Improves execution speed by predicting what the user wants.
    """

    def __init__(self, max_entries: int = 500) -> None:
        self._entries: dict[str, MemoryEntry] = {}
        self._max_entries = max_entries
        self._load()

    def record(
        self,
        category: str,
        value: str,
        metadata: dict | None = None,
    ) -> None:
        """Record a tool usage."""
        key = f"{category}:{value.lower().strip()}"
        if key not in self._entries:
            self._entries[key] = MemoryEntry(
                key=key, category=category, value=value,
            )
        entry = self._entries[key]
        entry.record_use()
        if metadata:
            entry.metadata.update(metadata)

        # Evict if over limit
        if len(self._entries) > self._max_entries:
            self._evict()

    def record_app(self, app_name: str) -> None:
        """Record an app being opened."""
        self.record("app", app_name)

    def record_website(self, url: str) -> None:
        """Record a website being opened."""
        self.record("website", url)

    def record_search(self, query: str) -> None:
        """Record a search query."""
        self.record("search", query)

    def record_command(self, command: str) -> None:
        """Record a terminal command."""
        self.record("command", command)

    def record_directory(self, path: str) -> None:
        """Record a directory being accessed."""
        self.record("directory", path)

    def record_project(self, project: str) -> None:
        """Record a project being worked on."""
        self.record("project", project)

    def record_file(self, file_path: str) -> None:
        """Record a file being accessed."""
        self.record("file", file_path)

    def record_download(self, file_path: str) -> None:
        """Record a download."""
        self.record("download", file_path)

    def get_frequent(self, category: str, limit: int = 10) -> list[MemoryEntry]:
        """Get most frequently used items in a category."""
        entries = [e for e in self._entries.values() if e.category == category]
        return sorted(entries, key=lambda e: e.use_count, reverse=True)[:limit]

    def get_recent(self, category: str, limit: int = 10) -> list[MemoryEntry]:
        """Get most recently used items in a category."""
        entries = [e for e in self._entries.values() if e.category == category]
        return sorted(entries, key=lambda e: e.last_used, reverse=True)[:limit]

    def get_popular(self, category: str, limit: int = 10) -> list[MemoryEntry]:
        """Get most popular items (by frequency) in a category."""
        entries = [e for e in self._entries.values() if e.category == category]
        return sorted(entries, key=lambda e: e.avg_frequency, reverse=True)[:limit]

    def predict(self, category: str, context: dict | None = None) -> str | None:
        """Predict what the user wants based on memory."""
        popular = self.get_popular(category, limit=5)
        if not popular:
            return None

        # Simple prediction: most frequent item
        return popular[0].value

    def get_all_categories(self) -> dict[str, int]:
        """Get count of entries per category."""
        counts: dict[str, int] = {}
        for entry in self._entries.values():
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "total_entries": len(self._entries),
            "categories": self.get_all_categories(),
            "total_uses": sum(e.use_count for e in self._entries.values()),
        }

    def _evict(self) -> None:
        """Remove least useful entries."""
        if len(self._entries) <= self._max_entries:
            return
        # Sort by use_count * avg_frequency (importance score)
        entries = sorted(
            self._entries.values(),
            key=lambda e: e.use_count * max(e.avg_frequency, 0.01),
        )
        # Remove bottom 10%
        to_remove = len(self._entries) - int(self._max_entries * 0.9)
        for entry in entries[:to_remove]:
            del self._entries[entry.key]

    def _save(self) -> None:
        """Save memory to disk."""
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "entries": {k: v.to_dict() for k, v in self._entries.items()},
                "saved_at": time.time(),
            }
            _MEMORY_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("Failed to save tool memory: %s", e)

    def _load(self) -> None:
        """Load memory from disk."""
        try:
            if _MEMORY_FILE.exists():
                data = json.loads(_MEMORY_FILE.read_text())
                for key, entry_data in data.get("entries", {}).items():
                    entry = MemoryEntry(
                        key=entry_data["key"],
                        category=entry_data["category"],
                        value=entry_data["value"],
                        use_count=entry_data.get("use_count", 0),
                        last_used=entry_data.get("last_used", 0),
                        avg_frequency=entry_data.get("avg_frequency", 0),
                    )
                    self._entries[key] = entry
        except Exception as e:
            logger.debug("Failed to load tool memory: %s", e)

    def save(self) -> None:
        """Public save method."""
        self._save()


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

tool_memory = ToolMemory()
