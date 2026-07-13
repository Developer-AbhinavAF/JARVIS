"""Unified NLP Command Engine for JARVIS AI OS v3.0.

Production-grade command understanding engine that achieves human-level
natural language understanding. Replaces all legacy NLP systems with a
single, modular pipeline.

Architecture:
  User Input
    → Enhanced Normalization (spelling, Hinglish, emoji, slang)
    → Multi-Intent Parsing (compound commands)
    → Context Resolution (follow-ups, pronouns)
    → Intent Classification (pattern + semantic + fuzzy)
    → Entity Recognition (apps, websites, parameters)
    → Confidence Scoring
    → Tool Selection
    → Execution (tools first, LLM last)
    → Self-Learning (track unknowns, usage patterns)

The LLM is ONLY called when no tool matches. This is mandatory.
"""

from __future__ import annotations

import logging
import re
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

# Import the new NLP components
from jarvis.nlp.normalizer import normalize
from jarvis.nlp.intent_classifier import IntentClassifier, IntentResult
from jarvis.nlp.context_memory import ContextMemory, context_memory
from jarvis.nlp.command_parser import CommandParser, command_parser
from jarvis.nlp.self_learning import SelfLearningEngine, self_learning
from jarvis.nlp.entity_extractor import EntityExtractor
from jarvis.nlp.confidence import ConfidenceScorer

# Known application names (not websites)
KNOWN_APPS = {
    "notepad", "calculator", "calc", "chrome", "firefox", "edge",
    "terminal", "cmd", "command prompt", "powershell", "vscode",
    "visual studio code", "notepad++", "sublime", "paint", "word",
    "excel", "powerpoint", "outlook", "teams", "discord", "slack",
    "zoom", "steam", "obs", "vlc", "spotify", "itunes",
    "snipping tool", "task manager", "control panel", "settings",
    "file explorer", "explorer", "files", "brave", "opera", "safari",
    "pycharm", "intellij", "blender", "photoshop", "gimp",
    "postman", "figma", "git", "android studio",
}

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
    message: str = ""  # optional confirmation message
    # Extended fields for the new NLP engine
    match_method: str = "pattern"  # pattern | semantic | fuzzy | context
    intent_result: IntentResult | None = None
    is_multi: bool = False
    execution_plan: list[dict[str, Any]] = field(default_factory=list)


class CommandEngine:
    """Unified NLP command engine with human-level understanding.

    This engine combines:
    1. Enhanced normalization (spelling correction, Hinglish, emoji, slang)
    2. Multi-intent parsing (compound commands)
    3. Context memory (follow-ups, pronouns)
    4. Semantic intent classification (pattern + keyword + fuzzy)
    5. Self-learning (track unknowns, usage patterns)
    """

    def __init__(self, tool_catalog: ToolCatalog | None = None) -> None:
        self.catalog = tool_catalog or catalog

        # Initialize NLP components
        self.intent_classifier = IntentClassifier()
        self.context_memory = context_memory
        self.command_parser = command_parser
        self.self_learning = self_learning
        self.entity_extractor = EntityExtractor()
        self.confidence_scorer = ConfidenceScorer()

        # Pre-compiled patterns for fast matching
        self._search_site_pattern = re.compile(
            r"search\s+(.+?)\s+on\s+(" + "|".join(re.escape(k) for k in sorted(SEARCH_SITES.keys(), key=len, reverse=True)) + r")\s*$",
            re.IGNORECASE,
        )
        self._website_pattern = re.compile(
            r"(?:open|launch|go\s+to|visit|navigate\s+to|browse)\s+(?:the\s+)?(?:website\s+)?(?:for\s+)?(?:the\s+)?("
            + "|".join(re.escape(k) for k in sorted(WEBSITES.keys(), key=len, reverse=True))
            + r")\s*$",
            re.IGNORECASE,
        )
        self._standalone_website = re.compile(
            r"^(" + "|".join(re.escape(k) for k in sorted(WEBSITES.keys(), key=len, reverse=True)) + r")\s*$",
            re.IGNORECASE,
        )
        self._search_prefix = re.compile(
            r"^(?:search|google|look\s+up|find|search\s+the\s+web\s+for|search\s+the\s+internet\s+for|search\s+web\s+for|search\s+internet\s+for)\s+",
            re.IGNORECASE,
        )

    def process(self, text: str) -> CommandResult:
        """Process user input through the full NLP pipeline.

        This is the main entry point. It processes input through:
        1. Normalization
        2. Multi-intent parsing
        3. Context resolution
        4. Intent classification
        5. Tool matching
        6. Confidence scoring
        """
        raw = text
        t0 = time.time()

        # ── Phase 0: Normalize ──
        normalized = normalize(text)
        if not normalized:
            return CommandResult(matched=False, raw_text=raw, normalized_text="")

        # ── Phase 1: Multi-intent parsing ──
        chain = self.command_parser.parse(normalized)
        if chain.is_multi and chain.count > 1:
            # For multi-commands, process the first command
            # The execution engine will handle the rest
            first_cmd = chain.commands[0]
            return self._process_single(first_cmd.text, raw, is_multi=True)

        # ── Phase 2: Process single command ──
        return self._process_single(normalized, raw)

    def _process_single(self, normalized: str, raw: str, is_multi: bool = False) -> CommandResult:
        """Process a single normalized command."""

        # ── Phase 2a: Context resolution ──
        if self.context_memory.should_use_context():
            # Resolve pronouns
            resolved = self.context_memory.resolve_pronouns(normalized)
            if resolved != normalized:
                normalized = resolved

        # ── Phase 3: Search on specific platform (before website open) ──
        result = self._try_search_on_platform(normalized)
        if result:
            platform = result.get("platform", "")
            query = result.get("query", "")
            cmd_result = CommandResult(
                matched=True,
                tool_name="search_on_platform",
                handler_name="jarvis.tools.web_search",
                params={"query": query, "platform": platform},
                confidence=0.96,
                raw_text=raw,
                normalized_text=normalized,
                message=f"Searching {platform} for: {query}",
                match_method="pattern",
            )
            self._record_success(raw, normalized, "search_on_platform", "jarvis.tools.web_search", 0.96)
            return cmd_result

        # ── Phase 4: Direct website open ──
        result = self._try_open_website(normalized)
        if result:
            cmd_result = CommandResult(
                matched=True,
                tool_name="open_website",
                handler_name="jarvis.tools.open_app",
                params=result,
                confidence=0.99,
                raw_text=raw,
                normalized_text=normalized,
                message=self._make_open_message(result.get("target", "")),
                match_method="pattern",
            )
            self._record_success(raw, normalized, "open_website", "jarvis.tools.open_app", 0.99)
            return cmd_result

        # ── Phase 4b: "google X" should be a search ──
        if re.match(r"^google\s+\S", normalized, re.IGNORECASE) and not normalized.startswith("google maps"):
            query = re.sub(r"^google\s+", "", normalized).strip()
            if query:
                cmd_result = CommandResult(
                    matched=True,
                    tool_name="web_search",
                    handler_name="jarvis.tools.web_search",
                    params={"query": query},
                    confidence=0.90,
                    raw_text=raw,
                    normalized_text=normalized,
                    message=f"Searching Google for: {query}",
                    match_method="pattern",
                )
                self._record_success(raw, normalized, "web_search", "jarvis.tools.web_search", 0.90)
                return cmd_result

        # ── Phase 5: Fallback patterns (before catalog to avoid broad matches) ──
        result = self._try_fallback_patterns(normalized)
        if result:
            cmd_result = CommandResult(
                matched=True,
                tool_name=result["tool_name"],
                handler_name=result.get("handler_name", ""),
                params=result.get("params", {}),
                confidence=result.get("confidence", 0.85),
                raw_text=raw,
                normalized_text=normalized,
                message=result.get("message", ""),
                match_method="pattern",
            )
            self._record_success(raw, normalized, result["tool_name"], result.get("handler_name", ""), result.get("confidence", 0.85))
            return cmd_result

        # ── Phase 6: Catalog pattern matching ──
        meta = self.catalog.find_by_pattern(normalized)
        if meta:
            params = {}
            if meta.extract_params:
                try:
                    params = meta.extract_params(normalized)
                except Exception:
                    params = {}

            # Handle special cases for tool routing
            handler_name = meta.handler_name
            params = self._fix_params_for_tool(meta.name, handler_name, params, normalized)

            # Redirect open_website to open_app if target is a known application
            if meta.name == "open_website":
                target = params.get("target", "").lower()
                is_known_app = target in KNOWN_APPS
                # Fuzzy match for typo'd targets (e.g., "spktiry" → "spotify")
                if not is_known_app and len(target) >= 3:
                    from difflib import get_close_matches
                    matches = get_close_matches(target, KNOWN_APPS, n=1, cutoff=0.6)
                    if matches:
                        is_known_app = True
                        params["target"] = matches[0]
                if is_known_app:
                    meta = self.catalog.get("open_app")
                    handler_name = meta.handler_name if meta else handler_name
                    params = self._fix_params_for_tool("open_app", handler_name, params, normalized)

            cmd_result = CommandResult(
                matched=True,
                tool_name=meta.name,
                handler_name=handler_name,
                params=params,
                confidence=meta.confidence,
                tool_meta=meta,
                raw_text=raw,
                normalized_text=normalized,
                message=self._make_confirmation_message(meta.name, params),
                match_method="pattern",
            )
            self._record_success(raw, normalized, meta.name, handler_name, meta.confidence)
            return cmd_result

        # ── Phase 6: Semantic intent classification ──
        intent_result = self.intent_classifier.classify(normalized)
        if intent_result and intent_result.confidence >= 0.75:
            # Try to map intent to a tool
            tool_mapping = self._map_intent_to_tool(intent_result)
            if tool_mapping:
                cmd_result = CommandResult(
                    matched=True,
                    tool_name=tool_mapping["tool_name"],
                    handler_name=tool_mapping["handler_name"],
                    params=tool_mapping.get("params", {}),
                    confidence=intent_result.confidence,
                    raw_text=raw,
                    normalized_text=normalized,
                    message=tool_mapping.get("message", ""),
                    match_method="semantic",
                    intent_result=intent_result,
                )
                self._record_success(raw, normalized, tool_mapping["tool_name"], tool_mapping["handler_name"], intent_result.confidence)
                return cmd_result

        # ── Phase 8: No match - record for learning ──
        self.self_learning.record_failed_command(
            text=raw,
            normalized=normalized,
            suggested_intent=intent_result.intent if intent_result else "",
            suggested_confidence=intent_result.confidence if intent_result else 0.0,
        )

        return CommandResult(
            matched=False,
            raw_text=raw,
            normalized_text=normalized,
        )

    def _map_intent_to_tool(self, intent_result: IntentResult) -> dict[str, Any] | None:
        """Map an intent classification result to a tool."""
        intent = intent_result.intent
        entities = intent_result.entities

        # Map intent to tool name and handler
        intent_tool_map = {
            "OPEN_WEBSITE": ("open_website", "jarvis.tools.open_app"),
            "OPEN_APP": ("open_app", "jarvis.tools.open_app"),
            "CLOSE_APP": ("close_app", "jarvis.tools.close_app"),
            "SEARCH_WEB": ("web_search", "jarvis.tools.web_search"),
            "SEARCH_YOUTUBE": ("search_on_platform", "jarvis.tools.web_search"),
            "SEARCH_ON_PLATFORM": ("search_on_platform", "jarvis.tools.web_search"),
            "PLAY_MUSIC": ("play_music", "jarvis.tools.play_music"),
            "PLAY_YOUTUBE": ("play_music", "jarvis.tools.play_music"),
            "PLAY_SPOTIFY": ("play_music", "jarvis.tools.play_music"),
            "GET_WEATHER": ("weather", "jarvis.tools.get_weather"),
            "GET_NEWS": ("news", "jarvis.tools.finnhub_market_news"),
            "SYSTEM_STATUS": ("system_status", "jarvis.dashboard.get_system_stats"),
            "VOLUME_CONTROL": ("volume_control", "jarvis.system_control.volume_control"),
            "BRIGHTNESS_CONTROL": ("brightness_control", "jarvis.system_control.brightness_control"),
            "SCREENSHOT": ("screenshot", "jarvis.system_control.take_screenshot"),
            "SYSTEM_POWER": ("system_power", "jarvis.system_control.system_power"),
            "CLIPBOARD": ("clipboard_paste", "jarvis.system_control.clipboard_manager"),
            "CALCULATOR": ("calculator", "jarvis.tools.calculator"),
            "TIMER": ("timer", "jarvis.tools.timer"),
            "DATETIME": ("datetime", "jarvis.tools.get_datetime"),
            "SAVE_MEMORY": ("memory_save", "jarvis.memory.memory_save_permanent"),
            "RECALL_MEMORY": ("memory_search", "jarvis.memory.memory_search_notes"),
            "WINDOW_CONTROL": ("window_control", "jarvis.system_control.window_control"),
            "JOKE": ("joke", "jarvis.tools.get_joke"),
            "QUOTE": ("quote", "jarvis.tools.get_quote"),
            "FLIP_COIN": ("flip_coin", "jarvis.tools.flip_coin"),
            "DICE_ROLL": ("roll_dice", "jarvis.tools.roll_dice"),
            "NASA_APOD": ("nasa_apod", "jarvis.tools.nasa_apod"),
            "NASA_MARS": ("nasa_mars", "jarvis.tools.nasa_mars_rover"),
            "ISS_LOCATION": ("nasa_iss", "jarvis.tools.nasa_iss"),
            "STOCK_QUOTE": ("stock_quote", "jarvis.tools.finnhub_quote"),
            "RANDOM_FACT": ("random_fact", "jarvis.tools.random_fact"),
            "IP_LOOKUP": ("ip_lookup", "jarvis.tools.ip_lookup"),
            "ADD_TODO": ("add_todo", "jarvis.memory.memory_add_todo"),
            "LIST_TODOS": ("list_todos", "jarvis.memory.memory_get_todos"),
            "ADD_NOTE": ("add_note", "jarvis.memory.memory_add_note"),
            "GREETING": ("greeting", "jarvis.tools.greeting"),
            "WEB_SEARCH": ("web_search", "jarvis.tools.web_search"),
        }

        if intent not in intent_tool_map:
            return None

        tool_name, handler_name = intent_tool_map[intent]

        # Extract params from entities
        params = {}
        if entities and hasattr(entities, 'entities'):
            for name, entity in entities.entities.items():
                if name == "target":
                    params["target"] = entity.value
                elif name == "query":
                    params["query"] = entity.value
                elif name == "platform":
                    params["platform"] = entity.value
                elif name == "city":
                    params["city"] = entity.value
                elif name == "action":
                    params["action"] = entity.value
                elif name == "value":
                    params["value"] = entity.value
                elif name == "expression":
                    params["expression"] = entity.value

        # Build confirmation message
        message = f"Executing {tool_name}..."

        return {
            "tool_name": tool_name,
            "handler_name": handler_name,
            "params": params,
            "message": message,
        }

    def _record_success(self, raw: str, normalized: str, tool_name: str, handler_name: str, confidence: float) -> None:
        """Record a successful command for self-learning."""
        self.self_learning.record_successful_command(
            text=raw,
            normalized=normalized,
            intent=tool_name,
            tool_name=handler_name,
            confidence=confidence,
        )

    def _try_open_website(self, normalized: str) -> dict[str, str] | None:
        """Try to match a direct website open command."""
        # Direct website open: "open youtube" → open_website
        m = self._website_pattern.search(normalized)
        if m:
            site = m.group(1).strip().lower()
            url = WEBSITES.get(site, "")
            if url:
                # If target is a known app, skip website open — let open_app handle it
                if site in KNOWN_APPS:
                    return None
                return {"target": site, "url": url}

        # Standalone website name: "youtube" → open_website
        m = self._standalone_website.match(normalized)
        if m:
            site = m.group(1).strip().lower()
            url = WEBSITES.get(site, "")
            if url:
                if site in KNOWN_APPS:
                    return None
                return {"target": site, "url": url}

        return None

    def _try_search_on_platform(self, normalized: str) -> dict[str, str] | None:
        """Try to match a search-on-platform command."""
        m = self._search_site_pattern.search(normalized)
        if m:
            query = m.group(1).strip()
            platform = m.group(2).strip().lower()
            if platform in SEARCH_SITES:
                return {"query": query, "platform": platform}
        return None

    def _try_fallback_patterns(self, normalized: str) -> dict[str, Any] | None:
        """Try fallback patterns for common commands not in the catalog."""
        # ── App opening via alternative verbs (fire up, bring up, boot up, load) ──
        m = re.match(
            r"^(?:fire\s+up|bring\s+up|boot\s+up|load)\s+(.+?)(?:\s+(?:please|for\s+me|now|up))?\s*$",
            normalized,
            re.IGNORECASE,
        )
        if m:
            target = m.group(1).strip().rstrip("?!. ")
            if target and len(target) >= 2:
                return {
                    "tool_name": "open_app",
                    "handler_name": "jarvis.tools.open_app",
                    "params": {"target": target},
                    "message": f"Opening {target}...",
                    "confidence": 0.88,
                }

        # ── Standalone app name (e.g., just "spotify") ──
        if normalized.strip() in KNOWN_APPS:
            return {
                "tool_name": "open_app",
                "handler_name": "jarvis.tools.open_app",
                "params": {"target": normalized.strip()},
                "message": f"Opening {normalized.strip()}...",
                "confidence": 0.88,
            }

        # Wifi/Bluetooth settings
        if re.search(r"wifi\s+(?:off|on|settings|toggle)", normalized):
            return {
                "tool_name": "system_power",
                "handler_name": "jarvis.system_control.system_power",
                "params": {"action": "settings", "target": "network"},
                "message": "Opening network settings...",
                "confidence": 0.85,
            }
        if re.search(r"bluetooth\s+(?:off|on|settings|toggle)", normalized):
            return {
                "tool_name": "system_power",
                "handler_name": "jarvis.system_control.system_power",
                "params": {"action": "settings", "target": "bluetooth"},
                "message": "Opening Bluetooth settings...",
                "confidence": 0.85,
            }

        # Create folder
        m = re.match(r"create\s+(?:a\s+)?(?:new\s+)?folder\s+(?:named?\s+)?(.+)", normalized)
        if m:
            folder_name = m.group(1).strip()
            return {
                "tool_name": "create_folder",
                "handler_name": "jarvis.file_ops.create_folder",
                "params": {"name": folder_name},
                "message": f"Creating folder: {folder_name}",
                "confidence": 0.88,
            }

        # Delete file/folder
        m = re.match(r"delete\s+(?:the\s+)?(?:file|folder)\s+(.+)", normalized)
        if m:
            target = m.group(1).strip()
            return {
                "tool_name": "delete_file",
                "handler_name": "jarvis.file_ops.delete_file",
                "params": {"path": target},
                "message": f"Deleting: {target}",
                "confidence": 0.88,
            }

        # "what is/are X" question patterns
        # Clipboard
        if re.search(r"what\s+(?:is|are)\s+(?:on\s+)?(?:the\s+)?clipboard", normalized):
            return {
                "tool_name": "clipboard_paste",
                "handler_name": "jarvis.system_control.clipboard_manager",
                "params": {"action": "get"},
                "message": "Getting clipboard contents...",
                "confidence": 0.88,
            }

        # Battery
        if re.search(r"what\s+(?:is|are)\s+(?:my\s+)?(?:the\s+)?battery", normalized):
            return {
                "tool_name": "battery_status",
                "handler_name": "jarvis.dashboard.get_battery_status",
                "params": {},
                "message": "Checking battery status...",
                "confidence": 0.88,
            }

        # Weather
        m = re.search(r"what\s+(?:is|are)\s+(?:the\s+)?weather\s+(?:in|at|for|of)\s+(.+)", normalized)
        if m:
            city = m.group(1).strip()
            return {
                "tool_name": "weather",
                "handler_name": "jarvis.tools.get_weather",
                "params": {"city": city},
                "message": f"Getting weather for {city}...",
                "confidence": 0.88,
            }

        # Date/time
        if re.search(r"what\s+(?:is|are)\s+(?:the\s+)?(?:date|time|day)", normalized):
            return {
                "tool_name": "datetime",
                "handler_name": "jarvis.tools.get_datetime",
                "params": {},
                "message": "Getting current date and time...",
                "confidence": 0.88,
            }

        # What's running
        if re.search(r"what\s+(?:is|are)\s+(?:currently\s+)?(?:running|open|active|currently\s+running)", normalized):
            return {
                "tool_name": "list_apps",
                "handler_name": "jarvis.system_control.list_running_apps",
                "params": {},
                "message": "Listing running applications...",
                "confidence": 0.88,
            }

        # "search X" (bare search without web prefix)
        m = re.match(r"^search\s+(.+)$", normalized)
        if m:
            query = m.group(1).strip()
            if query:
                return {
                    "tool_name": "web_search",
                    "handler_name": "jarvis.tools.web_search",
                    "params": {"query": query},
                    "message": f"Searching for: {query}",
                    "confidence": 0.85,
                }

        return None

    def _fix_params_for_tool(self, tool_name: str, handler_name: str, params: dict, normalized: str) -> dict:
        """Fix parameters for specific tools."""
        # If target is empty, try to extract from text
        if tool_name in ("open_app", "open_website") and not params.get("target"):
            # Try to extract app/website name after action verb
            m = re.search(r"(?:open|launch|start|run|fire\s+up|bring\s+up|boot\s+up|load)\s+(?:up\s+)?(.+)", normalized)
            if m:
                params["target"] = m.group(1).strip()

        if tool_name == "close_app" and not params.get("target"):
            m = re.search(r"(?:close|kill|stop|quit|exit)\s+(.+)", normalized)
            if m:
                params["target"] = m.group(1).strip()

        if tool_name == "web_search" and not params.get("query"):
            # Remove search prefix
            query = self._search_prefix.sub("", normalized).strip()
            if query:
                params["query"] = query

        if tool_name == "play_music" and not params.get("query"):
            m = re.search(r"play\s+(.+)", normalized)
            if m:
                params["query"] = m.group(1).strip()

        if tool_name == "weather" and not params.get("city"):
            m = re.search(r"weather\s+(?:in|at|for|of)\s+(.+)", normalized)
            if m:
                params["city"] = m.group(1).strip()

        if tool_name == "timer" and not params.get("seconds"):
            m = re.search(r"(\d+)\s*(?:seconds?|minutes?|hours?)", normalized)
            if m:
                params["seconds"] = int(m.group(1))

        if tool_name == "calculator" and not params.get("expression"):
            params["expression"] = normalized

        if tool_name == "volume_control" and not params.get("action"):
            if "up" in normalized or "increase" in normalized or "louder" in normalized:
                params["action"] = "up"
            elif "down" in normalized or "decrease" in normalized or "softer" in normalized:
                params["action"] = "down"
            elif "mute" in normalized:
                params["action"] = "mute"
            elif "unmute" in normalized:
                params["action"] = "unmute"

        if tool_name == "brightness_control" and not params.get("action"):
            if "up" in normalized or "increase" in normalized or "brighter" in normalized:
                params["action"] = "up"
            elif "down" in normalized or "decrease" in normalized or "dimmer" in normalized or "dim" in normalized:
                params["action"] = "down"

        if tool_name == "system_power" and not params.get("action"):
            if "shutdown" in normalized or "shut down" in normalized or "power off" in normalized:
                params["action"] = "shutdown"
            elif "restart" in normalized or "reboot" in normalized:
                params["action"] = "restart"
            elif "sleep" in normalized or "hibernate" in normalized:
                params["action"] = "sleep"
            elif "lock" in normalized:
                params["action"] = "lock"

        if tool_name == "window_control" and not params.get("action"):
            if "minimize" in normalized:
                params["action"] = "minimize"
            elif "maximize" in normalized:
                params["action"] = "maximize"
            elif "restore" in normalized:
                params["action"] = "restore"
            elif "close" in normalized:
                params["action"] = "close"
            elif "list" in normalized or "show" in normalized:
                params["action"] = "list"

        if tool_name == "clipboard_paste" and not params.get("action"):
            if "paste" in normalized:
                params["action"] = "paste"
            elif "copy" in normalized:
                params["action"] = "copy"
            else:
                params["action"] = "get"

        if tool_name == "stock_quote" and not params.get("symbol"):
            m = re.search(r"(?:stock|price|quote)\s+(?:of\s+|for\s+)?(\w+)", normalized)
            if m:
                params["symbol"] = m.group(1).upper()

        return params

    def _make_open_message(self, target: str) -> str:
        """Make a confirmation message for opening something."""
        display = target.title() if target else "the requested site"
        return f"Opening {display}..."

    def _make_confirmation_message(self, tool_name: str, params: dict) -> str:
        """Make a confirmation message for a tool execution."""
        messages = {
            "open_website": lambda p: f"Opening {p.get('target', 'website').title()}...",
            "open_app": lambda p: f"Opening {p.get('target', 'app').title()}...",
            "close_app": lambda p: f"Closing {p.get('target', 'app').title()}...",
            "web_search": lambda p: f"Searching for: {p.get('query', 'your query')}",
            "search_on_platform": lambda p: f"Searching {p.get('platform', 'platform')} for: {p.get('query', 'query')}",
            "play_music": lambda p: f"Playing: {p.get('query', 'music')}",
            "weather": lambda p: f"Getting weather for {p.get('city', 'your location')}...",
            "news": lambda p: "Getting latest news...",
            "screenshot": lambda p: "Taking screenshot...",
            "volume_control": lambda p: f"Volume {p.get('action', 'up')}...",
            "brightness_control": lambda p: f"Brightness {p.get('action', 'up')}...",
            "system_power": lambda p: f"System {p.get('action', 'shutdown')}...",
            "calculator": lambda p: f"Calculating: {p.get('expression', '...')}",
            "timer": lambda p: f"Setting timer for {p.get('seconds', '?')} seconds...",
            "datetime": lambda p: "Getting current date and time...",
            "memory_save": lambda p: "Saving to memory...",
            "memory_search": lambda p: "Searching memory...",
            "joke": lambda p: "Here's a joke...",
            "quote": lambda p: "Here's an inspirational quote...",
            "flip_coin": lambda p: "Flipping a coin...",
            "roll_dice": lambda p: "Rolling a dice...",
            "nasa_apod": lambda p: "Getting NASA Picture of the Day...",
            "nasa_mars": lambda p: "Getting Mars rover photos...",
            "stock_quote": lambda p: f"Getting stock quote for {p.get('symbol', '...')}...",
            "greeting": lambda p: "Hello! How can I help you?",
            "list_apps": lambda p: "Listing running applications...",
            "system_status": lambda p: "Getting system status...",
            "battery_status": lambda p: "Checking battery status...",
            "network_status": lambda p: "Checking network status...",
            "speed_test": lambda p: "Running speed test...",
            "clipboard_paste": lambda p: "Getting clipboard contents...",
            "window_control": lambda p: f"Window {p.get('action', 'control')}...",
            "add_todo": lambda p: "Adding to-do item...",
            "list_todos": lambda p: "Listing to-do items...",
            "ip_lookup": lambda p: "Looking up IP address...",
            "random_fact": lambda p: "Here's a random fact...",
            "create_folder": lambda p: f"Creating folder: {p.get('name', '...')}...",
            "delete_file": lambda p: f"Deleting: {p.get('path', '...')}...",
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
