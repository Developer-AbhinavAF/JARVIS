"""Safe structured action parsing for JARVIS.

Model output is never treated as executable code. Only these action identifiers
are accepted, and each maps to a small structured payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import quote_plus, urlparse


class ActionType(str, Enum):
    OPEN_YOUTUBE = "OPEN_YOUTUBE"
    OPEN_CHROME = "OPEN_CHROME"
    SEARCH_WEB = "SEARCH_WEB"
    OPEN_WEBSITE = "OPEN_WEBSITE"
    OPEN_APP = "OPEN_APP"
    YOUTUBE_SEARCH = "YOUTUBE_SEARCH"
    YOUTUBE_PLAY = "YOUTUBE_PLAY"
    GET_WEATHER = "GET_WEATHER"
    GET_NEWS = "GET_NEWS"


SAFE_APP_NAMES = {
    "chrome",
    "notepad",
    "calculator",
    "calc",
    "explorer",
    "file explorer",
    "settings",
    "terminal",
    "cmd",
    "vscode",
    "visual studio code",
    "spotify",
}


@dataclass
class Action:
    action_type: ActionType
    value: str = ""
    data: dict = field(default_factory=dict)

    def to_frontend_action(self) -> dict:
        if self.action_type == ActionType.OPEN_YOUTUBE:
            return {"tool": "open_url", "url": "https://youtube.com"}

        if self.action_type == ActionType.OPEN_CHROME:
            return {"tool": "open_app", "app": "chrome"}

        if self.action_type == ActionType.SEARCH_WEB:
            query = self.value.strip()
            return {
                "tool": "web_search",
                "query": query,
                "url": f"https://www.google.com/search?q={quote_plus(query)}",
            }

        if self.action_type == ActionType.OPEN_WEBSITE:
            return {"tool": "open_url", "url": self.value}

        if self.action_type == ActionType.OPEN_APP:
            return {"tool": "open_app", "app": self.value.lower().strip()}

        if self.action_type == ActionType.YOUTUBE_SEARCH:
            query = self.data.get("query", self.value).strip()
            return {
                "tool": "open_url",
                "url": f"https://youtube.com/results?search_query={quote_plus(query)}",
                "query": query,
            }

        if self.action_type == ActionType.YOUTUBE_PLAY:
            query = self.data.get("query", self.value).strip()
            return {
                "tool": "open_url",
                "url": f"https://youtube.com/results?search_query={quote_plus(query)}",
                "query": query,
            }

        if self.action_type == ActionType.GET_WEATHER:
            city = self.data.get("city", self.value).strip()
            query = f"weather in {city}" if city else "weather"
            return {
                "tool": "web_search",
                "query": query,
                "url": f"https://www.google.com/search?q={quote_plus(query)}",
            }

        if self.action_type == ActionType.GET_NEWS:
            topic = self.data.get("topic", self.value).strip()
            query = f"{topic} news" if topic else "latest news"
            return {
                "tool": "web_search",
                "query": query,
                "url": f"https://www.google.com/search?q={quote_plus(query)}",
            }

        return {"tool": "action", "action": self.action_type.value}


def _safe_url(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None
    return url.strip()


def parse_action_line(line: str) -> Action | None:
    """Parse an allowlisted ``ACTION:...`` line."""
    raw = (line or "").strip()
    if not raw.startswith("ACTION:"):
        return None

    payload = raw[len("ACTION:") :].strip()
    name, _, value = payload.partition("|")
    name = name.strip().upper()
    value = value.strip()

    try:
        action_type = ActionType(name)
    except ValueError:
        return None

    if action_type in {ActionType.OPEN_YOUTUBE, ActionType.OPEN_CHROME}:
        return Action(action_type)

    if action_type == ActionType.SEARCH_WEB:
        return Action(action_type, value[:200]) if value else None

    if action_type == ActionType.OPEN_WEBSITE:
        safe = _safe_url(value)
        return Action(action_type, safe) if safe else None

    if action_type == ActionType.OPEN_APP:
        app_name = value.lower().strip()
        return Action(action_type, app_name) if app_name in SAFE_APP_NAMES else None

    if action_type in {ActionType.YOUTUBE_SEARCH, ActionType.YOUTUBE_PLAY}:
        query = value[:200].strip()
        return Action(action_type, query, {"query": query}) if query else None

    if action_type == ActionType.GET_WEATHER:
        city = value[:120].strip()
        return Action(action_type, city, {"city": city}) if city else None

    if action_type == ActionType.GET_NEWS:
        topic = value[:120].strip()
        return Action(action_type, topic, {"topic": topic})

    return None
