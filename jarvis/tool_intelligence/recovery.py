"""Autonomous Recovery Engine for JARVIS.

NEVER immediately fail.

When execution fails:
1. Analyze the failure
2. Retry with adjusted parameters
3. Try alternative tool
4. Try alternative platform/API
5. Try cached result
6. Ask user as last resort

Every failure is an opportunity to learn.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# FAILURE ANALYSIS
# ════════════════════════════════════════════════════════════════════

@dataclass
class FailureAnalysis:
    """Analysis of why an execution failed."""
    error_type: str          # "network", "permission", "not_found", "timeout", "api_limit", "unknown"
    error_message: str
    is_transient: bool       # Can be retried?
    is_recoverable: bool     # Can we find an alternative?
    suggested_action: str    # "retry", "alternative_tool", "alternative_platform", "cached", "ask_user"
    confidence: float        # How confident we are in the analysis
    recovery_params: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "error_message": self.error_message,
            "is_transient": self.is_transient,
            "is_recoverable": self.is_recoverable,
            "suggested_action": self.suggested_action,
            "confidence": round(self.confidence, 3),
        }


# ── Error Pattern Classification ──
_ERROR_PATTERNS: dict[str, dict[str, Any]] = {
    "network": {
        "patterns": [
            "connection", "connect", "network", "dns", "resolve",
            "timeout", "timed out", "unreachable", "refused",
            "ssl", "certificate", "tls",
        ],
        "is_transient": True,
        "suggested_action": "retry",
    },
    "permission": {
        "patterns": [
            "permission", "access denied", "forbidden", "unauthorized",
            "elevated", "admin", "root", "privilege",
        ],
        "is_transient": False,
        "suggested_action": "ask_user",
    },
    "not_found": {
        "patterns": [
            "not found", "no such", "does not exist", "doesn't exist",
            "cannot find", "couldn't find", "missing",
        ],
        "is_transient": False,
        "suggested_action": "alternative_tool",
    },
    "timeout": {
        "patterns": [
            "timeout", "timed out", "took too long", "slow",
            "deadline exceeded",
        ],
        "is_transient": True,
        "suggested_action": "retry",
    },
    "api_limit": {
        "patterns": [
            "rate limit", "too many requests", "quota",
            "exceeded", "throttl",
        ],
        "is_transient": True,
        "suggested_action": "alternative_platform",
    },
    "syntax": {
        "patterns": [
            "syntax", "invalid", "parse", "malformed",
            "bad request", "invalid argument",
        ],
        "is_transient": False,
        "suggested_action": "retry",
    },
    "import": {
        "patterns": [
            "import", "module not found", "no module named",
            "cannot import", "ImportError", "ModuleNotFoundError",
        ],
        "is_transient": False,
        "suggested_action": "alternative_tool",
    },
}


# ════════════════════════════════════════════════════════════════════
# RECOVERY STRATEGIES
# ════════════════════════════════════════════════════════════════════

@dataclass
class RecoveryAttempt:
    """A single recovery attempt."""
    strategy: str           # "retry", "alternative_tool", "alternative_platform", "cached", "ask_user"
    tool_name: str
    params: dict
    timestamp: float = 0.0
    success: bool = False
    result: str = ""


@dataclass
class RecoveryResult:
    """Result of recovery process."""
    recovered: bool
    strategy_used: str
    attempts: list[RecoveryAttempt]
    final_result: str
    total_time_ms: float
    analysis: FailureAnalysis | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovered": self.recovered,
            "strategy_used": self.strategy_used,
            "attempts": len(self.attempts),
            "final_result": self.final_result[:200],
            "total_time_ms": round(self.total_time_ms, 1),
        }


# ════════════════════════════════════════════════════════════════════
# AUTONOMOUS RECOVERY ENGINE
# ════════════════════════════════════════════════════════════════════

class AutonomousRecovery:
    """Handles execution failures with autonomous recovery.

    Recovery chain:
    1. Analyze failure → classify error type
    2. Retry (if transient) → with backoff
    3. Alternative tool → same capability, different implementation
    4. Alternative platform → different API/source
    5. Cached result → if available
    6. Ask user → last resort
    """

    def __init__(self) -> None:
        self._failure_history: list[FailureAnalysis] = []
        self._recovery_history: list[RecoveryResult] = []
        self._cache: dict[str, str] = {}  # Simple result cache
        self._max_retries: int = 2
        self._retry_delay_ms: float = 500.0
        self._max_cache_size: int = 100

    def analyze_failure(self, error: Exception | str) -> FailureAnalysis:
        """Analyze a failure and determine recovery strategy."""
        error_str = str(error).lower()

        for error_type, config in _ERROR_PATTERNS.items():
            for pattern in config["patterns"]:
                if pattern.lower() in error_str:
                    analysis = FailureAnalysis(
                        error_type=error_type,
                        error_message=str(error),
                        is_transient=config["is_transient"],
                        is_recoverable=config["is_transient"] or error_type != "permission",
                        suggested_action=config["suggested_action"],
                        confidence=0.8,
                    )
                    self._failure_history.append(analysis)
                    return analysis

        # Unknown error — assume transient and try alternative
        analysis = FailureAnalysis(
            error_type="unknown",
            error_message=str(error),
            is_transient=True,
            is_recoverable=True,
            suggested_action="alternative_tool",
            confidence=0.4,
        )
        self._failure_history.append(analysis)
        return analysis

    def get_recovery_chain(
        self,
        tool_name: str,
        params: dict[str, Any],
        analysis: FailureAnalysis,
        alternatives: list[str] | None = None,
        cached_result: str | None = None,
    ) -> list[dict[str, Any]]:
        """Build a chain of recovery attempts.

        Returns ordered list of recovery strategies to try.
        """
        chain = []

        # Strategy 1: Retry (if transient)
        if analysis.is_transient:
            for attempt in range(self._max_retries):
                chain.append({
                    "strategy": "retry",
                    "tool_name": tool_name,
                    "params": params.copy(),
                    "delay_ms": self._retry_delay_ms * (attempt + 1),
                    "reason": f"Transient {analysis.error_type} error, retry #{attempt + 1}",
                })

        # Strategy 2: Alternative tool
        if alternatives:
            for alt_tool in alternatives[:2]:
                chain.append({
                    "strategy": "alternative_tool",
                    "tool_name": alt_tool,
                    "params": params.copy(),
                    "delay_ms": 0,
                    "reason": f"Primary tool failed: {analysis.error_type}",
                })

        # Strategy 3: Alternative platform (for search queries)
        if analysis.error_type in ("api_limit", "network", "not_found"):
            chain.append({
                "strategy": "alternative_platform",
                "tool_name": tool_name,
                "params": {**params, "_use_fallback_platform": True},
                "delay_ms": 0,
                "reason": "Platform failure, trying alternative source",
            })

        # Strategy 4: Cached result
        if cached_result:
            chain.append({
                "strategy": "cached",
                "tool_name": tool_name,
                "params": {},
                "delay_ms": 0,
                "reason": "Using cached result",
                "cached_result": cached_result,
            })

        # Strategy 5: Ask user (always last)
        chain.append({
            "strategy": "ask_user",
            "tool_name": tool_name,
            "params": {},
            "delay_ms": 0,
            "reason": f"All recovery strategies exhausted. Error: {analysis.error_message[:100]}",
        })

        return chain

    def cache_result(self, key: str, result: str) -> None:
        """Cache a successful result for future recovery."""
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = result

    def get_cached(self, key: str) -> str | None:
        """Get a cached result."""
        return self._cache.get(key)

    def get_failure_stats(self) -> dict[str, Any]:
        """Get failure statistics for learning."""
        type_counts: dict[str, int] = {}
        for f in self._failure_history:
            type_counts[f.error_type] = type_counts.get(f.error_type, 0) + 1

        return {
            "total_failures": len(self._failure_history),
            "failure_types": type_counts,
            "total_recoveries": len(self._recovery_history),
            "successful_recoveries": sum(1 for r in self._recovery_history if r.recovered),
        }

    def record_recovery(self, result: RecoveryResult) -> None:
        """Record a recovery result for learning."""
        self._recovery_history.append(result)
        # Keep history bounded
        if len(self._recovery_history) > 200:
            self._recovery_history = self._recovery_history[-100:]

    def get_alternatives(self, tool_name: str) -> list[str]:
        """Get alternative tools for a given tool."""
        _ALTERNATIVE_MAP: dict[str, list[str]] = {
            "web_search": ["search_on_platform", "search_youtube"],
            "search_youtube": ["web_search", "play_music"],
            "play_music": ["search_youtube", "play_youtube"],
            "open_app": ["open_website", "web_search"],
            "open_website": ["open_app", "web_search"],
            "get_weather": ["web_search"],
            "get_news": ["web_search", "get_weather"],
            "calculator": ["web_search"],
            "get_joke": ["web_search", "get_quote"],
            "screenshot": ["web_search"],
            "volume_control": ["system_status"],
            "file_management": ["open_app", "open_folder"],
        }
        return _ALTERNATIVE_MAP.get(tool_name, [])


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

autonomous_recovery = AutonomousRecovery()
