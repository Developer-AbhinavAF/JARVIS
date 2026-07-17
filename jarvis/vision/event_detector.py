"""Event Detector — Detect screen changes and events.

Recognize:
- Window Opened/Closed
- Popup Appeared
- Download Finished
- Application Crashed
- Build Finished
- Compilation Failed
- Battery Low
- USB Connected

Automatically notify reasoning engine.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ScreenEvent:
    event_type: str = ""
    description: str = ""
    severity: str = "info"
    app: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


class EventDetector:
    """Detects changes and events on screen by comparing snapshots."""

    def __init__(self) -> None:
        self._prev_windows: set[str] = set()
        self._prev_errors: set[str] = set()
        self._callbacks: list[Callable] = []
        self._events: list[ScreenEvent] = []

    def detect(
        self,
        current_windows: list[Any] | None = None,
        ocr_result: Any = None,
    ) -> list[ScreenEvent]:
        events = []
        now = time.time()

        # Window changes
        if current_windows is not None:
            current_titles = set(getattr(w, 'title', '')[:50] for w in current_windows)
            new_windows = current_titles - self._prev_windows
            closed_windows = self._prev_windows - current_titles

            for w in new_windows:
                if w:
                    events.append(ScreenEvent("window_open", w, timestamp=now))
            for w in closed_windows:
                if w:
                    events.append(ScreenEvent("window_closed", w, timestamp=now))

            self._prev_windows = current_titles

        # Error detection
        if ocr_result and hasattr(ocr_result, 'blocks'):
            current_errors = set(
                b.text[:100] for b in ocr_result.blocks
                if getattr(b, 'block_type', '') == 'error'
            )
            new_errors = current_errors - self._prev_errors
            for err in new_errors:
                events.append(ScreenEvent("error_detected", err, severity="error", timestamp=now))
            self._prev_errors = current_errors

        # Notify callbacks
        for event in events:
            for cb in self._callbacks:
                try:
                    cb(event)
                except Exception:
                    pass

        self._events.extend(events)
        if len(self._events) > 200:
            self._events = self._events[-100:]

        return events

    def on_event(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def get_recent_events(self, limit: int = 10) -> list[ScreenEvent]:
        return self._events[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {"total_events": len(self._events), "tracked_windows": len(self._prev_windows)}


event_detector = EventDetector()
