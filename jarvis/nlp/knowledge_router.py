"""Knowledge source router for JARVIS NLP.

Routes requests to the best knowledge source based on domain:
- Programming: Official Docs -> GitHub -> Stack Overflow -> LLM
- General Knowledge: LLM -> Wikipedia
- Current News: News APIs -> Web Search
- Research: Arxiv -> Papers -> Official Sources
- Music: Spotify -> YouTube Music -> YouTube

Never uses a random source first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jarvis.nlp.utils import GoalCategory


@dataclass
class KnowledgeSource:
    """A knowledge source with its priority and handler."""
    name: str
    priority: int  # Lower = higher priority
    handler: str
    description: str = ""
    requires_network: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "priority": self.priority,
            "handler": self.handler,
            "description": self.description,
            "requires_network": self.requires_network,
        }


# Domain -> ordered list of knowledge sources
KNOWLEDGE_SOURCES: dict[str, list[KnowledgeSource]] = {
    "programming": [
        KnowledgeSource("official_docs", 1, "jarvis.tools.web_search", "Official Documentation"),
        KnowledgeSource("github", 2, "jarvis.tools.web_search", "GitHub Repositories & Issues"),
        KnowledgeSource("stackoverflow", 3, "jarvis.tools.web_search", "Stack Overflow Answers"),
        KnowledgeSource("llm", 4, "jarvis.llm", "LLM Knowledge", requires_network=False),
    ],
    "general": [
        KnowledgeSource("llm", 1, "jarvis.llm", "LLM Knowledge", requires_network=False),
        KnowledgeSource("wikipedia", 2, "jarvis.tools.web_search", "Wikipedia"),
        KnowledgeSource("web", 3, "jarvis.tools.web_search", "Web Search"),
    ],
    "news": [
        KnowledgeSource("news_api", 1, "jarvis.tools.finnhub_market_news", "News APIs"),
        KnowledgeSource("web_search", 2, "jarvis.tools.web_search", "Web Search"),
    ],
    "research": [
        KnowledgeSource("arxiv", 1, "jarvis.tools.web_search", "Arxiv Papers"),
        KnowledgeSource("scholar", 2, "jarvis.tools.web_search", "Google Scholar"),
        KnowledgeSource("official", 3, "jarvis.tools.web_search", "Official Sources"),
    ],
    "music": [
        KnowledgeSource("spotify", 1, "jarvis.tools.play_music", "Spotify"),
        KnowledgeSource("youtube_music", 2, "jarvis.tools.web_search", "YouTube Music"),
        KnowledgeSource("youtube", 3, "jarvis.tools.play_music", "YouTube"),
    ],
    "video": [
        KnowledgeSource("youtube", 1, "jarvis.tools.play_music", "YouTube"),
        KnowledgeSource("vimeo", 2, "jarvis.tools.web_search", "Vimeo"),
    ],
    "docs": [
        KnowledgeSource("official_docs", 1, "jarvis.tools.web_search", "Official Documentation"),
        KnowledgeSource("dev_docs", 2, "jarvis.tools.web_search", "Developer Documentation"),
        KnowledgeSource("web", 3, "jarvis.tools.web_search", "Web Search"),
    ],
    "weather": [
        KnowledgeSource("weather_api", 1, "jarvis.tools.get_weather", "Weather API"),
        KnowledgeSource("web_search", 2, "jarvis.tools.web_search", "Web Search"),
    ],
    "finance": [
        KnowledgeSource("stock_api", 1, "jarvis.tools.finnhub_quote", "Stock API"),
        KnowledgeSource("market_news", 2, "jarvis.tools.finnhub_market_news", "Market News"),
        KnowledgeSource("web_search", 3, "jarvis.tools.web_search", "Web Search"),
    ],
    "shopping": [
        KnowledgeSource("amazon", 1, "jarvis.tools.web_search", "Amazon"),
        KnowledgeSource("web_search", 2, "jarvis.tools.web_search", "Web Search"),
    ],
}

# Intent to domain mapping
_INTENT_DOMAINS: dict[str, str] = {
    "PROGRAMMING": "programming",
    "SEARCH_WEB": "general",
    "GET_NEWS": "news",
    "GET_WEATHER": "weather",
    "STOCK_QUOTE": "finance",
    "PLAY_MUSIC": "music",
    "PLAY_YOUTUBE": "music",
    "PLAY_SPOTIFY": "music",
    "SEARCH_YOUTUBE": "video",
    "NASA_APOD": "research",
    "NASA_MARS": "research",
    "ISS_LOCATION": "research",
    "RANDOM_FACT": "general",
    "CALCULATOR": "general",
    "DATETIME": "general",
}

# Platform intelligence: detect platform from entity patterns
_PLATFORM_PATTERNS: dict[str, str] = {
    "github.com": "github",
    "gitlab.com": "gitlab",
    "stackoverflow.com": "stackoverflow",
    "arxiv.org": "arxiv",
    "pypi.org": "pypi",
    "npmjs.com": "npm",
    "hub.docker.com": "dockerhub",
    "leetcode.com": "leetcode",
    "medium.com": "medium",
    "reddit.com": "reddit",
    "youtube.com": "youtube",
    "spotify.com": "spotify",
    "amazon.com": "amazon",
    "imdb.com": "imdb",
    "docs.python.org": "python_docs",
    "developer.mozilla.org": "mdn",
}


@dataclass
class RoutingResult:
    """Result of knowledge routing."""
    domain: str
    sources: list[KnowledgeSource]
    primary_source: KnowledgeSource | None
    platform: str
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "sources": [s.to_dict() for s in self.sources],
            "primary_source": self.primary_source.to_dict() if self.primary_source else None,
            "platform": self.platform,
            "reasoning": self.reasoning,
        }


class KnowledgeRouter:
    """Routes requests to the best knowledge source based on domain.

    Analyzes the intent, entities, and context to determine which
    knowledge domain the request belongs to, then returns the
    ordered list of sources to try.
    """

    def route(
        self,
        intent: str,
        entities: dict[str, Any],
        goal: GoalCategory = GoalCategory.UNKNOWN,
    ) -> RoutingResult:
        """Route a request to the best knowledge source.

        Parameters
        ----------
        intent:
            The classified intent string.
        entities:
            Extracted entities from the NLP pipeline.
        goal:
            The detected goal category.

        Returns
        -------
        RoutingResult with ordered sources and platform detection.
        """
        # Determine domain from intent
        domain = _INTENT_DOMAINS.get(intent, self._goal_to_domain(goal))

        # Detect platform from entities
        platform = self._detect_platform(entities)

        # Get sources for the domain
        sources = KNOWLEDGE_SOURCES.get(domain, KNOWLEDGE_SOURCES["general"])

        # If a specific platform is detected, reorder sources
        if platform:
            sources = self._reorder_for_platform(sources, platform)

        primary = sources[0] if sources else None

        reasoning = f"Intent '{intent}' -> domain '{domain}'"
        if platform:
            reasoning += f", platform '{platform}'"

        return RoutingResult(
            domain=domain,
            sources=sources,
            primary_source=primary,
            platform=platform,
            reasoning=reasoning,
        )

    def get_source_for_query(
        self,
        query: str,
        domain: str = "general",
    ) -> KnowledgeSource | None:
        """Get the best source for a free-form query."""
        sources = KNOWLEDGE_SOURCES.get(domain, KNOWLEDGE_SOURCES["general"])
        query_lower = query.lower()

        # Check for platform-specific patterns
        for pattern, platform in _PLATFORM_PATTERNS.items():
            if pattern in query_lower:
                reordered = self._reorder_for_platform(sources, platform)
                return reordered[0] if reordered else None

        return sources[0] if sources else None

    def detect_platform_from_url(self, url: str) -> str:
        """Detect the platform from a URL."""
        url_lower = url.lower()
        for pattern, platform in _PLATFORM_PATTERNS.items():
            if pattern in url_lower:
                return platform
        return ""

    @staticmethod
    def _detect_platform(entities: dict[str, Any]) -> str:
        """Detect platform from entity values."""
        for key in ("platform", "url", "website", "target"):
            value = str(entities.get(key, "")).lower()
            for pattern, platform in _PLATFORM_PATTERNS.items():
                if pattern in value:
                    return platform
        return ""

    @staticmethod
    def _goal_to_domain(goal: GoalCategory) -> str:
        """Map a goal category to a knowledge domain."""
        goal_domain_map = {
            GoalCategory.PROGRAMMING: "programming",
            GoalCategory.INFORMATION: "general",
            GoalCategory.ENTERTAINMENT: "music",
            GoalCategory.EDUCATION: "research",
            GoalCategory.FINANCE: "finance",
            GoalCategory.SHOPPING: "shopping",
            GoalCategory.PRODUCTIVITY: "general",
            GoalCategory.SYSTEM: "general",
            GoalCategory.COMMUNICATION: "general",
        }
        return goal_domain_map.get(goal, "general")

    @staticmethod
    def _reorder_for_platform(
        sources: list[KnowledgeSource],
        platform: str,
    ) -> list[KnowledgeSource]:
        """Reorder sources to prioritize the detected platform."""
        platform_handlers = {
            "github": "github",
            "stackoverflow": "stackoverflow",
            "arxiv": "arxiv",
            "pypi": "pypi",
            "npm": "npm",
            "youtube": "youtube",
            "spotify": "spotify",
            "reddit": "reddit",
            "medium": "medium",
            "amazon": "amazon",
        }

        handler_keyword = platform_handlers.get(platform, platform)
        prioritized = []
        deprioritized = []

        for source in sources:
            if handler_keyword in source.handler.lower() or platform in source.name.lower():
                prioritized.append(source)
            else:
                deprioritized.append(source)

        return prioritized + deprioritized
