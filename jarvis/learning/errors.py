"""Error Learning — Every failure becomes knowledge.

Store: Error, Cause, Fix, Recovery Time, Success Rate
Future occurrences should become easier to solve.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ErrorRecord:
    """A learned error pattern."""
    error_id: str = ""
    error_type: str = ""
    error_message: str = ""
    cause: str = ""
    fix: str = ""
    tool: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    occurrences: int = 1
    fix_success_rate: float = 0.0
    avg_recovery_ms: float = 0.0
    last_seen: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "error_message": self.error_message[:100],
            "cause": self.cause,
            "fix": self.fix,
            "occurrences": self.occurrences,
            "fix_success_rate": round(self.fix_success_rate, 3),
        }


class ErrorLearner:
    """Learns from errors and suggests fixes."""

    def __init__(self) -> None:
        self._errors: dict[str, ErrorRecord] = {}
        self._error_counter: int = 0
        self._total_errors: int = 0
        self._total_fixes: int = 0

    def learn_error(
        self,
        error_type: str,
        error_message: str,
        cause: str = "",
        fix: str = "",
        tool: str = "",
        context: dict | None = None,
    ) -> ErrorRecord:
        """Learn from an error."""
        err_key = f"{error_type}:{error_message[:50]}"

        if err_key in self._errors:
            record = self._errors[err_key]
            record.occurrences += 1
            record.last_seen = time.time()
            if fix:
                record.fix = fix
                record.fix_success_rate = min(1.0, record.fix_success_rate + 0.1)
        else:
            self._error_counter += 1
            record = ErrorRecord(
                error_id=f"err_{self._error_counter:04d}",
                error_type=error_type,
                error_message=error_message,
                cause=cause,
                fix=fix,
                tool=tool,
                context=context or {},
                fix_success_rate=0.5 if fix else 0.0,
            )
            self._errors[err_key] = record

        self._total_errors += 1
        return record

    def record_fix(self, error_id: str, success: bool) -> None:
        """Record whether a fix worked."""
        for record in self._errors.values():
            if record.error_id == error_id:
                if success:
                    record.fix_success_rate = min(1.0, record.fix_success_rate + 0.15)
                    self._total_fixes += 1
                else:
                    record.fix_success_rate = max(0.0, record.fix_success_rate - 0.2)
                break

    def suggest_fix(self, error_type: str, error_message: str = "") -> str | None:
        """Suggest a fix for a known error."""
        err_key = f"{error_type}:{error_message[:50]}"
        record = self._errors.get(err_key)
        if record and record.fix and record.fix_success_rate > 0.3:
            return record.fix
        # Fuzzy search
        for key, rec in self._errors.items():
            if rec.error_type == error_type and rec.fix and rec.fix_success_rate >= 0.3:
                return rec.fix
        return None

    def should_ignore(self, error_type: str) -> bool:
        """Check if a recurring error can be safely ignored."""
        for rec in self._errors.values():
            if rec.error_type == error_type and rec.occurrences > 5 and rec.fix_success_rate > 0.8:
                return True
        return False

    def get_errors(self, tool: str = "", limit: int = 50) -> list[dict[str, Any]]:
        records = list(self._errors.values())
        if tool:
            records = [r for r in records if r.tool == tool]
        records.sort(key=lambda r: -r.occurrences)
        return [r.to_dict() for r in records[:limit]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "unique_errors": len(self._errors),
            "total_errors": self._total_errors,
            "total_fixes": self._total_fixes,
            "fix_rate": round(self._total_fixes / max(1, self._total_errors), 3),
        }


error_learner = ErrorLearner()

__all__ = ["ErrorLearner", "ErrorRecord", "error_learner"]
