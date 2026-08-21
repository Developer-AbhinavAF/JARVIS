"""core/foods.py — Ultra-Optimized Food Injection Engine for JARVIS AGI.

Compiles prompt food files from foods/*.md into an internal index.
Dynamically injects only intent-relevant food prompt instructions.

Optimized for multi-model orchestration with Groq as primary.
Uses high-density "Cognitive Primes" - minimal tokens, maximum effect.
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

    def get_food_for_intent(self, intent: str, session_id: str = "default") -> str:
        """Return optimized food prompt based on intent.
        
        Includes orchestration instructions for multi-model routing.
        Uses cognitive primes: short, high-impact phrases.
        """
        self.reload()  # Check mtimes for hot reload
        
        intent_clean = intent.lower()
        foods_list = []
        
        # Always include identity (core being)
        if "00_identity.md" in self._index:
            foods_list.append(self._index["00_identity.md"])
        
        # Include orchestration (multi-model brain)
        if "23_orchestration.md" in self._index:
            foods_list.append(self._index["23_orchestration.md"])
        
        # Intent-specific cognitive primes
        if any(k in intent_clean for k in ["code", "debug", "fix", "run"]):
            if "01_reasoning.md" in self._index:
                foods_list.append(self._index["01_reasoning.md"])
        elif any(k in intent_clean for k in ["tool", "open", "close", "execute"]):
            if "02_tools.md" in self._index:
                foods_list.append(self._index["02_tools.md"])
        elif any(k in intent_clean for k in ["memory", "remember", "recall", "learn"]):
            if "03_memory.md" in self._index:
                foods_list.append(self._index["03_memory.md"])
        elif "desktop" in intent_clean:
            if "05_desktop.md" in self._index:
                foods_list.append(self._index["05_desktop.md"])
        elif any(k in intent_clean for k in ["nasa", "space", "image", "visual"]):
            if "22_nasa_visual.md" in self._index:
                foods_list.append(self._index["22_nasa_visual.md"])
        elif any(k in intent_clean for k in ["chat", "talk", "conversation"]):
            if "10_personality.md" in self._index:
                foods_list.append(self._index["10_personality.md"])
        elif any(k in intent_clean for k in ["write", "email", "text"]):
            if "19_response_style.md" in self._index:
                foods_list.append(self._index["19_response_style.md"])
        
        # Safety always included (non-negotiable)
        if "11_safety.md" in self._index:
            foods_list.append(self._index["11_safety.md"])
        
        return "\n\n".join(foods_list) if foods_list else self._index.get("00_identity.md", "")


food_engine = DynamicFoodEngine()
