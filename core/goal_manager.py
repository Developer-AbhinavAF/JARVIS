"""core/goal_manager.py — Goal & Project Manager for JARVIS vNext++.

Tracks and prioritizes long-term, short-term, daily, and project goals.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class Goal:
    id: str
    title: str
    category: str = "daily"  # long_term, short_term, daily, weekly
    priority: int = 1
    progress: float = 0.0  # 0.0 to 1.0
    completed: bool = False
    dependencies: List[str] = field(default_factory=list)


class GoalManager:
    """Manages active user and system goals."""

    def __init__(self, storage_dir: str = "memory"):
        self.storage_file = Path(storage_dir) / "goals.json"
        self._goals: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self._goals = json.load(f)
            except Exception:
                self._goals = []
        else:
            self._goals = [
                asdict(Goal(id="g1", title="Build JARVIS AGI OS", category="long_term", priority=1)),
                asdict(Goal(id="g2", title="Optimize low-end hardware latency", category="short_term", priority=1)),
            ]
            self._save()

    def _save(self) -> None:
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self._goals, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving goals: {e}")

    def add_goal(self, title: str, category: str = "daily", priority: int = 1) -> Goal:
        gid = f"g_{len(self._goals)+1}"
        goal = Goal(id=gid, title=title, category=category, priority=priority)
        self._goals.append(asdict(goal))
        self._save()
        return goal

    def get_active_goals(self) -> List[Dict[str, Any]]:
        return [g for g in self._goals if not g.get("completed")]

    def get_summary(self) -> str:
        active = self.get_active_goals()
        if not active:
            return "No active goals."
        return f"Active Goal: {active[0]['title']}"


goal_manager = GoalManager()
