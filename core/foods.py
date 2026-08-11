"""core/foods.py — Dynamic Food Injection Engine with Hot Reload for JARVIS vNext++.

Compiles prompt food files from foods/*.md into an internal index.
Dynamically injects only intent-relevant food prompt instructions.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DynamicFoodEngine:
    """Manages food prompt files with mtime hot reload."""

    def __init__(self, foods_dir: str = "foods"):
        self.foods_dir = Path(foods_dir)
        self._index: Dict[str, str] = {}
        self._mtimes: Dict[str, float] = {}
        self.reload()

    def reload(self) -> None:
        """Scan and compile foods directory."""
        if not self.foods_dir.exists():
            return
        
        for file in self.foods_dir.glob("*.md"):
            mtime = file.stat().st_mtime
            if file.name not in self._mtimes or self._mtimes[file.name] != mtime:
                try:
                    self._index[file.name] = file.read_text(encoding="utf-8")
                    self._mtimes[file.name] = mtime
                    logger.debug(f"Loaded/Updated food file: {file.name}")
                except Exception as e:
                    logger.error(f"Error reading food {file}: {e}")

    def get_food_for_intent(self, intent: str) -> str:
        """Return only intent-relevant food prompt section."""
        self.reload()  # Check mtimes for hot reload
        
        intent_clean = intent.lower()
        if "code" in intent_clean or "debug" in intent_clean:
            return self._index.get("01_reasoning.md", "")
        elif "tool" in intent_clean or "open" in intent_clean:
            return self._index.get("02_tools.md", "")
        elif "memory" in intent_clean:
            return self._index.get("03_memory.md", "")
        elif "desktop" in intent_clean:
            return self._index.get("05_desktop.md", "")
        elif "nasa" in intent_clean or "visual" in intent_clean:
            return self._index.get("22_nasa_visual.md", "")
        elif "conversation" in intent_clean or "chat" in intent_clean:
            return self._index.get("10_personality.md", "")
        elif "writing" in intent_clean:
            return self._index.get("19_response_style.md", "")
        
        # Default identity food
        return self._index.get("00_identity.md", "")


food_engine = DynamicFoodEngine()
