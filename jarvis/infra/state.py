"""State Manager — Centralized application state.

The entire AI should know its current state.
Thread-safe, observable, event-driven.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

from .events import EventBus, EventType, event_bus

logger = logging.getLogger(__name__)


class StateManager:
    """Manages global application state with change notifications.

    Usage:
        state = StateManager()
        state.set("current_user", "abhin")
        user = state.get("current_user")
        all_state = state.snapshot()
    """

    def __init__(self, bus: EventBus | None = None):
        self._state: dict[str, Any] = {}
        self._history: dict[str, list[tuple[float, Any]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._bus = bus or event_bus
        self._max_history = 50

        # Initialize default state
        self._state = {
            "current_user": "default",
            "current_project": "",
            "current_conversation": "",
            "current_task": "",
            "current_window": "",
            "current_agent": "",
            "current_memory": "",
            "current_theme": "dark",
            "current_voice": "default",
            "current_environment": "desktop",
            "app_ready": False,
            "boot_progress": 0.0,
            "boot_phase": "",
            "performance_mode": "balanced",
            "developer_mode": False,
        }

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any, notify: bool = True):
        with self._lock:
            old = self._state.get(key)
            self._state[key] = value
            self._history[key].append((time.time(), value))
            if len(self._history[key]) > self._max_history:
                self._history[key] = self._history[key][-self._max_history:]

        if notify and old != value:
            self._bus.emit(EventType.SETTINGS_CHANGED, source=f"state:{key}", data={
                "key": key, "old": old, "new": value,
            })

    def get_many(self, *keys: str) -> dict[str, Any]:
        with self._lock:
            return {k: self._state.get(k) for k in keys}

    def set_many(self, values: dict[str, Any], notify: bool = True):
        for k, v in values.items():
            self.set(k, v, notify=notify)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def get_history(self, key: str, limit: int = 10) -> list[tuple[float, Any]]:
        with self._lock:
            return list(self._history.get(key, []))[-limit:]

    def reset(self, key: str):
        defaults = {
            "current_user": "default", "current_project": "", "current_conversation": "",
            "current_task": "", "current_window": "", "current_agent": "",
            "current_memory": "", "current_theme": "dark", "current_voice": "default",
            "current_environment": "desktop", "app_ready": False,
            "boot_progress": 0.0, "boot_phase": "", "performance_mode": "balanced",
            "developer_mode": False,
        }
        if key in defaults:
            self.set(key, defaults[key])

    def reset_all(self):
        with self._lock:
            self._state.clear()
            self._history.clear()
        # Re-initialize defaults
        self.set("current_user", "default")
        self.set("current_theme", "dark")

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "keys": len(self._state),
                "history_entries": sum(len(v) for v in self._history.values()),
            }


# Global instance
state_manager = StateManager()

__all__ = ["StateManager", "state_manager"]
