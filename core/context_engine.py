"""context_engine — Context tracking and resolution engine.

Maintains conversation context, resolves pronouns, tracks entities,
and provides context-aware information for LLM processing.
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ContextEntity:
    """Represents an entity mentioned in conversation."""
    name: str
    type: str  # app, website, person, file, etc.
    mentions: int = 1
    last_mentioned: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextWindow:
    """Represents a single context window (conversation turn)."""
    user_input: str
    intent: str = ""
    tool: str = ""
    entities: List[ContextEntity] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextEngine:
    """Manages conversation context and reference resolution."""
    
    def __init__(self, max_history: int = 20):
        self._max_history = max_history
        self._history: deque[ContextWindow] = deque(maxlen=max_history)
        self._entities: Dict[str, ContextEntity] = {}
        self._active_app: str = ""
        self._active_url: str = ""
        self._last_tool: str = ""
        self._last_result: Any = None
        self._browser_tabs: List[str] = []
        self._current_task: str = ""
        
    def add_context(self, user_input: str, intent: str = "", tool: str = "", 
                    entities: List[ContextEntity] = None, metadata: Dict[str, Any] = None) -> None:
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
                self._entities[entity.name].mentions += 1
                self._entities[entity.name].last_mentioned = time.time()
            else:
                self._entities[entity.name] = entity
        
        # Update tracking
        if tool:
            self._last_tool = tool
        
        logger.debug(f"Added context: {user_input[:50]}...")
    
    def resolve_reference(self, reference: str) -> Optional[Any]:
        """Resolve pronoun references to actual entities."""
        reference_lower = reference.lower().strip()
        
        # Handle "there"
        if reference_lower in ["there", "us", "wahan"]:
            # Return last mentioned location/website
            for context in reversed(self._history):
                for entity in context.entities:
                    if entity.type in ["website", "url", "location"]:
                        return entity.name
            return self._active_url
        
        # Handle "that" / "it"
        if reference_lower in ["that", "it", "ye", "wo"]:
            # Return last mentioned entity
            if self._entities:
                # Get most recently mentioned entity
                latest_entity = max(self._entities.values(), key=lambda e: e.last_mentioned)
                return latest_entity.name
            return self._last_result
        
        # Handle "this"
        if reference_lower in ["this", "ye"]:
            # Return current subject (last tool result)
            return self._last_result
        
        # Handle "he/she/they"
        if reference_lower in ["he", "she", "they", "woh", "ve"]:
            # Return last mentioned person
            for context in reversed(self._history):
                for entity in context.entities:
                    if entity.type == "person":
                        return entity.name
            return None
        
        # Handle "first one", "second one", etc.
        if "one" in reference_lower:
            # Return from last result if it's a list
            if isinstance(self._last_result, list) and self._last_result:
                if "first" in reference_lower:
                    return self._last_result[0]
                elif "second" in reference_lower and len(self._last_result) > 1:
                    return self._last_result[1]
            return None
        
        logger.debug(f"Could not resolve reference: {reference}")
        return None
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context as dictionary."""
        return {
            "last_query": self._history[-1].user_input if self._history else "",
            "last_intent": self._history[-1].intent if self._history else "",
            "last_tool": self._last_tool,
            "active_app": self._active_app,
            "active_url": self._active_url,
            "browser_tabs": self._browser_tabs,
            "entities": {name: {"type": e.type, "mentions": e.mentions} 
                        for name, e in self._entities.items()},
            "current_task": self._current_task,
            "timestamp": time.time()
        }
    
    def update_context(self, key: str, value: Any) -> None:
        """Update a specific context field."""
        if key == "active_app":
            self._active_app = value
        elif key == "active_url":
            self._active_url = value
        elif key == "browser_tabs":
            self._browser_tabs = value
        elif key == "current_task":
            self._current_task = value
        elif key == "last_result":
            self._last_result = value
        logger.debug(f"Updated context {key} = {value}")
    
    def set_active_app(self, app_name: str) -> None:
        """Set the currently active application."""
        self._active_app = app_name
        self.add_entity(app_name, "app")
    
    def set_active_url(self, url: str) -> None:
        """Set the currently active URL."""
        self._active_url = url
        self.add_entity(url, "website")
    
    def add_entity(self, name: str, entity_type: str, metadata: Dict[str, Any] = None) -> None:
        """Add or update an entity in context."""
        if name in self._entities:
            self._entities[name].mentions += 1
            self._entities[name].last_mentioned = time.time()
            if metadata:
                self._entities[name].metadata.update(metadata)
        else:
            self._entities[name] = ContextEntity(
                name=name,
                type=entity_type,
                metadata=metadata or {}
            )
    
    def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history in chat format."""
        recent = list(self._history)[-limit:]
        history = []
        for c in recent:
            # Add user message
            history.append({
                "role": "user",
                "content": c.user_input
            })
            # Add assistant response if available (from metadata)
            if c.metadata and "response" in c.metadata:
                history.append({
                    "role": "assistant", 
                    "content": c.metadata["response"]
                })
        return history
    
    def get_entities_by_type(self, entity_type: str) -> List[ContextEntity]:
        """Get all entities of a specific type."""
        return [e for e in self._entities.values() if e.type == entity_type]
    
    def clear_context(self) -> None:
        """Clear all context (use with caution)."""
        self._history.clear()
        self._entities.clear()
        self._active_app = ""
        self._active_url = ""
        self._last_tool = ""
        self._last_result = None
        self._current_task = ""
        logger.info("Context cleared")
    
    def get_context_summary(self) -> str:
        """Get a human-readable context summary."""
        summary_parts = []
        
        if self._active_app:
            summary_parts.append(f"Active app: {self._active_app}")
        if self._active_url:
            summary_parts.append(f"Active URL: {self._active_url}")
        if self._current_task:
            summary_parts.append(f"Current task: {self._current_task}")
        if self._entities:
            summary_parts.append(f"Recent entities: {', '.join(list(self._entities.keys())[-5:])}")
        
        return "\n".join(summary_parts) if summary_parts else "No active context"


# Global context engine instance
context_engine = ContextEngine()