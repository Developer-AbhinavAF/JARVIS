"""Confidence scoring system for JARVIS NLP pipeline.

Determines whether to auto-execute, ask confirmation, or fallback to LLM.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfidenceLevel:
    """Confidence threshold levels."""
    AUTO_EXECUTE: float = 0.95      # Execute immediately, no questions
    EXECUTE: float = 0.90           # Execute normally
    CONFIRM_IF_DESTRUCTIVE: float = 0.80  # Ask confirmation for destructive actions
    LOW_CONFIDENCE: float = 0.70    # Consider LLM fallback
    FALLBACK_TO_LLM: float = 0.0   # Below this, always use LLM


LEVELS = ConfidenceLevel()


@dataclass
class ConfidenceResult:
    """Result of confidence scoring."""
    score: float
    level: str  # "auto_execute", "execute", "confirm", "low", "fallback"
    should_execute: bool
    requires_confirmation: bool
    should_fallback_to_llm: bool
    reason: str

    def __str__(self) -> str:
        return f"ConfidenceResult(score={self.score:.2f}, level={self.level}, execute={self.should_execute}, confirm={self.requires_confirmation}, llm={self.should_fallback_to_llm})"


class ConfidenceScorer:
    """Scores confidence for tool execution decisions."""

    # Destructive actions that require confirmation at lower confidence
    DESTRUCTIVE_ACTIONS: set[str] = {
        "system_power", "shutdown", "restart", "close_app",
        "delete_file", "delete_folder", "kill_process",
    }

    def score(
        self,
        raw_confidence: float,
        action: str | None = None,
        has_entity: bool = True,
        pattern_count: int = 1,
    ) -> ConfidenceResult:
        """Score confidence and determine execution strategy.

        Args:
            raw_confidence: Base confidence from pattern matching (0.0-1.0)
            action: The action/tool name (for destructive check)
            has_entity: Whether required entities were extracted
            pattern_count: Number of patterns that matched (higher = more certain)

        Returns:
            ConfidenceResult with execution decision
        """
        # Adjust confidence based on factors
        adjusted = raw_confidence

        # Boost for multiple pattern matches
        if pattern_count > 1:
            adjusted = min(1.0, adjusted + 0.02 * (pattern_count - 1))

        # Reduce if required entity missing
        if not has_entity:
            adjusted *= 0.85

        # Clamp to valid range
        adjusted = max(0.0, min(1.0, adjusted))

        is_destructive = action in self.DESTRUCTIVE_ACTIONS if action else False

        # Determine level
        if adjusted >= LEVELS.AUTO_EXECUTE:
            level = "auto_execute"
            should_execute = True
            requires_confirmation = False
            should_fallback = False
            reason = "High confidence match"

        elif adjusted >= LEVELS.EXECUTE:
            level = "execute"
            should_execute = True
            requires_confirmation = is_destructive
            should_fallback = False
            reason = "Good confidence match" + (" (destructive - confirmation needed)" if is_destructive else "")

        elif adjusted >= LEVELS.CONFIRM_IF_DESTRUCTIVE:
            level = "confirm"
            should_execute = not is_destructive
            requires_confirmation = True
            should_fallback = False
            reason = "Moderate confidence" + (" - destructive action needs confirmation" if is_destructive else " - executing anyway")

        elif adjusted >= LEVELS.LOW_CONFIDENCE:
            level = "low"
            should_execute = False
            requires_confirmation = False
            should_fallback = True
            reason = "Low confidence - falling back to LLM"

        else:
            level = "fallback"
            should_execute = False
            requires_confirmation = False
            should_fallback = True
            reason = "Very low confidence - using LLM"

        return ConfidenceResult(
            score=adjusted,
            level=level,
            should_execute=should_execute,
            requires_confirmation=requires_confirmation,
            should_fallback_to_llm=should_fallback,
            reason=reason,
        )

    def should_block_llm_response(self, confidence: float) -> bool:
        """Check if a tool match should block the LLM from responding.

        If confidence is high enough and a tool matched, the LLM should
        NEVER be called - even if the tool fails.
        """
        return confidence >= LEVELS.EXECUTE


# Global instance
confidence_scorer = ConfidenceScorer()
