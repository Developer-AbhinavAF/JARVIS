import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SpeechSettings:
    def __init__(self):
        self.settings_file = Path(__file__).parent / "settings.json"
        self._default_settings = {
            "provider": "veena",
            "voice": "agastya",
            "speech": True,
            "cache": True,
            "interrupt": True,
            "veena_model": "maya-research/Veena",
            "snac_model": "hubertsiuzdak/snac_24khz"
        }
        self.settings = self.load()

    def load(self):
        if not self.settings_file.exists():
            self.save(self._default_settings)
            return self._default_settings.copy()
        
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged = self._default_settings.copy()
                merged.update(data)
                # Force voice to agastya as per requirements
                merged["voice"] = "agastya"
                return merged
        except Exception as e:
            logger.error(f"Error loading speech settings: {e}")
            return self._default_settings.copy()

    def save(self, data=None):
        if data is not None:
            self.settings = data
        
        # Enforce permanent voice
        self.settings["voice"] = "agastya"
        
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving speech settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

settings = SpeechSettings()
