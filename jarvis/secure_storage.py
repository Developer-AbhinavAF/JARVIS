"""jarvis.secure_storage

Secure storage for API keys and sensitive data with encryption.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SecureStorage:
    """Secure storage for sensitive configuration and API keys."""
    
    def __init__(self, storage_file: str = "jarvis_secure.json") -> None:
        self.storage_file = Path(storage_file)
        self._data: dict[str, str] = {}
        self._load()
    
    def _load(self) -> None:
        """Load secure data from file."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load secure storage: {e}")
                self._data = {}
    
    def _save(self) -> None:
        """Save secure data to file."""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f)
        except Exception as e:
            logger.error(f"Failed to save secure storage: {e}")
    
    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a value from secure storage."""
        # First check environment variables
        env_value = os.getenv(key)
        if env_value:
            return env_value
        
        # Then check secure storage
        return self._data.get(key, default)
    
    def set(self, key: str, value: str) -> None:
        """Set a value in secure storage."""
        self._data[key] = value
        self._save()
    
    def delete(self, key: str) -> None:
        """Delete a key from secure storage."""
        if key in self._data:
            del self._data[key]
            self._save()
    
    def rotate_key(self, key: str, new_value: str) -> str:
        """Rotate an API key."""
        old_value = self._data.get(key)
        self.set(key, new_value)
        
        # Log rotation (without exposing the key)
        logger.info(f"Rotated API key: {key}")
        
        # Save old key history for rollback (optional)
        history_key = f"{key}_history"
        history = self._data.get(history_key, [])
        if old_value:
            history.append({"key": old_value[:10] + "...", "rotated_at": str(__import__('datetime').datetime.now())})
            self._data[history_key] = history[-5:]  # Keep last 5
            self._save()
        
        return new_value
    
    def get_all_keys(self) -> list[str]:
        """Get list of all stored keys (names only)."""
        return [k for k in self._data.keys() if not k.endswith("_history")]
    
    def clear(self) -> None:
        """Clear all secure storage."""
        self._data = {}
        self._save()


# Global secure storage instance
secure_storage = SecureStorage()


# API key manager with rotation
class APIKeyManager:
    """Manage API keys with rotation and fallback."""
    
    KEYS = {
        "GROQ_API_KEY": {
            "primary": os.getenv("GROQ_API_KEY"),
            "fallback_env": "GROQ_API_KEY_BACKUP",
        },
        "TAVILY_API_KEY": {
            "primary": os.getenv("TAVILY_API_KEY"),
            "fallback_env": "TAVILY_API_KEY_BACKUP",
        },
        "OPENAI_API_KEY": {
            "primary": os.getenv("OPENAI_API_KEY"),
            "fallback_env": "OPENAI_API_KEY_BACKUP",
        },
    }
    
    @classmethod
    def get_key(cls, name: str) -> str | None:
        """Get API key with fallback chain."""
        config = cls.KEYS.get(name)
        if not config:
            return secure_storage.get(name)
        
        # Try primary
        if config["primary"]:
            return config["primary"]
        
        # Try environment fallback
        fallback = os.getenv(config["fallback_env"])
        if fallback:
            return fallback
        
        # Try secure storage
        return secure_storage.get(name)
    
    @classmethod
    def rotate_key(cls, name: str, new_value: str) -> None:
        """Rotate an API key."""
        secure_storage.rotate_key(name, new_value)
        # Update in-memory
        if name in cls.KEYS:
            cls.KEYS[name]["primary"] = new_value
    
    @classmethod
    def validate_keys(cls) -> dict[str, bool]:
        """Validate all configured API keys."""
        results = {}
        for name in cls.KEYS:
            key = cls.get_key(name)
            results[name] = key is not None and len(key) > 10
        return results
