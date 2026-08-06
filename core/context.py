"""context — Unified context system for all JARVIS interfaces.

Consolidates SessionContext from execution_first and ContextEngine
into a single shared context system used by CLI, Web, and Speech.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from collections import deque

from core.cache import get_cache

logger = logging.getLogger(__name__)


@dataclass
class ContextEntity:
    """Represents an entity mentioned in conversation."""
    name: str
    entity_type: str  # app, website, person, file, etc.
    mentions: int = 1
    last_mentioned: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def touch(self) -> None:
        """Update last mentioned time."""
        self.last_mentioned = time.time()
        self.mentions += 1


@dataclass
class ContextWindow:
    """Represents a single context window (conversation turn)."""
    user_input: str
    intent: str = ""
    tool: str = ""
    entities: List[ContextEntity] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_input": self.user_input,
            "intent": self.intent,
            "tool": self.tool,
            "entities": [asdict(e) for e in self.entities],
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class SessionContext:
    """Current session context state."""
    current_browser: str = ""
    current_website: str = ""
    current_folder: str = ""
    current_app: str = ""
    current_window: str = ""
    current_tab: str = ""
    current_selection: str = ""
    current_clipboard: str = ""
    current_screenshot: str = ""
    current_file: str = ""
    current_camera_frame: str = ""
    current_mouse_position: str = ""
    last_tool: str = ""
    last_entity: str = ""
    last_person: str = ""
    last_command: str = ""
    last_user_request: str = ""
    conversation_topic: str = ""
    
    def snapshot(self) -> Dict[str, str]:
        """Get current context as dictionary."""
        return asdict(self)
    
    def update(self, **updates: str) -> None:
        """Update context fields."""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def resolve(self, reference: str) -> str:
        """Resolve pronoun references to actual values."""
        reference_lower = reference.lower().strip()
        
        targets = {
            "there": self.current_website or self.current_folder,
            "it": self.last_entity or self.current_selection,
            "that": self.last_entity or self.current_selection,
            "this": self.current_selection or self.last_entity,
            "again": self.last_command,
            "same": self.last_entity,
            "previous": self.last_entity,
            "file": self.current_file,
            "window": self.current_window,
            "tab": self.current_tab,
        }
        
        return targets.get(reference_lower, "")


class Context:
    """Unified context system."""
    
    def __init__(self, max_history: int = 20):
        self._max_history = max_history
        self._cache = get_cache()
        
        # Conversation history
        self._history: deque[ContextWindow] = deque(maxlen=max_history)
        
        # Entity tracking
        self._entities: Dict[str, ContextEntity] = {}
        
        # Current session state
        self._session = SessionContext()
        
        # Browser state
        self._browser_tabs: List[str] = []
        
        # Current task
        self._current_task: str = ""
    
    def add_context(self, user_input: str, intent: str = "", tool: str = "",
                    entities: List[ContextEntity] = None,
                    metadata: Dict[str, Any] = None) -> None:
        """Add a new context window."""
        context = ContextWindow(
            user_input=user_input,
            intent=intent,
            tool=tool,
            entities=entities or [],
            metadata=metadata or {}
        )
        self._history.append(context)
        
        # Update entities
        for entity in entities or []:
            if entity.name in self._entities:
                self._entities[entity.name].touch()
            else:
                self._entities[entity.name] = entity
        
        # Update session state
        if tool:
            self._session.last_tool = tool
        self._session.last_user_request = user_input
        
        # Cache recent context
        self._cache.set_context("recent_context", self.get_context())
        
        logger.debug(f"Added context: {user_input[:50]}...")
    
    def resolve_reference(self, reference: str) -> Optional[Any]:
        """Resolve pronoun references to actual entities."""
        reference_lower = reference.lower().strip()
        
        # Handle "there"
        if reference_lower in ["there", "us", "wahan"]:
            for context in reversed(self._history):
                for entity in context.entities:
                    if entity.entity_type in ["website", "url", "location"]:
                        return entity.name
            return self._session.current_website
        
        # Handle "that" / "it"
        if reference_lower in ["that", "it", "ye", "wo"]:
            if self._entities:
                latest_entity = max(self._entities.values(), key=lambda e: e.last_mentioned)
                return latest_entity.name
            return self._session.last_entity
        
        # Handle "this"
        if reference_lower in ["this", "ye"]:
            return self._session.current_selection
        
        # Handle "he/she/they"
        if reference_lower in ["he", "she", "they", "woh", "ve"]:
            for context in reversed(self._history):
                for entity in context.entities:
                    if entity.entity_type == "person":
                        return entity.name
            return None
        
        # Handle "first one", "second one", etc.
        if "one" in reference_lower:
            last_result = self._history[-1].metadata.get("result") if self._history else None
            if isinstance(last_result, list) and last_result:
                if "first" in reference_lower:
                    return last_result[0]
                elif "second" in reference_lower and len(last_result) > 1:
                    return last_result[1]
            return None
        
        logger.debug(f"Could not resolve reference: {reference}")
        return None
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context as dictionary."""
        return {
            "session": self._session.snapshot(),
            "last_query": self._history[-1].user_input if self._history else "",
            "last_intent": self._history[-1].intent if self._history else "",
            "last_tool": self._session.last_tool,
            "browser_tabs": self._browser_tabs,
            "entities": {
                name: {
                    "type": e.entity_type,
                    "mentions": e.mentions,
                    "last_mentioned": e.last_mentioned
                }
                for name, e in self._entities.items()
            },
            "current_task": self._current_task,
            "timestamp": time.time()
        }
    
    def update_session(self, key: str, value: Any) -> None:
        """Update session context field."""
        if hasattr(self._session, key):
            setattr(self._session, key, value)
            logger.debug(f"Updated session context {key} = {value}")
    
    def set_active_app(self, app_name: str) -> None:
        """Set currently active application."""
        self._session.current_app = app_name
        self.add_entity(app_name, "app")
    
    def set_active_url(self, url: str) -> None:
        """Set currently active URL."""
        self._session.current_website = url
        self.add_entity(url, "website")
    
    def set_current_folder(self, folder: str) -> None:
        """Set current working folder."""
        self._session.current_folder = folder
    
    def set_current_file(self, file_path: str) -> None:
        """Set current file."""
        self._session.current_file = file_path
        self.add_entity(file_path, "file")
    
    def add_entity(self, name: str, entity_type: str, 
                   metadata: Dict[str, Any] = None) -> None:
        """Add or update an entity in context."""
        if name in self._entities:
            self._entities[name].touch()
            if metadata:
                self._entities[name].metadata.update(metadata)
        else:
            self._entities[name] = ContextEntity(
                name=name,
                entity_type=entity_type,
                metadata=metadata or {}
            )
    
    def get_entities_by_type(self, entity_type: str) -> List[ContextEntity]:
        """Get all entities of a specific type."""
        return [e for e in self._entities.values() if e.entity_type == entity_type]
    
    def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history in chat format."""
        recent = list(self._history)[-limit:]
        history = []
        for context in recent:
            history.append({
                "role": "user",
                "content": context.user_input
            })
            if context.metadata and "response" in context.metadata:
                history.append({
                    "role": "assistant",
                    "content": context.metadata["response"]
                })
        return history
    
    def get_context_summary(self) -> str:
        """Get human-readable context summary."""
        parts = []
        
        if self._session.current_app:
            parts.append(f"Active app: {self._session.current_app}")
        if self._session.current_website:
            parts.append(f"Active website: {self._session.current_website}")
        if self._session.current_folder:
            parts.append(f"Current folder: {self._session.current_folder}")
        if self._session.current_file:
            parts.append(f"Current file: {self._session.current_file}")
        
        if self._entities:
            top_entities = sorted(
                self._entities.values(),
                key=lambda e: e.mentions,
                reverse=True
            )[:5]
            entity_str = ", ".join(f"{e.name} ({e.entity_type})" for e in top_entities)
            parts.append(f"Top entities: {entity_str}")
        
        return "\n".join(parts) if parts else "No context available"
    
    def clear_context(self) -> None:
        """Clear all context (use with caution)."""
        self._history.clear()
        self._entities.clear()
        self._session = SessionContext()
        self._browser_tabs.clear()
        self._current_task = ""
        self._cache.clear_cache("context")
        logger.info("Context cleared")
    
    def set_current_task(self, task: str) -> None:
        """Set current task."""
        self._current_task = task
    
    def get_current_task(self) -> str:
        """Get current task."""
        return self._current_task
    
    def set_browser_tabs(self, tabs: List[str]) -> None:
        """Set browser tabs."""
        self._browser_tabs = tabs
    
    def get_browser_tabs(self) -> List[str]:
        """Get browser tabs."""
        return self._browser_tabs.copy()


# Global context instance
global_context: Optional[Context] = None


def get_context() -> Context:
    """Get global context instance."""
    global global_context
    if global_context is None:
        global_context = Context()
    return global_context


def set_context(context: Context) -> None:
    """Set global context instance."""
    global global_context
    global_context = context
