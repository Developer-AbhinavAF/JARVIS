"""Cognitive Architecture for JARVIS AI.

The thinking brain.

Every execution goes through:
Perception → Attention → Decision → Execute → Verify → Reflect → Learn

This is what makes JARVIS think before acting, never blindly execute,
and always try to understand the user's true intent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .perception import PerceptionLayer, Situation
from .attention import AttentionSystem, Focus
from .decision_engine import DecisionEngine, DecisionOption
from .reflection import ReflectionEngine, Reflection
from .experience import ExperienceLearning, experience_learning
from .thinking_modes import (
    ThinkingMode,
    ThinkingModeManager,
    ThinkingContext,
    ResearchMode,
    CodingMode,
    thinking_mode_manager,
    research_mode,
    coding_mode,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# COGNITIVE PIPELINE STATE
# ════════════════════════════════════════════════════════════════════

@dataclass
class CognitiveState:
    """Complete state of a single cognitive cycle."""
    # Perception
    situation: Situation | None = None

    # Attention
    focus: Focus | None = None

    # Thinking
    thinking_ctx: ThinkingContext | None = None

    # Decision
    decision_options: list[DecisionOption] = None
    chosen_option: DecisionOption | None = None

    # Execution
    execution_result: Any = None
    execution_success: bool = False
    execution_error: str = ""

    # Reflection
    reflection: Reflection | None = None

    # Timing
    perception_ms: float = 0.0
    attention_ms: float = 0.0
    decision_ms: float = 0.0
    total_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.decision_options is None:
            self.decision_options = []


# ════════════════════════════════════════════════════════════════════
# COGNITIVE ENGINE
# ════════════════════════════════════════════════════════════════════

class CognitiveEngine:
    """The executive brain.

    Orchestrates the full cognitive loop:
    1. PERCEIVE — Build understanding of current situation
    2. ATTEND — Filter and prioritize what matters
    3. THINK — Select thinking mode
    4. DECIDE — Generate and evaluate options
    5. ACT — Execute the chosen action
    6. VERIFY — Check the result
    7. REFLECT — Analyze what happened and learn

    Every step produces context for the next step.
    """

    def __init__(self) -> None:
        self.perception = PerceptionLayer()
        self.attention = AttentionSystem()
        self.decision = DecisionEngine()
        self.reflection_engine = ReflectionEngine()
        self.experience = experience_learning
        self.thinking_modes = thinking_mode_manager
        self.research = research_mode
        self.coding = coding_mode

        self._cycle_count = 0
        self._current_state: CognitiveState | None = None

    def process(
        self,
        text: str,
        intent: str = "",
        entities: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        action_executor=None,
    ) -> CognitiveState:
        """Run the full cognitive cycle.

        Args:
            text: User input.
            intent: Detected intent (from NLP pipeline).
            entities: Extracted entities.
            context: Conversation context.
            action_executor: Callable to execute the chosen action.

        Returns:
            CognitiveState with full cycle results.
        """
        import time

        state = CognitiveState()
        self._cycle_count += 1
        start = time.perf_counter()

        # ── 1. PERCEIVE ──
        t0 = time.perf_counter()
        state.situation = self.perception.observe(text, context)
        state.perception_ms = (time.perf_counter() - t0) * 1000

        # ── 2. ATTEND ──
        t0 = time.perf_counter()
        state.focus = self.attention.focus(
            state.situation,
            intent,
            entities,
        )
        state.attention_ms = (time.perf_counter() - t0) * 1000

        # ── 3. THINK — Select Mode ──
        state.thinking_ctx = self.thinking_modes.determine_mode(
            intent, text, entities, context,
        )

        # ── 4. DECIDE ──
        t0 = time.perf_counter()

        decision = self.decision.decide(
            state.situation,
            state.focus,
            intent,
            entities or {},
        )

        state.chosen_option = decision.chosen
        state.decision_options = decision.all_options
        state.decision_ms = (time.perf_counter() - t0) * 1000

        # ── 5. ACT ──
        if action_executor and state.chosen_option:
            try:
                state.execution_result = action_executor(
                    text, intent, entities or {},
                )
                state.execution_success = state.execution_result is not None
            except Exception as e:
                state.execution_error = str(e)
                state.execution_success = False

        # ── 6. VERIFY + 7. REFLECT ──
        if state.chosen_option:
            state.reflection = self.reflection_engine.reflect(
                intent,
                state.chosen_option.name,
                state.execution_success,
            )

        # ── 8. LEARN ──
        self.experience.record(
            intent=intent,
            tool_used=state.chosen_option.name if state.chosen_option else "",
            success=state.execution_success,
            confidence=state.chosen_option.confidence if state.chosen_option else 0.5,
            thinking_mode=state.thinking_ctx.mode if state.thinking_ctx else "fast",
            user_emotion=context.get("emotion", "neutral") if context else "neutral",
            response_quality=0.5,
            error=state.execution_error,
        )

        state.total_ms = (time.perf_counter() - start) * 1000
        self._current_state = state

        return state

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_cycles": self._cycle_count,
            "thinking_modes": self.thinking_modes.get_stats(),
            "experience": self.experience.get_stats(),
        }

    def process_without_execution(
        self,
        text: str,
        intent: str = "",
        entities: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CognitiveState:
        """Run cognitive cycle without executing (for NLP-only mode)."""
        return self.process(text, intent, entities, context, action_executor=None)


# ════════════════════════════════════════════════════════════════════
# CONVENIENCE
# ════════════════════════════════════════════════════════════════════

cognitive_engine = CognitiveEngine()

__all__ = [
    "CognitiveEngine",
    "CognitiveState",
    "cognitive_engine",
]
