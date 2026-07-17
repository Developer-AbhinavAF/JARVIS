"""Mouse Tracker — Track cursor position and hover state.

Track:
- Current Position
- Hovered Element
- Clicked Element
- Selection
- Drag Operations
- Scrolling
- Focus Changes

Never move the cursor unexpectedly without permission.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


@dataclass
class MouseState:
    x: int = 0
    y: int = 0
    is_moving: bool = False
    is_clicked: bool = False
    is_scrolling: bool = False
    button: str = ""        # left, right, middle
    scroll_direction: int = 0  # 1=up, -1=down
    timestamp: float = 0.0


class MouseTracker:
    """Tracks mouse position and interaction state."""

    def __init__(self) -> None:
        self._current = MouseState()
        self._history: list[MouseState] = []
        self._max_history = 100

    def get_position(self) -> tuple[int, int]:
        if HAS_PYAUTOGUI:
            try:
                pos = pyautogui.position()
                return (pos.x, pos.y)
            except Exception:
                pass
        return (0, 0)

    def get_state(self) -> MouseState:
        x, y = self.get_position()
        self._current = MouseState(x=x, y=y, timestamp=time.time())
        return self._current

    def find_element_at(
        self,
        x: int, y: int,
        elements: list[Any] | None = None,
    ) -> Any | None:
        if not elements:
            return None
        for elem in elements:
            if hasattr(elem, 'contains') and elem.contains(x, y):
                return elem
        return None

    def get_stats(self) -> dict[str, Any]:
        return {"position": self.get_position(), "has_pyautogui": HAS_PYAUTOGUI}


mouse_tracker = MouseTracker()
