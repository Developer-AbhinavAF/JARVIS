"""Screen Memory — Remember screen context for reasoning and continuity.

Stores:
- Detected Application
- Current Window
- Recent Errors
- Visible Documents
- Recent Projects
- Current Workspace
- Visible URLs
- Current Screen Context

The next question should use this information.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScreenEvent:
    """A recorded screen event."""
    event_type: str = ""      # window_open, error, dialog, notification, etc.
    description: str = ""
    app: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class VisionContext:
    """Structured context from the most recent vision analysis."""
    focused_app: str = ""
    focused_window: str = ""
    window_count: int = 0
    has_errors: bool = False
    error_messages: list[str] = field(default_factory=list)
    visible_urls: list[str] = field(default_factory=list)
    visible_documents: list[str] = field(default_factory=list)
    visible_code: bool = False
    visible_terminal: bool = False
    element_count: int = 0
    ocr_text_preview: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "app": self.focused_app,
            "window": self.focused_window[:100],
            "windows": self.window_count,
            "errors": self.has_errors,
            "error_messages": self.error_messages[:3],
            "urls": self.visible_urls[:5],
            "documents": self.visible_documents[:5],
            "has_code": self.visible_code,
            "has_terminal": self.visible_terminal,
            "elements": self.element_count,
            "text_preview": self.ocr_text_preview[:200],
        }


class ScreenMemory:
    """Remembers screen history for context across interactions."""

    def __init__(self, max_events: int = 200) -> None:
        self._events: list[ScreenEvent] = []
        self._max_events = max_events
        self._seen_errors: dict[str, int] = {}
        self._seen_windows: dict[str, float] = {}
        self._current_context: VisionContext = VisionContext()
        self._context_history: list[VisionContext] = []
        self._max_context_history: int = 50

    def update_context(
        self,
        focused_app: str = "",
        focused_window: str = "",
        window_count: int = 0,
        has_errors: bool = False,
        error_messages: list[str] | None = None,
        visible_urls: list[str] | None = None,
        visible_documents: list[str] | None = None,
        visible_code: bool = False,
        visible_terminal: bool = False,
        element_count: int = 0,
        ocr_text_preview: str = "",
    ) -> VisionContext:
        """Update the current vision context."""
        # Save previous context to history
        if self._current_context.focused_app or self._current_context.window_count > 0:
            self._context_history.append(self._current_context)
            if len(self._context_history) > self._max_context_history:
                self._context_history = self._context_history[-self._max_context_history // 2:]

        self._current_context = VisionContext(
            focused_app=focused_app,
            focused_window=focused_window,
            window_count=window_count,
            has_errors=has_errors,
            error_messages=error_messages or [],
            visible_urls=visible_urls or [],
            visible_documents=visible_documents or [],
            visible_code=visible_code,
            visible_terminal=visible_terminal,
            element_count=element_count,
            ocr_text_preview=ocr_text_preview,
            timestamp=time.time(),
        )
        return self._current_context

    def get_current_context(self) -> VisionContext:
        """Get the current vision context."""
        return self._current_context

    def get_previous_context(self) -> VisionContext | None:
        """Get the previous vision context (before the current one)."""
        if self._context_history:
            return self._context_history[-1]
        return None

    def get_context_for_query(self, query: str) -> dict[str, Any]:
        """Get relevant context for a specific query type."""
        ctx = self._current_context
        result: dict[str, Any] = {}

        query_lower = query.lower()

        # Always include basic context
        result["current_app"] = ctx.focused_app
        result["window_count"] = ctx.window_count

        # Error context
        if any(w in query_lower for w in ["error", "exception", "traceback", "bug"]):
            result["has_errors"] = ctx.has_errors
            result["error_messages"] = ctx.error_messages
            # Also check recent error history
            recent_errors = self.get_recent("error", limit=5)
            result["recent_errors"] = [e.description[:200] for e in recent_errors]

        # Code context
        if any(w in query_lower for w in ["code", "script", "function", "debug"]):
            result["has_code"] = ctx.visible_code
            result["has_terminal"] = ctx.visible_terminal

        # Document context
        if any(w in query_lower for w in ["document", "file", "pdf", "doc"]):
            result["visible_documents"] = ctx.visible_documents

        # URL context
        if any(w in query_lower for w in ["url", "link", "website", "http"]):
            result["visible_urls"] = ctx.visible_urls

        # Text content
        if any(w in query_lower for w in ["read", "text", "say", "content"]):
            result["text_preview"] = ctx.ocr_text_preview

        return result

    def record(self, event_type: str, description: str, app: str = "", **details: Any) -> None:
        """Record a screen event."""
        event = ScreenEvent(
            event_type=event_type, description=description,
            app=app, details=details, timestamp=time.time(),
        )
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events // 2:]
        if event_type == "error":
            self._seen_errors[description[:100]] = self._seen_errors.get(description[:100], 0) + 1
        if event_type == "window_open":
            self._seen_windows[description[:50]] = time.time()

    def get_recent(self, event_type: str = "", limit: int = 10) -> list[ScreenEvent]:
        """Get recent events, optionally filtered by type."""
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def has_seen_error(self, error_text: str) -> bool:
        """Check if an error has been seen before."""
        return error_text[:100] in self._seen_errors

    def get_opened_windows(self, since_minutes: float = 30) -> list[str]:
        """Get windows opened in the last N minutes."""
        cutoff = time.time() - since_minutes * 60
        return [w for w, t in self._seen_windows.items() if t > cutoff]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": len(self._events),
            "unique_errors": len(self._seen_errors),
            "seen_windows": len(self._seen_windows),
            "current_app": self._current_context.focused_app,
            "context_history": len(self._context_history),
        }


screen_memory = ScreenMemory()
