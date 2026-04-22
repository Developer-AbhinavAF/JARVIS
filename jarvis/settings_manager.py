"""jarvis.settings_manager

Configuration management with validation, backup, import/export.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class UserSettings:
    """User configurable settings."""
    # Voice settings
    wake_word: str = "hello"
    tts_rate: int = 175
    tts_volume: float = 1.0
    stt_energy_threshold: int = 300
    stt_pause_threshold: float = 0.5
    
    # LLM settings
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    
    # System settings
    startup_with_windows: bool = False
    minimize_to_tray: bool = True
    dark_mode: bool = True
    
    # Feature toggles
    enable_voice: bool = True
    enable_dashboard: bool = True
    enable_memory: bool = True
    
    # User preferences
    user_name: str = ""
    preferred_language: str = "en"
    timezone: str = "UTC"
    
    # Advanced
    auto_update: bool = True
    debug_mode: bool = False
    log_level: str = "INFO"


class SettingsValidator:
    """Validate settings values."""
    
    @staticmethod
    def validate_wake_word(value: str) -> tuple[bool, str]:
        if not value or len(value) < 2:
            return False, "Wake word must be at least 2 characters"
        if len(value) > 20:
            return False, "Wake word too long (max 20)"
        return True, "OK"
    
    @staticmethod
    def validate_tts_rate(value: int) -> tuple[bool, str]:
        if not 50 <= value <= 300:
            return False, "TTS rate must be between 50 and 300"
        return True, "OK"
    
    @staticmethod
    def validate_volume(value: float) -> tuple[bool, str]:
        if not 0.0 <= value <= 1.0:
            return False, "Volume must be between 0.0 and 1.0"
        return True, "OK"
    
    @staticmethod
    def validate_temperature(value: float) -> tuple[bool, str]:
        if not 0.0 <= value <= 2.0:
            return False, "Temperature must be between 0.0 and 2.0"
        return True, "OK"


class SettingsManager:
    """Manage user settings with backup and validation."""
    
    SETTINGS_FILE = "jarvis_settings.json"
    BACKUP_DIR = "jarvis_backups"
    MAX_BACKUPS = 10
    
    def __init__(self) -> None:
        self.settings = UserSettings()
        self.validators: dict[str, Callable[[Any], tuple[bool, str]]] = {
            "wake_word": SettingsValidator.validate_wake_word,
            "tts_rate": SettingsValidator.validate_tts_rate,
            "tts_volume": SettingsValidator.validate_volume,
            "llm_temperature": SettingsValidator.validate_temperature,
        }
        self.change_callbacks: list[Callable[[str, Any], None]] = []
        self._load()
        self._auto_backup()
    
    def _get_settings_path(self) -> Path:
        """Get path to settings file."""
        return Path(self.SETTINGS_FILE)
    
    def _load(self) -> None:
        """Load settings from file."""
        path = self._get_settings_path()
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Update settings from loaded data
                    for key, value in data.items():
                        if hasattr(self.settings, key):
                            setattr(self.settings, key, value)
                logger.info("Settings loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
    
    def save(self) -> bool:
        """Save settings to file."""
        try:
            path = self._get_settings_path()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.settings), f, indent=2)
            logger.info("Settings saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return getattr(self.settings, key, default)
    
    def set(self, key: str, value: Any) -> tuple[bool, str]:
        """Set a setting value with validation."""
        # Validate if validator exists
        if key in self.validators:
            is_valid, message = self.validators[key](value)
            if not is_valid:
                return False, message
        
        # Set the value
        if hasattr(self.settings, key):
            old_value = getattr(self.settings, key)
            setattr(self.settings, key, value)
            
            # Save to file
            if self.save():
                # Notify callbacks
                for callback in self.change_callbacks:
                    try:
                        callback(key, value)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                # Auto backup on significant changes
                if old_value != value:
                    self._auto_backup()
                
                return True, "OK"
            return False, "Failed to save"
        
        return False, f"Unknown setting: {key}"
    
    def _auto_backup(self) -> None:
        """Create automatic backup."""
        try:
            backup_dir = Path(self.BACKUP_DIR)
            backup_dir.mkdir(exist_ok=True)
            
            # Create timestamped backup
            timestamp = int(time.time())
            backup_file = backup_dir / f"settings_backup_{timestamp}.json"
            
            shutil.copy(self._get_settings_path(), backup_file)
            
            # Clean old backups
            backups = sorted(backup_dir.glob("settings_backup_*.json"))
            if len(backups) > self.MAX_BACKUPS:
                for old_backup in backups[:-self.MAX_BACKUPS]:
                    old_backup.unlink()
                    
            logger.info(f"Settings backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Backup failed: {e}")
    
    def list_backups(self) -> list[Path]:
        """List available backups."""
        backup_dir = Path(self.BACKUP_DIR)
        if not backup_dir.exists():
            return []
        return sorted(backup_dir.glob("settings_backup_*.json"))
    
    def restore_backup(self, backup_file: Path) -> bool:
        """Restore settings from backup."""
        try:
            if backup_file.exists():
                shutil.copy(backup_file, self._get_settings_path())
                self._load()
                logger.info(f"Settings restored from {backup_file}")
                return True
            return False
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def export_settings(self, export_path: str) -> bool:
        """Export settings to a file."""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.settings), f, indent=2)
            logger.info(f"Settings exported to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def import_settings(self, import_path: str) -> bool:
        """Import settings from a file."""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Backup current before importing
            self._auto_backup()
            
            # Update settings
            for key, value in data.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
            
            self.save()
            logger.info(f"Settings imported from {import_path}")
            return True
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False
    
    def on_change(self, callback: Callable[[str, Any], None]) -> None:
        """Register a callback for setting changes."""
        self.change_callbacks.append(callback)
    
    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults."""
        try:
            self._auto_backup()  # Backup current
            self.settings = UserSettings()
            return self.save()
        except Exception as e:
            logger.error(f"Reset failed: {e}")
            return False


# Global settings manager
settings = SettingsManager()
