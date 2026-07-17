"""Settings Storage — Persistent settings that survive restarts.

Theme, voice, preferences, performance settings — all persisted as JSON.
"""

from __future__ import annotations

import os
import json
import logging
import threading
from typing import Any
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_DEFAULT_SETTINGS: dict[str, Any] = {
    # UI
    "theme": "dark",
    "accent_color": "#6C5CE7",
    "font_family": "Segoe UI",
    "font_size": 14,
    "background_image": "",
    "background_video": "",
    # Voice
    "voice_provider": "elevenlabs",
    "voice_id": "default",
    "speech_rate": 1.0,
    "auto_speak": False,
    # Performance
    "performance_mode": "balanced",
    "developer_mode": False,
    "vision_enabled": True,
    "learning_enabled": True,
    # Memory
    "memory_compression": True,
    "memory_retention_days": 30,
    "auto_forget_sensitive": True,
    # Router
    "default_provider": "",
    "default_model": "",
    "auto_fallback": True,
}


class SettingsStorage:
    """Persistent JSON settings store.

    Usage:
        settings = SettingsStorage()
        settings.set("theme", "light")
        theme = settings.get("theme")
        settings.save()
    """

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else Path.home() / ".jarvis" / "settings.json"
        self._settings: dict[str, Any] = dict(_DEFAULT_SETTINGS)
        self._lock = threading.Lock()
        self._callbacks: list = []
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value: Any, save: bool = False):
        with self._lock:
            old = self._settings.get(key)
            self._settings[key] = value
        for cb in self._callbacks:
            try:
                cb(key, old, value)
            except Exception:
                pass
        if save:
            self.save()

    def get_many(self, *keys: str) -> dict[str, Any]:
        with self._lock:
            return {k: self._settings.get(k) for k in keys}

    def set_many(self, values: dict[str, Any], save: bool = False):
        for k, v in values.items():
            self.set(k, v)
        if save:
            self.save()

    def all(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._settings)

    def reset(self, key: str):
        if key in _DEFAULT_SETTINGS:
            self.set(key, _DEFAULT_SETTINGS[key])

    def reset_all(self):
        with self._lock:
            self._settings = dict(_DEFAULT_SETTINGS)

    def on_change(self, callback):
        self._callbacks.append(callback)

    def load(self):
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with self._lock:
                    self._settings.update(data)
                logger.info("Settings loaded from %s", self._path)
        except Exception as e:
            logger.warning("Settings load error: %s", e)

    def save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                data = dict(self._settings)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Settings save error: %s", e)

    def get_path(self) -> str:
        return str(self._path)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "path": str(self._path),
                "exists": self._path.exists(),
                "keys": len(self._settings),
            }


# Global instance
settings_storage = SettingsStorage()

__all__ = ["SettingsStorage", "settings_storage", "_DEFAULT_SETTINGS"]
