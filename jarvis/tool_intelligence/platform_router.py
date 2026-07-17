"""Platform-Aware Search Router for JARVIS.

NEVER search randomly.

Every query type has an optimal set of platforms/sources.
The router determines the best source(s) based on query content,
domain, and context.

Examples:
    "Search Python"       → Google + Official Docs + GitHub + Stack Overflow
    "Search AI Papers"    → Arxiv + Google Scholar
    "Search package"      → PyPI (Python) / npm (Node)
    "Search React package"→ npm
    "Search memes"        → Reddit
    "Search song"         → Spotify → YouTube Music → YouTube
    "Search world war II" → Wikipedia
    "Search AI news"      → Web Search + News APIs
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# PLATFORM DEFINITIONS
# ════════════════════════════════════════════════════════════════════

@dataclass
class Platform:
    """A searchable platform/source."""
    name: str
    base_url: str
    search_url: str
    category: str  # "search_engine", "code", "academic", "media", "social", "docs", "news"
    requires_network: bool = True
    latency_ms: float = 500.0
    reliability: float = 0.95
    supports_languages: list[str] = field(default_factory=lambda: ["en"])
    priority: int = 50  # Higher = preferred


# ── Platform Registry ──
PLATFORMS: dict[str, Platform] = {
    # Search Engines
    "google": Platform("Google", "https://google.com", "https://google.com/search?q={}", "search_engine", priority=80),
    "bing": Platform("Bing", "https://bing.com", "https://bing.com/search?q={}", "search_engine", priority=60),
    "duckduckgo": Platform("DuckDuckGo", "https://duckduckgo.com", "https://duckduckgo.com/?q={}", "search_engine", priority=70),

    # Code & Development
    "github": Platform("GitHub", "https://github.com", "https://github.com/search?q={}", "code", priority=85),
    "stackoverflow": Platform("Stack Overflow", "https://stackoverflow.com", "https://stackoverflow.com/search?q={}", "code", priority=80),
    "pypi": Platform("PyPI", "https://pypi.org", "https://pypi.org/search/?q={}", "code", priority=90),
    "npm": Platform("npm", "https://npmjs.com", "https://www.npmjs.com/search?q={}", "code", priority=90),
    "crates": Platform("crates.io", "https://crates.io", "https://crates.io/search?q={}", "code", priority=85),
    "maven": Platform("Maven", "https://mvnrepository.com", "https://mvnrepository.com/search?q={}", "code", priority=85),

    # Documentation
    "python_docs": Platform("Python Docs", "https://docs.python.org", "https://docs.python.org/3/search.html?q={}", "docs", priority=85),
    "mdn": Platform("MDN", "https://developer.mozilla.org", "https://developer.mozilla.org/search?q={}", "docs", priority=85),
    "react_docs": Platform("React Docs", "https://react.dev", "https://react.dev/search?q={}", "docs", priority=80),

    # Academic & Research
    "arxiv": Platform("Arxiv", "https://arxiv.org", "https://arxiv.org/search/?query={}", "academic", priority=90),
    "scholar": Platform("Google Scholar", "https://scholar.google.com", "https://scholar.google.com/scholar?q={}", "academic", priority=85),
    "pubmed": Platform("PubMed", "https://pubmed.ncbi.nlm.nih.gov", "https://pubmed.ncbi.nlm.nih.gov/?term={}", "academic", priority=80),

    # Media
    "youtube": Platform("YouTube", "https://youtube.com", "https://youtube.com/results?search_query={}", "media", priority=85),
    "spotify": Platform("Spotify", "https://open.spotify.com", "https://open.spotify.com/search/{}", "media", priority=80),
    "youtube_music": Platform("YouTube Music", "https://music.youtube.com", "https://music.youtube.com/search?q={}", "media", priority=75),

    # Social & Community
    "reddit": Platform("Reddit", "https://reddit.com", "https://reddit.com/search?q={}", "social", priority=80),
    "hackernews": Platform("Hacker News", "https://news.ycombinator.com", "https://hn.algolia.com/?q={}", "social", priority=75),

    # Knowledge
    "wikipedia": Platform("Wikipedia", "https://wikipedia.org", "https://wikipedia.org/wiki/Special:Search?search={}", "knowledge", priority=85),
    "wolfram": Platform("Wolfram Alpha", "https://wolframalpha.com", "https://wolframalpha.com/input/?i={}", "knowledge", priority=80),

    # News
    "google_news": Platform("Google News", "https://news.google.com", "https://news.google.com/search?q={}", "news", priority=80),
    "bing_news": Platform("Bing News", "https://bing.com/news", "https://bing.com/news/search?q={}", "news", priority=70),
}


# ════════════════════════════════════════════════════════════════════
# QUERY DOMAIN CLASSIFICATION
# ════════════════════════════════════════════════════════════════════

# Keywords/patterns that indicate query domains
_QUERY_SIGNALS: dict[str, list[re.Pattern[str]]] = {
    "programming": [
        re.compile(r"\b(python|java|javascript|typescript|rust|go|c\+\+|ruby|php|swift|kotlin)\b", re.I),
        re.compile(r"\b(function|class|method|variable|loop|if\s+else|array|dict|list|tuple|set)\b", re.I),
        re.compile(r"\b(code|coding|program|develop|implement|refactor|debug|compile|build)\b", re.I),
        re.compile(r"\b(error|exception|traceback|bug|fix|issue|problem)\b.*\b(code|program|script)\b", re.I),
        re.compile(r"\b(decorator|generator|iterator|context\s+manager|async|await|lambda)\b", re.I),
    ],
    "package": [
        re.compile(r"\b(install|package|library|module|dependency|pip|npm|cargo|gem)\b", re.I),
        re.compile(r"\b(pip\s+install|npm\s+install|cargo\s+add|gem\s+install)\b", re.I),
        re.compile(r"\b(package\s+for|library\s+for|module\s+for)\b", re.I),
    ],
    "ai_ml": [
        re.compile(r"\b(machine\s+learning|deep\s+learning|neural\s+network|AI|artificial\s+intelligence)\b", re.I),
        re.compile(r"\b(transformer|GPT|LLM|BERT|CNN|RNN|LSTM|GAN|diffusion)\b", re.I),
        re.compile(r"\b(training|inference|dataset|model|epoch|batch|loss|accuracy)\b", re.I),
        re.compile(r"\b(paper|research|arxiv|publication|study)\b.*\b(AI|ML|model|neural)\b", re.I),
    ],
    "academic": [
        re.compile(r"\b(paper|research|study|thesis|dissertation|journal|publication)\b", re.I),
        re.compile(r"\b(arxiv|scholar|doi|citation|abstract|methodology|hypothesis)\b", re.I),
        re.compile(r"\b(equation|formula|theorem|proof|derivation|analysis)\b", re.I),
    ],
    "music": [
        re.compile(r"\b(song|track|album|artist|band|playlist|music|listen|play)\b", re.I),
        re.compile(r"\b(singer|guitar|piano|concert|genre|lyrics|melody|beat)\b", re.I),
    ],
    "video": [
        re.compile(r"\b(video|watch|tutorial|lecture|stream|youtube|episode|movie)\b", re.I),
        re.compile(r"\b(explain|how\s+to|walkthrough|demo|demonstration)\b", re.I),
    ],
    "news": [
        re.compile(r"\b(news|headline|announce|breaking|latest|recent|today|this\s+week)\b", re.I),
        re.compile(r"\b(election|government|president|minister|parliament|congress)\b", re.I),
    ],
    "meme": [
        re.compile(r"\b(meme|memes|funny|humor|joke|jokes|lol|lmao|rofl)\b", re.I),
    ],
    "factual": [
        re.compile(r"\b(who\s+is|what\s+is|when\s+did|where\s+is|how\s+many|how\s+much|how\s+old)\b", re.I),
        re.compile(r"\b(history|war|battle|empire|civilization|ancient|century)\b", re.I),
        re.compile(r"\b(country|capital|population|area|currency|language)\b", re.I),
    ],
    "weather": [
        re.compile(r"\b(weather|temperature|forecast|rain|snow|sunny|cloudy|humidity)\b", re.I),
    ],
    "finance": [
        re.compile(r"\b(stock|share|price|market|invest|trading|crypto|bitcoin|forex)\b", re.I),
        re.compile(r"\b(company|ticker|NYSE|NASDAQ|SENSEX|NIFTY)\b", re.I),
    ],
    "docs": [
        re.compile(r"\b(documentation|docs|reference|manual|guide|tutorial|api)\b", re.I),
        re.compile(r"\b(how\s+to\s+use|syntax|example|usage|api\s+reference)\b", re.I),
    ],
}

# Domain → preferred platforms (ordered by priority)
_DOMAIN_PLATFORMS: dict[str, list[str]] = {
    "programming": ["stackoverflow", "github", "google", "python_docs", "mdn"],
    "package":     ["pypi", "npm", "crates", "maven", "google"],
    "ai_ml":       ["arxiv", "scholar", "google", "github", "reddit"],
    "academic":    ["arxiv", "scholar", "pubmed", "google", "wikipedia"],
    "music":       ["spotify", "youtube_music", "youtube", "google"],
    "video":       ["youtube", "google", "reddit", "hackernews"],
    "news":        ["google_news", "bing_news", "google", "reddit"],
    "meme":        ["reddit", "google", "bing"],
    "factual":     ["wikipedia", "wolfram", "google"],
    "weather":     ["google"],
    "finance":     ["google", "wikipedia"],
    "docs":        ["python_docs", "mdn", "react_docs", "google"],
    "general":     ["google", "bing", "duckduckgo", "wikipedia"],
}


# ════════════════════════════════════════════════════════════════════
# PLATFORM-AWARE ROUTER
# ════════════════════════════════════════════════════════════════════

@dataclass
class RouteResult:
    """Result of platform-aware routing."""
    domain: str
    platforms: list[Platform]
    primary_platform: Platform
    search_urls: list[str]
    reasoning: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "platforms": [p.name for p in self.platforms],
            "primary": self.primary_platform.name,
            "search_urls": self.search_urls,
            "reasoning": self.reasoning,
            "confidence": round(self.confidence, 3),
        }


class PlatformAwareRouter:
    """Routes queries to optimal platforms.

    Core principle: NEVER search randomly.
    Every query type has an optimal set of platforms.
    """

    def __init__(self) -> None:
        self._platforms = PLATFORMS.copy()
        self._domain_platforms = _DOMAIN_PLATFORMS.copy()
        self._query_signals = _QUERY_SIGNALS.copy()
        self._usage_stats: dict[str, int] = {name: 0 for name in PLATFORMS}
        self._success_stats: dict[str, int] = {name: 0 for name in PLATFORMS}

    def route(
        self,
        query: str,
        intent: str = "",
        entities: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> RouteResult:
        """Route a query to the best platform(s).

        Args:
            query: The search query or user input.
            intent: NLP-detected intent (if any).
            entities: Extracted entities (if any).
            context: Conversation context (if any).

        Returns:
            RouteResult with optimal platforms and search URLs.
        """
        entities = entities or {}
        context = context or {}

        # Step 1: Classify query domain
        domain = self._classify_domain(query, intent, entities)

        # Step 2: Get platform candidates for domain
        platform_names = self._domain_platforms.get(domain, self._domain_platforms["general"])

        # Step 3: Filter by entity-detected platform preference
        entity_platform = self._detect_platform_from_entities(entities)
        if entity_platform and entity_platform in self._platforms:
            # Insert entity-detected platform at front
            if entity_platform not in platform_names:
                platform_names = [entity_platform] + platform_names
            else:
                platform_names = [entity_platform] + [p for p in platform_names if p != entity_platform]

        # Step 4: Score and rank platforms
        platforms = []
        for name in platform_names[:5]:  # Top 5 candidates
            if name in self._platforms:
                platforms.append(self._platforms[name])

        if not platforms:
            platforms = [self._platforms["google"]]

        primary = self._rank_platforms(platforms, query, context)[0]

        # Step 5: Generate search URLs
        search_urls = []
        for p in platforms[:3]:  # Top 3
            url = p.search_url.replace("{}", self._url_encode_query(query))
            search_urls.append(url)

        # Step 6: Build reasoning
        reasoning = self._build_reasoning(domain, primary, entity_platform, query)

        confidence = 0.8
        if entity_platform:
            confidence += 0.1
        if len(self._classify_domain(query, intent, entities)) > 3:
            confidence += 0.05

        return RouteResult(
            domain=domain,
            platforms=platforms,
            primary_platform=primary,
            search_urls=search_urls,
            reasoning=reasoning,
            confidence=min(confidence, 1.0),
        )

    def get_handler_for_platform(self, platform_name: str) -> str | None:
        """Get the tool handler for a platform."""
        _HANDLER_MAP = {
            "google": "jarvis.tools.web_search",
            "bing": "jarvis.tools.web_search",
            "duckduckgo": "jarvis.tools.web_search",
            "github": "jarvis.tools.web_search",
            "stackoverflow": "jarvis.tools.web_search",
            "pypi": "jarvis.tools.web_search",
            "npm": "jarvis.tools.web_search",
            "arxiv": "jarvis.tools.web_search",
            "scholar": "jarvis.tools.web_search",
            "youtube": "jarvis.tools.search_youtube",
            "spotify": "jarvis.tools.play_music",
            "youtube_music": "jarvis.tools.play_music",
            "reddit": "jarvis.tools.web_search",
            "wikipedia": "jarvis.tools.web_search",
            "wolfram": "jarvis.tools.web_search",
            "google_news": "jarvis.tools.web_search",
            "bing_news": "jarvis.tools.web_search",
        }
        return _HANDLER_MAP.get(platform_name)

    def record_usage(self, platform_name: str, success: bool) -> None:
        """Record platform usage for learning."""
        if platform_name in self._usage_stats:
            self._usage_stats[platform_name] += 1
            if success:
                self._success_stats[platform_name] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get platform usage statistics."""
        return {
            "total_platforms": len(self._platforms),
            "total_queries": sum(self._usage_stats.values()),
            "platform_usage": dict(self._usage_stats),
            "platform_success": dict(self._success_stats),
        }

    # ── Private Methods ──

    def _classify_domain(
        self, query: str, intent: str, entities: dict[str, Any],
    ) -> str:
        """Classify query into a domain based on signals."""
        # Check intent-based classification first
        intent_domain = self._intent_to_domain(intent)
        if intent_domain:
            return intent_domain

        # Check entity-based classification
        entity_domain = self._entities_to_domain(entities)
        if entity_domain:
            return entity_domain

        # Signal-based classification
        scores: dict[str, int] = {}
        for domain, patterns in self._query_signals.items():
            score = sum(1 for p in patterns if p.search(query))
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)  # type: ignore

        return "general"

    def _intent_to_domain(self, intent: str) -> str | None:
        """Map NLP intent to search domain."""
        _INTENT_DOMAIN_MAP = {
            "WEB_SEARCH": None,  # Let signal classification handle it
            "SEARCH_ON_PLATFORM": None,
            "SEARCH_YOUTUBE": "video",
            "PROGRAMMING": "programming",
            "GET_WEATHER": "weather",
            "GET_NEWS": "news",
            "STOCK_QUOTE": "finance",
            "NASA_APOD": "academic",
            "NASA_MARS": "academic",
            "ISS_LOCATION": "academic",
            "CALCULATOR": None,
            "DATETIME": None,
            "JOKE": "meme",
            "QUOTE": "factual",
            "RANDOM_FACT": "factual",
        }
        return _INTENT_DOMAIN_MAP.get(intent)

    def _entities_to_domain(self, entities: dict[str, Any]) -> str | None:
        """Detect domain from extracted entities."""
        for key, val in entities.items():
            if not isinstance(val, dict):
                continue
            value = str(val.get("value", "")).lower()

            # Check for programming language entities
            if key in ("language", "technology", "framework"):
                return "programming"
            if key in ("package", "library", "module"):
                return "package"
            if key in ("paper", "research", "study"):
                return "academic"
            if key in ("song", "artist", "album"):
                return "music"
            if key in ("video", "tutorial"):
                return "video"
        return None

    def _detect_platform_from_entities(self, entities: dict[str, Any]) -> str | None:
        """Detect specific platform from entities."""
        for key, val in entities.items():
            if not isinstance(val, dict):
                continue
            value = str(val.get("value", "")).lower()

            # Direct platform mentions
            if "youtube" in value:
                return "youtube"
            if "spotify" in value:
                return "spotify"
            if "github" in value:
                return "github"
            if "reddit" in value:
                return "reddit"
            if "wikipedia" in value:
                return "wikipedia"
            if "arxiv" in value or "arxiv" in value:
                return "arxiv"
            if "stackoverflow" in value or "stack overflow" in value:
                return "stackoverflow"
            if "npm" in value or "node" in value:
                return "npm"
            if "pypi" in value or "pip" in value:
                return "pypi"

        return None

    def _rank_platforms(
        self, platforms: list[Platform], query: str, context: dict[str, Any],
    ) -> list[Platform]:
        """Rank platforms by relevance, reliability, and usage history."""
        def score(p: Platform) -> float:
            s = float(p.priority)

            # Reliability bonus
            s += p.reliability * 10

            # Latency penalty (faster = better)
            s -= (p.latency_ms / 1000) * 5

            # Usage success rate bonus
            total = self._usage_stats.get(p.name, 0)
            success = self._success_stats.get(p.name, 0)
            if total > 0:
                s += (success / total) * 15

            return s

        return sorted(platforms, key=score, reverse=True)

    def _build_reasoning(
        self, domain: str, primary: Platform,
        entity_platform: str | None, query: str,
    ) -> str:
        """Build human-readable routing reasoning."""
        parts = [f"Domain: {domain}"]
        if entity_platform:
            parts.append(f"User-specified platform: {entity_platform}")
        parts.append(f"Primary source: {primary.name}")
        return " | ".join(parts)

    @staticmethod
    def _url_encode_query(query: str) -> str:
        """URL-encode a query string."""
        import urllib.parse
        return urllib.parse.quote_plus(query)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

platform_router = PlatformAwareRouter()
