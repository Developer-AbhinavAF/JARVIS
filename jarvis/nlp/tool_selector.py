"""Tool selection for the JARVIS NLP engine.

Replaces keyword-based tool routing with a registry-driven approach
that considers intent, entities, context, and system capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ════════════════════════════════════════════════════════════════════


@dataclass
class ToolConfig:
    """Configuration for a single tool candidate."""

    tool_name: str
    handler: str
    param_map: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.5
    required_capabilities: list[str] = field(default_factory=list)
    context_requirements: dict[str, Any] = field(default_factory=dict)


TOOL_REGISTRY: dict[str, list[ToolConfig]] = {
    # ── Web / Browser ───────────────────────────────────────────
    "OPEN_WEBSITE": [
        ToolConfig(
            tool_name="open_website",
            handler="jarvis.tools.open_app",
            param_map={"target": "target", "url": "url", "website": "target"},
            confidence=0.95,
            required_capabilities=["browser"],
        ),
    ],
    "SEARCH_WEB": [
        ToolConfig(
            tool_name="web_search",
            handler="jarvis.tools.web_search",
            param_map={"query": "query", "search_term": "query", "target": "query"},
            confidence=0.95,
            required_capabilities=["search_engine"],
        ),
    ],
    "SEARCH_ON_PLATFORM": [
        ToolConfig(
            tool_name="search_on_platform",
            handler="jarvis.tools.web_search",
            param_map={"query": "query", "platform": "platform"},
            confidence=0.95,
            required_capabilities=["search_engine"],
        ),
    ],
    "SEARCH_YOUTUBE": [
        ToolConfig(
            tool_name="search_youtube",
            handler="jarvis.tools.web_search",
            param_map={"query": "query"},
            confidence=0.95,
            required_capabilities=["search_engine"],
        ),
    ],
    "WEB_SEARCH": [
        ToolConfig(
            tool_name="web_search",
            handler="jarvis.tools.web_search",
            param_map={"query": "query", "search_term": "query", "target": "query"},
            confidence=0.90,
            required_capabilities=["search_engine"],
        ),
    ],

    # ── App Launching ───────────────────────────────────────────
    "OPEN_APP": [
        ToolConfig(
            tool_name="open_app",
            handler="jarvis.tools.open_app",
            param_map={"target": "target", "app_name": "target", "app": "target"},
            confidence=0.95,
            required_capabilities=["app_launcher"],
        ),
    ],
    "CLOSE_APP": [
        ToolConfig(
            tool_name="close_app",
            handler="jarvis.tools.close_app",
            param_map={"target": "target", "app_name": "target"},
            confidence=0.90,
            required_capabilities=["app_launcher"],
        ),
    ],

    # ── Media ───────────────────────────────────────────────────
    "PLAY_MUSIC": [
        ToolConfig(
            tool_name="play_music",
            handler="jarvis.tools.play_music",
            param_map={"query": "query", "song": "query", "target": "query"},
            confidence=0.95,
            required_capabilities=["media_player"],
        ),
    ],
    "PLAY_YOUTUBE": [
        ToolConfig(
            tool_name="play_music",
            handler="jarvis.tools.play_music",
            param_map={"query": "query", "song": "query", "target": "query"},
            confidence=0.92,
            required_capabilities=["media_player"],
        ),
    ],
    "PLAY_SPOTIFY": [
        ToolConfig(
            tool_name="play_music",
            handler="jarvis.tools.play_music",
            param_map={"query": "query", "song": "query", "target": "query"},
            confidence=0.92,
            required_capabilities=["media_player"],
        ),
    ],

    # ── System Control ──────────────────────────────────────────
    "VOLUME_CONTROL": [
        ToolConfig(
            tool_name="volume_control",
            handler="jarvis.system_control.volume_control",
            param_map={"action": "action", "value": "value"},
            confidence=0.95,
            required_capabilities=["system_control"],
        ),
    ],
    "BRIGHTNESS_CONTROL": [
        ToolConfig(
            tool_name="brightness_control",
            handler="jarvis.system_control.brightness_control",
            param_map={"action": "action", "value": "value"},
            confidence=0.93,
            required_capabilities=["system_control", "display"],
        ),
    ],
    "SYSTEM_POWER": [
        ToolConfig(
            tool_name="system_power",
            handler="jarvis.system_control.system_power",
            param_map={"action": "action"},
            confidence=0.95,
            required_capabilities=["system_control"],
            context_requirements={"confirm": True},
        ),
    ],
    "SCREENSHOT": [
        ToolConfig(
            tool_name="screenshot",
            handler="jarvis.system_control.take_screenshot",
            confidence=0.95,
            required_capabilities=["display"],
        ),
    ],
    "WINDOW_CONTROL": [
        ToolConfig(
            tool_name="window_control",
            handler="jarvis.system_control.window_control",
            param_map={"action": "action", "target": "title"},
            confidence=0.88,
            required_capabilities=["system_control"],
        ),
    ],
    "CLIPBOARD": [
        ToolConfig(
            tool_name="clipboard_paste",
            handler="jarvis.system_control.clipboard_manager",
            param_map={"action": "action", "text": "text"},
            confidence=0.90,
            required_capabilities=["system_control"],
        ),
    ],
    "SYSTEM_STATUS": [
        ToolConfig(
            tool_name="system_status",
            handler="jarvis.dashboard.get_system_stats",
            confidence=0.95,
            required_capabilities=["system_control"],
        ),
    ],
    "TIMER": [
        ToolConfig(
            tool_name="timer",
            handler="jarvis.tools.timer",
            param_map={"seconds": "seconds"},
            confidence=0.93,
            required_capabilities=["system_control"],
        ),
    ],

    # ── File System ─────────────────────────────────────────────
    "PROGRAMMING": [
        ToolConfig(
            tool_name="open_vscode",
            handler="jarvis.tools.open_app",
            param_map={"target": "target", "app_name": "target"},
            confidence=0.90,
            required_capabilities=["app_launcher"],
        ),
    ],
    "OPEN_FOLDER": [
        ToolConfig(
            tool_name="open_folder",
            handler="jarvis.tools.open_app",
            param_map={"path": "target", "folder": "target"},
            confidence=0.90,
            required_capabilities=["file_system"],
        ),
    ],
    "FILE_MANAGEMENT": [
        ToolConfig(
            tool_name="file_management",
            handler="jarvis.file_ops.create_folder",
            param_map={"action": "action", "path": "path"},
            confidence=0.85,
            required_capabilities=["file_system"],
        ),
    ],

    # ── Memory ──────────────────────────────────────────────────
    "SAVE_MEMORY": [
        ToolConfig(
            tool_name="memory_save",
            handler="jarvis.memory.memory_save_permanent",
            param_map={"content": "info"},
            confidence=0.94,
            required_capabilities=["memory"],
        ),
    ],
    "RECALL_MEMORY": [
        ToolConfig(
            tool_name="memory_search",
            handler="jarvis.memory.memory_search_notes",
            param_map={"query": "query"},
            confidence=0.88,
            required_capabilities=["memory"],
        ),
    ],
    "ADD_TODO": [
        ToolConfig(
            tool_name="add_todo",
            handler="jarvis.memory.memory_add_todo",
            param_map={"task": "task"},
            confidence=0.90,
            required_capabilities=["memory"],
        ),
    ],
    "LIST_TODOS": [
        ToolConfig(
            tool_name="list_todos",
            handler="jarvis.memory.memory_get_todos",
            confidence=0.90,
            required_capabilities=["memory"],
        ),
    ],
    "ADD_NOTE": [
        ToolConfig(
            tool_name="add_note",
            handler="jarvis.memory.memory_add_note",
            param_map={"content": "content"},
            confidence=0.88,
            required_capabilities=["memory"],
        ),
    ],

    # ── Calculation ─────────────────────────────────────────────
    "CALCULATOR": [
        ToolConfig(
            tool_name="calculator",
            handler="jarvis.tools.calculator",
            param_map={"expression": "expression", "query": "expression", "target": "expression"},
            confidence=0.92,
            required_capabilities=["calculator"],
        ),
    ],

    # ── Information ─────────────────────────────────────────────
    "GET_WEATHER": [
        ToolConfig(
            tool_name="get_weather",
            handler="jarvis.tools.get_weather",
            param_map={"city": "city", "location": "city", "target": "city"},
            confidence=0.95,
            required_capabilities=["network"],
        ),
    ],
    "GET_NEWS": [
        ToolConfig(
            tool_name="get_news",
            handler="jarvis.tools.finnhub_market_news",
            param_map={"topic": "topic"},
            confidence=0.90,
            required_capabilities=["network"],
        ),
    ],
    "DATETIME": [
        ToolConfig(
            tool_name="datetime",
            handler="jarvis.tools.get_datetime",
            confidence=0.95,
            required_capabilities=[],
        ),
    ],
    "JOKE": [
        ToolConfig(
            tool_name="joke",
            handler="jarvis.tools.get_joke",
            confidence=0.93,
            required_capabilities=[],
        ),
    ],
    "QUOTE": [
        ToolConfig(
            tool_name="quote",
            handler="jarvis.tools.get_quote",
            confidence=0.90,
            required_capabilities=[],
        ),
    ],
    "FLIP_COIN": [
        ToolConfig(
            tool_name="flip_coin",
            handler="jarvis.tools.flip_coin",
            confidence=0.95,
            required_capabilities=[],
        ),
    ],
    "DICE_ROLL": [
        ToolConfig(
            tool_name="roll_dice",
            handler="jarvis.tools.roll_dice",
            param_map={"sides": "sides"},
            confidence=0.95,
            required_capabilities=[],
        ),
    ],
    "NASA_APOD": [
        ToolConfig(
            tool_name="nasa_apod",
            handler="jarvis.tools.nasa_apod",
            confidence=0.95,
            required_capabilities=["network"],
        ),
    ],
    "NASA_MARS": [
        ToolConfig(
            tool_name="nasa_mars",
            handler="jarvis.tools.nasa_mars_rover",
            confidence=0.90,
            required_capabilities=["network"],
        ),
    ],
    "ISS_LOCATION": [
        ToolConfig(
            tool_name="iss_location",
            handler="jarvis.tools.nasa_iss",
            confidence=0.90,
            required_capabilities=["network"],
        ),
    ],
    "STOCK_QUOTE": [
        ToolConfig(
            tool_name="stock_quote",
            handler="jarvis.tools.finnhub_quote",
            param_map={"symbol": "symbol"},
            confidence=0.90,
            required_capabilities=["network"],
        ),
    ],
    "RANDOM_FACT": [
        ToolConfig(
            tool_name="random_fact",
            handler="jarvis.tools.random_fact",
            confidence=0.90,
            required_capabilities=[],
        ),
    ],
    "IP_LOOKUP": [
        ToolConfig(
            tool_name="ip_lookup",
            handler="jarvis.tools.ip_lookup",
            confidence=0.90,
            required_capabilities=["network"],
        ),
    ],
    "GREETING": [
        ToolConfig(
            tool_name="greeting",
            handler="jarvis.tools.greeting",
            confidence=0.85,
            required_capabilities=[],
        ),
    ],
    "CHAT": [
        ToolConfig(
            tool_name="greeting",
            handler="jarvis.tools.greeting",
            confidence=0.85,
            required_capabilities=[],
        ),
    ],
}


# ════════════════════════════════════════════════════════════════════
# TOOL SELECTOR
# ════════════════════════════════════════════════════════════════════


class ToolSelector:
    """Selects the best tool based on intent, entities, context, and capabilities.

    Driven entirely by :data:`TOOL_REGISTRY` — no keyword matching or
    hard-coded routing logic.
    """

    def select(
        self,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
        capabilities: list[str],
    ) -> tuple[str, str, dict[str, Any]]:
        """Select the best tool for an intent.

        Args:
            intent: Classified intent string.
            entities: Extracted entities from the NLP pipeline.
            context: Conversation / session context.
            capabilities: Available system capabilities.

        Returns:
            Tuple of ``(tool_name, handler_name, parameters)``.
            Returns empty strings and empty dict when no tool matches.
        """
        candidates = TOOL_REGISTRY.get(intent)
        if not candidates:
            return ("", "", {})

        # Filter by capability availability
        cap_set = set(capabilities)
        eligible = [
            c for c in candidates
            if not c.required_capabilities
            or cap_set.issuperset(c.required_capabilities)
        ]

        if not eligible:
            # Fall back to highest-confidence candidate regardless
            eligible = candidates

        best = self._select_best_tool(eligible, context)
        params = self._map_parameters(best, entities, context)
        handler = self._resolve_handler(best.handler)

        return (best.tool_name, handler, params)

    def _select_best_tool(
        self,
        candidates: list[ToolConfig],
        context: dict[str, Any],
    ) -> ToolConfig:
        """Choose the best tool from a list of candidates.

        Scoring considers:
        1. Base confidence from the registry.
        2. Context requirement bonuses (e.g. confirmation already granted).
        3. Context requirement penalties (unmet requirements).
        """
        scored: list[tuple[float, ToolConfig]] = []

        for tool in candidates:
            score = tool.confidence

            # Bonus / penalty for context requirements
            for req_key, req_val in tool.context_requirements.items():
                ctx_val = context.get(req_key)
                if ctx_val == req_val:
                    score += 0.05
                elif ctx_val is not None and ctx_val != req_val:
                    score -= 0.10

            scored.append((score, tool))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _map_parameters(
        self,
        tool_config: ToolConfig,
        entities: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Map extracted entities to the selected tool's parameter names.

        Iterates over the tool's ``param_map`` and resolves each
        parameter from entities first, then falls back to context.

        Args:
            tool_config: The selected tool configuration.
            entities: Extracted entity dict.
            context: Session context dict.

        Returns:
            Mapped parameter dict ready for the handler.
        """
        params: dict[str, Any] = {}

        for entity_key, param_name in tool_config.param_map.items():
            value = entities.get(entity_key)
            if value is None:
                value = context.get(entity_key)
            if value is not None:
                params[param_name] = value

        return params

    @staticmethod
    def _resolve_handler(tool_name: str) -> str:
        """Get the handler module path for a tool name.

        Resolves the handler from the TOOL_REGISTRY by scanning
        all entries for a matching tool_name.  Falls back to a
        conventional ``jarvis.tools.<tool_name>`` path.

        Args:
            tool_name: The tool's registered name.

        Returns:
            Dotted module path string.
        """
        # If the input is already a dotted module path, return as-is
        if "." in tool_name:
            return tool_name

        # Fast path: scan registry for a direct match on tool_name
        for entries in TOOL_REGISTRY.values():
            for entry in entries:
                if entry.tool_name == tool_name:
                    return entry.handler

        # Fallback convention
        return f"jarvis.tools.{tool_name}"
