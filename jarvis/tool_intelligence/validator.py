"""Execution Validator for JARVIS.

Every tool execution returns:
- Status (success/failure)
- Warnings
- Execution Time
- Output
- Confidence
- Retry Possible
- Recovery Suggestion

The AI verifies every result.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# EXECUTION RESULT
# ════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionResult:
    """Validated result of a tool execution."""
    success: bool
    output: str
    tool_name: str = ""
    execution_time_ms: float = 0.0
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    retry_possible: bool = False
    recovery_suggestion: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output[:500],
            "tool": self.tool_name,
            "execution_time_ms": round(self.execution_time_ms, 1),
            "confidence": round(self.confidence, 3),
            "warnings": self.warnings,
            "errors": self.errors,
            "retry_possible": self.retry_possible,
            "recovery_suggestion": self.recovery_suggestion,
        }


# ════════════════════════════════════════════════════════════════════
# FAILURE PATTERNS
# ════════════════════════════════════════════════════════════════════

# Patterns that indicate failure in tool output
_FAILURE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(error|exception|traceback|failed|failure)\b", re.I),
    re.compile(r"\b(could not|cannot|can't|unable to)\b", re.I),
    re.compile(r"\b(not found|does not exist|doesn't exist)\b", re.I),
    re.compile(r"\b(permission denied|access denied|forbidden)\b", re.I),
    re.compile(r"\b(timeout|timed out|connection refused)\b", re.I),
    re.compile(r"\b(no such|missing|invalid)\b", re.I),
]

# Patterns that indicate success
_SUCCESS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(success|done|completed|finished|saved|created|opened)\b", re.I),
    re.compile(r"\b(ok|okay|yes|true|1)\b", re.I),
]

# Empty/meaningless output patterns
_EMPTY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*$"),
    re.compile(r"^(none|null|undefined|void|nan)$", re.I),
    re.compile(r"^(error:\s*)$", re.I),
]


# ════════════════════════════════════════════════════════════════════
# EXECUTION VALIDATOR
# ════════════════════════════════════════════════════════════════════

class ExecutionValidator:
    """Validates tool execution results.

    Checks:
    1. Output is not empty
    2. Output doesn't contain error patterns
    3. Output matches expected format
    4. Execution time is reasonable
    5. Confidence is acceptable
    """

    def __init__(self) -> None:
        self._validation_history: list[ExecutionResult] = []

    def validate(
        self,
        output: str,
        tool_name: str = "",
        execution_time_ms: float = 0.0,
        expected_format: str | None = None,
    ) -> ExecutionResult:
        """Validate a tool execution result.

        Args:
            output: The raw output from the tool.
            tool_name: Name of the tool that produced the output.
            execution_time_ms: How long the execution took.
            expected_format: Optional expected output format.

        Returns:
            ExecutionResult with validation details.
        """
        result = ExecutionResult(
            success=True,
            output=output,
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
        )

        # Check 1: Empty output
        if self._is_empty(output):
            result.success = False
            result.confidence = 0.0
            result.warnings.append("Empty output")
            result.recovery_suggestion = "Retry with different parameters"
            result.retry_possible = True
            self._record(result)
            return result

        # Check 2: Error patterns
        errors = self._detect_errors(output)
        if errors:
            result.errors = errors
            result.success = False
            result.confidence = 0.1
            result.retry_possible = True
            result.recovery_suggestion = self._suggest_recovery(errors, tool_name)
            self._record(result)
            return result

        # Check 3: Success patterns
        has_success = self._detect_success(output)

        # Check 4: Execution time
        if execution_time_ms > 30000:  # > 30 seconds
            result.warnings.append(f"Slow execution: {execution_time_ms:.0f}ms")
            result.confidence *= 0.8

        if execution_time_ms > 60000:  # > 60 seconds
            result.warnings.append("Very slow execution")
            result.confidence *= 0.6

        # Check 5: Output quality
        if len(output) < 5 and not has_success:
            result.warnings.append("Very short output")
            result.confidence *= 0.7

        if len(output) > 10000:
            result.warnings.append("Very long output (may be truncated)")
            result.confidence *= 0.9

        # Check 6: Expected format
        if expected_format:
            if not self._matches_format(output, expected_format):
                result.warnings.append(f"Output doesn't match expected format: {expected_format}")
                result.confidence *= 0.8

        # Final confidence
        if has_success:
            result.confidence = max(result.confidence, 0.8)

        result.confidence = max(0.0, min(1.0, result.confidence))

        self._record(result)
        return result

    def validate_with_context(
        self,
        output: str,
        intent: str,
        tool_name: str,
        entities: dict[str, Any] | None = None,
        execution_time_ms: float = 0.0,
    ) -> ExecutionResult:
        """Validate with NLP context for smarter validation."""
        result = self.validate(output, tool_name, execution_time_ms)

        # Intent-specific checks
        if intent == "GET_WEATHER":
            if not any(w in output.lower() for w in ["temperature", "weather", "°", "degree", "celsius", "fahrenheit"]):
                result.warnings.append("Weather output doesn't contain expected weather data")
                result.confidence *= 0.8

        elif intent == "DATETIME":
            if not any(w in output for w in [":", "AM", "PM", "am", "pm", "20"]):
                result.warnings.append("Datetime output doesn't look like a timestamp")
                result.confidence *= 0.8

        elif intent == "CALCULATOR":
            # Check if output looks like a number
            cleaned = output.strip().replace(",", "")
            try:
                float(cleaned)
            except ValueError:
                if not any(w in output.lower() for w in ["error", "invalid", "cannot"]):
                    result.warnings.append("Calculator output doesn't look like a number")
                    result.confidence *= 0.7

        elif intent == "JOKE":
            if len(output) < 20:
                result.warnings.append("Joke seems too short")
                result.confidence *= 0.8

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get validation statistics."""
        total = len(self._validation_history)
        successes = sum(1 for r in self._validation_history if r.success)
        return {
            "total_validations": total,
            "success_rate": round(successes / max(total, 1), 4),
            "avg_confidence": round(
                sum(r.confidence for r in self._validation_history) / max(total, 1), 4,
            ),
            "total_warnings": sum(len(r.warnings) for r in self._validation_history),
            "total_errors": sum(len(r.errors) for r in self._validation_history),
        }

    # ── Private Methods ──

    def _is_empty(self, output: str) -> bool:
        """Check if output is empty or meaningless."""
        if not output:
            return True
        for pattern in _EMPTY_PATTERNS:
            if pattern.search(output):
                return True
        return False

    def _detect_errors(self, output: str) -> list[str]:
        """Detect error patterns in output."""
        errors = []
        for pattern in _FAILURE_PATTERNS:
            match = pattern.search(output)
            if match:
                errors.append(match.group(0))
        return errors

    def _detect_success(self, output: str) -> bool:
        """Detect success patterns in output."""
        for pattern in _SUCCESS_PATTERNS:
            if pattern.search(output):
                return True
        return False

    def _suggest_recovery(self, errors: list[str], tool_name: str) -> str:
        """Suggest recovery based on detected errors."""
        error_text = " ".join(errors).lower()

        if "permission" in error_text or "denied" in error_text:
            return "Run with elevated privileges or try alternative approach"
        if "not found" in error_text or "does not exist" in error_text:
            return "Check input parameters or try alternative tool"
        if "timeout" in error_text or "timed out" in error_text:
            return "Retry with shorter timeout or simpler request"
        if "connection" in error_text or "network" in error_text:
            return "Check network connection and retry"
        return "Retry with different parameters or alternative tool"

    def _matches_format(self, output: str, expected_format: str) -> bool:
        """Check if output matches expected format."""
        if expected_format == "json":
            try:
                import json
                json.loads(output)
                return True
            except (json.JSONDecodeError, ValueError):
                return False
        elif expected_format == "number":
            try:
                float(output.strip().replace(",", ""))
                return True
            except ValueError:
                return False
        elif expected_format == "url":
            return output.startswith("http://") or output.startswith("https://")
        return True

    def _record(self, result: ExecutionResult) -> None:
        """Record validation result."""
        self._validation_history.append(result)
        if len(self._validation_history) > 500:
            self._validation_history = self._validation_history[-250:]


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

execution_validator = ExecutionValidator()
