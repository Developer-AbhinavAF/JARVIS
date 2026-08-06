"""core/world_state.py — World State Engine for JARVIS vNext++.

Continuously tracks real-time operating system and environment state:
- Active Application, Window Title, Browser Tab, Website URL
- Current Directory / Folder, Open File
- Clipboard text, Mouse Position, Keyboard Focus
- Running Processes, Network/Internet State, Battery Status
- Notifications, Camera / Microphone state, Recent Screenshot path
- Last Tool Executed, Active Task, Active Goal, Active Project
"""

from __future__ import annotations

import os
import sys
import time
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class WorldState:
    current_app: str = "Unknown"
    current_window: str = "Desktop"
    current_website: str = ""
    current_browser: str = ""
    current_folder: str = os.getcwd()
    current_file: str = ""
    clipboard_preview: str = ""
    selection: str = ""
    mouse_position: tuple = (0, 0)
    keyboard_focus: str = ""
    running_processes_count: int = 0
    internet_connected: bool = True
    battery_percent: Optional[float] = None
    notifications: list = field(default_factory=list)
    camera_active: bool = False
    mic_active: bool = False
    last_screenshot_path: str = ""
    last_tool_executed: str = ""
    last_entity_referenced: str = ""
    current_task: str = ""
    current_goal: str = ""
    current_project: str = ""
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorldStateEngine:
    """Engine maintaining current environment and OS context."""

    def __init__(self):
        self._state = WorldState()

    def update(self, **kwargs) -> WorldState:
        """Update specific fields in WorldState."""
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self._state.updated_at = time.time()
        return self._state

    def get_state(self) -> WorldState:
        """Get current state."""
        return self._state

    def get_context_summary(self) -> str:
        """Format state as concise prompt context."""
        parts = [
            f"App: {self._state.current_app} | Window: {self._state.current_window}",
            f"Folder: {self._state.current_folder}",
        ]
        if self._state.current_website:
            parts.append(f"Website: {self._state.current_website}")
        if self._state.last_tool_executed:
            parts.append(f"Last Tool: {self._state.last_tool_executed}")
        if self._state.current_goal:
            parts.append(f"Active Goal: {self._state.current_goal}")
        return " | ".join(parts)


world_state_engine = WorldStateEngine()
