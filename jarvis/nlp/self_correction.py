"""Self-correction and fallback system for JARVIS NLP.

When execution fails, tries alternatives before asking the user.
Chrome not found → Edge → Firefox → Default Browser
Spotify unavailable → YouTube Music → YouTube
GitHub API failed → Website → Search Engine → Cached Result

Always attempts recovery before reporting failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# FALLBACK CHAINS
# ════════════════════════════════════════════════════════════════════

@dataclass
class FallbackStep:
    """A single step in a fallback chain."""
    name: str
    handler: str
    params_transform: dict[str, str] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "handler": self.handler,
            "params_transform": self.params_transform,
            "description": self.description,
        }


# Intent → ordered list of fallback alternatives
FALLBACK_CHAINS: dict[str, list[FallbackStep]] = {
    "OPEN_WEBSITE": [
        FallbackStep("chrome", "jarvis.tools.open_app", description="Google Chrome"),
        FallbackStep("edge", "jarvis.tools.open_app", description="Microsoft Edge"),
        FallbackStep("firefox", "jarvis.tools.open_app", description="Mozilla Firefox"),
    ],
    "OPEN_APP": [
        # Dynamic — depends on which app was requested
    ],
    "PLAY_MUSIC": [
        FallbackStep("spotify", "jarvis.tools.play_music", description="Spotify"),
        FallbackStep("youtube_music", "jarvis.tools.web_search", description="YouTube Music"),
        FallbackStep("youtube", "jarvis.tools.play_music", description="YouTube"),
    ],
    "SEARCH_WEB": [
        FallbackStep("google", "jarvis.tools.web_search", description="Google Search"),
        FallbackStep("bing", "jarvis.tools.web_search", description="Bing Search"),
        FallbackStep("duckduckgo", "jarvis.tools.web_search", description="DuckDuckGo"),
    ],
    "GET_WEATHER": [
        FallbackStep("api", "jarvis.tools.get_weather", description="Weather API"),
        FallbackStep("web_search", "jarvis.tools.web_search", description="Web Search Fallback"),
    ],
    "GET_NEWS": [
        FallbackStep("api", "jarvis.tools.finnhub_market_news", description="News API"),
        FallbackStep("web_search", "jarvis.tools.web_search", description="Web Search Fallback"),
    ],
    "RECALL_MEMORY": [
        FallbackStep("local_memory", "jarvis.memory.memory_search_notes", description="Local Memory"),
        FallbackStep("web_search", "jarvis.tools.web_search", description="Web Search"),
    ],
}

# App-specific fallback chains
_APP_FALLBACKS: dict[str, list[str]] = {
    "chrome": ["edge", "firefox", "brave", "opera"],
    "firefox": ["chrome", "edge", "brave", "opera"],
    "edge": ["chrome", "firefox", "brave", "opera"],
    "vscode": ["sublime", "notepad++", "notepad"],
    "pycharm": ["vscode", "sublime", "notepad"],
    "spotify": ["youtube_music", "youtube"],
    "notepad": ["vscode", "sublime"],
}


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

@dataclass
class CorrectionResult:
    """Result of a self-correction attempt."""
    success: bool
    fallback_name: str
    fallback_handler: str
    parameters: dict[str, Any]
    attempt_number: int
    chain_length: int
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "fallback_name": self.fallback_name,
            "fallback_handler": self.fallback_handler,
            "parameters": self.parameters,
            "attempt_number": self.attempt_number,
            "chain_length": self.chain_length,
            "description": self.description,
        }


class SelfCorrectionEngine:
    """Provides fallback chains for failed executions.

    When a tool execution fails, this engine suggests the next
    alternative in the fallback chain, allowing the system to
    retry with different tools/providers before giving up.
    """

    def __init__(self) -> None:
        self._execution_history: list[dict[str, Any]] = []

    def get_fallback_chain(
        self,
        intent: str,
        entities: dict[str, Any],
        failed_handler: str = "",
    ) -> list[FallbackStep]:
        """Get the ordered fallback chain for a failed intent.

        Parameters
        ----------
        intent:
            The intent that failed.
        entities:
            Extracted entities from the original command.
        failed_handler:
            The handler that just failed (to skip in the chain).

        Returns
        -------
        Ordered list of FallbackSteps to try, excluding the failed handler.
        """
        chain = FALLBACK_CHAINS.get(intent, [])

        # For OPEN_APP, generate dynamic chain based on requested app
        if intent == "OPEN_APP":
            app_name = str(entities.get("target", "")).lower()
            if app_name in _APP_FALLBACKS:
                alternatives = _APP_FALLBACKS[app_name]
                chain = [
                    FallbackStep(
                        name=alt,
                        handler="jarvis.tools.open_app",
                        params_transform={"target": alt},
                        description=f"Try {alt}",
                    )
                    for alt in alternatives
                ]

        # Filter out the failed handler
        if failed_handler:
            chain = [s for s in chain if s.handler != failed_handler]

        return chain

    def get_next_fallback(
        self,
        intent: str,
        entities: dict[str, Any],
        failed_handlers: list[str],
    ) -> FallbackStep | None:
        """Get the next fallback to try, given a list of already-failed handlers.

        Returns None when all alternatives have been exhausted.
        """
        chain = self.get_fallback_chain(intent, entities)

        for step in chain:
            if step.handler not in failed_handlers:
                return step

        return None

    def record_attempt(
        self,
        intent: str,
        handler: str,
        success: bool,
        entities: dict[str, Any],
    ) -> None:
        """Record an execution attempt for learning purposes."""
        self._execution_history.append({
            "intent": intent,
            "handler": handler,
            "success": success,
            "entities": {k: str(v) for k, v in entities.items()},
        })
        # Cap at 200 entries
        if len(self._execution_history) > 200:
            self._execution_history = self._execution_history[-200:]

    def get_success_rates(self) -> dict[str, dict[str, float]]:
        """Return success rates for each handler by intent.

        Useful for reordering fallback chains based on actual reliability.
        """
        stats: dict[str, dict[str, dict[str, int]]] = {}

        for record in self._execution_history:
            intent = record["intent"]
            handler = record["handler"]
            if intent not in stats:
                stats[intent] = {}
            if handler not in stats[intent]:
                stats[intent][handler] = {"success": 0, "total": 0}
            stats[intent][handler]["total"] += 1
            if record["success"]:
                stats[intent][handler]["success"] += 1

        rates: dict[str, dict[str, float]] = {}
        for intent, handlers in stats.items():
            rates[intent] = {}
            for handler, counts in handlers.items():
                rates[intent][handler] = (
                    counts["success"] / counts["total"]
                    if counts["total"] > 0
                    else 0.0
                )

        return rates

    def should_give_up(
        self,
        intent: str,
        failed_count: int,
        entities: dict[str, Any],
    ) -> bool:
        """Determine if we should stop retrying and ask the user.

        Returns True when:
        - All fallbacks exhausted
        - Too many attempts (> 3)
        """
        if failed_count >= 3:
            return True

        chain = self.get_fallback_chain(intent, entities)
        if not chain and failed_count > 0:
            return True

        return False

    def get_user_message(
        self,
        intent: str,
        failed_handlers: list[str],
        entities: dict[str, Any],
    ) -> str:
        """Generate a user-friendly message when all fallbacks are exhausted."""
        app_name = str(entities.get("target", "") or entities.get("query", ""))

        if intent == "OPEN_APP" and app_name:
            return (
                f"I couldn't find '{app_name}' on your system. "
                f"Would you like me to search for an alternative?"
            )
        elif intent == "PLAY_MUSIC":
            return (
                "I couldn't access your music player. "
                "Would you like me to search for the song online?"
            )
        elif intent == "OPEN_WEBSITE":
            return (
                "I couldn't open the browser. "
                "Would you like me to try a different browser?"
            )
        else:
            return (
                "I tried several alternatives but couldn't complete the action. "
                "Could you rephrase or be more specific?"
            )
