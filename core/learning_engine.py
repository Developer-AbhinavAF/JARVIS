"""core/learning_engine.py — Continuous Learning & Reflection Engine for JARVIS vNext++.

Tracks execution failures, analyzes root causes, updates mistakes.json,
and generates learned patterns to prevent repeated mistakes.
"""

from __future__ import annotations

import os
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FailureEvent:
    tool_name: str
    args: Dict[str, Any]
    error_message: str
    context: str = ""
    timestamp: float = time.time()


class LearningEngine:
    """Continuous learning subsystem."""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.mistakes_file = self.memory_dir / "mistakes.json"
        self.patterns_file = self.memory_dir / "patterns.json"
        self._mistakes: List[Dict[str, Any]] = []
        self._patterns: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        if self.mistakes_file.exists():
            try:
                with open(self.mistakes_file, "r", encoding="utf-8") as f:
                    self._mistakes = json.load(f)
            except Exception:
                self._mistakes = []
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, "r", encoding="utf-8") as f:
                    self._patterns = json.load(f)
            except Exception:
                self._patterns = []

    def _save(self) -> None:
        try:
            with open(self.mistakes_file, "w", encoding="utf-8") as f:
                json.dump(self._mistakes, f, indent=2)
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(self._patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save learning files: {e}")

    def record_failure(self, failure: FailureEvent) -> None:
        """Record execution failure and generate learning pattern."""
        mistake_entry = {
            "tool": failure.tool_name,
            "args": failure.args,
            "error": failure.error_message,
            "timestamp": failure.timestamp,
        }
        self._mistakes.append(mistake_entry)

        # Generate automatic pattern improvement
        pattern_entry = {
            "trigger_tool": failure.tool_name,
            "rule": f"Avoid {failure.error_message} when invoking {failure.tool_name}",
            "learned_at": failure.timestamp,
        }
        self._patterns.append(pattern_entry)
        self._save()
        logger.info(f"Learned pattern recorded for failure in {failure.tool_name}")

    def get_relevant_mistakes(self, tool_name: str) -> List[str]:
        """Retrieve recent mistake warnings for a tool."""
        return [
            m["error"]
            for m in self._mistakes
            if m.get("tool") == tool_name
        ][-3:]


learning_engine = LearningEngine()
