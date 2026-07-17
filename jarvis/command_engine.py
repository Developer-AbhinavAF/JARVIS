"""Unified NLP Command Engine for JARVIS AI OS v4.0 — Semantic Engine.

Production-grade command understanding engine that achieves human-level
natural language understanding. Uses semantic intent detection instead
of keyword matching.

Architecture:
  User Input
    → Semantic NLP Pipeline (language detect → normalize → parse → intent → entities → context → goal → plan → tool → params)
    → Confidence Scoring
    → Tool Execution (tools first, LLM last)
    → Self-Learning (track unknowns, usage patterns)

The LLM is ONLY called when no tool matches. This is mandatory.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from jarvis.tool_metadata import (
    ToolCatalog,
    ToolMeta,
    catalog,
    WEBSITES,
    SEARCH_SITES,
    FOLDERS,
)

# Import the new semantic NLP engine
from jarvis.nlp import (
    nlp_engine,
    SemanticNLPEngine,
    NLPOutput,
    normalize,
)
from jarvis.nlp.context_memory import ContextMemory, context_memory
from jarvis.nlp.self_learning import SelfLearningEngine, self_learning
from jarvis.nlp.intent_classifier import IntentClassifier, IntentResult
from jarvis.nlp.entity_extractor import EntityExtractor
from jarvis.nlp.confidence import ConfidenceScorer
from jarvis.nlp.utils import GoalCategory, ExecutionMode

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of command engine processing."""
    matched: bool
    tool_name: str = ""
    handler_name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    tool_meta: ToolMeta | None = None
    raw_text: str = ""
    normalized_text: str = ""
    message: str = ""
    # Extended fields for semantic NLP
    match_method: str = "semantic"
    intent_result: IntentResult | None = None
    is_multi: bool = False
    execution_plan: list[dict[str, Any]] = field(default_factory=list)
    # New semantic fields
    goal: str = ""
    language: str = ""
    processing_time_ms: float = 0.0
    nlp_output: NLPOutput | None = None


class CommandEngine:
    """Unified NLP command engine with semantic understanding.

    This engine uses the new semantic NLP pipeline:
    1. Language detection (English, Hindi, Hinglish)
    2. Semantic normalization (filler removal, Hinglish transliteration)
    3. Sentence parsing (action-object extraction)
    4. Semantic intent classification (not keyword matching)
    5. Entity extraction (fuzzy matching)
    6. Context resolution (pronouns, follow-ups)
    7. Goal detection (implicit objectives)
    8. Tool resolution (intent + entities + context → tool)
    9. Self-learning (track unknowns, usage patterns)
    """

    def __init__(self, tool_catalog: ToolCatalog | None = None) -> None:
        self.catalog = tool_catalog or catalog
        self.nlp = nlp_engine
        self.context_memory = context_memory
        self.self_learning = self_learning
        # Keep legacy components for fallback
        self.legacy_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.confidence_scorer = ConfidenceScorer()

    def process(self, text: str) -> CommandResult:
        """Process user input through the semantic NLP pipeline.

        This is the main entry point. It processes input through:
        1. Full semantic NLP pipeline
        2. Tool matching and execution planning
        3. Confidence scoring
        """
        raw = text
        t0 = time.time()

        # ── Phase 1: Run through semantic NLP pipeline ──
        nlp_output = self.nlp.process(text)

        # ── Phase 2: Check for LLM fallback ──
        if nlp_output.should_fallback_to_llm:
            elapsed = (time.time() - t0) * 1000
            return CommandResult(
                matched=False,
                raw_text=raw,
                normalized_text=nlp_output.normalized_text,
                processing_time_ms=elapsed,
                nlp_output=nlp_output,
            )

        # ── Phase 3: Map NLP output to CommandResult ──
        result = self._nlp_to_command_result(nlp_output, raw, t0)

        # ── Phase 4: Record for learning ──
        if result.matched:
            self.self_learning.record_successful_command(
                text=raw,
                normalized=result.normalized_text,
                intent=result.tool_name,
                tool_name=result.handler_name,
                confidence=result.confidence,
            )
        else:
            self.self_learning.record_failed_command(
                text=raw,
                normalized=nlp_output.normalized_text,
                suggested_intent=nlp_output.intent,
                suggested_confidence=nlp_output.intent_confidence,
            )

        return result

    def _nlp_to_command_result(
        self, output: NLPOutput, raw: str, t0: float
    ) -> CommandResult:
        """Convert NLPOutput to CommandResult."""
        elapsed = (time.time() - t0) * 1000

        # Check if tool was resolved
        if not output.tool:
            # Try catalog fallback for common patterns
            catalog_result = self._try_catalog_fallback(output.normalized_text)
            if catalog_result:
                return catalog_result

            return CommandResult(
                matched=False,
                raw_text=raw,
                normalized_text=output.normalized_text,
                processing_time_ms=elapsed,
                nlp_output=output,
            )

        # Build confirmation message
        message = self._make_confirmation_message(output.tool, output.parameters)

        return CommandResult(
            matched=True,
            tool_name=output.tool,
            handler_name=output.handler,
            params=output.parameters,
            confidence=output.confidence_score,
            raw_text=raw,
            normalized_text=output.normalized_text,
            message=message,
            match_method=output.match_method,
            is_multi=output.is_multi_intent,
            execution_plan=output.planner,
            goal=output.goal.value if output.goal else "",
            language=output.language.value if output.language else "",
            processing_time_ms=elapsed,
            nlp_output=output,
        )

    def _try_catalog_fallback(self, normalized: str) -> CommandResult | None:
        """Try catalog pattern matching as fallback."""
        meta = self.catalog.find_by_pattern(normalized)
        if meta:
            params = {}
            if meta.extract_params:
                try:
                    params = meta.extract_params(normalized)
                except Exception:
                    params = {}

            handler_name = meta.handler_name
            message = self._make_confirmation_message(meta.name, params)

            return CommandResult(
                matched=True,
                tool_name=meta.name,
                handler_name=handler_name,
                params=params,
                confidence=meta.confidence,
                tool_meta=meta,
                normalized_text=normalized,
                message=message,
                match_method="catalog_fallback",
            )

        return None

    def _make_confirmation_message(self, tool_name: str, params: dict) -> str:
        """Make a confirmation message for a tool execution."""
        messages = {
            "OPEN_WEBSITE": lambda p: f"Opening {p.get('target', 'website').title()}...",
            "OPEN_APP": lambda p: f"Opening {p.get('target', 'app').title()}...",
            "CLOSE_APP": lambda p: f"Closing {p.get('target', 'app').title()}...",
            "SEARCH_WEB": lambda p: f"Searching for: {p.get('query', 'your query')}",
            "SEARCH_ON_PLATFORM": lambda p: f"Searching {p.get('platform', 'platform')} for: {p.get('query', 'query')}",
            "PLAY_MUSIC": lambda p: f"Playing: {p.get('query', 'music')}",
            "PLAY_YOUTUBE": lambda p: f"Playing on YouTube: {p.get('query', 'music')}",
            "GET_WEATHER": lambda p: f"Getting weather for {p.get('city', 'your location')}...",
            "GET_NEWS": lambda p: "Getting latest news...",
            "SCREENSHOT": lambda p: "Taking screenshot...",
            "VOLUME_CONTROL": lambda p: f"Volume {p.get('action', 'up')}...",
            "BRIGHTNESS_CONTROL": lambda p: f"Brightness {p.get('action', 'up')}...",
            "SYSTEM_POWER": lambda p: f"System {p.get('action', 'shutdown')}...",
            "CALCULATOR": lambda p: f"Calculating: {p.get('expression', '...')}",
            "TIMER": lambda p: f"Setting timer for {p.get('seconds', '?')} seconds...",
            "DATETIME": lambda p: "Getting current date and time...",
            "SAVE_MEMORY": lambda p: "Saving to memory...",
            "RECALL_MEMORY": lambda p: "Searching memory...",
            "JOKE": lambda p: "Here's a joke...",
            "QUOTE": lambda p: "Here's an inspirational quote...",
            "FLIP_COIN": lambda p: "Flipping a coin...",
            "DICE_ROLL": lambda p: "Rolling a dice...",
            "NASA_APOD": lambda p: "Getting NASA Picture of the Day...",
            "STOCK_QUOTE": lambda p: f"Getting stock quote for {p.get('symbol', '...')}...",
            "GREETING": lambda p: "Hello! How can I help you?",
            "SYSTEM_STATUS": lambda p: "Getting system status...",
            "CLIPBOARD": lambda p: "Getting clipboard contents...",
            "WINDOW_CONTROL": lambda p: f"Window {p.get('action', 'control')}...",
            "ADD_TODO": lambda p: "Adding to-do item...",
            "LIST_TODOS": lambda p: "Listing to-do items...",
            "IP_LOOKUP": lambda p: "Looking up IP address...",
            "RANDOM_FACT": lambda p: "Here's a random fact...",
        }

        msg_fn = messages.get(tool_name)
        if msg_fn:
            try:
                return msg_fn(params)
            except Exception:
                pass

        return f"Executing {tool_name}..."

    def get_learning_stats(self) -> dict[str, Any]:
        """Get self-learning statistics."""
        return self.self_learning.get_stats()

    def get_frequent_commands(self, top_n: int = 20) -> list[dict[str, Any]]:
        """Get most frequently used commands."""
        return self.self_learning.get_frequent_commands(top_n)

    def get_unknown_commands(self, top_n: int = 20) -> list[dict[str, Any]]:
        """Get commands that weren't understood."""
        return self.self_learning.get_unknown_commands(top_n)


# Global instance
engine = CommandEngine()
