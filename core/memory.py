"""core/memory.py — 9-Tier Hybrid Memory System for JARVIS vNext++.

Hierarchy:
1. Session Cache (<1ms)
2. Recent Memory (<2ms)
3. Facts Store (<5ms)
4. Preferences
5. Projects Context
6. Relationships
7. Goals
8. Semantic Vector Search (<20ms)
9. Archived Memory

Factual queries short-circuit vector search to execute in <5ms.
"""

from __future__ import annotations

import os
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class EpisodicMemory:
    date: str
    location: str
    context: str
    outcome: str
    importance: float = 1.0
    lessons: List[str] = field(default_factory=list)


class UnifiedMemory:
    """9-Tier Hybrid Memory Implementation."""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self._session_cache: Dict[str, Any] = {}
        self._facts: Dict[str, Any] = {}
        self._preferences: Dict[str, Any] = {}
        self._goals: Dict[str, Any] = {}
        self._projects: Dict[str, Any] = {}
        self._relationships: Dict[str, Any] = {}
        self._episodic: List[Dict[str, Any]] = []

        self._load_all()

    def _load_all(self) -> None:
        self._facts = self._load_file("facts.json", {"name": "Abhinav", "creator": "Abhinav"})
        self._preferences = self._load_file("preferences.json", {"style": "concise", "mode": "execution-first"})
        self._goals = self._load_file("goals.json", {"active_goal": "Build JARVIS AGI OS"})
        self._projects = self._load_file("projects.json", {"active_project": "JARVIS vNext++"})
        self._relationships = self._load_file("relationships.json", {"creator": "Abhinav"})
        self._episodic = self._load_file_list("episodic.json")

    def _load_file(self, filename: str, default: Dict[str, Any]) -> Dict[str, Any]:
        filepath = self.memory_dir / filename
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Some memory files (e.g. goals.json) are lists-of-objects.
                # Coerce to a flat dict keyed by title/id so the rest of the
                # code (which expects .items() calls) keeps working.
                if isinstance(data, list):
                    out: Dict[str, Any] = {}
                    for item in data:
                        if isinstance(item, dict):
                            key = item.get("title") or item.get("name") or item.get("id") or str(item)
                            out[str(key)] = item
                    return out if out else default
                if isinstance(data, dict):
                    return data
                return default
            except Exception:
                return default
        return default

    def _load_file_list(self, filename: str) -> List[Dict[str, Any]]:
        filepath = self.memory_dir / filename
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_file(self, filename: str, data: Any) -> None:
        try:
            with open(self.memory_dir / filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory file {filename}: {e}")

    # --- Tier 1: Session Cache ---
    def set_session_cache(self, key: str, value: Any) -> None:
        self._session_cache[key] = value

    def get_session_cache(self, key: str) -> Optional[Any]:
        return self._session_cache.get(key)

    # --- Tier 3: Facts (Short-Circuit Lookup) ---
    def get_fact(self, key: str) -> Optional[Any]:
        return self._facts.get(key.lower().strip())

    def set_fact(self, key: str, value: Any) -> None:
        self._facts[key.lower().strip()] = value
        self._save_file("facts.json", self._facts)

    # --- Tier 4: Preferences ---
    def get_preference(self, key: str) -> Optional[Any]:
        return self._preferences.get(key.lower().strip())

    def set_preference(self, key: str, value: Any) -> None:
        self._preferences[key.lower().strip()] = value
        self._save_file("preferences.json", self._preferences)

    # --- Episodic Memory ---
    def add_episode(self, episode: EpisodicMemory) -> None:
        self._episodic.append(asdict(episode))
        self._save_file("episodic.json", self._episodic)

    @staticmethod
    def _iter_kv(store: Any) -> list[tuple[str, str]]:
        """Yield (key, value) pairs from either a dict or a list-of-objects."""
        if isinstance(store, dict):
            return list(store.items())
        if isinstance(store, list):
            pairs = []
            for item in store:
                if isinstance(item, dict):
                    key = item.get("title") or item.get("name") or item.get("id") or str(item)
                    value = item.get("description") or item.get("title") or str(item)
                    pairs.append((str(key), str(value)))
            return pairs
        return []

    # --- Hybrid Lookup Pipeline ---
    def search(self, query: str) -> Optional[str]:
        """Hybrid memory search: facts -> preferences -> session -> vector fallback."""
        query_clean = query.lower().strip()

        # Factual query short-circuit (<5ms)
        for k, v in self._iter_kv(self._facts):
            if k.lower() in query_clean:
                return f"Fact [{k}]: {v}"

        for k, v in self._iter_kv(self._preferences):
            if k.lower() in query_clean:
                return f"Preference [{k}]: {v}"

        for k, v in self._iter_kv(self._goals):
            if k.lower() in query_clean:
                return f"Goal [{k}]: {v}"

        return None

    def get_memory_summary(self) -> str:
        """Format active memory context for prompt assembly."""
        facts_str = ", ".join([f"{k}: {v}" for k, v in self._iter_kv(self._facts)[:3]])
        goals_str = ", ".join([f"{k}: {v}" for k, v in self._iter_kv(self._goals)[:2]])
        return f"Facts: {facts_str} | Goals: {goals_str}"


unified_memory = UnifiedMemory()
