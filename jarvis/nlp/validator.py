"""Confidence scoring and validation for JARVIS NLP engine.

Determines whether to auto-execute, ask confirmation, fallback to LLM,
or ask for clarification. Also validates the complete NLP output.
"""

from __future__ import annotations

from dataclasses import dataclass

from .utils import NLPOutput, ExecutionMode


# ════════════════════════════════════════════════════════════════════
# CONFIDENCE THRESHOLDS
# ════════════════════════════════════════════════════════════════════

class Thresholds:
    """Confidence threshold levels."""
    HIGH = 0.90       # Execute immediately
    MEDIUM = 0.75     # Execute normally
    MODERATE = 0.60   # Execute non-destructive, confirm destructive
    LOW = 0.45        # Consider LLM fallback
    MINIMAL = 0.0     # Always use LLM


# Destructive actions that need higher confidence
DESTRUCTIVE_ACTIONS: set[str] = {
    "system_power", "shutdown", "restart", "close_app",
    "delete_file", "delete_folder", "kill_process",
}


@dataclass
class ValidationResult:
    """Result of NLP output validation."""
    is_valid: bool
    confidence_score: float
    confidence_level: str  # "high", "medium", "moderate", "low", "minimal"
    execution_mode: ExecutionMode
    requires_clarification: bool
    clarification_message: str
    issues: list[str]

    @property
    def should_execute(self) -> bool:
        return self.execution_mode == ExecutionMode.AUTO

    @property
    def should_fallback_to_llm(self) -> bool:
        return self.execution_mode == ExecutionMode.FALLBACK_LLM


class ConfidenceScorer:
    """Scores confidence and determines execution strategy.

    Uses multiple signals:
    1. Raw intent confidence from the semantic engine
    2. Entity completeness (are required entities present?)
    3. Context support (does context confirm this intent?)
    4. Action safety (destructive actions need higher confidence)
    """

    def score(
        self,
        raw_confidence: float,
        has_entities: bool = True,
        entity_count: int = 0,
        has_context: bool = False,
        is_destructive: bool = False,
        is_followup: bool = False,
        language_confidence: float = 1.0,
    ) -> ValidationResult:
        """Score confidence and determine execution mode.

        Args:
            raw_confidence: Base confidence from intent detection (0.0-1.0)
            has_entities: Whether required entities were found
            entity_count: Number of entities extracted
            has_context: Whether conversation context supports this intent
            is_destructive: Whether the action is destructive
            is_followup: Whether this is a follow-up command
            language_confidence: Confidence of language detection

        Returns:
            ValidationResult with execution decision
        """
        issues = []
        adjusted = raw_confidence

        # Adjust: entity completeness
        if not has_entities:
            adjusted *= 0.80
            issues.append("Missing required entities")

        # Adjust: context support
        if has_context:
            adjusted = min(1.0, adjusted + 0.05)

        # Adjust: multi-entity bonus
        if entity_count >= 2:
            adjusted = min(1.0, adjusted + 0.03)

        # Adjust: language confidence
        if language_confidence < 0.5:
            adjusted *= 0.90
            issues.append("Low language detection confidence")

        # Clamp
        adjusted = max(0.0, min(1.0, adjusted))

        # Determine level and execution mode
        if adjusted >= Thresholds.HIGH:
            level = "high"
            mode = ExecutionMode.AUTO
            clarify = False
        elif adjusted >= Thresholds.MEDIUM:
            level = "medium"
            mode = ExecutionMode.AUTO
            clarify = False
        elif adjusted >= Thresholds.MODERATE:
            level = "moderate"
            if is_destructive:
                mode = ExecutionMode.CONFIRM
                clarify = True
            else:
                mode = ExecutionMode.AUTO
            clarify = is_destructive
        elif adjusted >= Thresholds.LOW:
            level = "low"
            mode = ExecutionMode.FALLBACK_LLM
            clarify = False
        else:
            level = "minimal"
            mode = ExecutionMode.FALLBACK_LLM
            clarify = False

        # Generate clarification message if needed
        clarification_msg = ""
        if clarify:
            clarification_msg = "This action cannot be undone. Should I proceed?"

        return ValidationResult(
            is_valid=adjusted >= Thresholds.MODERATE,
            confidence_score=adjusted,
            confidence_level=level,
            execution_mode=mode,
            requires_clarification=clarify,
            clarification_message=clarification_msg,
            issues=issues,
        )

    def should_block_llm(self, confidence: float) -> bool:
        """Check if a tool match should block the LLM from responding."""
        return confidence >= Thresholds.HIGH


class NLPOutputValidator:
    """Validates the complete NLP output for correctness."""

    def validate(self, output: NLPOutput) -> ValidationResult:
        """Validate a complete NLP output.

        Checks:
        1. Has an intent
        2. Has a tool (unless LLM fallback)
        3. Has required parameters
        4. Confidence is reasonable
        """
        issues = []

        if not output.intent:
            issues.append("No intent detected")

        if not output.tool and output.execution_mode != ExecutionMode.FALLBACK_LLM:
            issues.append("No tool selected")

        if output.tool and not output.handler:
            issues.append("Tool selected but no handler defined")

        # Score based on completeness
        has_entities = bool(output.entities)
        entity_count = len(output.entities)

        return ConfidenceScorer().score(
            raw_confidence=output.intent_confidence,
            has_entities=has_entities,
            entity_count=entity_count,
            has_context=bool(output.context),
            is_destructive=output.tool in DESTRUCTIVE_ACTIONS,
        )
