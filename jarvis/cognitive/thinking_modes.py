"""Thinking Modes for JARVIS Cognitive Architecture.

Fast Thinking: Simple tasks (Open Chrome, Volume Up, Play Music)
Slow Thinking: Programming, Debugging, Architecture, Research
Research Mode: Complex questions requiring multi-source investigation
Coding Mode: Project-aware code generation and debugging

Automatically switch mode based on task complexity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# THINKING MODE DEFINITIONS
# ════════════════════════════════════════════════════════════════════

class ThinkingMode:
    FAST = "fast"           # Simple, direct execution
    SLOW = "slow"           # Complex reasoning needed
    RESEARCH = "research"   # Multi-source investigation
    CODING = "coding"       # Project-aware coding


# Intent → default thinking mode
_INTENT_MODE_MAP: dict[str, str] = {
    # Fast
    "OPEN_APP": ThinkingMode.FAST,
    "CLOSE_APP": ThinkingMode.FAST,
    "VOLUME_CONTROL": ThinkingMode.FAST,
    "BRIGHTNESS_CONTROL": ThinkingMode.FAST,
    "SCREENSHOT": ThinkingMode.FAST,
    "DATETIME": ThinkingMode.FAST,
    "CALCULATOR": ThinkingMode.FAST,
    "GREETING": ThinkingMode.FAST,
    "FLIP_COIN": ThinkingMode.FAST,
    "DICE_ROLL": ThinkingMode.FAST,
    "SYSTEM_POWER": ThinkingMode.FAST,
    "WINDOW_CONTROL": ThinkingMode.FAST,
    "CLIPBOARD": ThinkingMode.FAST,

    # Slow
    "PROGRAMMING": ThinkingMode.SLOW,
    "VERSION_CONTROL": ThinkingMode.SLOW,
    "FILE_MANAGEMENT": ThinkingMode.SLOW,
    "SYSTEM_STATUS": ThinkingMode.SLOW,

    # Research
    "WEB_SEARCH": ThinkingMode.RESEARCH,
    "SEARCH_ON_PLATFORM": ThinkingMode.RESEARCH,
    "SEARCH_YOUTUBE": ThinkingMode.RESEARCH,
    "GET_NEWS": ThinkingMode.RESEARCH,
    "GET_WEATHER": ThinkingMode.RESEARCH,
    "STOCK_QUOTE": ThinkingMode.RESEARCH,

    # Coding
    "OPEN_VSCODE": ThinkingMode.CODING,
    "OPEN_TERMINAL": ThinkingMode.CODING,
}


# ════════════════════════════════════════════════════════════════════
# COMPLEXITY SIGNALS
# ════════════════════════════════════════════════════════════════════

# Words that increase complexity
_SLOW_SIGNALS = [
    "analyze", "compare", "explain", "why", "how does", "architecture",
    "design", "refactor", "debug", "optimize", "implement", "create",
    "build", "develop", "research", "investigate", "evaluate",
]

# Words that indicate coding mode
_CODING_SIGNALS = [
    "code", "coding", "program", "function", "class", "method", "variable",
    "import", "module", "package", "dependency", "error", "bug", "debug",
    "compile", "build", "test", "deploy", "git", "commit", "branch",
    "python", "javascript", "typescript", "rust", "java", "golang",
    "vscode", "editor", "terminal", "console",
]

# Words that indicate research mode
_RESEARCH_SIGNALS = [
    "search", "find", "look up", "research", "paper", "study",
    "news", "latest", "recent", "current", "today", "what is",
    "who is", "when did", "how many", "compare", "review",
]


# ════════════════════════════════════════════════════════════════════
# THINKING MODE MANAGER
# ════════════════════════════════════════════════════════════════════

@dataclass
class ThinkingContext:
    """Context for the current thinking process."""
    mode: str = ThinkingMode.FAST
    confidence: float = 0.8
    reasoning: str = ""
    estimated_steps: int = 1
    requires_tools: bool = True
    requires_research: bool = False
    requires_coding: bool = False


class ThinkingModeManager:
    """Manages thinking modes and auto-switching.

    Automatically determines the appropriate thinking mode based on:
    - Intent complexity
    - Text signals
    - Context
    - Entity types
    """

    def __init__(self) -> None:
        self._current_mode: str = ThinkingMode.FAST
        self._mode_history: list[str] = []
        self._switch_count: int = 0

    def determine_mode(
        self,
        intent: str,
        text: str,
        entities: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ThinkingContext:
        """Determine the appropriate thinking mode.

        Args:
            intent: Detected intent.
            text: User input text.
            entities: Extracted entities.
            context: Conversation context.

        Returns:
            ThinkingContext with mode and reasoning.
        """
        entities = entities or {}
        text_lower = text.lower()

        # Step 1: Check intent-based mode
        mode = _INTENT_MODE_MAP.get(intent)

        # Step 2: Check text signals
        if not mode:
            mode = self._detect_mode_from_text(text_lower)

        # Step 3: Check entity signals
        if not mode:
            mode = self._detect_mode_from_entities(entities)

        # Step 4: Default to fast
        if not mode:
            mode = ThinkingMode.FAST

        # Step 5: Track mode switches
        if mode != self._current_mode:
            self._switch_count += 1
            self._current_mode = mode

        self._mode_history.append(mode)
        if len(self._mode_history) > 100:
            self._mode_history = self._mode_history[-50:]

        # Build context
        ctx = ThinkingContext(
            mode=mode,
            confidence=0.8,
            reasoning=self._build_reasoning(mode, intent, text_lower),
            estimated_steps=self._estimate_steps(mode, text_lower),
            requires_tools=mode != ThinkingMode.FAST or intent not in ("GREETING", "DATETIME"),
            requires_research=mode == ThinkingMode.RESEARCH,
            requires_coding=mode == ThinkingMode.CODING,
        )

        return ctx

    def get_current_mode(self) -> str:
        """Get the current thinking mode."""
        return self._current_mode

    def get_stats(self) -> dict[str, Any]:
        mode_counts: dict[str, int] = {}
        for m in self._mode_history:
            mode_counts[m] = mode_counts.get(m, 0) + 1
        return {
            "current_mode": self._current_mode,
            "mode_distribution": mode_counts,
            "total_switches": self._switch_count,
        }

    # ── Private Methods ──

    @staticmethod
    def _detect_mode_from_text(text: str) -> str | None:
        """Detect thinking mode from text signals."""
        coding_score = sum(1 for s in _CODING_SIGNALS if s in text)
        research_score = sum(1 for s in _RESEARCH_SIGNALS if s in text)
        slow_score = sum(1 for s in _SLOW_SIGNALS if s in text)

        if coding_score >= 2:
            return ThinkingMode.CODING
        if research_score >= 2:
            return ThinkingMode.RESEARCH
        if slow_score >= 2:
            return ThinkingMode.SLOW
        return None

    @staticmethod
    def _detect_mode_from_entities(entities: dict[str, Any]) -> str | None:
        """Detect thinking mode from entity types."""
        for key, val in entities.items():
            if isinstance(val, dict):
                v = str(val.get("value", "")).lower()
            else:
                v = str(val).lower()
            if key in ("language", "framework", "technology"):
                return ThinkingMode.CODING
            if key in ("paper", "research", "study"):
                return ThinkingMode.RESEARCH
        return None

    @staticmethod
    def _estimate_steps(mode: str, text: str) -> int:
        """Estimate number of steps for the task."""
        if mode == ThinkingMode.FAST:
            return 1
        if mode == ThinkingMode.CODING:
            return 3
        if mode == ThinkingMode.RESEARCH:
            return 4
        # Slow
        compound_markers = [" and ", " then ", " after ", " also "]
        count = sum(1 for m in compound_markers if m in text)
        return max(2, count + 1)

    @staticmethod
    def _build_reasoning(mode: str, intent: str, text: str) -> str:
        """Build reasoning for the mode selection."""
        if mode == ThinkingMode.CODING:
            return "Coding signals detected, using project-aware mode"
        if mode == ThinkingMode.RESEARCH:
            return "Research signals detected, using multi-source mode"
        if mode == ThinkingMode.SLOW:
            return "Complex task detected, using slow thinking mode"
        return "Simple task, using fast thinking mode"


# ════════════════════════════════════════════════════════════════════
# RESEARCH MODE
# ════════════════════════════════════════════════════════════════════

class ResearchMode:
    """Multi-source research pipeline.

    Plan → Search → Collect → Compare → Verify → Summarize
    Never relies on one source.
    """

    def plan_research(self, query: str) -> list[str]:
        """Plan research steps."""
        return [
            f"Search primary sources for: {query}",
            "Cross-reference with secondary sources",
            "Verify key claims",
            "Synthesize findings",
        ]

    def get_sources(self, domain: str) -> list[str]:
        """Get recommended sources for a domain."""
        _DOMAIN_SOURCES: dict[str, list[str]] = {
            "programming": ["GitHub", "Stack Overflow", "Official Docs"],
            "academic": ["Arxiv", "Google Scholar", "PubMed"],
            "news": ["Google News", "Reuters", "AP"],
            "general": ["Wikipedia", "Google", "Reddit"],
        }
        return _DOMAIN_SOURCES.get(domain, _DOMAIN_SOURCES["general"])


# ════════════════════════════════════════════════════════════════════
# CODING MODE
# ════════════════════════════════════════════════════════════════════

class CodingMode:
    """Project-aware coding pipeline.

    Read Project → Understand → Find Dependencies → Analyze →
    Reason → Generate → Verify → Explain
    """

    def plan_coding(self, task: str, project: str = "") -> list[str]:
        """Plan coding steps."""
        steps = []
        if project:
            steps.append(f"Understand project: {project}")
        steps.extend([
            "Analyze requirements",
            "Identify dependencies",
            "Generate solution",
            "Verify correctness",
            "Explain approach",
        ])
        return steps

    def get_project_info(self, project_path: str) -> dict[str, Any]:
        """Get basic project information."""
        return {
            "path": project_path,
            "languages": [],
            "frameworks": [],
            "dependencies": [],
            "entry_points": [],
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCES
# ════════════════════════════════════════════════════════════════════

thinking_mode_manager = ThinkingModeManager()
research_mode = ResearchMode()
coding_mode = CodingMode()
