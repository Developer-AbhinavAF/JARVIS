"""Centralized tool metadata registry for JARVIS.

Every tool exposes structured metadata: name, aliases, patterns, category,
priority, permissions, parameters, and examples. This replaces the scattered
registrations across tools.py, tool_router.py, and tool_system.py.

The registry is scanned at startup. No hardcoded tool list is needed.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ToolMeta:
    """Metadata for a single tool."""
    name: str
    description: str
    category: str
    handler: Callable[..., Any] | None = None
    handler_name: str = ""  # dotted import path for lazy loading
    aliases: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)  # regex patterns for matching
    priority: int = 0  # higher = checked first
    confidence: float = 0.90
    permissions: list[str] = field(default_factory=lambda: ["read_only"])
    parameters: dict[str, Any] = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)
    return_type: str = "str"
    requires_confirmation: bool = False
    enabled: bool = True
    extract_params: Callable[[str], dict[str, Any]] | None = None


class ToolCatalog:
    """Central registry of all tools with their metadata."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolMeta] = {}
        self._by_handler: dict[str, ToolMeta] = {}
        self._aliases: dict[str, str] = {}
        self._sorted: list[ToolMeta] | None = None

    def register(self, meta: ToolMeta) -> None:
        self._tools[meta.name] = meta
        if meta.handler_name:
            self._by_handler[meta.handler_name] = meta
        for alias in meta.aliases:
            self._aliases[alias.lower()] = meta.name
        self._sorted = None  # invalidate cache

    def get(self, name: str) -> ToolMeta | None:
        canonical = self._aliases.get(name.lower(), name)
        return self._tools.get(canonical)

    def get_by_handler(self, handler_name: str) -> ToolMeta | None:
        return self._by_handler.get(handler_name)

    def list_all(self) -> list[ToolMeta]:
        if self._sorted is None:
            self._sorted = sorted(
                self._tools.values(),
                key=lambda t: (-t.priority, t.name),
            )
        return self._sorted

    def find_by_pattern(self, text: str) -> ToolMeta | None:
        """Find the best matching tool for the given text."""
        cleaned = text.strip().lower()
        if not cleaned:
            return None
        best: ToolMeta | None = None
        best_confidence = 0.0
        for meta in self.list_all():
            if not meta.enabled:
                continue
            for pattern in meta.patterns:
                try:
                    m = re.search(pattern, cleaned, re.IGNORECASE)
                    if m:
                        if meta.confidence > best_confidence:
                            best = meta
                            best_confidence = meta.confidence
                        break
                except re.error:
                    continue
        return best

    def resolve_handler(self, meta: ToolMeta) -> Callable[..., Any] | None:
        """Resolve the handler function from handler_name or handler attr."""
        if meta.handler:
            return meta.handler
        if meta.handler_name:
            return self._lazy_import(meta.handler_name)
        return None

    def _lazy_import(self, dotted_path: str) -> Callable[..., Any] | None:
        """Import a function from a dotted path like 'jarvis.tools.open_app'."""
        try:
            parts = dotted_path.rsplit(".", 1)
            if len(parts) != 2:
                return None
            module_path, func_name = parts
            import importlib
            module = importlib.import_module(module_path)
            return getattr(module, func_name)
        except Exception as e:
            logger.warning("Failed to import %s: %s", dotted_path, e)
            return None


def _extract_after_prefix(text: str, *prefixes: str) -> dict[str, Any]:
    """Extract the text after one of the given prefixes."""
    cleaned = text.strip().lower()
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            return {"target": cleaned[len(prefix):].strip()}
    return {"target": cleaned}


def _extract_search_query(text: str) -> dict[str, Any]:
    """Extract search query, removing common prefixes."""
    cleaned = text.strip().lower()
    for prefix in [
        "search ", "google ", "look up ", "look for ",
        "find ", "search the web for ", "search the internet for ",
        "search web for ", "search internet for ",
    ]:
        if cleaned.startswith(prefix):
            return {"query": cleaned[len(prefix):].strip()}
    return {"query": cleaned}


def _extract_search_on_platform(text: str) -> dict[str, Any]:
    """Extract query and platform from 'search X on Y'."""
    cleaned = text.strip().lower()
    m = re.match(r"search\s+(.+?)\s+on\s+(\w[\w\s]*?)\s*$", cleaned, re.IGNORECASE)
    if m:
        return {"query": m.group(1).strip(), "platform": m.group(2).strip()}
    return {"query": cleaned}


def _extract_play_query(text: str) -> dict[str, Any]:
    """Extract query from 'play X'."""
    cleaned = text.strip().lower()
    for prefix in ["play ", "play the ", "play a ", "play some "]:
        if cleaned.startswith(prefix):
            return {"query": cleaned[len(prefix):].strip()}
    return {"query": cleaned}


def _extract_open_target(text: str) -> dict[str, Any]:
    """Extract target from 'open X'."""
    cleaned = text.strip().lower()
    for prefix in ["open ", "launch ", "start ", "go to ", "visit ", "navigate to "]:
        if cleaned.startswith(prefix):
            return {"target": cleaned[len(prefix):].strip()}
    return {"target": cleaned}


def _extract_close_target(text: str) -> dict[str, Any]:
    """Extract target from 'close X'."""
    cleaned = text.strip().lower()
    for prefix in ["close ", "quit ", "exit ", "kill "]:
        if cleaned.startswith(prefix):
            return {"target": cleaned[len(prefix):].strip()}
    return {"target": cleaned}


def _extract_volume_action(text: str) -> dict[str, Any]:
    """Extract volume action."""
    cleaned = text.strip().lower()
    if any(w in cleaned for w in ["mute", "silent", "silence"]):
        return {"action": "mute"}
    if any(w in cleaned for w in ["unmute", "un silent", "unsilence"]):
        return {"action": "unmute"}
    m = re.search(r"set\s+(?:the\s+)?volume\s+(?:to\s+)?(\d+)", cleaned)
    if m:
        return {"action": "set", "value": int(m.group(1))}
    if any(w in cleaned for w in ["increase", "up", "raise", "louder", "higher"]):
        return {"action": "up"}
    if any(w in cleaned for w in ["decrease", "down", "lower", "quieter", "softer"]):
        return {"action": "down"}
    return {"action": "up"}


def _extract_brightness_action(text: str) -> dict[str, Any]:
    """Extract brightness action."""
    cleaned = text.strip().lower()
    m = re.search(r"set\s+(?:the\s+)?brightness\s+(?:to\s+)?(\d+)", cleaned)
    if m:
        return {"action": "set", "value": int(m.group(1))}
    if any(w in cleaned for w in ["increase", "up", "brighter", "higher", "brighten"]):
        return {"action": "up"}
    if any(w in cleaned for w in ["decrease", "down", "dimmer", "lower", "dim"]):
        return {"action": "down"}
    return {"action": "up"}


def _extract_power_action(text: str) -> dict[str, Any]:
    """Extract system power action."""
    cleaned = text.strip().lower()
    if any(w in cleaned for w in ["shutdown", "shut down", "power off", "turn off"]):
        return {"action": "shutdown"}
    if any(w in cleaned for w in ["restart", "reboot"]):
        return {"action": "restart"}
    if any(w in cleaned for w in ["sleep", "hibernate"]):
        return {"action": "sleep"}
    if any(w in cleaned for w in ["lock", "lock pc", "lock computer", "lock screen"]):
        return {"action": "lock"}
    if any(w in cleaned for w in ["logout", "log out", "sign out"]):
        return {"action": "logout"}
    return {"action": "shutdown"}


def _extract_calculator(text: str) -> dict[str, Any]:
    """Extract math expression."""
    cleaned = text.strip().lower()
    for prefix in ["calculate ", "calc ", "compute ", "evaluate ", "solve ", "what is ", "what's "]:
        if cleaned.startswith(prefix):
            return {"expression": cleaned[len(prefix):].strip()}
    return {"expression": cleaned}


def _extract_weather_city(text: str) -> dict[str, Any]:
    """Extract city from weather command."""
    cleaned = text.strip().lower()
    m = re.search(r"weather\s+(?:in|at|for|of)\s+(.+)", cleaned)
    if m:
        return {"city": m.group(1).strip()}
    m = re.search(r"(?:what'?s|what\s+is)\s+(?:the\s+)?weather\s+(?:like\s+)?(?:in|at|for)\s+(.+)", cleaned)
    if m:
        return {"city": m.group(1).strip()}
    return {"city": ""}


def _extract_stock_symbol(text: str) -> dict[str, Any]:
    """Extract stock symbol."""
    cleaned = text.strip().lower()
    # "how is tesla doing" → tesla
    m = re.search(r"how\s+(?:is|'s)\s+(\w+)\s+(?:doing|performing|trading)", cleaned)
    if m:
        return {"symbol": m.group(1).upper()}
    # "what about AAPL" → AAPL
    m = re.search(r"what(?:'s| about)\s+(\w+)", cleaned)
    if m:
        return {"symbol": m.group(1).upper()}
    # "check TSLA stock" → TSLA
    m = re.search(r"check\s+(\w+)\s+(?:stock|share|price)", cleaned)
    if m:
        return {"symbol": m.group(1).upper()}
    # Generic: "AAPL stock" → AAPL
    m = re.search(r"(?:stock|price|quote)\s+(?:price\s+)?(?:of\s+|for\s+)?(\w+)", text.strip().upper())
    if m:
        return {"symbol": m.group(1)}
    m = re.search(r"(\w+)\s+(?:stock|share)\s+(?:price|quote)", text.strip().upper())
    if m:
        return {"symbol": m.group(1)}
    words = text.strip().upper().split()
    for w in reversed(words):
        if w.isalpha() and 1 <= len(w) <= 5:
            return {"symbol": w}
    return {"symbol": "AAPL"}


def _extract_window_action(text: str) -> dict[str, Any]:
    """Extract window control action."""
    cleaned = text.strip().lower()
    if "minimize" in cleaned:
        return {"action": "minimize"}
    if "maximize" in cleaned:
        return {"action": "maximize"}
    if "restore" in cleaned:
        return {"action": "restore"}
    if "close" in cleaned:
        return {"action": "close"}
    if "list" in cleaned or "show" in cleaned or "what" in cleaned:
        return {"action": "list"}
    if "switch" in cleaned or "next" in cleaned:
        return {"action": "switch"}
    return {"action": "list"}


def _extract_timer_seconds(text: str) -> dict[str, Any]:
    """Extract timer duration."""
    cleaned = text.strip().lower()
    # Check for minutes
    m = re.search(r"(\d+)\s*(?:minutes?|mins?)", cleaned)
    if m:
        return {"seconds": int(m.group(1)) * 60}
    # Check for hours
    m = re.search(r"(\d+)\s*(?:hours?|hrs?)", cleaned)
    if m:
        return {"seconds": int(m.group(1)) * 3600}
    # Default to seconds
    m = re.search(r"(\d+)", cleaned)
    if m:
        return {"seconds": int(m.group(1))}
    return {"seconds": 30}


# ---------------------------------------------------------------------------
# WEBSITE MAP
# ---------------------------------------------------------------------------
WEBSITES: dict[str, str] = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "reddit": "https://reddit.com",
    "x": "https://x.com",
    "twitter": "https://x.com",
    "instagram": "https://instagram.com",
    "facebook": "https://facebook.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://netflix.com",
    "amazon": "https://amazon.com",
    "linkedin": "https://linkedin.com",
    "whatsapp": "https://web.whatsapp.com",
    "wikipedia": "https://wikipedia.org",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "discord": "https://discord.com",
    "telegram": "https://web.telegram.org",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "translate": "https://translate.google.com",
    "google translate": "https://translate.google.com",
    "drive": "https://drive.google.com",
    "google drive": "https://drive.google.com",
    "meet": "https://meet.google.com",
    "google meet": "https://meet.google.com",
    "docs": "https://docs.google.com",
    "google docs": "https://docs.google.com",
    "sheets": "https://sheets.google.com",
    "google sheets": "https://sheets.google.com",
    "slides": "https://slides.google.com",
    "google slides": "https://slides.google.com",
    "google news": "https://news.google.com",
    "photos": "https://photos.google.com",
    "google photos": "https://photos.google.com",
    "calendar": "https://calendar.google.com",
    "google calendar": "https://calendar.google.com",
    "keep": "https://keep.google.com",
    "google keep": "https://keep.google.com",
    "earth": "https://earth.google.com",
    "bing": "https://bing.com",
    "yahoo": "https://yahoo.com",
    "duckduckgo": "https://duckduckgo.com",
    "medium": "https://medium.com",
    "devto": "https://dev.to",
    "gitlab": "https://gitlab.com",
    "bitbucket": "https://bitbucket.org",
    "npm": "https://npmjs.com",
    "pypi": "https://pypi.org",
    "docker hub": "https://hub.docker.com",
    "figma": "https://figma.com",
    "notion": "https://notion.so",
    "trello": "https://trello.com",
    "slack": "https://slack.com",
    "zoom": "https://zoom.us",
    "teams": "https://teams.microsoft.com",
    "outlook": "https://outlook.live.com",
    "onedrive": "https://onedrive.live.com",
    "dropbox": "https://dropbox.com",
    "twitch": "https://twitch.tv",
    "steam": "https://store.steampowered.com",
    "ebay": "https://ebay.com",
    "flipkart": "https://flipkart.com",
    "aliexpress": "https://aliexpress.com",
    "quora": "https://quora.com",
    "pinterest": "https://pinterest.com",
    "snapchat": "https://snapchat.com",
    "tiktok": "https://tiktok.com",
    "replit": "https://replit.com",
    "codepen": "https://codepen.io",
    "leetcode": "https://leetcode.com",
    "hackerrank": "https://hackerrank.com",
    "coursera": "https://coursera.org",
    "udemy": "https://udemy.com",
    "khan academy": "https://khanacademy.org",
    "wolfram alpha": "https://wolframalpha.com",
    "perplexity": "https://perplexity.ai",
    "copilot": "https://copilot.microsoft.com",
    "deepseek": "https://chat.deepseek.com",
    "grok": "https://grok.com",
    "midjourney": "https://midjourney.com",
    "dalle": "https://labs.openai.com",
    "canva": "https://canva.com",
    "archive": "https://archive.org",
    "wayback machine": "https://web.archive.org",
}

# Build website regex pattern
_WEBSITE_NAMES = "|".join(re.escape(k) for k in sorted(WEBSITES.keys(), key=len, reverse=True))


def _build_website_open_patterns() -> list[str]:
    """Generate regex patterns for opening known websites."""
    return [
        rf"(?:open|launch|go\s+to|visit|navigate\s+to|browse)\s+(?:the\s+)?(?:website\s+)?(?:for\s+)?(?:the\s+)?({_WEBSITE_NAMES})\s*$",
        rf"^{_WEBSITE_NAMES}\s*$",
    ]


# ---------------------------------------------------------------------------
# SEARCH ROUTING MAP
# ---------------------------------------------------------------------------
SEARCH_SITES: dict[str, str] = {
    "youtube": "https://youtube.com/results?search_query=",
    "google": "https://www.google.com/search?q=",
    "github": "https://github.com/search?q=",
    "reddit": "https://www.reddit.com/search/?q=",
    "wikipedia": "https://en.wikipedia.org/w/index.php?search=",
    "stackoverflow": "https://stackoverflow.com/search?q=",
    "stack overflow": "https://stackoverflow.com/search?q=",
    "amazon": "https://www.amazon.com/s?k=",
    "imdb": "https://www.imdb.com/find?q=",
    "spotify": "https://open.spotify.com/search/",
    "x": "https://x.com/search?q=",
    "twitter": "https://x.com/search?q=",
    "linkedin": "https://www.linkedin.com/search/results/all/?keywords=",
    "bing": "https://www.bing.com/search?q=",
    "yahoo": "https://search.yahoo.com/search?p=",
    "duckduckgo": "https://duckduckgo.com/?q=",
    "npm": "https://www.npmjs.com/search?q=",
    "pypi": "https://pypi.org/search/?q=",
    "medium": "https://medium.com/search?q=",
    "quora": "https://www.quora.com/search?q=",
    "ebay": "https://www.ebay.com/sch/i.html?_nkw=",
    "flipkart": "https://www.flipkart.com/search?q=",
    "aliexpress": "https://www.aliexpress.com/wholesale?SearchText=",
    "pinterest": "https://www.pinterest.com/search/pins/?q=",
    "leetcode": "https://leetcode.com/problemset/all/?search=",
    "replit": "https://replit.com/search?q=",
    "notion": "https://www.notion.so/search?q=",
    "google scholar": "https://scholar.google.com/scholar?q=",
    "arxiv": "https://arxiv.org/search/?query=",
    "pubmed": "https://pubmed.ncbi.nlm.nih.gov/?term=",
    "zlib": "https://z-lib.org/s/",
    "libgen": "https://libgen.is/search.php?req=",
    "archive": "https://archive.org/search?query=",
    "wolfram alpha": "https://www.wolframalpha.com/input?i=",
}

_SEARCH_SITE_NAMES = "|".join(re.escape(k) for k in sorted(SEARCH_SITES.keys(), key=len, reverse=True))


# ---------------------------------------------------------------------------
# FOLDER / FILE OPEN PATTERNS
# ---------------------------------------------------------------------------
FOLDERS: dict[str, str] = {
    "downloads": "~/Downloads",
    "documents": "~/Documents",
    "desktop": "~/Desktop",
    "pictures": "~/Pictures",
    "music": "~/Music",
    "videos": "~/Videos",
    "home": "~",
    "my computer": "::{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
    "this pc": "::{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
    "recycle bin": "::{645FF040-5081-101B-9F08-00A002F954E}",
    "control panel": "control",
    "settings": "ms-settings:",
    "task manager": "taskmgr.exe",
}


def build_catalog() -> ToolCatalog:
    """Build the complete tool catalog with all metadata."""
    catalog = ToolCatalog()

    # ──────────────────────────────────────────────────────────
    # OPEN WEBSITE / APP
    # ──────────────────────────────────────────────────────────
    website_patterns = _build_website_open_patterns()
    catalog.register(ToolMeta(
        name="open_website",
        description="Open a known website in the default browser",
        category="browser",
        handler_name="jarvis.tools.open_app",
        patterns=website_patterns,
        priority=100,
        confidence=0.98,
        permissions=["network"],
        parameters={"target": {"required": True, "type": "str"}},
        examples=["open youtube", "launch github", "go to reddit", "visit google"],
        extract_params=_extract_open_target,
    ))

    # Open known folders
    folder_names = "|".join(re.escape(k) for k in FOLDERS)
    catalog.register(ToolMeta(
        name="open_folder",
        description="Open a known folder or system location",
        category="system",
        handler_name="jarvis.tools.open_app",
        patterns=[
            rf"(?:open|launch|go\s+to|show|explore)\s+(?:the\s+)?(?:folder\s+)?(?:my\s+)?({folder_names})\s*$",
            rf"(?:open|show)\s+(?:my\s+)?(?:downloads|documents|desktop|pictures|music|videos)\s*$",
        ],
        priority=99,
        confidence=0.95,
        permissions=["system"],
        parameters={"target": {"required": True, "type": "str"}},
        examples=["open downloads", "open documents", "show desktop", "open my computer"],
        extract_params=_extract_open_target,
    ))

    # Greeting
    catalog.register(ToolMeta(
        name="greeting",
        description="Handle greetings and small talk",
        category="entertainment",
        handler_name="jarvis.tools.greeting",
        patterns=[
            r"^(?:hello|hi|hey|howdy|yo|sup|hola|greetings)\s*$",
            r"^good\s+(?:morning|afternoon|evening|day)\s*$",
            r"^how\s+(?:are\s+you|do\s+you\s+do|have\s+you\s+been)\s*$",
            r"^(?:what'?s?\s+up|how's\s+it\s+going|how\s+are\s+things)\s*$",
            r"^(?:who\s+are\s+you|what\s+are\s+you|what'?s?\s+your\s+name)\s*$",
            r"^(?:thanks?|thank\s+you|thx|ty|cheers)\s*$",
            r"^(?:bye|goodbye|see\s+you|later|good\s+night)\s*$",
            r"^(?:please|thanks|thank\s+you)\s*$",
        ],
        priority=100,
        confidence=0.95,
        permissions=["read_only"],
        parameters={},
        examples=["hello", "hi", "how are you", "who are you", "thanks", "bye"],
    ))

    # Open apps
    catalog.register(ToolMeta(
        name="open_app",
        description="Open an application by name",
        category="system",
        handler_name="jarvis.tools.open_app",
        patterns=[
            r"(?:open|launch|start|run)\s+(?:the\s+)?(?:app|application|program|software)\s+(.+)",
            r"(?:open|launch|start|run|fire\s+up|bring\s+up|boot\s+up|load)\s+(notepad|calculator|chrome|firefox|edge|explorer|terminal|cmd|powershell|vscode|visual\s+studio\s+code|spotify|vlc|paint|word|excel|powerpoint|outlook|teams|discord|slack|zoom|steam|obs|git|postman|figma|brave|opera|safari|ie|internet\s+explorer|snipping\s+tool|control\s+panel|task\s+manager|settings)",
            r"(?:open|launch|start|run)\s+file\s+explorer",
            r"(?:open|launch|start)\s+command\s+prompt",
            r"(?:open|launch|start)\s+power\s+shell",
            r"(?:open|launch|start|run)\s+(?:the\s+)?(.+?)\s+(?:app|application|program|software)\s*$",
            r"(?:open|launch|start|run|fire\s+up|bring\s+up|boot\s+up|load)\s+(?:up\s+)?(.+?)\s+(?:please|for\s+me|now)?\s*$",
        ],
        priority=98,
        confidence=0.92,
        permissions=["system"],
        parameters={"target": {"required": True, "type": "str"}},
        examples=["open chrome", "launch notepad", "start calculator", "open vs code"],
        extract_params=_extract_open_target,
    ))

    # Close app
    catalog.register(ToolMeta(
        name="close_app",
        description="Close an application by name",
        category="system",
        handler_name="jarvis.tools.close_app",
        patterns=[
            r"(?:close|kill|stop|exit|quit)\s+(?:the\s+)?(?:app|application|program|process)\s+(.+)",
            r"(?:close|kill|stop|exit|quit)\s+(notepad|calculator|chrome|firefox|edge|explorer|terminal|cmd|vscode|spotify|vlc|paint|word|excel|powerpoint|teams|discord|slack|zoom|steam|obs)",
        ],
        priority=95,
        confidence=0.90,
        permissions=["system"],
        parameters={"target": {"required": True, "type": "str"}},
        examples=["close chrome", "kill notepad", "exit spotify"],
        extract_params=_extract_close_target,
    ))

    # ──────────────────────────────────────────────────────────
    # SEARCH
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="search_on_platform",
        description="Search on a specific platform or website",
        category="search",
        handler_name="jarvis.tools.search_on_platform",
        patterns=[
            rf"search\s+(.+?)\s+on\s+({_SEARCH_SITE_NAMES})\s*$",
            rf"find\s+(.+?)\s+on\s+({_SEARCH_SITE_NAMES})\s*$",
            rf"look\s+up\s+(.+?)\s+on\s+({_SEARCH_SITE_NAMES})\s*$",
        ],
        priority=97,
        confidence=0.96,
        permissions=["network"],
        parameters={"query": {"required": True, "type": "str"}, "platform": {"required": True, "type": "str"}},
        examples=[
            "search AI on youtube", "search python on github",
            "search machine learning on reddit", "search quantum on wikipedia",
            "search javascript on stackoverflow", "search laptop on amazon",
            "search inception on imdb", "search jazz on spotify",
            "search AI on x", "search jobs on linkedin",
            "search recipe on medium",
        ],
        extract_params=_extract_search_on_platform,
    ))

    catalog.register(ToolMeta(
        name="web_search",
        description="Search the web using Google (default) or other search engine",
        category="search",
        handler_name="jarvis.tools.web_search",
        patterns=[
            r"^search\s+(?:the\s+)?(?:web|internet)\s+for\s+",
            r"^search\s+",
            r"^google\s+",
            r"^look\s+up\s+",
            r"^find\s+(?:me\s+)?(?:information|about|out|some)?\s*",
            r"^what\s+is\s+",
            r"^who\s+is\s+",
            r"^how\s+(?:to|do|does|can|would|should)",
            r"^why\s+(?:is|are|do|does|did|can|would)",
            r"^where\s+(?:is|are|can|do|does)",
            r"^when\s+(?:is|are|do|does|did|was|were)",
            r"^tell\s+me\s+(?:about|something)",
            r"^explain\s+",
            r"^define\s+",
            r"^describe\s+",
        ],
        priority=80,
        confidence=0.85,
        permissions=["network"],
        parameters={"query": {"required": True, "type": "str"}},
        examples=["search AI", "search the web for python tutorials", "google machine learning"],
        extract_params=_extract_search_query,
    ))

    # ──────────────────────────────────────────────────────────
    # PLAY / MEDIA
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="play_music",
        description="Play a song or music on YouTube / YouTube Music",
        category="media",
        handler_name="jarvis.tools.play_music",
        patterns=[
            r"^play\s+",
            r"^play\s+(?:the\s+)?(?:song|music|track|album)\s+",
            r"^play\s+(?:some\s+)?(?:music|songs?)\s*$",
            r"^play\s+(?:the\s+)?(?:music|song|track)\s+",
            r"^listen\s+to\s+",
            r"^put\s+on\s+",
            r"^start\s+playing\s+",
            r"^kya\s+(?:bajaa|chala|suna)\s+",
        ],
        priority=96,
        confidence=0.92,
        permissions=["network"],
        parameters={"query": {"required": True, "type": "str"}},
        examples=["play believer", "play never gonna give you up", "play some jazz", "play ed sheeran"],
        extract_params=_extract_play_query,
    ))

    # ──────────────────────────────────────────────────────────
    # SYSTEM CONTROL
    # ──────────────────────────────────────────────────────────

    # Screenshot
    catalog.register(ToolMeta(
        name="screenshot",
        description="Take a screenshot of the current screen",
        category="system",
        handler_name="jarvis.system_control.screenshot",
        patterns=[
            r"(?:take|get|capture)\s+(?:a\s+)?(?:screenshot|screen\s*shot|screen\s*capture|snapshot)",
            r"^screenshot\s*$",
            r"^screenshot\s+(?:now|please)\s*$",
            r"(?:capture|grab)\s+(?:the\s+)?(?:screen|display)",
            r"capture\s+(?:my\s+)?(?:screen|display)",
        ],
        priority=94,
        confidence=0.98,
        permissions=["system"],
        parameters={},
        examples=["take screenshot", "capture screen", "screenshot"],
    ))

    # Volume
    catalog.register(ToolMeta(
        name="volume_control",
        description="Control system volume (up, down, mute, unmute, set)",
        category="system",
        handler_name="jarvis.system_control.volume_control",
        patterns=[
            r"(?:turn\s+)?(?:the\s+)?volume\s+(?:to\s+)?(up|down|increase|decrease|raise|lower)",
            r"(?:turn\s+)?(?:it\s+)?(?:up|down)\s+(?:the\s+)?volume",
            r"(?:increase|raise|louder|higher)\s+(?:the\s+)?(?:volume|sound|audio)",
            r"(?:decrease|lower|quieter|softer)\s+(?:the\s+)?(?:volume|sound|audio)",
            r"^mute\s*(?:the\s+)?(?:audio|sound|volume)?\s*$",
            r"^unmute\s*(?:the\s+)?(?:audio|sound|volume)?\s*$",
            r"(?:turn|set)\s+(?:the\s+)?volume\s+(?:to\s+)?(\d+)",
            r"^volume\s+(?:to\s+)?(\d+)\s*$",
            r"^set\s+(?:the\s+)?volume\s+(?:to\s+)?(\d+)",
            r"^(?:make|turn)\s+it\s+(?:louder|quieter|softer|higher|lower|up|down)",
            r"^volume\s+(?:up|down|increase|decrease|raise|lower)\s*$",
        ],
        priority=93,
        confidence=0.95,
        permissions=["system"],
        parameters={"action": {"required": True, "type": "str"}, "value": {"required": False, "type": "int"}},
        examples=["mute volume", "volume up", "increase volume", "set volume to 50"],
        extract_params=_extract_volume_action,
    ))

    # Brightness
    catalog.register(ToolMeta(
        name="brightness_control",
        description="Control screen brightness (up, down, set)",
        category="system",
        handler_name="jarvis.system_control.brightness_control",
        patterns=[
            r"(?:turn\s+)?(?:the\s+)?brightness\s+(?:to\s+)?(up|down|increase|decrease|raise|lower)",
            r"(?:increase|raise|make)\s+(?:it|the|screen|display|monitor)\s+(?:brighter|bright)",
            r"(?:decrease|lower|dim|make)\s+(?:it|the|screen|display|monitor)\s+(?:dimmer|dim)",
            r"(?:turn|set)\s+(?:the\s+)?brightness\s+(?:to\s+)?(\d+)",
            r"^brightness\s+(?:to\s+)?(\d+)\s*$",
            r"^set\s+(?:the\s+)?brightness\s+(?:to\s+)?(\d+)",
            r"^brightness\s+(up|down|increase|decrease)\s*$",
            r"^increase\s+(?:the\s+)?brightness\s*$",
            r"^decrease\s+(?:the\s+)?brightness\s*$",
            r"^dim\s+(?:the\s+)?(?:screen|display|monitor)\s*$",
            r"^brighten\s+(?:the\s+)?(?:screen|display|monitor)\s*$",
            r"(?:turn|make)\s+(?:it|the\s+)?(?:screen|display)?\s*(?:brighter|dimmer)",
            r"^(?:turn|make)\s+(?:the\s+)?screen\s+(?:up|down)\s*$",
            r"^turn\s+(?:the\s+)?brightness\s+(?:up|down|higher|lower)\s*$",
            r"^turn\s+(?:the\s+)?(?:screen|display)?\s*(?:up|down|brighter|dimmer)\s*$",
            r"^turn\s+(?:up|down)\s+(?:the\s+)?(?:brightness|screen|display|monitor)\s*$",
        ],
        priority=92,
        confidence=0.93,
        permissions=["system"],
        parameters={"action": {"required": True, "type": "str"}, "value": {"required": False, "type": "int"}},
        examples=["increase brightness", "brightness up", "set brightness to 80", "dim screen"],
        extract_params=_extract_brightness_action,
    ))

    # System power
    catalog.register(ToolMeta(
        name="system_power",
        description="Control system power (shutdown, restart, sleep, lock, logout)",
        category="system",
        handler_name="jarvis.system_control.system_power",
        patterns=[
            r"(?:shut\s*down|shutdown|power\s*off|poweroff|turn\s*off)\s*(?:the\s+)?(?:computer|pc|system|laptop|machine)?\s*$",
            r"(?:restart|reboot)\s*(?:the\s+)?(?:computer|pc|system|laptop|machine)?\s*$",
            r"(?:sleep|hibernate|suspend)\s*(?:the\s+)?(?:computer|pc|system|laptop|machine)?\s*$",
            r"(?:lock|lock\s+the)\s*(?:the\s+)?(?:computer|pc|system|laptop|screen|workstation)?\s*$",
            r"(?:log\s*out|sign\s*out|logout|signout)\s*(?:of\s+)?(?:the\s+)?(?:computer|pc|system)?\s*$",
            r"^shutdown\s*$",
            r"^restart\s*$",
            r"^reboot\s*$",
            r"^lock\s*(?:pc|screen|computer)?\s*$",
        ],
        priority=91,
        confidence=0.95,
        permissions=["system", "sensitive"],
        parameters={"action": {"required": True, "type": "str"}},
        examples=["shutdown pc", "restart computer", "lock screen", "sleep laptop"],
        requires_confirmation=True,
        extract_params=_extract_power_action,
    ))

    # ──────────────────────────────────────────────────────────
    # CLIPBOARD
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="clipboard_paste",
        description="Paste clipboard contents",
        category="system",
        handler_name="jarvis.system_control.clipboard_manager",
        patterns=[
            r"^paste\s*$",
            r"^paste\s+(?:it|this|that|text|content)\s*$",
            r"(?:show|get|read|what'?s?\s+on)\s+(?:the\s+)?(?:clipboard|clip\s*board)",
            r"what'?s?\s+(?:copied|in\s+the\s+clipboard)",
            r"^paste\s+(?:from\s+)?(?:the\s+)?clipboard\s*$",
            r"^clipboard\s+(?:paste|show|get|read)\s*$",
        ],
        priority=88,
        confidence=0.92,
        permissions=["system"],
        parameters={"action": {"required": True, "type": "str"}},
        examples=["paste", "show clipboard", "what's on clipboard"],
        extract_params=lambda t: {"action": "paste" if t.strip().lower().startswith("paste") else "get"},
    ))

    catalog.register(ToolMeta(
        name="clipboard_copy",
        description="Copy text to clipboard",
        category="system",
        handler_name="jarvis.system_control.clipboard_manager",
        patterns=[
            r"^copy\s+(?!file\b)(.+)",
            r"^copy\s+(?:this|that|the\s+following)\s+(.+)",
        ],
        priority=87,
        confidence=0.85,
        permissions=["system"],
        parameters={"action": {"required": True, "type": "str"}, "text": {"required": True, "type": "str"}},
        examples=["copy hello world", "copy this text"],
        extract_params=lambda t: {"action": "copy", "text": t.split(None, 1)[-1] if len(t.split(None, 1)) > 1 else ""},
    ))

    catalog.register(ToolMeta(
        name="copy_file",
        description="Copy a file",
        category="files",
        handler_name="jarvis.file_ops.copy_file",
        patterns=[
            r"^copy\s+file\s*$",
            r"^copy\s+(?:a\s+)?file\s*$",
        ],
        priority=91,
        confidence=0.90,
        permissions=["files"],
        parameters={},
        examples=["copy file"],
    ))

    catalog.register(ToolMeta(
        name="rename_file",
        description="Rename a file",
        category="files",
        handler_name="jarvis.file_ops.rename_file",
        patterns=[
            r"^rename\s+file\s*$",
            r"^rename\s+(?:a\s+)?file\s*$",
        ],
        priority=91,
        confidence=0.90,
        permissions=["files"],
        parameters={},
        examples=["rename file"],
    ))

    # ──────────────────────────────────────────────────────────
    # SYSTEM STATUS
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="system_status",
        description="Get system status (CPU, RAM, battery, disk)",
        category="system",
        handler_name="jarvis.dashboard.get_system_stats",
        patterns=[
            r"(?:system|computer|pc|laptop)\s+(?:status|stats|info|information|health|performance)",
            r"(?:show|get|check|tell)\s+(?:me\s+)?(?:the\s+)?(?:system|computer|pc)\s+(?:status|stats|info)",
            r"(?:what'?s?|what\s+is)\s+(?:the\s+)?(?:system|computer|pc)\s+(?:status|health|stats)",
            r"(?:how(?:'?s| is))\s+(?:the\s+)?(?:system|computer|pc)\s+(?:doing|running|health|performance)",
            r"^system\s+(?:status|stats|info)\s*$",
            r"^status\s*$",
            r"^pc\s+(?:status|stats)\s*$",
            r"(?:how\s+much|what(?:'s| is))\s+(?:the\s+)?(?:cpu|ram|memory|disk|storage|space)\s+(?:am\s+i\s+)?(?:using|usage|left|free|available)",
            r"(?:cpu|ram|memory|disk|storage)\s+(?:usage|utilization|load)\s+(?:right\s+now|currently|now)?",
            r"(?:check|show|get|what(?:'s| is))\s+(?:my\s+)?(?:cpu|ram|memory|disk|storage)\s+(?:usage|level|amount)",
            r"(?:what|how)\s+(?:is|does)\s+my\s+(?:system|computer|pc)\s+(?:look\s+like|show|display)",
            r"^how\s+(?:is|'s)\s+(?:my\s+)?system\s+(?:doing|running|performing)\s*$",
        ],
        priority=90,
        confidence=0.95,
        permissions=["read_only"],
        parameters={},
        examples=["system status", "check pc status", "how's the system doing"],
    ))

    catalog.register(ToolMeta(
        name="battery_status",
        description="Get battery status",
        category="system",
        handler_name="jarvis.dashboard.get_system_stats",
        patterns=[
            r"(?:what'?s?|how(?:'s| is))\s+(?:my\s+)?(?:battery|power|charge)",
            r"(?:check|get|show)\s+(?:my\s+)?(?:battery|power)\s+(?:status|level|percentage|charge)",
            r"^battery\s+(?:status|level|charge|percentage)\s*$",
            r"^battery\s*$",
            r"^how\s+much\s+(?:battery|power|charge)\s+(?:do\s+i\s+have|is\s+left|remaining)\s*$",
            r"^is\s+(?:my\s+)?(?:laptop|computer|pc)\s+(?:charging|plugged\s+in|on\s+battery)\s*$",
            r"^battery\s+(?:level|percentage|left|remaining|charge)\s*$",
            r"^what(?:'s| is)\s+(?:the\s+)?battery\s+level\s*$",
        ],
        priority=90,
        confidence=0.95,
        permissions=["read_only"],
        parameters={},
        examples=["battery status", "what's my battery level", "check battery"],
    ))

    catalog.register(ToolMeta(
        name="network_status",
        description="Get network status or run speed test",
        category="network",
        handler_name="jarvis.dashboard.run_network_speed_test",
        patterns=[
            r"(?:network|internet)\s+(?:status|speed|test|speedtest|performance|info)",
            r"(?:check|run|do)\s+(?:a\s+)?(?:network|internet)\s+(?:speed|test)",
            r"^network\s+(?:status|speed|info)\s*$",
            r"^internet\s+(?:status|speed|test)\s*$",
            r"^speed\s+test\s*$",
        ],
        priority=89,
        confidence=0.93,
        permissions=["read_only"],
        parameters={},
        examples=["network status", "run speed test", "internet speed"],
    ))

    # ──────────────────────────────────────────────────────────
    # WINDOW CONTROL
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="window_control",
        description="Control windows (minimize, maximize, close, switch, list)",
        category="system",
        handler_name="jarvis.system_control.window_control",
        patterns=[
            r"(?:minimize|maximize|restore|close)\s+(?:the\s+)?(?:window|app|application|screen)",
            r"(?:minimize|maximize|restore|close)\s+this\s+(?:window|app|application)",
            r"(?:switch|alt)\s+tab",
            r"^switch\s+(?:to|window)\s*$",
            r"(?:show|list)\s+(?:all\s+)?(?:windows?|open\s+apps?)",
            r"^list\s+(?:active\s+)?windows?\s*$",
            r"^(?:minimize|maximize|restore|close)\s+(?:the\s+)?(?:current\s+)?window\s*$",
            r"^(?:minimize|maximize|restore|close)\s+this\s*$",
        ],
        priority=85,
        confidence=0.88,
        permissions=["system"],
        parameters={"action": {"required": True, "type": "str"}},
        examples=["minimize window", "maximize window", "list windows", "switch window"],
        extract_params=_extract_window_action,
    ))

    # ──────────────────────────────────────────────────────────
    # SCREEN INFO
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="screen_info",
        description="Get screen resolution and mouse position",
        category="system",
        handler_name="jarvis.system_control.get_screen_info",
        patterns=[
            r"(?:screen|display|monitor)\s+(?:resolution|info|information|size|details)",
            r"(?:what'?s?|what\s+is|get)\s+(?:my\s+)?(?:screen|display)\s+(?:resolution|size)",
        ],
        priority=84,
        confidence=0.90,
        permissions=["read_only"],
        parameters={},
        examples=["screen resolution", "display info"],
    ))

    # ──────────────────────────────────────────────────────────
    # CALCULATOR
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="calculator",
        description="Calculate mathematical expressions",
        category="tools",
        handler_name="jarvis.tools.calculator",
        patterns=[
            r"(?:calculate|calc|compute|eval|evaluate|solve)\s+",
            r"(?:what\s+is|what'?s)\s+\d+[\s]*[\+\-\*\/\%][\s]*\d+",
            r"^\d+[\s]*[\+\-\*\/\%][\s]*\d+",
            r"(?:multiply|times|multiplied)\s+\d+[\s]*(?:by|x|X|\*)\s*\d+",
            r"(?:divide|divided)\s+\d+[\s]*(?:by|\/)\s*\d+",
            r"(?:add|plus|sum)\s+\d+[\s]*(?:and|to|\+)\s*\d+",
            r"(?:subtract|minus|less)\s+\d+[\s]*(?:from|minus|-)\s*\d+",
            r"\d+[\s]*(?:\+|\-|\*|\/|x|X|times|plus|minus|divided|multiplied)\s*\d+",
            r"\d+\s+divided\s+by\s+\d+",
            r"\d+\s+times\s+\d+",
            r"\d+\s+plus\s+\d+",
            r"\d+\s+minus\s+\d+",
        ],
        priority=75,
        confidence=0.90,
        permissions=["read_only"],
        parameters={"expression": {"required": True, "type": "str"}},
        examples=["calculate 2+2", "calc 100*5", "what is 15*3"],
        extract_params=_extract_calculator,
    ))

    # ──────────────────────────────────────────────────────────
    # WEATHER
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="weather",
        description="Get weather information for a city",
        category="weather",
        handler_name="jarvis.tools.get_weather",
        patterns=[
            r"^weather\s+(?:in|at|for|of)\s+",
            r"^weather\s+\S+",
            r"(?:what'?s?|what\s+is)\s+(?:the\s+)?(?:weather|temperature|forecast)\s+(?:like\s+)?(?:in|at|for)",
            r"(?:how(?:'?s| is))\s+(?:the\s+)?(?:weather|temperature)\s+(?:in|at|for)",
            r"^weather\s*$",
            r"(?:what'?s?|what\s+is)\s+(?:the\s+)?weather\s+(?:like\s+)?here\s*$",
            r"^is\s+it\s+(?:going\s+to\s+)?(?:rain|snow|hot|cold|warm|sunny|cloudy)\s+(?:today|tomorrow|this\s+week)?\s*$",
            r"^how\s+(?:hot|cold|warm|cool)\s+is\s+it\s+(?:in|at|today|now)?\s*\w*\s*$",
            r"^what'?s?\s+(?:the\s+)?(?:temperature|forecast)\s*$",
            r"^do\s+i\s+(?:need|bring)\s+(?:an?\s+)?(?:umbrella|raining|rain\s+gear)\s*$",
            r"^weather\s+like\s*$",
            r"^what(?:'s|\s+is)\s+(?:the\s+)?weather\s+like\s*$",
            r"^whats\s+(?:the\s+)?weather\s+like\s*$",
        ],
        priority=86,
        confidence=0.95,
        permissions=["network"],
        parameters={"city": {"required": True, "type": "str"}},
        examples=["weather in London", "weather tokyo", "what's the weather in Delhi"],
        extract_params=_extract_weather_city,
    ))

    # ──────────────────────────────────────────────────────────
    # NEWS
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="news",
        description="Get latest news headlines",
        category="news",
        handler_name="jarvis.tools.finnhub_market_news",
        patterns=[
            r"(?:latest|breaking|today'?s?|current)\s+(?:news|headlines)",
            r"^news\s+(?:about|on|in|of|for)\s+",
            r"^news\s*$",
            r"^headlines\s*$",
            r"(?:what'?s?|what\s+is)\s+happening\s+(?:in|around)",
            r"^give\s+me\s+(?:the\s+)?(?:news|headlines|latest)\s*$",
            r"^show\s+me\s+(?:the\s+)?(?:news|headlines)\s*$",
            r"^what(?:'s| is)\s+(?:in\s+)?(?:the\s+)?news\s*$",
            r"^any\s+(?:new|breaking)\s+(?:news|headlines)\s*$",
        ],
        priority=82,
        confidence=0.88,
        permissions=["network"],
        parameters={},
        examples=["latest news", "news about AI", "headlines"],
    ))

    # ──────────────────────────────────────────────────────────
    # JOKE / QUOTE / ENTERTAINMENT
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="joke",
        description="Tell a random joke",
        category="entertainment",
        handler_name="jarvis.tools.get_joke",
        patterns=[
            r"(?:tell|make|crack|give|say)\s+(?:me\s+)?(?:a\s+)?(?:joke|funny|laugh)",
            r"^joke\s*(?:please|now)?\s*$",
            r"^tell\s+me\s+a\s+joke\s*$",
            r"^something\s+funny\s*$",
            r"^make\s+me\s+laugh\s*$",
            r"^got\s+(?:any\s+)?(?:jokes?|funny)\s*$",
            r"^tell\s+me\s+something\s+funny\s*$",
            r"^i(?:'m| am)\s+bored\s*$",
            r"^entertain\s+me\s*$",
            r"^make\s+(?:a\s+)?(?:joke|funny)\s*$",
        ],
        priority=70,
        confidence=0.95,
        permissions=["read_only"],
        parameters={},
        examples=["tell me a joke", "joke", "say something funny"],
    ))

    catalog.register(ToolMeta(
        name="quote",
        description="Get an inspirational quote",
        category="entertainment",
        handler_name="jarvis.tools.get_quote",
        patterns=[
            r"(?:give|tell|show|inspire|send)\s+(?:me\s+)?(?:an?\s+)?(?:quote|inspiration|motivational)",
            r"^quote\s+(?:of\s+the\s+day|please|now)?\s*$",
            r"^inspire\s+me\s*$",
            r"^say\s+something\s+(?:motivational|inspirational|encouraging)\s*$",
            r"^give\s+me\s+(?:some\s+)?(?:inspiration|motivation|encouragement)\s*$",
            r"^i\s+(?:need|want)\s+(?:some\s+)?(?:inspiration|motivation|encouragement)\s*$",
            r"^motivat(?:e|ion)\s+me\s*$",
            r"^quote\s+of\s+the\s+day\s*$",
        ],
        priority=69,
        confidence=0.92,
        permissions=["read_only"],
        parameters={},
        examples=["give me a quote", "inspire me", "quote of the day"],
    ))

    catalog.register(ToolMeta(
        name="flip_coin",
        description="Flip a coin",
        category="entertainment",
        handler_name="jarvis.tools.flip_coin",
        patterns=[
            r"(?:flip|toss)\s+(?:a\s+)?(?:coin|quarter)",
            r"^heads\s+or\s+tails\s*$",
        ],
        priority=68,
        confidence=0.98,
        permissions=["read_only"],
        parameters={},
        examples=["flip a coin", "heads or tails"],
    ))

    catalog.register(ToolMeta(
        name="roll_dice",
        description="Roll a dice",
        category="entertainment",
        handler_name="jarvis.tools.roll_dice",
        patterns=[
            r"(?:roll|throw|toss)\s+(?:a\s+)?(?:dice|die|d\s*6)",
        ],
        priority=67,
        confidence=0.98,
        permissions=["read_only"],
        parameters={"sides": {"required": False, "type": "int", "default": 6}},
        examples=["roll a dice", "roll dice"],
    ))

    # ──────────────────────────────────────────────────────────
    # TIMER
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="timer",
        description="Set a timer for specified duration",
        category="tools",
        handler_name="jarvis.tools.timer",
        patterns=[
            r"(?:set|start|create)\s+(?:a\s+)?timer\s+(?:for\s+)?(\d+)",
            r"^timer\s+(\d+)",
            r"(?:set|start)\s+(?:a\s+)?timer\s+(?:for\s+)?(\d+)\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?)",
        ],
        priority=73,
        confidence=0.95,
        permissions=["read_only"],
        parameters={"seconds": {"required": True, "type": "int"}},
        examples=["set timer for 60", "timer 5 minutes", "start timer for 30 seconds"],
        extract_params=_extract_timer_seconds,
    ))

    # ──────────────────────────────────────────────────────────
    # DATETIME
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="datetime",
        description="Get current date and time",
        category="tools",
        handler_name="jarvis.tools.get_datetime",
        patterns=[
            r"(?:what'?s?|what\s+is|tell\s+me)\s+(?:the\s+)?(?:time|date|day)(?:\s+(?:right\s+now|now|currently|today))?\s*$",
            r"(?:current|today'?s?)\s+(?:time|date|day)(?:\s+(?:right\s+now|now|currently))?\s*$",
            r"(?:what|which)\s+(?:day|date|time)\s+is\s+(?:it|today)\s*$",
            r"^what\s+time\s+is\s+it\s+(?:right\s+now|now|currently)?\s*$",
            r"^current\s+(?:date\s+and\s+)?time\s*$",
            r"^current\s+date\s+and\s+time\s*$",
            r"^what(?:'s|\s+is)\s+the\s+current\s+(?:time|date|day)\s*$",
        ],
        priority=72,
        confidence=0.98,
        permissions=["read_only"],
        parameters={},
        examples=["what time is it", "what's the date", "current time"],
    ))

    # ──────────────────────────────────────────────────────────
    # MEMORY
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="memory_save",
        description="Save information to memory",
        category="memory",
        handler_name="jarvis.memory.memory_save_permanent",
        patterns=[
            r"^(?:remember|save|store|keep)\s+",
            r"^(?:learn|memorize)\s+",
            r"^add\s+(?:this|to)\s+(?:memory|notes)",
            r"^save\s+(?:this\s+)?(?:to\s+)?(?:memory|my\s+notes)",
            r"^note\s+(?:this|that)\s+",
            r"^write\s+down\s+",
            r"^don'?t?\s+forget\s+(?:that|about|to)\s+",
        ],
        priority=81,
        confidence=0.90,
        permissions=["read_only"],
        parameters={"info": {"required": True, "type": "str"}},
        examples=["remember my birthday is Jan 1", "save this to memory"],
        extract_params=lambda t: {"info": t.split(None, 1)[-1] if len(t.split(None, 1)) > 1 else t},
    ))

    catalog.register(ToolMeta(
        name="memory_search",
        description="Search personal memory",
        category="memory",
        handler_name="jarvis.memory.memory_search_notes",
        patterns=[
            r"^(?:what|tell\s+me)\s+(?:do\s+you\s+)?(?:remember|know|have)",
            r"^search\s+(?:my\s+)?(?:memory|notes)",
            r"^(?:find|show|list)\s+(?:in\s+)?(?:my\s+)?(?:memory|notes)",
            r"^what\s+(?:did\s+you\s+learn|have\s+you\s+learned|do\s+you\s+know)",
        ],
        priority=80,
        confidence=0.88,
        permissions=["read_only"],
        parameters={"query": {"required": True, "type": "str"}},
        examples=["what do you remember", "search my notes"],
        extract_params=lambda t: {"query": t.split(None, 2)[-1] if len(t.split(None, 2)) > 2 else ""},
    ))

    # ──────────────────────────────────────────────────────────
    # TODO
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="add_todo",
        description="Add a to-do item",
        category="memory",
        handler_name="jarvis.memory.memory_add_todo",
        patterns=[
            r"^(?:add|create|make)\s+(?:a\s+)?(?:todo|to.?do\s+item|task|reminder)",
            r"^(?:add|create|make)\s+.+\s+to\s+(?:my\s+)?(?:todo|to.?do|task|reminder|list)",
            r"^(?:remind|reminder)\s+(?:me\s+)?(?:to|about)\s+",
            r"^don'?t?\s+forget\s+(?:to|about)\s+",
        ],
        priority=78,
        confidence=0.88,
        permissions=["read_only"],
        parameters={"task": {"required": True, "type": "str"}},
        examples=["add todo buy groceries", "remind me to call mom"],
        extract_params=lambda t: {"task": t.split(None, 2)[-1] if len(t.split(None, 2)) > 2 else t},
    ))

    catalog.register(ToolMeta(
        name="list_todos",
        description="List to-do items",
        category="memory",
        handler_name="jarvis.memory.memory_get_todos",
        patterns=[
            r"^(?:list|show|get|what\s+are)\s+(?:my\s+)?(?:todos?|to.?do\s+(?:list|items|tasks)|tasks|reminders)",
            r"^what\s+(?:do\s+i\s+need\s+to\s+do|is\s+on\s+my\s+(?:list|schedule))",
            r"^show\s+me\s+(?:my\s+)?(?:tasks?|todos?|reminders?)\s*$",
            r"^what(?:'s| are)\s+(?:on\s+)?(?:my\s+)?(?:list|schedule|agenda|plan)\s*$",
            r"^my\s+(?:tasks?|todos?|reminders?)\s*$",
        ],
        priority=77,
        confidence=0.88,
        permissions=["read_only"],
        parameters={},
        examples=["show my todos", "what do I need to do"],
    ))

    # ──────────────────────────────────────────────────────────
    # NOTES
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="add_note",
        description="Add a note",
        category="memory",
        handler_name="jarvis.memory.memory_add_note",
        patterns=[
            r"^(?:add|create|make|save|take)\s+(?:a\s+)?note\s+",
        ],
        priority=76,
        confidence=0.85,
        permissions=["read_only"],
        parameters={"title": {"required": False, "type": "str"}, "content": {"required": True, "type": "str"}},
        examples=["add note buy milk"],
        extract_params=lambda t: {"title": "Quick Note", "content": t.split(None, 2)[-1] if len(t.split(None, 2)) > 2 else t},
    ))

    # ──────────────────────────────────────────────────────────
    # DOCUMENTS
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="read_document",
        description="Read a document file",
        category="documents",
        handler_name="jarvis.tools.read_document",
        patterns=[
            r"^(?:read|open|show)\s+(?:the\s+)?(?:file|document)\s+",
            r"^what'?s?\s+(?:written|in|inside)\s+(?:the\s+)?(?:file|document)",
        ],
        priority=74,
        confidence=0.85,
        permissions=["file_read"],
        parameters={"file_path": {"required": True, "type": "str"}},
        examples=["read file report.pdf", "open document notes.txt"],
        extract_params=lambda t: {"file_path": t.split(None, 2)[-1] if len(t.split(None, 2)) > 2 else ""},
    ))

    # ──────────────────────────────────────────────────────────
    # NASA
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="nasa_apod",
        description="Get NASA Astronomy Picture of the Day",
        category="science",
        handler_name="jarvis.tools.nasa_apod",
        patterns=[
            r"nasa\s+(?:apod|picture\s+of\s+the\s+day|astronomy\s+picture)",
            r"(?:picture|photo|image)\s+of\s+the\s+day\s+nasa",
            r"^show\s+me\s+(?:a\s+)?(?:picture|photo|image)\s+(?:from\s+)?(?:space|nasa)\s*$",
            r"^nasa\s+(?:photo|picture|image)\s+of\s+the\s+day\s*$",
            r"^(?:apod|astronomy\s+picture)\s+of\s+the\s+day\s*$",
            r"^picture\s+of\s+the\s+day\s*$",
            r"^photo\s+of\s+the\s+day\s*$",
        ],
        priority=60,
        confidence=0.95,
        permissions=["network"],
        parameters={},
        examples=["nasa apod", "nasa picture of the day"],
    ))

    catalog.register(ToolMeta(
        name="nasa_mars",
        description="Get Mars rover photos",
        category="science",
        handler_name="jarvis.tools.nasa_mars_rover",
        patterns=[
            r"nasa\s+mars\s+(?:rover|photo|picture)",
            r"mars\s+rover\s+",
        ],
        priority=59,
        confidence=0.90,
        permissions=["network"],
        parameters={"sol_or_latest": {"required": False, "type": "str", "default": "latest"}},
        examples=["nasa mars rover", "mars rover photos"],
    ))

    catalog.register(ToolMeta(
        name="nasa_iss",
        description="Get current ISS location",
        category="science",
        handler_name="jarvis.tools.nasa_iss",
        patterns=[
            r"(?:iss|international\s+space\s+station)\s+(?:location|where|position|track)",
            r"^where\s+is\s+(?:the\s+)?iss\s*$",
        ],
        priority=58,
        confidence=0.92,
        permissions=["network"],
        parameters={},
        examples=["where is the ISS", "iss location"],
    ))

    # ──────────────────────────────────────────────────────────
    # STOCKS / FINANCE
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="stock_quote",
        description="Get stock quote",
        category="finance",
        handler_name="jarvis.tools.finnhub_quote",
        patterns=[
            r"(?:stock|share|price|quote)\s+(?:price\s+)?(?:of\s+|for\s+)?(\w+)",
            r"(\w+)\s+(?:stock|share)\s+(?:price|quote)",
            r"^how\s+(?:is|'s)\s+(\w+)\s+(?:doing|performing|trading)\s*$",
            r"^what(?:'s| about)\s+(\w+)\s+(?:stock|share|price)\s*$",
            r"^check\s+(\w+)\s+(?:stock|share|price)\s*$",
            r"^(\w+)\s+(?:stock|share)\s*$",
        ],
        priority=65,
        confidence=0.90,
        permissions=["network"],
        parameters={"symbol": {"required": True, "type": "str"}},
        examples=["stock price AAPL", "quote TSLA", "price of MSFT"],
        extract_params=_extract_stock_symbol,
    ))

    # ──────────────────────────────────────────────────────────
    # RANDOM FACT
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="random_fact",
        description="Get a random fact",
        category="entertainment",
        handler_name="jarvis.tools.random_fact",
        patterns=[
            r"(?:tell|give|show|get)\s+(?:me\s+)?(?:a\s+)?(?:random\s+)?(?:fact|trivia)",
            r"^fact\s*(?:please|now)?\s*$",
            r"^did\s+you\s+know\s*$",
        ],
        priority=66,
        confidence=0.90,
        permissions=["network"],
        parameters={},
        examples=["tell me a random fact", "did you know"],
    ))

    # ──────────────────────────────────────────────────────────
    # CHART
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="plot_chart",
        description="Create a chart (bar, line, pie)",
        category="tools",
        handler_name="jarvis.tools.plot_chart",
        patterns=[
            r"(?:plot|draw|create|make|show)\s+(?:a\s+)?(?:bar|line|pie)\s+(?:chart|graph|plot)",
            r"(?:bar|line|pie)\s+(?:chart|graph|plot)",
        ],
        priority=64,
        confidence=0.82,
        permissions=["read_only"],
        parameters={"chart_type": {"required": True, "type": "str"}},
        examples=["create bar chart", "plot pie chart"],
        extract_params=lambda t: {"chart_type": "bar" if "bar" in t else "line" if "line" in t else "pie" if "pie" in t else "bar", "title": t, "labels": [], "values": []},
    ))

    # ──────────────────────────────────────────────────────────
    # LIST APPS
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="list_apps",
        description="List running applications",
        category="system",
        handler_name="jarvis.tools.list_running_apps",
        patterns=[
            r"^(?:list|show|what)\s+(?:running\s+)?(?:apps?|applications?|programs?|processes?)",
            r"^what'?s?\s+running\s*$",
            r"^running\s+(?:apps?|applications?|programs?|processes?)\s*$",
            r"^show\s+me\s+(?:the\s+)?(?:open|running)\s+(?:apps?|applications?|programs?)\s*$",
            r"^how\s+many\s+(?:apps?|applications?|programs?)\s+(?:are\s+)?(?:open|running)\s*$",
            r"^what\s+(?:apps?|applications?|programs?)\s+(?:are\s+)?(?:open|running)\s*$",
            r"^list\s+(?:open|running)\s+(?:apps?|applications?|programs?)\s*$",
        ],
        priority=83,
        confidence=0.92,
        permissions=["read_only"],
        parameters={},
        examples=["list apps", "what's running", "show running applications"],
    ))

    # ──────────────────────────────────────────────────────────
    # IP LOOKUP
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="ip_lookup",
        description="Look up IP address geolocation",
        category="network",
        handler_name="jarvis.tools.ip_lookup",
        patterns=[
            r"(?:what'?s?|what\s+is|find|look\s+up|trace)\s+(?:my\s+)?(?:ip|ip\s+address)",
            r"^ip\s+(?:address\s+)?(?:lookup|info|geolocation)\s*$",
        ],
        priority=63,
        confidence=0.90,
        permissions=["network"],
        parameters={},
        examples=["what's my ip", "ip lookup"],
    ))

    # ──────────────────────────────────────────────────────────
    # NUTRITION
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="nutrition",
        description="Get nutrition info for food",
        category="health",
        handler_name="jarvis.tools.nutrition_info",
        patterns=[
            r"(?:nutrition|calories?|protein|carbs?|fat|food\s+info)\s+(?:for|of|in)\s+",
            r"how\s+many\s+(?:calories|protein|carbs|fat)\s+in\s+",
        ],
        priority=62,
        confidence=0.88,
        permissions=["network"],
        parameters={"query": {"required": True, "type": "str"}},
        examples=["nutrition for apple", "calories in banana"],
        extract_params=_extract_search_query,
    ))

    # ──────────────────────────────────────────────────────────
    # CITY INFO
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="city_info",
        description="Get city information",
        category="reference",
        handler_name="jarvis.tools.city_info",
        patterns=[
            r"(?:city|place|location)\s+(?:info|information|details)\s+(?:for|about|on)\s+",
            r"(?:tell|give)\s+(?:me\s+)?(?:about|info\s+on)\s+(?:the\s+)?(?:city|town|place)\s+",
        ],
        priority=61,
        confidence=0.82,
        permissions=["network"],
        parameters={"query": {"required": True, "type": "str"}},
        examples=["city info for Tokyo", "tell me about London"],
        extract_params=_extract_search_query,
    ))

    # ──────────────────────────────────────────────────────────
    # EMAIL VALIDATE
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="email_validate",
        description="Validate an email address",
        category="tools",
        handler_name="jarvis.tools.email_validate",
        patterns=[
            r"(?:validate|verify|check)\s+(?:the\s+)?(?:email|e.?mail)\s+",
            r"^is\s+(?:this\s+)?(?:the\s+)?(?:email|e.?mail)\s+(?:address\s+)?valid",
        ],
        priority=57,
        confidence=0.88,
        permissions=["network"],
        parameters={"email": {"required": True, "type": "str"}},
        examples=["validate email test@example.com"],
        extract_params=lambda t: {"email": t.split(None, 2)[-1] if len(t.split(None, 2)) > 2 else ""},
    ))

    # ──────────────────────────────────────────────────────────
    # EXERCISE
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="exercise",
        description="Get exercises for a muscle group",
        category="health",
        handler_name="jarvis.tools.exercises",
        patterns=[
            r"(?:exercise|workout|gym)\s+(?:for|routine|info|guide)",
            r"(?:tell|give|show)\s+(?:me\s+)?(?:exercises?|workouts?)\s+(?:for|to|about)\s+",
        ],
        priority=56,
        confidence=0.85,
        permissions=["network"],
        parameters={"query": {"required": True, "type": "str"}},
        examples=["exercise for biceps", "show me workouts for chest"],
        extract_params=_extract_search_query,
    ))

    # ──────────────────────────────────────────────────────────
    # SENTIMENT
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="sentiment",
        description="Analyze sentiment of text",
        category="tools",
        handler_name="jarvis.tools.sentiment_analysis",
        patterns=[
            r"(?:sentiment|sentiment\s+analysis|mood)\s+(?:of|analyze|analysis|check)",
            r"^analyze\s+(?:the\s+)?(?:sentiment|mood|tone|emotion)\s+",
        ],
        priority=55,
        confidence=0.82,
        permissions=["network"],
        parameters={"text": {"required": True, "type": "str"}},
        examples=["sentiment of I love this", "analyze sentiment"],
        extract_params=_extract_search_query,
    ))

    # ──────────────────────────────────────────────────────────
    # HOLIDAYS
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="holidays",
        description="Get holidays for a country",
        category="reference",
        handler_name="jarvis.tools.global_holidays",
        patterns=[
            r"(?:holidays?|festivals?|events)\s+(?:in|for|on)\s+",
            r"^list\s+(?:holidays?|festivals?)\s*$",
            r"(?:national|public)\s+(?:holidays?)\s+",
        ],
        priority=54,
        confidence=0.85,
        permissions=["network"],
        parameters={"country_code": {"required": False, "type": "str", "default": "IN"}},
        examples=["holidays in India", "list holidays"],
        extract_params=lambda t: {"country_code": t.split()[-1].upper() if len(t.split()) > 1 else "IN"},
    ))

    # ──────────────────────────────────────────────────────────
    # SPEED TEST
    # ──────────────────────────────────────────────────────────
    catalog.register(ToolMeta(
        name="speed_test",
        description="Run network speed test",
        category="network",
        handler_name="jarvis.dashboard.run_network_speed_test",
        patterns=[
            r"^speed\s+test\s*$",
            r"(?:run|do)\s+(?:a\s+)?speed\s+test\s*$",
        ],
        priority=88,
        confidence=0.95,
        permissions=["network"],
        parameters={},
        examples=["speed test", "run speed test"],
    ))

    return catalog


# Global catalog instance
catalog = build_catalog()
