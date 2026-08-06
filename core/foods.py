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
            return self._index.get("coding.md", self._index.get("01_execution.md", ""))
        elif "tool" in intent_clean or "open" in intent_clean:
            return self._index.get("tools.md", self._index.get("03_tool_registry.md", ""))
        elif "memory" in intent_clean:
            return self._index.get("memory.md", self._index.get("04_memory.md", ""))
        elif "desktop" in intent_clean:
            return self._index.get("desktop.md", self._index.get("07_desktop.md", ""))
        
        # Default identity food
        return self._index.get("00_identity.md", "")


food_engine = DynamicFoodEngine()
