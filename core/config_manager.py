"""core/config_manager.py — Configuration hot reload and management system.

This module implements:
- Configuration fingerprinting
- Change detection
- Hot reload for providers and web_food
- Safe configuration versioning
- Environment variable monitoring

Architecture:
    Configuration State
        ↓
    Fingerprint Calculation
        ↓
    Change Detection
        ↓
    Selective Reload
        ↓
    Version Update
"""

from __future__ import annotations

import os
import hashlib
import logging
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ConfigVersion:
    """Represents a version of the configuration."""
    version_id: str
    timestamp: float
    provider_fingerprint: str
    web_food_fingerprint: str
    env_fingerprint: str
    changes: List[str] = field(default_factory=list)


class ConfigManager:
    """Configuration manager with hot reload support."""
    
    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        
        # Current configuration state
        self._current_version: Optional[ConfigVersion] = None
        self._provider_fingerprint: str = ""
        self._web_food_fingerprint: str = ""
        self._env_fingerprint: str = ""
        
        # Version history
        self._version_history: List[ConfigVersion] = []
        self._max_history_size = 10
        
        # Change callbacks
        self._change_callbacks: List[Callable[[List[str]], None]] = []
        
        # Background monitoring
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Initial fingerprint calculation
        self._calculate_fingerprints()
        self._create_initial_version()
    
    def _calculate_env_fingerprint(self) -> str:
        """Calculate fingerprint of environment variables."""
        env_vars = [
            "GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
            "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "DEEPSEEK_API_KEY",
            "XAI_API_KEY", "CEREBRAS_API_KEY", "NVIDIA_API_KEY",
            "OLLAMA_BASE_URL", "OLLAMA_MODEL",
            "NASA_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
        ]
        
        fingerprint_data = []
        for var in sorted(env_vars):
            value = os.getenv(var, "")
            if value:
                # Hash the value to avoid storing actual keys
                hashed = hashlib.sha256(value.encode()).hexdigest()[:8]
                fingerprint_data.append(f"{var}:{hashed}")
            else:
                fingerprint_data.append(f"{var}:empty")
        
        fingerprint_str = "|".join(fingerprint_data)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def _calculate_provider_fingerprint(self) -> str:
        """Calculate fingerprint of provider configuration."""
        try:
            from core.provider_registry import provider_registry
            status = provider_registry.get_provider_status()
            
            fingerprint_data = []
            for name, config in sorted(status.items()):
                fingerprint_data.append(
                    f"{name}:{config['enabled']}:{config['priority']}:{config['keys_count']}"
                )
            
            fingerprint_str = "|".join(fingerprint_data)
            return hashlib.sha256(fingerprint_str.encode()).hexdigest()
        except Exception as e:
            logger.error("Error calculating provider fingerprint: %s", e)
            return ""
    
    def _calculate_web_food_fingerprint(self) -> str:
        """Calculate fingerprint of /web_food directory."""
        try:
            from core.web_food_loader import web_food_loader
            docs = web_food_loader.get_document_list()
            
            fingerprint_data = []
            for doc in sorted(docs, key=lambda d: d["path"]):
                fingerprint_data.append(f"{doc['path']}:{doc['hash']}:{doc['size']}")
            
            fingerprint_str = "|".join(fingerprint_data)
            return hashlib.sha256(fingerprint_str.encode()).hexdigest()
        except Exception as e:
            logger.error("Error calculating web_food fingerprint: %s", e)
            return ""
    
    def _calculate_fingerprints(self) -> None:
        """Calculate all configuration fingerprints."""
        self._env_fingerprint = self._calculate_env_fingerprint()
        self._provider_fingerprint = self._calculate_provider_fingerprint()
        self._web_food_fingerprint = self._calculate_web_food_fingerprint()
    
    def _create_initial_version(self) -> None:
        """Create the initial configuration version."""
        self._current_version = ConfigVersion(
            version_id=self._generate_version_id(),
            timestamp=time.time(),
            provider_fingerprint=self._provider_fingerprint,
            web_food_fingerprint=self._web_food_fingerprint,
            env_fingerprint=self._env_fingerprint,
            changes=["initial"],
        )
        self._version_history.append(self._current_version)
    
    def _generate_version_id(self) -> str:
        """Generate a unique version ID."""
        return f"v{int(time.time() * 1000)}"
    
    def detect_changes(self) -> List[str]:
        """Detect configuration changes."""
        changes = []
        
        # Calculate new fingerprints
        old_env_fp = self._env_fingerprint
        old_provider_fp = self._provider_fingerprint
        old_web_food_fp = self._web_food_fingerprint
        
        self._calculate_fingerprints()
        
        # Check for changes
        if self._env_fingerprint != old_env_fp:
            changes.append("environment_variables_changed")
            logger.info("[CONFIG] Environment variables changed")
        
        if self._provider_fingerprint != old_provider_fp:
            changes.append("provider_configuration_changed")
            logger.info("[CONFIG] Provider configuration changed")
        
        if self._web_food_fingerprint != old_web_food_fingerprint:
            changes.append("web_food_changed")
            logger.info("[CONFIG] /web_food directory changed")
        
        return changes
    
    def reload_configuration(self) -> bool:
        """Reload configuration if changes are detected."""
        changes = self.detect_changes()
        
        if not changes:
            return False
        
        logger.info("[CONFIG] Reloading configuration due to changes: %s", changes)
        
        # Reload providers if changed
        if "provider_configuration_changed" in changes or "environment_variables_changed" in changes:
            try:
                from core.provider_registry import provider_registry
                provider_registry.reload_if_changed()
                logger.info("[CONFIG] Provider registry reloaded")
            except Exception as e:
                logger.error("[CONFIG] Error reloading provider registry: %s", e)
        
        # Reload web_food if changed
        if "web_food_changed" in changes:
            try:
                from core.web_food_loader import web_food_loader
                web_food_loader.check_and_reload()
                logger.info("[CONFIG] Web food reloaded")
            except Exception as e:
                logger.error("[CONFIG] Error reloading web food: %s", e)
        
        # Create new version
        new_version = ConfigVersion(
            version_id=self._generate_version_id(),
            timestamp=time.time(),
            provider_fingerprint=self._provider_fingerprint,
            web_food_fingerprint=self._web_food_fingerprint,
            env_fingerprint=self._env_fingerprint,
            changes=changes,
        )
        
        self._current_version = new_version
        self._version_history.append(new_version)
        
        # Trim history
        if len(self._version_history) > self._max_history_size:
            self._version_history = self._version_history[-self._max_history_size:]
        
        # Notify callbacks
        for callback in self._change_callbacks:
            try:
                callback(changes)
            except Exception as e:
                logger.error("[CONFIG] Error in change callback: %s", e)
        
        return True
    
    def register_change_callback(self, callback: Callable[[List[str]], None]) -> None:
        """Register a callback to be called when configuration changes."""
        self._change_callbacks.append(callback)
    
    def start_monitoring(self) -> None:
        """Start background configuration monitoring."""
        if self._monitoring:
            logger.warning("[CONFIG] Monitoring already started")
            return
        
        self._monitoring = True
        self._stop_event.clear()
        
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("[CONFIG] Started configuration monitoring (interval: %.1fs)", self.check_interval)
    
    def stop_monitoring(self) -> None:
        """Stop background configuration monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        
        logger.info("[CONFIG] Stopped configuration monitoring")
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._stop_event.wait(self.check_interval)
                
                if self._stop_event.is_set():
                    break
                
                self.reload_configuration()
                
            except Exception as e:
                logger.error("[CONFIG] Error in monitoring loop: %s", e)
    
    def get_current_version(self) -> Optional[ConfigVersion]:
        """Get the current configuration version."""
        return self._current_version
    
    def get_version_history(self) -> List[ConfigVersion]:
        """Get the version history."""
        return list(self._version_history)
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration manager status."""
        return {
            "monitoring": self._monitoring,
            "check_interval": self.check_interval,
            "current_version": self._current_version.version_id if self._current_version else None,
            "version_count": len(self._version_history),
            "last_check": self._current_version.timestamp if self._current_version else None,
            "fingerprints": {
                "env": self._env_fingerprint[:16] + "...",  # Truncated for security
                "provider": self._provider_fingerprint[:16] + "...",
                "web_food": self._web_food_fingerprint[:16] + "...",
            },
        }
    
    def force_reload(self) -> bool:
        """Force a configuration reload regardless of changes."""
        logger.info("[CONFIG] Force reload requested")
        
        # Reload providers
        try:
            from core.provider_registry import provider_registry
            provider_registry.reload_if_changed()
            logger.info("[CONFIG] Provider registry force reloaded")
        except Exception as e:
            logger.error("[CONFIG] Error force reloading provider registry: %s", e)
        
        # Reload web_food
        try:
            from core.web_food_loader import web_food_loader
            web_food_loader.check_and_reload()
            logger.info("[CONFIG] Web food force reloaded")
        except Exception as e:
            logger.error("[CONFIG] Error force reloading web food: %s", e)
        
        # Create new version
        self._calculate_fingerprints()
        new_version = ConfigVersion(
            version_id=self._generate_version_id(),
            timestamp=time.time(),
            provider_fingerprint=self._provider_fingerprint,
            web_food_fingerprint=self._web_food_fingerprint,
            env_fingerprint=self._env_fingerprint,
            changes=["force_reload"],
        )
        
        self._current_version = new_version
        self._version_history.append(new_version)
        
        return True


# Global instance
config_manager = ConfigManager()
