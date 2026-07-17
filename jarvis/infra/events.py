"""Event Bus — The nervous system of JARVIS.

Every module communicates through events.
Decoupled, typed, thread-safe.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType(Enum):
    # Application lifecycle
    APP_STARTED = "app.started"
    APP_CLOSING = "app.closing"
    APP_CLOSED = "app.closed"
    # Speech
    SPEECH_STARTED = "speech.started"
    SPEECH_STOPPED = "speech.stopped"
    SPEECH_RECOGNIZED = "speech.recognized"
    # Memory
    MEMORY_UPDATED = "memory.updated"
    MEMORY_COMPRESSED = "memory.compressed"
    # Tools
    TOOL_EXECUTED = "tool.executed"
    TOOL_FAILED = "tool.failed"
    # Desktop
    WINDOW_OPENED = "window.opened"
    WINDOW_CLOSED = "window.closed"
    SESSION_CHANGED = "session.changed"
    # Network
    DOWNLOAD_COMPLETED = "download.completed"
    INTERNET_LOST = "internet.lost"
    INTERNET_RESTORED = "internet.restored"
    # Agents
    AGENT_ACTIVATED = "agent.activated"
    AGENT_COMPLETED = "agent.completed"
    # Vision
    VISION_UPDATED = "vision.updated"
    VISION_CAPTURED = "vision.captured"
    # Learning
    LEARNING_COMPLETED = "learning.completed"
    LEARNING_ERROR = "learning.error"
    # System
    BATTERY_LOW = "battery.low"
    BATTERY_CRITICAL = "battery.critical"
    CPU_HIGH = "cpu.high"
    CPU_NORMAL = "cpu.normal"
    MEMORY_LOW = "memory.low"
    # Router
    ROUTER_REQUEST = "router.request"
    ROUTER_RESPONSE = "router.response"
    ROUTER_FALLBACK = "router.fallback"
    # NLP
    NLP_PROCESSED = "nlp.processed"
    # Settings
    SETTINGS_CHANGED = "settings.changed"
    # Generic
    CUSTOM = "custom"


@dataclass
class Event:
    """A single event on the bus."""
    type: EventType = EventType.CUSTOM
    source: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    handled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
        }


EventHandler = Callable[[Event], None]


class EventBus:
    """Thread-safe publish/subscribe event bus.

    Usage:
        bus = EventBus()
        bus.on(EventType.APP_STARTED, my_handler)
        bus.emit(EventType.APP_STARTED, source="main")
    """

    def __init__(self, max_history: int = 1000):
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: list[EventHandler] = []
        self._history: list[Event] = []
        self._max_history = max_history
        self._lock = threading.Lock()
        self._event_count = 0

    def on(self, event_type: EventType | None, handler: EventHandler):
        """Subscribe to an event type. None = wildcard (all events)."""
        with self._lock:
            if event_type is None:
                self._wildcard_handlers.append(handler)
            else:
                self._handlers[event_type].append(handler)

    def off(self, event_type: EventType | None, handler: EventHandler):
        """Unsubscribe from an event type."""
        with self._lock:
            if event_type is None:
                self._wildcard_handlers = [h for h in self._wildcard_handlers if h != handler]
            else:
                self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    def emit(self, event_type: EventType, source: str = "", data: dict[str, Any] | None = None):
        """Emit an event to all subscribers."""
        event = Event(type=event_type, source=source, data=data or {})

        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            self._event_count += 1

        # Dispatch to handlers (copy lists to avoid mutation during iteration)
        handlers = list(self._handlers.get(event_type, []))
        wildcard = list(self._wildcard_handlers)

        for handler in handlers + wildcard:
            try:
                handler(event)
                event.handled = True
            except Exception as e:
                logger.warning("Event handler error for %s: %s", event_type.value, e)

    def get_history(self, event_type: EventType | None = None, limit: int = 50) -> list[Event]:
        """Get recent events, optionally filtered by type."""
        with self._lock:
            if event_type:
                events = [e for e in self._history if e.type == event_type]
            else:
                events = list(self._history)
        return events[-limit:]

    def clear_history(self):
        with self._lock:
            self._history.clear()

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_events": self._event_count,
                "history_size": len(self._history),
                "handler_count": sum(len(h) for h in self._handlers.values()) + len(self._wildcard_handlers),
                "event_types": len(self._handlers),
            }


# Global instance
event_bus = EventBus()

__all__ = ["EventBus", "EventType", "Event", "event_bus"]
