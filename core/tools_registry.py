"""
core/tools_registry.py
JARVIS vNext++ Unified Tool Registry

Responsibilities
----------------
1. Canonical tool registration
2. Alias resolution
3. Deterministic fast-path routing
4. Candidate tool retrieval
5. Natural-language argument extraction
6. Tool execution
7. Risk/confirmation policy
8. Retry handling
9. Post-execution verification
10. Structured execution results
11. Browser/web-app vs desktop-app distinction

Design principles
-----------------
- Fast deterministic commands should NOT require an LLM.
- Ambiguous requests can use candidate search + LLM selection upstream.
- Specialized tools are preferred over generic automation.
- Verification is tool-specific.
- Failed verification is not reported as success.
- Tool handlers should return structured dictionaries.
- Registry remains independent from the LLM provider.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import time
import urllib.parse
import webbrowser
import json

from core.memory import unified_memory

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


logger = logging.getLogger(__name__)


try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass(frozen=True)
class ToolSpec:
    """Immutable description of a JARVIS tool."""

    name: str
    aliases: Tuple[str, ...] = ()
    description: str = ""
    arguments: Dict[str, str] = field(default_factory=dict)
    examples: Tuple[str, ...] = ()
    risk_level: str = "low"
    verification_method: str = "none"
    category: str = "system"

    # Routing behaviour
    fast_path: bool = False
    requires_confirmation: bool = False

    # Reliability
    max_retries: int = 0
    timeout_seconds: float = 20.0

    def to_card(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolResult:
    """
    Canonical result returned by every registry execution.

    The registry converts legacy handler dictionaries into this shape.
    """

    success: bool
    tool: str
    output: Any = None
    error: Optional[str] = None
    verified: bool = False
    verification: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tool": self.tool,
            "output": self.output,
            "error": self.error,
            "verified": self.verified,
            "verification": self.verification,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


@dataclass
class RouteMatch:
    """Result of deterministic fast-path classification."""

    tool_name: str
    arguments: Dict[str, Any]
    confidence: float
    reason: str


# ============================================================================
# CONSTANTS
# ============================================================================


VALID_RISK_LEVELS = {
    "none",
    "low",
    "medium",
    "high",
    "critical",
}


# Known web applications.
KNOWN_WEBAPPS: Dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "yt": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "maps": "https://maps.google.com",
    "drive": "https://drive.google.com",
    "calendar": "https://calendar.google.com",
    "docs": "https://docs.google.com",
    "sheets": "https://sheets.google.com",
    "slides": "https://slides.google.com",
    "github": "https://github.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "facebook": "https://facebook.com",
    "instagram": "https://instagram.com",
    "reddit": "https://reddit.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "linkedin": "https://www.linkedin.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "chatgpt": "https://chatgpt.com",
    "openai": "https://openai.com",
    "perplexity": "https://www.perplexity.ai",
    "claude": "https://claude.ai",
    "deepseek": "https://chat.deepseek.com",
}


# Commands which are explicitly safe enough to run without confirmation.
# More dangerous tools should be marked on their ToolSpec instead.
SAFE_RISK_LEVELS = {"none", "low"}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def _normalize_text(value: Any) -> str:
    """Normalize arbitrary input into compact lowercase text."""

    if value is None:
        return ""

    text = str(value).strip().lower()

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text


def _normalize_alias(value: str) -> str:
    """Normalize an alias/tool name for registry lookup."""

    value = _normalize_text(value)

    # Collapse hyphens to underscores (preserve underscores as-is).
    value = value.replace("-", "_")

    return value.strip()


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _looks_like_url(value: str) -> bool:
    value = value.strip().lower()
    return value.startswith(("http://", "https://"))


# Match a full http(s) URL anywhere in free text (no spaces/quotes).
_ANY_URL_RE = re.compile(
    r"https?://[^\s<>\"']+",
    re.IGNORECASE,
)

# A bare registered-style domain (host may include a path).
_BARE_DOMAIN_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$",
    re.IGNORECASE,
)

_LOCALHOST_RE = re.compile(
    r"^localhost(?::\d{1,5})?(?:/[^\s]*)?$",
    re.IGNORECASE,
)

# Common web TLDs. A bare word with a non-web suffix (e.g. "chrome.exe")
# is treated as a local application name, never silently URL-ified.
_WEB_TLDS = {
    "com", "org", "net", "io", "dev", "ai", "co", "me", "app", "tv",
    "edu", "gov", "info", "xyz", "tech", "site", "online", "store",
    "blog", "cloud", "page", "pro", "live", "news", "today", "space",
    "digital", "media", "social", "design", "fun", "gg", "so", "cc",
    "us", "uk", "de", "fr", "es", "it", "ca", "au", "in", "jp", "cn",
    "br", "mx", "nl", "se", "ch", "at", "be", "dk", "fi", "no", "pl",
    "pt", "ru", "za", "kr", "hk", "sg", "nz", "ie", "il", "gr", "tr",
    "th", "id", "my", "ph", "vn", "ar", "cl", "cz", "hu", "ro", "sk",
    "ua", "bg", "hr", "rs", "si", "ee", "lt", "lv", "is", "lu", "mt",
    "cy", "ir", "pk", "bd", "ng",
}


def _extract_url(text: str) -> Optional[str]:
    """Return the first full http(s) URL found in text, or None."""
    match = _ANY_URL_RE.search(str(text or ""))
    if not match:
        return None
    return match.group(0).rstrip(".,;:!?")


def _normalize_url_target(value: str) -> Optional[str]:
    """Normalize a user target into a safe http/https URL, or None.

    Accepts full http(s) URLs, bare web domains (https://<domain>) and
    localhost[:port] (http://...). Everything else — including unsafe
    schemes such as javascript: or file: — is rejected.
    """
    raw = str(value or "").strip()
    if not raw:
        return None

    full = _ANY_URL_RE.match(raw)
    if full and full.group(0) == raw:
        parsed = urllib.parse.urlparse(raw)
        if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
            return raw
        return None

    if _LOCALHOST_RE.match(raw):
        return f"http://{raw}"

    netloc = raw.split("/", 1)[0]
    if _BARE_DOMAIN_RE.match(netloc):
        tld = netloc.rsplit(".", 1)[1].lower()
        if tld in _WEB_TLDS:
            return f"https://{raw}"

    return None


def _clean_query(value: str) -> str:
    """
    Remove conversational filler from the beginning/end of extracted
    search arguments without destroying the actual query.
    """

    value = value.strip()

    prefixes = (
        "for ",
        "about ",
        "on ",
        "the ",
        "a ",
        "an ",
    )

    changed = True

    while changed and value:
        changed = False

        lower = value.lower()

        for prefix in prefixes:
            if lower.startswith(prefix):
                value = value[len(prefix):].strip()
                changed = True
                break

    return value


# ============================================================================
# REGISTRY
# ============================================================================


class UnifiedToolRegistry:
    """
    Production-oriented tool registry.

    The registry intentionally does NOT ask the LLM to select tools for
    obvious commands. It exposes candidate search for ambiguous requests,
    allowing the upstream execution engine to decide when an LLM is needed.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, ToolSpec] = {}
        self._handlers: Dict[str, Callable[..., Any]] = {}

        # Alias -> canonical tool name.
        self._aliases: Dict[str, str] = {}

        # Canonical tool names only.
        self._canonical_tools: Dict[str, ToolSpec] = {}

        self._register_default_tools()

    # ========================================================================
    # REGISTRATION
    # ========================================================================

    def register(
        self,
        spec: ToolSpec,
        handler: Callable[..., Any],
    ) -> None:
        """Register exactly one canonical tool and its aliases."""

        canonical = _normalize_alias(spec.name)

        if not canonical:
            raise ValueError("Tool name cannot be empty.")

        if spec.risk_level not in VALID_RISK_LEVELS:
            raise ValueError(
                f"Invalid risk level for '{spec.name}': "
                f"{spec.risk_level!r}"
            )

        if not callable(handler):
            raise TypeError(f"Handler for '{spec.name}' is not callable.")

        # Do not silently overwrite another canonical tool.
        if canonical in self._canonical_tools:
            raise ValueError(
                f"Tool '{spec.name}' is already registered."
            )

        self._canonical_tools[canonical] = spec
        self._handlers[canonical] = handler
        self._registry[canonical] = spec

        # Canonical name is also an alias.
        self._aliases[canonical] = canonical

        for alias in spec.aliases:
            normalized_alias = _normalize_alias(alias)

            if not normalized_alias:
                continue

            existing = self._aliases.get(normalized_alias)

            if existing and existing != canonical:
                logger.warning(
                    "Alias collision: '%s' already points to '%s'; "
                    "ignoring alias for '%s'.",
                    alias,
                    existing,
                    spec.name,
                )
                continue

            self._aliases[normalized_alias] = canonical

    def unregister(self, tool_name: str) -> bool:
        """Remove a canonical tool and all of its aliases."""

        canonical = self.resolve_name(tool_name)

        if not canonical:
            return False

        spec = self._canonical_tools.pop(canonical, None)

        if spec is None:
            return False

        self._handlers.pop(canonical, None)
        self._registry.pop(canonical, None)

        aliases_to_remove = [
            alias
            for alias, target in self._aliases.items()
            if target == canonical
        ]

        for alias in aliases_to_remove:
            self._aliases.pop(alias, None)

        return True

    # ========================================================================
    # LOOKUP
    # ========================================================================

    def resolve_name(self, tool_name: str) -> str:
        """Resolve canonical name or alias."""

        normalized = _normalize_alias(tool_name)

        if not normalized:
            return ""

        return self._aliases.get(normalized, "")

    def get(self, tool_name: str) -> Optional[ToolSpec]:
        """Get a ToolSpec from a canonical name or alias."""

        canonical = self.resolve_name(tool_name)

        if not canonical:
            return None

        return self._canonical_tools.get(canonical)

    def get_handler(
        self,
        tool_name: str,
    ) -> Optional[Callable[..., Any]]:
        """Get a handler from a canonical name or alias."""

        canonical = self.resolve_name(tool_name)

        if not canonical:
            return None

        return self._handlers.get(canonical)

    def list_tools(
        self,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return canonical tool cards."""

        cards = []

        for spec in self._canonical_tools.values():
            if category and spec.category != category:
                continue

            cards.append(spec.to_card())

        return cards

    # ========================================================================
    # DEFAULT TOOLS
    # ========================================================================

    def _register_default_tools(self) -> None:
        """
        Register the tools currently present in the original registry.

        Existing specialized handlers are preserved.
        """

        self.register(
            ToolSpec(
                name="open_application",
                aliases=(
                    "open app",
                    "open application",
                    "launch app",
                    "launch application",
                    "start app",
                    "start application",
                ),
                description=(
                    "Open a local desktop application or a known web application."
                ),
                arguments={"app_name": "str"},
                examples=(
                    "open chrome",
                    "launch notepad",
                    "open youtube",
                ),
                risk_level="low",
                verification_method="application_or_url",
                category="system",
                fast_path=True,
            ),
            self._handle_open_application,
        )

        self.register(
            ToolSpec(
                name="open_url",
                aliases=(
                    "open url",
                    "open website",
                    "open site",
                    "open webpage",
                    "open page",
                    "open link",
                    "go to url",
                    "visit url",
                    "browse url",
                    "navigate to url",
                ),
                description=(
                    "Open an arbitrary http(s) URL in the default browser. "
                    "Accepts any valid http:// or https:// URL, bare web "
                    "domains (normalized to https://) and "
                    "localhost:[port] (normalized to http://)."
                ),
                arguments={"url": "str"},
                examples=(
                    "open https://example.com",
                    "go to example.com/path",
                ),
                risk_level="low",
                verification_method="url_opened",
                category="web",
                fast_path=True,
            ),
            self._handle_open_url,
        )

        self.register(
            ToolSpec(
                name="memory_store",
                aliases=(
                    "store memory",
                    "save memory",
                    "remember fact",
                    "memorize",
                ),
                description=(
                    "Persist a fact, preference or other memory to durable "
                    "long-term storage (survives restarts)."
                ),
                arguments={
                    "content": "str",
                    "memory_type": "str (optional: fact, preference, "
                    "identity, relationship, goal, project, decision, "
                    "event, instruction, task, observation)",
                    "key": "str (optional short identifier)",
                },
                examples=(
                    "remember that my favorite editor is VS Code",
                ),
                risk_level="low",
                verification_method="data_returned",
                category="system",
            ),
            self._handle_memory_store,
        )

        self.register(
            ToolSpec(
                name="memory_search",
                aliases=(
                    "search memory",
                    "recall memory",
                    "look up memory",
                    "retrieve memory",
                ),
                description=(
                    "Retrieve relevant memories (facts, preferences, "
                    "goals, ...) for a natural-language query."
                ),
                arguments={"query": "str"},
                examples=(
                    "what is my favorite editor?",
                ),
                risk_level="low",
                verification_method="data_returned",
                category="system",
            ),
            self._handle_memory_search,
        )

        self.register(
            ToolSpec(
                name="web_search",
                aliases=(
                    "google search",
                    "search google",
                    "search web",
                    "search on google",
                    "google it",
                ),
                description="Open a Google web search for a query.",
                arguments={"query": "str"},
                examples=(
                    "search python tutorials on google",
                    "google search NASA",
                ),
                risk_level="low",
                verification_method="url_opened",
                category="web",
                fast_path=True,
            ),
            self._handle_web_search,
        )

        self.register(
            ToolSpec(
                name="youtube_video_info",
                aliases=(
                    "youtube info",
                    "youtube video info",
                    "video info",
                    "get youtube info",
                ),
                description=(
                    "Get structured metadata for a YouTube video."
                ),
                arguments={"url": "str"},
                examples=(
                    "get info about https://youtube.com/watch?v=xxx",
                ),
                risk_level="low",
                verification_method="data_returned",
                category="media",
            ),
            self._handle_youtube_video_info,
        )

        self.register(
            ToolSpec(
                name="youtube_download",
                aliases=(
                    "download youtube",
                    "youtube download",
                    "download video",
                    "save youtube",
                ),
                description="Download a YouTube video using yt-dlp.",
                arguments={
                    "url": "str",
                    "output_path": "str (optional)",
                },
                examples=(
                    "download https://youtube.com/watch?v=xxx",
                ),
                risk_level="medium",
                verification_method="file_exists",
                category="media",
            ),
            self._handle_youtube_download,
        )

        self.register(
            ToolSpec(
                name="youtube_search",
                aliases=(
                    "search youtube",
                    "youtube search",
                    "find youtube",
                    "youtube find",
                ),
                description="Search YouTube videos using yt-dlp.",
                arguments={
                    "query": "str",
                    "max_results": "int (optional, default 5)",
                },
                examples=(
                    "search youtube for python tutorial",
                    "find youtube videos about cats",
                ),
                risk_level="low",
                verification_method="data_returned",
                category="media",
                fast_path=True,
            ),
            self._handle_youtube_search,
        )

        self.register(
            ToolSpec(
                name="instagram_user_info",
                aliases=(
                    "instagram info",
                    "instagram user info",
                    "get instagram user",
                    "insta info",
                ),
                description="Get public Instagram profile information.",
                arguments={"username": "str"},
                examples=(
                    "get instagram info for natgeo",
                ),
                risk_level="low",
                verification_method="data_returned",
                category="social",
            ),
            self._handle_instagram_user_info,
        )

        self.register(
            ToolSpec(
                name="instagram_posts",
                aliases=(
                    "instagram posts",
                    "instagram latest posts",
                    "get instagram posts",
                    "insta posts",
                ),
                description="Retrieve public Instagram posts.",
                arguments={
                    "username": "str",
                    "limit": "int (optional, default 10)",
                },
                examples=(
                    "get latest posts from natgeo",
                ),
                risk_level="low",
                verification_method="data_returned",
                category="social",
            ),
            self._handle_instagram_posts,
        )

        self.register(
            ToolSpec(
                name="nasa_apod",
                aliases=(
                    "apod",
                    "nasa apod",
                    "astronomy picture",
                    "astronomy picture of the day",
                    "nasa picture of the day",
                    "space picture of the day",
                ),
                description=(
                    "Get NASA Astronomy Picture of the Day."
                ),
                arguments={
                    "date": "str (optional, YYYY-MM-DD)",
                },
                examples=(
                    "show today's NASA picture",
                    "NASA APOD",
                ),
                risk_level="low",
                verification_method="data_returned",
                category="visual",
            ),
            self._handle_nasa_apod,
        )

        self.register(
            ToolSpec(
                name="nasa_image_search",
                aliases=(
                    "nasa image search",
                    "nasa images",
                    "nasa pictures",
                    "space images",
                    "find nasa pictures",
                ),
                description=(
                    "Search NASA Image and Video Library."
                ),
                arguments={
                    "query": "str",
                    "media_type": "str (optional: image/video/audio)",
                },
                examples=(
                    "show me NASA pictures of black holes",
                    "find images of Mars",
                ),
                risk_level="low",
                verification_method="data_returned",
                category="visual",
            ),
            self._handle_nasa_image_search,
        )

        self.register(
            ToolSpec(
                name="get_system_status",
                aliases=(
                    "system status",
                    "system stats",
                    "system health",
                    "cpu usage",
                    "ram usage",
                    "memory usage",
                    "check cpu",
                    "check ram",
                    "gpu usage",
                    "disk usage",
                ),
                description=(
                    "Get current CPU, RAM, disk and system load status. "
                    "Only call when the user explicitly asks about system "
                    "resources."
                ),
                arguments={},
                examples=(
                    "what is my CPU usage",
                    "how much RAM am I using",
                    "system status",
                ),
                risk_level="low",
                verification_method="data_returned",
                category="system",
                fast_path=True,
            ),
            self._handle_get_system_status,
        )

    # ========================================================================
    # DETERMINISTIC FAST PATH
    # ========================================================================

    def classify_input(
        self,
        query: str,
    ) -> Tuple[str, str, str]:
        """
        Backward-compatible classifier.

        Returns:
            (tool_name, primary_argument_name, primary_argument_value)

        Empty strings mean no deterministic route was found.
        """

        match = self.route_fast_path(query)

        if not match:
            return "", "", ""

        spec = self.get(match.tool_name)

        if not spec:
            return "", "", ""

        primary_argument = next(
            iter(spec.arguments),
            "",
        )

        primary_value = match.arguments.get(
            primary_argument,
            "",
        )

        return (
            match.tool_name,
            primary_argument,
            str(primary_value),
        )

    def route_fast_path(
        self,
        query: str,
    ) -> Optional[RouteMatch]:
        """
        Route only obvious, explicit commands.

        This is intentionally conservative. False-positive tool calls are
        worse than allowing an ambiguous query to reach the LLM.
        """

        raw = str(query or "").strip()
        q = _normalize_text(raw)

        if not q:
            return None

        # --------------------------------------------------------------
        # SEARCH ON PLATFORM
        # --------------------------------------------------------------

        match = re.match(
            r"^(?:please\s+)?search\s+(.+?)\s+on\s+"
            r"(google|youtube|web)\s*$",
            q,
        )

        if match:
            search_query = _clean_query(match.group(1))

            platform = match.group(2)

            if not search_query:
                return None

            if platform == "youtube":
                return RouteMatch(
                    tool_name="youtube_search",
                    arguments={
                        "query": search_query,
                        "max_results": 5,
                    },
                    confidence=0.99,
                    reason="explicit_search_on_youtube",
                )

            return RouteMatch(
                tool_name="web_search",
                arguments={"query": search_query},
                confidence=0.99,
                reason="explicit_search_on_web",
            )

        # --------------------------------------------------------------
        # YOUTUBE SEARCH
        # --------------------------------------------------------------

        patterns = (
            r"^(?:please\s+)?search\s+youtube(?:\s+for)?\s+(.+)$",
            r"^(?:please\s+)?youtube\s+search(?:\s+for)?\s+(.+)$",
            r"^(?:please\s+)?find\s+(.+?)\s+on\s+youtube$",
            r"^(?:please\s+)?find\s+youtube\s+(.+)$",
            r"^(?:please\s+)?youtube\s+find\s+(.+)$",
        )

        for pattern in patterns:
            match = re.match(pattern, q)

            if match:
                value = _clean_query(match.group(1))

                if value:
                    return RouteMatch(
                        tool_name="youtube_search",
                        arguments={
                            "query": value,
                            "max_results": 5,
                        },
                        confidence=0.98,
                        reason="explicit_youtube_search",
                    )

        # --------------------------------------------------------------
        # YOUTUBE DOWNLOAD
        # --------------------------------------------------------------

        dl_patterns = (
            r"^(?:please\s+)?download\s+youtube(?:\s+video)?\s+(.+)$",
            r"^(?:please\s+)?youtube\s+download(?:\s+video)?\s+(.+)$",
            r"^(?:please\s+)?save\s+youtube(?:\s+video)?\s+(.+)$",
        )

        for pattern in dl_patterns:
            match = re.match(pattern, q)

            if match:
                value = _clean_query(match.group(1))

                if value:
                    return RouteMatch(
                        tool_name="youtube_download",
                        arguments={"url": value},
                        confidence=0.98,
                        reason="explicit_youtube_download",
                    )

        # --------------------------------------------------------------
        # GOOGLE / WEB SEARCH
        # --------------------------------------------------------------

        patterns = (
            r"^(?:please\s+)?search\s+google(?:\s+for)?\s+(.+)$",
            r"^(?:please\s+)?google\s+search(?:\s+for)?\s+(.+)$",
            r"^(?:please\s+)?search\s+web(?:\s+for)?\s+(.+)$",
        )

        for pattern in patterns:
            match = re.match(pattern, q)

            if match:
                value = _clean_query(match.group(1))

                if value:
                    return RouteMatch(
                        tool_name="web_search",
                        arguments={"query": value},
                        confidence=0.98,
                        reason="explicit_web_search",
                    )

        # --------------------------------------------------------------
        # NASA APOD — must come BEFORE image search patterns
        # --------------------------------------------------------------

        apod_patterns = (
            r"^nasa\s+apod$",
            r"^apod$",
            r"^astronomy\s+picture(?:\s+of\s+the\s+day)?$",
            r"^nasa\s+picture\s+of\s+the\s+day$",
            r"^show\s+(?:me\s+)?today'?s\s+nasa\s+picture$",
        )

        for pattern in apod_patterns:
            if re.match(pattern, q):
                return RouteMatch(
                    tool_name="nasa_apod",
                    arguments={},
                    confidence=0.99,
                    reason="explicit_apod_request",
                )

        # --------------------------------------------------------------
        # NASA IMAGE SEARCH
        # --------------------------------------------------------------

        nasa_patterns = (
            r"^(?:show|find|get)\s+(?:me\s+)?"
            r"(?:a\s+)?(?:nasa\s+)?(?:image|images|picture|pictures|"
            r"photo|photos)\s+(?:of|from)\s+(.+)$",

            r"^(?:show|find|get)\s+(?:me\s+)?nasa\s+(.+?)\s+"
            r"(?:image|images|picture|pictures|photo|photos)$",

            r"^nasa\s+(?:image|images|picture|pictures|photo|photos)"
            r"\s+(?:of|for)?\s*(.+)$",

            r"^show\s+me\s+(.+?)\s+(?:image|picture|photo)s?$",

            r"^nasa\s+search\s+(.+)$",

            r"^(?:show|find|get)\s+(?:me\s+)?nasa\s+(.+)$",
        )

        for pattern in nasa_patterns:
            match = re.match(pattern, q)

            if match:
                value = _clean_query(match.group(1))

                if value:
                    return RouteMatch(
                        tool_name="nasa_image_search",
                        arguments={
                            "query": value,
                            "media_type": "image",
                        },
                        confidence=0.96,
                        reason="explicit_visual_search",
                    )

        # --------------------------------------------------------------
        # SYSTEM STATUS — only explicit resource requests route here
        # --------------------------------------------------------------

        status_patterns = (
            r"^system\s+(?:status|stats|health)\??\s*$",
            r"^(?:(?:the\s+)?(?:cpu|ram|memory|gpu|disk)\s+usage|"
            r"check\s+(?:the\s+)?(?:cpu|ram|memory|gpu))\??\s*$",
            r"^what(?:'?s| is)\s+my\s+(?:cpu|ram|memory|gpu)\s+usage\??\s*$",
            r"^how\s+much\s+(?:ram|memory|cpu)\s+(?:am|is)\s+i\s+using\??\s*$",
            r"^check\s+(?:system\s+)?(?:status|stats)\??\s*$",
        )

        for pattern in status_patterns:
            if re.match(pattern, q):
                return RouteMatch(
                    tool_name="get_system_status",
                    arguments={},
                    confidence=0.98,
                    reason="explicit_system_status",
                )

        # --------------------------------------------------------------
        # OPEN / NAVIGATE — arbitrary URL, known website, local app
        # --------------------------------------------------------------

        open_match = re.match(
            r"^(?:please\s+)?"
            r"(?:open|launch|start|go\s+to|visit|browse|"
            r"navigate\s+to|take\s+me\s+to)\s+(.+?)\s*$",
            q,
        )

        if open_match:
            target = open_match.group(1).strip()

            # Remove conversational trailing words.
            target = re.sub(
                r"\s+(?:please|for\s+me)$",
                "",
                target,
            ).strip()

            # Multi-command input ("open youtube and search gamerfleet") must
            # NOT be consumed by the single-action fast path — fall through to
            # the agent loop so the LLM can plan chained tool calls.
            if re.search(
                r"\b(?:and|then|also)\b\s+\b(?:open|launch|start|search|"
                r"find|play|show|download|run|visit|browse|navigate)\b",
                target,
            ):
                return None

            # Arbitrary full URL embedded in the target
            # ("open this website: https://example.com").
            url_found = _extract_url(target)
            if url_found:
                return RouteMatch(
                    tool_name="open_url",
                    arguments={"url": url_found},
                    confidence=0.99,
                    reason="explicit_url",
                )

            # Bare domain / localhost target — normalized to a real URL,
            # never treated as an executable name.
            normalized_url = _normalize_url_target(target)
            if normalized_url:
                return RouteMatch(
                    tool_name="open_url",
                    arguments={"url": normalized_url},
                    confidence=0.97,
                    reason="normalized_bare_domain",
                )

            if target in KNOWN_WEBAPPS:
                return RouteMatch(
                    tool_name="open_application",
                    arguments={"app_name": target},
                    confidence=0.99,
                    reason="known_web_application",
                )

            # Explicit local app command.
            if target and len(target.split()) <= 4:
                return RouteMatch(
                    tool_name="open_application",
                    arguments={"app_name": target},
                    confidence=0.92,
                    reason="explicit_application_command",
                )

        return None

    # ========================================================================
    # CANDIDATE SEARCH
    # ========================================================================

    def search_candidates(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve candidate tool cards.

        This is intentionally dependency-free.

        It is a lexical candidate retriever, NOT a fake "vector search".
        If a real embedding/vector layer is added later, it can call this
        registry's canonical cards as its source of truth.
        """

        top_k = max(1, min(int(top_k), 10))

        q = _normalize_text(query)

        if not q:
            return []

        query_tokens = set(
            re.findall(r"[a-z0-9_]+", q)
        )

        scored: List[
            Tuple[float, Dict[str, Any]]
        ] = []

        for spec in self._canonical_tools.values():
            score = 0.0

            name_tokens = set(
                _normalize_alias(spec.name).split()
            )

            alias_tokens = set()

            for alias in spec.aliases:
                alias_tokens.update(
                    _normalize_alias(alias).split()
                )

            description_tokens = set(
                re.findall(
                    r"[a-z0-9_]+",
                    _normalize_text(spec.description),
                )
            )

            # Exact canonical name.
            if _normalize_alias(spec.name) in q:
                score += 20

            # Exact alias.
            for alias in spec.aliases:
                alias_normalized = _normalize_alias(alias)

                if alias_normalized and alias_normalized in q:
                    score += 25

            # Token overlap.
            score += 3.0 * len(
                query_tokens & name_tokens
            )

            score += 2.0 * len(
                query_tokens & alias_tokens
            )

            score += 0.5 * len(
                query_tokens & description_tokens
            )

            # Category hints.
            category = spec.category

            if category == "media" and any(
                word in q
                for word in (
                    "youtube",
                    "video",
                    "song",
                    "music",
                )
            ):
                score += 4

            if category == "visual" and any(
                word in q
                for word in (
                    "image",
                    "picture",
                    "photo",
                    "visual",
                    "nasa",
                    "mars",
                    "space",
                )
            ):
                score += 4

            scored.append(
                (
                    score,
                    spec.to_card(),
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        results = []

        for score, card in scored[:top_k]:
            card = dict(card)
            card["candidate_score"] = round(score, 3)
            results.append(card)

        return results

    # ========================================================================
    # NATIVE TOOL SCHEMAS FOR LLM
    # ========================================================================

    def get_tool_schemas_for_llm(
        self,
        candidate_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate OpenAI-compatible tool schemas for native LLM tool calling.

        If candidate_names is provided, only those tools are included.
        Otherwise, all registered tools are returned.
        """
        tools = []
        specs = (
            [self._canonical_tools[n] for n in candidate_names if n in self._canonical_tools]
            if candidate_names
            else list(self._canonical_tools.values())
        )
        for spec in specs:
            properties = {}
            required = []
            for arg_name, type_desc in spec.arguments.items():
                prop: Dict[str, Any] = {}
                tl = type_desc.lower()
                if "int" in tl:
                    prop["type"] = "integer"
                elif "float" in tl or "number" in tl:
                    prop["type"] = "number"
                elif "bool" in tl:
                    prop["type"] = "boolean"
                else:
                    prop["type"] = "string"
                # Extract description from type string
                desc_parts = type_desc.split("(", 1)
                if len(desc_parts) > 1:
                    prop["description"] = desc_parts[1].rstrip(")")
                if "optional" in tl:
                    pass  # not required
                else:
                    required.append(arg_name)
                properties[arg_name] = prop

            tool_schema = {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }
            tools.append(tool_schema)
        return tools

    # ========================================================================
    # TOOL CALL VALIDATION (ToolValidator)
    # ========================================================================

    def validate_tool_call(
        self,
        tool_name: str,
        arguments: Any,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Validate a proposed tool call against the registered schema.

        Returns (ok, reason, normalized_kwargs).
        """
        canonical = self.resolve_name(tool_name)

        if not canonical:
            return False, "unknown_tool", None

        spec = self._canonical_tools.get(canonical)

        if spec is None:
            return False, "unknown_tool", None

        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(parsed, dict):
                arguments = parsed
            else:
                arguments = {}

        if not isinstance(arguments, dict):
            return False, "arguments_not_object", None

        normalized = dict(arguments)

        missing = [
            name
            for name, type_desc in spec.arguments.items()
            if "optional" not in type_desc.lower() and name not in normalized
        ]

        if missing:
            return False, f"missing_arguments:{','.join(missing)}", None

        known = set(spec.arguments)

        for extra in [k for k in normalized if k not in known]:
            normalized.pop(extra)

        return True, "valid", normalized

    # ========================================================================
    # EXECUTION
    # ========================================================================

    def execute(
        self,
        tool_name: str,
        *,
        confirmation_granted: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Execute a tool safely and return a canonical dictionary.

        Existing callers can continue doing:

            registry.execute("youtube_search", query="NASA")

        """

        canonical = self.resolve_name(tool_name)

        if not canonical:
            return ToolResult(
                success=False,
                tool=str(tool_name),
                error=f"Tool '{tool_name}' not found.",
            ).to_dict()

        spec = self._canonical_tools[canonical]
        handler = self._handlers[canonical]

        # --------------------------------------------------------------
        # Confirmation policy
        # --------------------------------------------------------------

        if (
            spec.requires_confirmation
            and not confirmation_granted
        ):
            return ToolResult(
                success=False,
                tool=canonical,
                error=(
                    f"Confirmation required before executing "
                    f"'{canonical}'."
                ),
                verification="confirmation_required",
            ).to_dict()

        # High/critical operations should never silently execute.
        if (
            spec.risk_level in {"high", "critical"}
            and not confirmation_granted
        ):
            return ToolResult(
                success=False,
                tool=canonical,
                error=(
                    f"Confirmation required for {spec.risk_level}-risk "
                    f"tool '{canonical}'."
                ),
                verification="confirmation_required",
            ).to_dict()

        # --------------------------------------------------------------
        # Argument normalization
        # --------------------------------------------------------------

        normalized_kwargs = self._normalize_arguments(
            spec,
            kwargs,
        )

        # --------------------------------------------------------------
        # Execution + retry
        # --------------------------------------------------------------

        attempts = 0
        last_error: Optional[str] = None

        while attempts <= spec.max_retries:
            try:
                raw_result = handler(
                    **normalized_kwargs
                )

                result = self._normalize_handler_result(
                    canonical,
                    raw_result,
                )

                if not result.success:
                    last_error = result.error

                    if attempts < spec.max_retries:
                        attempts += 1
                        self._backoff(attempts)
                        continue

                    result.retry_count = attempts
                    return result.to_dict()

                # --------------------------------------------------
                # Verification
                # --------------------------------------------------

                verified, verification_message = (
                    self.verify_tool_execution(
                        canonical,
                        normalized_kwargs,
                        result.to_dict(),
                    )
                )

                result.verified = verified
                result.verification = verification_message
                result.retry_count = attempts

                if not verified:
                    result.success = False

                    if not result.error:
                        result.error = (
                            "Tool completed, but post-execution "
                            "verification failed."
                        )

                return result.to_dict()

            except Exception as exc:
                last_error = str(exc)

                logger.exception(
                    "Tool execution failed: %s",
                    canonical,
                )

                if attempts < spec.max_retries:
                    attempts += 1
                    self._backoff(attempts)
                    continue

                return ToolResult(
                    success=False,
                    tool=canonical,
                    error=last_error,
                    verified=False,
                    verification="handler_exception",
                    retry_count=attempts,
                ).to_dict()

        return ToolResult(
            success=False,
            tool=canonical,
            error=last_error or "Unknown execution failure.",
            retry_count=attempts,
        ).to_dict()

    # ========================================================================
    # ARGUMENT NORMALIZATION
    # ========================================================================

    def _normalize_arguments(
        self,
        spec: ToolSpec,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize known argument types without guessing missing values."""

        result = dict(kwargs)

        for argument_name, type_description in spec.arguments.items():
            if argument_name not in result:
                continue

            value = result[argument_name]

            type_lower = type_description.lower()

            if "int" in type_lower:
                result[argument_name] = _safe_int(
                    value,
                    5,
                )

            elif "str" in type_lower and value is not None:
                result[argument_name] = str(value).strip()

        return result

    # ========================================================================
    # RESULT NORMALIZATION
    # ========================================================================

    def _normalize_handler_result(
        self,
        tool_name: str,
        raw_result: Any,
    ) -> ToolResult:
        """
        Convert legacy handler output into ToolResult.

        This protects the execution engine from handlers returning:
        - dict
        - None
        - strings
        - malformed objects
        """

        if isinstance(raw_result, ToolResult):
            raw_result.tool = tool_name
            return raw_result

        if isinstance(raw_result, dict):
            success = bool(
                raw_result.get(
                    "success",
                    False,
                )
            )

            error = raw_result.get("error")

            output = raw_result.get(
                "output",
                raw_result.get("result"),
            )

            metadata = dict(
                raw_result.get(
                    "metadata",
                    {},
                )
                or {}
            )

            # Preserve extra handler fields.
            reserved = {
                "success",
                "error",
                "output",
                "result",
                "verified",
                "verification",
                "retry_count",
                "metadata",
            }

            for key, value in raw_result.items():
                if key not in reserved:
                    metadata[key] = value

            return ToolResult(
                success=success,
                tool=tool_name,
                output=output,
                error=str(error) if error else None,
                verified=bool(
                    raw_result.get(
                        "verified",
                        False,
                    )
                ),
                verification=raw_result.get(
                    "verification"
                ),
                retry_count=_safe_int(
                    raw_result.get(
                        "retry_count",
                        0,
                    ),
                    0,
                ),
                metadata=metadata,
            )

        if raw_result is None:
            return ToolResult(
                success=False,
                tool=tool_name,
                error="Tool returned no result.",
            )

        if isinstance(raw_result, str):
            return ToolResult(
                success=True,
                tool=tool_name,
                output=raw_result,
            )

        return ToolResult(
            success=True,
            tool=tool_name,
            output=raw_result,
        )

    # ========================================================================
    # RETRIES
    # ========================================================================

    @staticmethod
    def _backoff(attempt: int) -> None:
        """
        Small bounded exponential backoff.

        Keeps transient retries from hammering external services.
        """

        delay = min(
            0.25 * (2 ** max(0, attempt - 1)),
            2.0,
        )

        time.sleep(delay)

    # ========================================================================
    # VERIFICATION
    # ========================================================================

    def verify_tool_execution(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Perform tool-specific post-execution verification.

        Returns:
            (verified, explanation)
        """

        canonical = self.resolve_name(tool_name)

        if not canonical:
            return False, "unknown_tool"

        spec = self._canonical_tools[canonical]
        method = spec.verification_method

        # No verification required.
        if method in {"none", ""}:
            return True, "no_verification_required"

        # --------------------------------------------------------------
        # DATA RETURNED
        # --------------------------------------------------------------

        if method == "data_returned":
            output = result.get("output")

            if output is None:
                return False, "no_output_returned"

            if isinstance(output, (list, tuple, dict, str)):
                if len(output) == 0:
                    return False, "empty_output_returned"

            return True, "data_returned"

        # --------------------------------------------------------------
        # FILE EXISTS
        # --------------------------------------------------------------

        if method == "file_exists":
            file_path = (
                result.get("metadata", {}).get("file_path")
                or result.get("file_path")
                or args.get("output_path")
            )

            if not file_path:
                return False, "file_path_missing"

            try:
                exists = os.path.isfile(
                    os.path.expanduser(
                        str(file_path)
                    )
                )
            except OSError:
                exists = False

            return (
                exists,
                "file_exists"
                if exists
                else "file_not_found",
            )

        # --------------------------------------------------------------
        # APPLICATION OR URL
        # --------------------------------------------------------------

        if method == "application_or_url":
            app_name = _normalize_text(
                args.get("app_name", "")
            )

            if not app_name:
                return False, "application_name_missing"

            # URL target deflected to the browser executor — verify the
            # dispatched URL, never a process.
            if _normalize_url_target(app_name) is not None:
                url = (
                    result.get("metadata", {}).get("url")
                    or result.get("url")
                )
                if url and _looks_like_url(str(url)):
                    return True, "url_dispatched"
                return False, "invalid_url"

            # Known web application.
            if app_name in KNOWN_WEBAPPS:
                return self._verify_browser_target(
                    app_name,
                    result,
                )

            # Local application.
            return self._verify_process(
                app_name,
            )

        # --------------------------------------------------------------
        # URL OPENED
        # --------------------------------------------------------------

        if method == "url_opened":
            url = (
                result.get("metadata", {}).get("url")
                or result.get("url")
            )

            if not url:
                return False, "url_missing"

            return (
                _looks_like_url(str(url)),
                "url_dispatched"
                if _looks_like_url(str(url))
                else "invalid_url",
            )

        # --------------------------------------------------------------
        # PROCESS FOUND
        # --------------------------------------------------------------

        if method == "process_found":
            app_name = _normalize_text(
                args.get("app_name", "")
            )

            return self._verify_process(
                app_name,
            )

        # --------------------------------------------------------------
        # CUSTOM
        # --------------------------------------------------------------

        if method == "custom":
            return True, "custom_verification_delegated"

        logger.warning(
            "Unknown verification method '%s' for '%s'.",
            method,
            canonical,
        )

        return False, f"unknown_verification_method:{method}"

    # ========================================================================
    # VERIFICATION HELPERS
    # ========================================================================

    def _verify_browser_target(
        self,
        app_name: str,
        result: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Verify a known website target.

        We intentionally do NOT claim that the webpage loaded merely because
        webbrowser.open() was called. The standard library gives us a dispatch
        request, not a reliable browser DOM/load confirmation.

        Therefore this verification distinguishes:
            dispatched -> true
            actual browser page validation -> delegated to browser automation
        """

        url = KNOWN_WEBAPPS.get(app_name)

        if not url:
            return False, "unknown_web_target"

        metadata = result.get(
            "metadata",
            {},
        )

        if metadata.get("browser_verified") is True:
            return True, "browser_confirmed"

        if metadata.get("url_dispatched") is True:
            return True, "browser_dispatch_confirmed"

        return False, "browser_dispatch_not_confirmed"

    @staticmethod
    def _verify_process(
        app_name: str,
    ) -> Tuple[bool, str]:
        """Verify a local process when psutil is available.

        Retries briefly because a spawned process may take a moment to
        become visible in the process table.
        """

        if not app_name:
            return False, "application_name_missing"

        if not PSUTIL_AVAILABLE:
            return True, "process_verification_unavailable"

        try:
            normalized = re.sub(
                r"\.exe$",
                "",
                app_name,
                flags=re.IGNORECASE,
            )

            for attempt in range(2):
                for process in psutil.process_iter(
                    ["name"],
                ):
                    try:
                        name = process.info.get(
                            "name"
                        )

                        if not name:
                            continue

                        process_name = re.sub(
                            r"\.exe$",
                            "",
                            name,
                            flags=re.IGNORECASE,
                        )

                        if (
                            normalized == process_name.lower()
                            or normalized in process_name.lower()
                        ):
                            return True, "process_found"

                    except (
                        psutil.NoSuchProcess,
                        psutil.AccessDenied,
                    ):
                        continue

                if attempt == 0:
                    time.sleep(0.35)

        except Exception:
            logger.exception(
                "Process verification failed."
            )

        return False, "process_not_found"

    # ========================================================================
    # TOOL HANDLERS
    # ========================================================================

    def _handle_open_application(
        self,
        app_name: str = "",
    ) -> Dict[str, Any]:
        """
        Open either a known website or a local application.

        No shell interpolation is used for local process launching.
        """

        app_clean = _normalize_text(app_name)

        if not app_clean:
            return {
                "success": False,
                "error": "Application name is required.",
            }

        # --------------------------------------------------------------
        # Arbitrary URL — NEVER send URLs to subprocess/executable
        # execution. Route through the generic browser executor instead.
        # --------------------------------------------------------------

        normalized_url = _normalize_url_target(str(app_name or "").strip())
        if normalized_url:
            return self._handle_open_url(normalized_url)

        # --------------------------------------------------------------
        # Known web application
        # --------------------------------------------------------------

        if app_clean in KNOWN_WEBAPPS:
            url = KNOWN_WEBAPPS[app_clean]

            try:
                opened = webbrowser.open_new_tab(url)
            except Exception as exc:
                return {
                    "success": False,
                    "error": (
                        f"Failed to open {app_clean}: {exc}"
                    ),
                }

            return {
                "success": bool(opened) or True,
                "output": f"Opened {app_name}.",
                "metadata": {
                    "url": url,
                    "url_dispatched": True,
                    "browser_verified": False,
                    "target_type": "web",
                },
            }

        # --------------------------------------------------------------
        # Local application
        # --------------------------------------------------------------

        try:
            if sys.platform == "win32":
                process = subprocess.Popen(
                    [app_clean],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=getattr(
                        subprocess,
                        "CREATE_NO_WINDOW",
                        0,
                    ),
                )

            else:
                process = subprocess.Popen(
                    [app_clean],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )

            return {
                "success": True,
                "output": f"Launched {app_name}.",
                "metadata": {
                    "pid": process.pid,
                    "target_type": "desktop",
                },
            }

        except FileNotFoundError:
            return {
                "success": False,
                "error": (
                    f"Application '{app_name}' was not found."
                ),
            }

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    f"Failed to launch '{app_name}': {exc}"
                ),
            }

    def _handle_open_url(
        self,
        url: str = "",
    ) -> Dict[str, Any]:
        """Open an arbitrary http(s) URL in the default browser.

        Security: only http/https schemes are accepted; URLs are never
        passed through a shell, subprocess, or executable lookup. Paths
        and query strings are preserved. Returns structured success info.
        """
        raw = str(url or "").strip()
        normalized = _normalize_url_target(raw)

        if not normalized:
            return {
                "success": False,
                "action": "open_url",
                "url": raw,
                "error": (
                    "Invalid URL: only http:// and https:// "
                    "targets are supported."
                ),
            }

        parsed = urllib.parse.urlparse(normalized)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            return {
                "success": False,
                "action": "open_url",
                "url": raw,
                "error": "Unsupported URL scheme.",
            }

        logger.info("[TOOL] open_url normalized=%s", normalized)

        try:
            opened = webbrowser.open_new_tab(normalized)
        except Exception as exc:
            return {
                "success": False,
                "action": "open_url",
                "url": raw,
                "error": f"Failed to open URL: {exc}",
            }

        return {
            "success": bool(opened) or True,
            "action": "open_url",
            "url": normalized,
            "output": f"Opened {normalized}.",
            "metadata": {
                "url": normalized,
                "normalized_url": normalized,
                "url_dispatched": True,
                "browser_verified": False,
                "target_type": "web",
            },
        }

    def _handle_memory_store(
        self,
        content: str = "",
        memory_type: str = "fact",
        key: str = None,
    ) -> Dict[str, Any]:
        """Persist one memory entry through the canonical store() path."""
        result = unified_memory.store(
            content=content,
            memory_type=memory_type,
            key=key or None,
            explicit=True,
            source="tool",
        )
        if result.get("success"):
            return {
                "success": True,
                "output": (
                    f"Memory stored (id={result.get('memory_id')}, "
                    f"type={result.get('type')}, "
                    f"action={result.get('action')})."
                ),
                "metadata": {
                    "memory_id": result.get("memory_id"),
                    "memory_type": result.get("type"),
                    "action": result.get("action"),
                },
            }
        return {
            "success": False,
            "error": (
                result.get("error")
                or "Memory could not be persisted."
            ),
            "metadata": {
                "memory_id": result.get("memory_id"),
                "action": result.get("action"),
            },
        }

    def _handle_memory_search(
        self,
        query: str = "",
    ) -> Dict[str, Any]:
        """Retrieve relevant memories through the hybrid pipeline."""
        query = str(query or "").strip()
        if not query:
            return {
                "success": False,
                "error": "A search query is required.",
            }
        entries = unified_memory.retrieve(query, top_k=5)
        if not entries:
            return {
                "success": False,
                "error": "No matching memory found.",
                "metadata": {"matches": 0},
            }
        return {
            "success": True,
            "output": unified_memory.format_memories(entries),
            "metadata": {"matches": len(entries)},
        }

    def _handle_web_search(
        self,
        query: str = "",
    ) -> Dict[str, Any]:
        """Open a properly encoded Google search URL."""

        query = str(query or "").strip()

        if not query:
            return {
                "success": False,
                "error": "Search query is required.",
            }

        encoded = urllib.parse.quote_plus(query)

        url = (
            "https://www.google.com/search"
            f"?q={encoded}"
        )

        try:
            opened = webbrowser.open_new_tab(url)
        except Exception as exc:
            return {
                "success": False,
                "error": f"Failed to open search: {exc}",
            }

        return {
            "success": bool(opened) or True,
            "output": f"Searched the web for '{query}'.",
            "metadata": {
                "url": url,
                "url_dispatched": True,
                "query": query,
            },
        }

    # ========================================================================
    # YOUTUBE
    # ========================================================================

    def _handle_youtube_video_info(
        self,
        url: str = "",
    ) -> Dict[str, Any]:
        """Get YouTube video metadata using yt-dlp."""

        url = str(url or "").strip()

        if not url:
            return {
                "success": False,
                "error": "YouTube URL is required.",
            }

        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:
                info = ydl.extract_info(
                    url,
                    download=False,
                )

            description = info.get(
                "description",
                "",
            ) or ""

            return {
                "success": True,
                "output": {
                    "title": info.get("title"),
                    "views": info.get("view_count"),
                    "length": info.get("duration"),
                    "author": info.get("uploader"),
                    "description": (
                        description[:500] + "..."
                        if len(description) > 500
                        else description
                    ),
                    "thumbnail_url": info.get(
                        "thumbnail"
                    ),
                    "url": url,
                },
            }

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    "Failed to get YouTube video info: "
                    f"{exc}"
                ),
            }

    def _handle_youtube_download(
        self,
        url: str = "",
        output_path: str = "",
    ) -> Dict[str, Any]:
        """Download a YouTube video using yt-dlp."""

        url = str(url or "").strip()

        if not url:
            return {
                "success": False,
                "error": "YouTube URL is required.",
            }

        try:
            import yt_dlp

            ydl_opts = {
                "format": "best",
                "outtmpl": (
                    output_path
                    if output_path
                    else "%(title)s.%(ext)s"
                ),
                "quiet": True,
            }

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:
                info = ydl.extract_info(
                    url,
                    download=True,
                )

                filename = ydl.prepare_filename(
                    info
                )

            return {
                "success": True,
                "output": f"Downloaded: {filename}",
                "metadata": {
                    "file_path": filename,
                },
            }

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    "Failed to download YouTube video: "
                    f"{exc}"
                ),
            }

    def _handle_youtube_search(
        self,
        query: str = "",
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """Search YouTube using yt-dlp."""

        query = str(query or "").strip()

        if not query:
            return {
                "success": False,
                "error": "YouTube search query is required.",
            }

        max_results = _clamp(
            _safe_int(
                max_results,
                5,
            ),
            1,
            20,
        )

        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_search",
            }

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:
                search_results = ydl.extract_info(
                    f"ytsearch{int(max_results)}:{query}",
                    download=False,
                )

            results = []

            for video in (
                search_results.get("entries", [])
                or []
            ):
                if not video:
                    continue

                video_id = video.get("id")

                if not video_id:
                    continue

                results.append(
                    {
                        "title": video.get("title"),
                        "url": (
                            "https://www.youtube.com/watch?v="
                            f"{video_id}"
                        ),
                        "views": video.get(
                            "view_count"
                        ),
                        "duration": video.get(
                            "duration"
                        ),
                        "author": video.get(
                            "uploader"
                        ),
                        "thumbnail": video.get(
                            "thumbnail"
                        ),
                    }
                )

            return {
                "success": True,
                "output": (
                    f"Found {len(results)} videos "
                    f"for '{query}'."
                ),
                "results": results,
            }

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    "Failed to search YouTube: "
                    f"{exc}"
                ),
            }

    # ========================================================================
    # INSTAGRAM
    # ========================================================================

    def _handle_instagram_user_info(
        self,
        username: str = "",
    ) -> Dict[str, Any]:
        """Get public Instagram profile information."""

        username = str(username or "").strip().lstrip("@")

        if not username:
            return {
                "success": False,
                "error": "Instagram username is required.",
            }

        try:
            import instaloader

            loader = instaloader.Instaloader()

            profile = (
                instaloader.Profile.from_username(
                    loader.context,
                    username,
                )
            )

            return {
                "success": True,
                "output": {
                    "username": profile.username,
                    "userid": profile.userid,
                    "full_name": profile.full_name,
                    "bio": profile.bio,
                    "followers": profile.followers,
                    "followees": profile.followees,
                    "posts": profile.mediacount,
                    "is_private": profile.is_private,
                    "is_verified": profile.is_verified,
                    "profile_pic_url": profile.profile_pic_url,
                    "external_url": profile.external_url,
                },
            }

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    "Failed to get Instagram user info: "
                    f"{exc}"
                ),
            }

    def _handle_instagram_posts(
        self,
        username: str = "",
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get recent public Instagram posts."""

        username = str(username or "").strip().lstrip("@")

        if not username:
            return {
                "success": False,
                "error": "Instagram username is required.",
            }

        limit = _clamp(
            _safe_int(limit, 10),
            1,
            50,
        )

        try:
            import instaloader

            loader = instaloader.Instaloader()

            profile = (
                instaloader.Profile.from_username(
                    loader.context,
                    username,
                )
            )

            posts = []

            for index, post in enumerate(
                profile.get_posts()
            ):
                if index >= limit:
                    break

                caption = post.caption or ""

                posts.append(
                    {
                        "shortcode": post.shortcode,
                        "url": post.url,
                        "caption": (
                            caption[:200] + "..."
                            if len(caption) > 200
                            else caption
                        ),
                        "likes": post.likes,
                        "comments": post.comments,
                        "is_video": post.is_video,
                        "date": post.date_local,
                    }
                )

            return {
                "success": True,
                "output": (
                    f"Retrieved {len(posts)} posts "
                    f"from @{username}."
                ),
                "posts": posts,
            }

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    "Failed to retrieve Instagram posts: "
                    f"{exc}"
                ),
            }

    # ========================================================================
    # NASA
    # ========================================================================

    def _handle_get_system_status(
        self,
    ) -> Dict[str, Any]:
        """Report CPU / RAM / disk / process status (lightweight psutil).

        Intentionally cheap: no interval sampling and no network speedtests.
        Only invoked when the user explicitly asks about system resources.
        """

        if not PSUTIL_AVAILABLE:
            return {
                "success": False,
                "error": (
                    "System statistics unavailable (psutil not installed)."
                ),
            }

        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            stats = {
                "cpu_percent": round(cpu, 1),
                "ram_percent": round(mem.percent, 1),
                "ram_used_gb": round(mem.used / (1024 ** 3), 1),
                "ram_total_gb": round(mem.total / (1024 ** 3), 1),
                "disk_percent": round(disk.percent, 1),
                "process_count": len(psutil.pids()),
            }

            summary = (
                f"CPU: {stats['cpu_percent']}% | "
                f"RAM: {stats['ram_percent']}% "
                f"({stats['ram_used_gb']}GB/{stats['ram_total_gb']}GB) | "
                f"Disk: {stats['disk_percent']}%"
            )

            return {
                "success": True,
                "output": summary,
                "metadata": stats,
            }

        except Exception as exc:
            return {
                "success": False,
                "error": f"Failed to collect system stats: {exc}",
            }

    def _handle_nasa_apod(
        self,
        date: str = "",
    ) -> Dict[str, Any]:
        """Get NASA Astronomy Picture of the Day."""

        try:
            from core.tools_nasa import nasa_apod

            return nasa_apod(
                date=date or None,
            )

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    f"NASA APOD failed: {exc}"
                ),
            }

    def _handle_nasa_image_search(
        self,
        query: str = "",
        media_type: str = "image",
    ) -> Dict[str, Any]:
        """Search NASA Image and Video Library."""

        query = str(query or "").strip()

        if not query:
            return {
                "success": False,
                "error": "NASA search query is required.",
            }

        media_type = str(
            media_type or "image"
        ).lower().strip()

        if media_type not in {
            "image",
            "video",
            "audio",
        }:
            media_type = "image"

        try:
            from core.tools_nasa import nasa_image_search

            return nasa_image_search(
                query=query,
                media_type=media_type,
            )

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    f"NASA image search failed: {exc}"
                ),
            }


# ============================================================================
# SINGLETON
# ============================================================================

tool_registry = UnifiedToolRegistry()


__all__ = [
    "ToolSpec",
    "ToolResult",
    "RouteMatch",
    "UnifiedToolRegistry",
    "tool_registry",
    "KNOWN_WEBAPPS",
]