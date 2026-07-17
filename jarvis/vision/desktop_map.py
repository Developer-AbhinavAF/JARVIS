"""Desktop Map — Internal representation of the workspace.

Build a hierarchical model:
Workspace → Displays → Windows → Controls → Elements → Relationships

Instead of pixels, understand objects.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# DESKTOP MAP
# ════════════════════════════════════════════════════════════════════

@dataclass
class DesktopState:
    """Complete snapshot of the desktop environment."""
    timestamp: float = 0.0

    # Displays
    display_count: int = 1
    primary_display: dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})

    # Windows
    window_count: int = 0
    focused_window: str = ""
    focused_app: str = ""
    windows: list[dict[str, Any]] = field(default_factory=list)

    # UI Elements
    element_count: int = 0
    elements: list[dict[str, Any]] = field(default_factory=list)

    # OCR
    visible_text: str = ""
    has_errors: bool = False
    error_messages: list[str] = field(default_factory=list)

    # Layout
    layout_description: str = ""
    regions: list[dict[str, Any]] = field(default_factory=list)

    # Activity
    active_apps: list[str] = field(default_factory=list)
    desktop_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "displays": self.display_count,
            "windows": self.window_count,
            "focused": self.focused_window[:50],
            "app": self.focused_app,
            "elements": self.element_count,
            "has_errors": self.has_errors,
            "text_preview": self.visible_text[:100],
        }


class DesktopMap:
    """Maintains a live internal representation of the desktop.

    Updates continuously by combining data from:
    - Screen capture
    - Window manager
    - OCR engine
    - UI detection
    - Layout analyzer
    """

    def __init__(self) -> None:
        self._current_state: DesktopState | None = None
        self._history: list[DesktopState] = []
        self._max_history: int = 50

    def update(
        self,
        windows: list[Any] | None = None,
        elements: list[Any] | None = None,
        ocr_result: Any = None,
        regions: list[Any] | None = None,
        displays: list[dict[str, Any]] | None = None,
    ) -> DesktopState:
        """Update the desktop map with new data."""
        state = DesktopState(timestamp=time.time())

        # Displays
        if displays:
            state.display_count = len(displays)
            if displays:
                primary = next((d for d in displays if d.get("is_primary")), displays[0])
                state.primary_display = {"width": primary["width"], "height": primary["height"]}

        # Windows
        if windows:
            state.window_count = len(windows)
            state.windows = [w.to_dict() if hasattr(w, 'to_dict') else w for w in windows]
            focused = next((w for w in windows if getattr(w, 'is_focused', False)), None)
            if focused:
                state.focused_window = getattr(focused, 'title', '')
                state.focused_app = getattr(focused, 'app_name', '')
            state.active_apps = list(set(
                getattr(w, 'app_name', '') for w in windows
                if not getattr(w, 'is_minimized', False)
            ))

        # Elements
        if elements:
            state.element_count = len(elements)
            state.elements = [e.to_dict() if hasattr(e, 'to_dict') else e for e in elements]

        # OCR
        if ocr_result:
            state.visible_text = getattr(ocr_result, 'full_text', '')
            state.has_errors = getattr(ocr_result, 'has_errors', False)
            if state.has_errors:
                state.error_messages = [
                    b.text for b in getattr(ocr_result, 'blocks', [])
                    if getattr(b, 'block_type', '') == 'error'
                ]

        # Layout
        if regions:
            state.regions = [r.to_dict() if hasattr(r, 'to_dict') else r for r in regions]
            state.layout_description = self._describe_regions(regions)

        # Summary
        state.desktop_summary = self._build_summary(state)

        self._current_state = state
        self._history.append(state)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history // 2:]

        return state

    def get_current(self) -> DesktopState | None:
        return self._current_state

    def get_history(self, limit: int = 10) -> list[DesktopState]:
        return self._history[-limit:]

    def detect_changes(self) -> list[str]:
        """Detect changes since last update."""
        if len(self._history) < 2:
            return []

        current = self._history[-1]
        previous = self._history[-2]
        changes = []

        if current.window_count != previous.window_count:
            diff = current.window_count - previous.window_count
            changes.append(f"Window count changed: {'+' if diff > 0 else ''}{diff}")

        if current.focused_window != previous.focused_window:
            changes.append(f"Focus changed to: {current.focused_window[:50]}")

        if current.has_errors and not previous.has_errors:
            changes.append("New errors detected on screen")

        if current.focused_app != previous.focused_app:
            changes.append(f"Active app changed to: {current.focused_app}")

        return changes

    @staticmethod
    def _describe_regions(regions: list[Any]) -> str:
        types = [getattr(r, 'region_type', '') for r in regions]
        return ", ".join(t for t in types if t)

    @staticmethod
    def _build_summary(state: DesktopState) -> str:
        parts = []
        if state.focused_app:
            parts.append(f"Using {state.focused_app}")
        if state.window_count:
            parts.append(f"{state.window_count} windows open")
        if state.has_errors:
            parts.append(f"{len(state.error_messages)} errors visible")
        if state.element_count:
            parts.append(f"{state.element_count} UI elements")
        return ". ".join(parts) if parts else "Desktop active"

    def get_stats(self) -> dict[str, Any]:
        return {
            "history_size": len(self._history),
            "current": self._current_state.to_dict() if self._current_state else None,
        }


desktop_map = DesktopMap()
