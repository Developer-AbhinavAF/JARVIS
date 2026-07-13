from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SecureStorage:
    def __init__(self, storage_file: str = "jarvis_secure.json") -> None:
        self.storage_file = Path(storage_file)
        self._data: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load secure storage: {e}")
                self._data = {}

    def _save(self) -> None:
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f)
        except Exception as e:
            logger.error(f"Failed to save secure storage: {e}")

    def get(self, key: str, default: str | None = None) -> str | None:
        env_value = os.getenv(key)
        if env_value:
            return env_value
        return self._data.get(key, default)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._save()

    def clear(self) -> None:
        self._data = {}
        self._save()


secure_storage = SecureStorage()


class APIKeyManager:
    @classmethod
    def get_key(cls, name: str) -> str | None:
        return secure_storage.get(name)

    @classmethod
    def validate_keys(cls) -> dict[str, bool]:
        return {}
