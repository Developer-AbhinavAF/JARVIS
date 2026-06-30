"""Ultra-fast command execution for JARVIS.

Checked before any routing or LLM calls.
Target: under 10ms per match.
"""

from __future__ import annotations

import logging
import re
import time
import webbrowser
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import quote_plus

from jarvis.action_router import Action, ActionType

logger = logging.getLogger(__name__)


@dataclass
class FastAction:
    name: str
    execute: Callable[[], str]
    latency_ms: float = 0.0
    structured_action: Action | None = None


_WEBSITES: dict[str, str] = {
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
}


def _open_url(url: str) -> str:
    webbrowser.open(url)
    return f"Opened {url}"


def _open_website_action(name: str, url: str) -> FastAction:
    def execute() -> str:
        webbrowser.open(url)
        return f"Opening {name}."
    return FastAction(
        name=name,
        execute=execute,
        structured_action=Action(ActionType.OPEN_WEBSITE, url),
    )


_PATTERNS: list[tuple[re.Pattern, Callable[[str], FastAction | None]]] = []


def _build_patterns():
    global _PATTERNS

    # open X website patterns
    names = "|".join(re.escape(k) for k in _WEBSITES)
    p_open = re.compile(rf"^(?:open|launch|go\s+to|visit|start)\s+(?:the\s+)?(?:website\s+)?({names})\s*$", re.IGNORECASE)
    _PATTERNS.append((p_open, lambda m: _open_website_action(m.group(1), _WEBSITES[m.group(1).lower()])))

    # just "youtube", "google", etc. as standalone
    p_standalone = re.compile(rf"^({names})\s*$", re.IGNORECASE)
    _PATTERNS.append((p_standalone, lambda m: _open_website_action(m.group(1), _WEBSITES[m.group(1).lower()])))

    # search X on youtube
    p_yt_search = re.compile(r"^(?:search|find)\s+(.+?)\s+on\s+youtube\s*$", re.IGNORECASE)
    def yt_search(m):
        q = m.group(1).strip()
        url = f"https://youtube.com/results?search_query={quote_plus(q)}"
        return FastAction(
            name="youtube_search",
            execute=lambda: _open_url(url) and f"Searched YouTube for: {q}",
            structured_action=Action(ActionType.YOUTUBE_SEARCH, q, {"query": q}),
        )
    _PATTERNS.append((p_yt_search, yt_search))

    # play X (YouTube)
    p_play = re.compile(r"^play\s+(.+)\s*$", re.IGNORECASE)
    def yt_play(m):
        q = m.group(1).strip()
        url = f"https://youtube.com/results?search_query={quote_plus(q)}"
        return FastAction(
            name="play_youtube",
            execute=lambda: _open_url(url) and f"Playing: {q}",
            structured_action=Action(ActionType.YOUTUBE_PLAY, q, {"query": q}),
        )
    _PATTERNS.append((p_play, yt_play))

    # weather in X
    p_weather = re.compile(r"^weather\s+(?:in|at|for|of)\s+(.+)\s*$", re.IGNORECASE)
    def weather_search(m):
        city = m.group(1).strip()
        query = f"weather in {city}"
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        return FastAction(
            name="weather",
            execute=lambda: _open_url(url) and f"Showing weather for {city}",
            structured_action=Action(ActionType.GET_WEATHER, city, {"city": city}),
        )
    _PATTERNS.append((p_weather, weather_search))

    # latest news / news about X
    p_news = re.compile(r"^(?:latest\s+)?(?:news|headlines)(?:\s+(?:about|on|in|of)\s+(.+))?\s*$", re.IGNORECASE)
    def news_search(m):
        topic = m.group(1).strip() if m.group(1) else ""
        q = f"{topic} news" if topic else "latest news"
        url = f"https://www.google.com/search?q={quote_plus(q)}"
        return FastAction(
            name="news",
            execute=lambda: _open_url(url) and f"Showing news: {q}",
            structured_action=Action(ActionType.GET_NEWS, topic, {"topic": topic}),
        )
    _PATTERNS.append((p_news, news_search))

    # search web for X
    p_search = re.compile(r"^(?:search\s+(?:the\s+)?(?:web|internet)\s+for\s+|google\s+)(.+)\s*$", re.IGNORECASE)
    def web_search(m):
        q = m.group(1).strip()
        url = f"https://www.google.com/search?q={quote_plus(q)}"
        return FastAction(
            name="web_search",
            execute=lambda: _open_url(url) and f"Searched for: {q}",
            structured_action=Action(ActionType.SEARCH_WEB, q),
        )
    _PATTERNS.append((p_search, web_search))

    # time/date
    p_time = re.compile(r"^(?:what'?s?|what\s+is|tell\s+me)\s+(?:the\s+)?(?:time|date|day)\s*$", re.IGNORECASE)
    p_time2 = re.compile(r"^(?:current|today'?s?)\s+(?:time|date|day)\s*$", re.IGNORECASE)
    from datetime import datetime
    def time_action(m=None):
        now = datetime.now()
        return FastAction(name="datetime", execute=lambda: now.strftime("%A, %d %B %Y — %H:%M"))
    _PATTERNS.append((p_time, lambda m: time_action()))
    _PATTERNS.append((p_time2, lambda m: time_action()))

    # system status
    p_sys = re.compile(r"^(?:system|computer|pc)\s+(?:status|stats|info|health)\s*$", re.IGNORECASE)
    _PATTERNS.append((p_sys, lambda m: FastAction(name="system_status", execute=lambda: "Checking system...")))

    # calculator
    p_calc = re.compile(r"^(?:calculate|calc)\s+(.+)\s*$", re.IGNORECASE)
    _PATTERNS.append((p_calc, lambda m: FastAction(name="calculator", execute=lambda: f"Calculating: {m.group(1)}")))

    # tell a joke
    p_joke = re.compile(r"^(?:tell|make|give)\s+(?:me\s+)?(?:a\s+)?joke\s*$", re.IGNORECASE)
    _PATTERNS.append((p_joke, lambda m: FastAction(name="joke", execute=lambda: "")))

    # flip coin
    p_coin = re.compile(r"^(?:flip|toss)\s+(?:a\s+)?coin\s*$", re.IGNORECASE)
    _PATTERNS.append((p_coin, lambda m: FastAction(name="coin", execute=lambda: "")))


_build_patterns()

_TRIVIAL: set[str] = {"hello", "hi", "hey", "thanks", "thank you", "ok", "okay", "yes", "no", "bye", "goodbye", "thankyou", "thx", "ty", "👍", "🙏", "k", "kk", "cool", "nice", "great", "awesome", "good", "fine"}


def is_trivial(text: str) -> bool:
    return text.strip().lower() in _TRIVIAL


def match_fast(text: str) -> FastAction | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    for pattern, handler in _PATTERNS:
        m = pattern.match(cleaned)
        if m:
            try:
                result = handler(m)
                if result:
                    return result
            except Exception:
                continue
    return None
