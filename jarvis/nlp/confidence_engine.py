"""Multi-signal confidence engine for JARVIS NLP.

Combines signals from intent detection, entity extraction, goal
detection, context resolution, planner, and tool selection into
a single confidence score with high/medium/low tiers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jarvis.nlp.utils import ExecutionMode


SIGNAL_WEIGHTS: dict[str, float] = {
    "intent": 0.35,
    "entity": 0.15,
    "goal": 0.10,
    "context": 0.10,
    "planner": 0.10,
    "tool": 0.10,
    "language": 0.05,
    "safety": 0.05,
}

TIER_HIGH = 0.85
TIER_MEDIUM = 0.65
TIER_LOW = 0.40


@dataclass
class ConfidenceSignals:
    intent_score: float = 0.0
    entity_score: float = 0.0
    goal_score: float = 0.0
    context_score: float = 0.0
    planner_score: float = 0.0
    tool_score: float = 0.0
    language_score: float = 1.0
    safety_score: float = 1.0

    def to_dict(self) -> dict[str, float]:
        return {
            "intent": self.intent_score,
            "entity": self.entity_score,
            "goal": self.goal_score,
            "context": self.context_score,
            "planner": self.planner_score,
            "tool": self.tool_score,
            "language": self.language_score,
            "safety": self.safety_score,
        }


@dataclass
class ConfidenceResult:
    score: float = 0.0
    tier: str = "minimal"
    execution_mode: ExecutionMode = ExecutionMode.FALLBACK_LLM
    signals: ConfidenceSignals = field(default_factory=ConfidenceSignals)
    signal_breakdown: dict[str, float] = field(default_factory=dict)
    requires_confirmation: bool = False
    should_fallback_to_llm: bool = True
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "tier": self.tier,
            "execution_mode": self.execution_mode.value,
            "signals": self.signals.to_dict(),
            "signal_breakdown": self.signal_breakdown,
            "requires_confirmation": self.requires_confirmation,
            "should_fallback_to_llm": self.should_fallback_to_llm,
            "reasoning": self.reasoning,
        }


class ConfidenceEngine:
    """Aggregates confidence signals from all NLP modules.

    Takes individual confidence scores and produces a single
    weighted confidence score with tier classification and
    execution mode decision.
    """

    def calculate(
        self,
        signals: ConfidenceSignals,
        is_destructive: bool = False,
        has_tool: bool = True,
        is_followup: bool = False,
    ) -> ConfidenceResult:
        """Calculate overall confidence from all signals."""
        breakdown: dict[str, float] = {}
        weighted_sum = 0.0

        signal_values = signals.to_dict()
        for name, weight in SIGNAL_WEIGHTS.items():
            value = signal_values.get(name, 0.0)
            weighted = weight * value
            breakdown[name] = round(weighted, 4)
            weighted_sum += weighted

        score = min(weighted_sum, 1.0)

        # CRITICAL FIX: If intent score is high, floor the overall confidence
        # This ensures identified intents always get meaningful confidence
        if signals.intent_score >= 0.80:
            score = max(score, min(signals.intent_score * 0.95, 1.0))
        elif signals.intent_score >= 0.60:
            score = max(score, min(signals.intent_score * 0.85, 1.0))
        elif signals.intent_score > 0.0:
            score = max(score, min(signals.intent_score * 0.70, 1.0))

        # Boost for follow-up commands with strong context
        if is_followup and signals.context_score > 0.7:
            score = min(score + 0.05, 1.0)

        # Penalty for missing tool when one is expected
        if not has_tool and score > 0.3:
            score *= 0.7

        # Determine tier
        if score >= TIER_HIGH:
            tier = "high"
        elif score >= TIER_MEDIUM:
            tier = "medium"
        elif score >= TIER_LOW:
            tier = "low"
        else:
            tier = "minimal"

        # Determine execution mode
        if is_destructive and tier in ("medium", "low"):
            mode = ExecutionMode.CONFIRM
            requires_confirm = True
        elif tier == "high":
            mode = ExecutionMode.AUTO
            requires_confirm = False
        elif tier == "medium":
            mode = ExecutionMode.AUTO
            requires_confirm = False
        elif tier == "low":
            mode = ExecutionMode.FALLBACK_LLM
            requires_confirm = False
        else:
            mode = ExecutionMode.FALLBACK_LLM
            requires_confirm = False

        should_fallback = mode == ExecutionMode.FALLBACK_LLM

        reasoning = self._build_reasoning(tier, score, signals, is_destructive)

        return ConfidenceResult(
            score=round(score, 4),
            tier=tier,
            execution_mode=mode,
            signals=signals,
            signal_breakdown=breakdown,
            requires_confirmation=requires_confirm,
            should_fallback_to_llm=should_fallback,
            reasoning=reasoning,
        )

    def calculate_entity_score(
        self,
        entities: dict[str, Any],
        required_entities: list[str] | None = None,
    ) -> float:
        """Calculate entity completeness score (0.0 to 1.0)."""
        if not required_entities:
            if not entities:
                return 0.3
            return min(0.5 + len(entities) * 0.1, 1.0)

        if not entities:
            return 0.0

        found = sum(1 for e in required_entities if e in entities)
        return found / len(required_entities) if required_entities else 1.0

    def calculate_context_score(
        self,
        has_context: bool,
        context_relevance: float = 0.0,
        is_followup: bool = False,
    ) -> float:
        """Calculate context support score."""
        if not has_context:
            return 0.2
        base = 0.5 + context_relevance * 0.3
        if is_followup:
            base += 0.2
        return min(base, 1.0)

    def calculate_tool_score(
        self,
        tool_found: bool,
        tool_confidence: float = 0.0,
    ) -> float:
        """Calculate tool resolution score."""
        if not tool_found:
            return 0.0
        return max(tool_confidence, 0.5)

    @staticmethod
    def _build_reasoning(
        tier: str,
        score: float,
        signals: ConfidenceSignals,
        is_destructive: bool,
    ) -> str:
        """Build a human-readable reasoning string."""
        parts = [f"Overall score: {score:.2f} ({tier})"]

        if signals.intent_score < 0.3:
            parts.append("Low intent confidence")
        if signals.entity_score < 0.3:
            parts.append("Missing entities")
        if is_destructive:
            parts.append("Destructive action - extra caution")
        if signals.context_score > 0.7:
            parts.append("Strong context support")
        if signals.tool_score < 0.3:
            parts.append("No matching tool found")

        return "; ".join(parts)
