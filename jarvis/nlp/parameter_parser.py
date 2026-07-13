"""Parameter parsing for JARVIS NLP pipeline.

Converts extracted entities into tool-ready parameters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .entity_extractor import ExtractionResult


@dataclass
class ParsedParams:
    """Parsed parameters ready for tool execution."""
    tool_name: str
    params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_entities: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)

    def __str__(self) -> str:
        return f"ParsedParams(tool={self.tool_name}, params={self.params})"


class ParameterParser:
    """Converts extracted entities to tool-ready parameters."""

    def parse(self, intent: str, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse entities into tool parameters.

        Args:
            intent: Classified intent
            entities: Extracted entities
            action: Direct action name from pattern

        Returns:
            ParsedParams ready for tool execution
        """
        parser = getattr(self, f"_parse_{intent.lower()}", None)
        if parser:
            return parser(entities, action)
        return self._parse_generic(entities, action)

    def _parse_generic(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Generic parameter parsing."""
        params = {}
        tool_name = action or "unknown"

        if entities.has("query"):
            params["query"] = entities.get("query")
        if entities.has("target"):
            params["target"] = entities.get("target")
        if entities.has("text"):
            params["text"] = entities.get("text")

        return ParsedParams(
            tool_name=tool_name,
            params=params,
            confidence=0.80,
            raw_entities=entities.to_dict(),
        )

    def _parse_open_website(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse OPEN_WEBSITE parameters."""
        website = entities.get("website")
        url = entities.get("url")

        if url:
            return ParsedParams(
                tool_name="open_app",
                params={"target": url},
                confidence=0.95,
                raw_entities=entities.to_dict(),
            )
        elif website:
            return ParsedParams(
                tool_name="open_app",
                params={"target": website},
                confidence=0.95,
                raw_entities=entities.to_dict(),
            )
        return ParsedParams(
            tool_name="open_app",
            params={"target": entities.get("target", "")},
            confidence=0.85,
            raw_entities=entities.to_dict(),
        )

    def _parse_open_app(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse OPEN_APP parameters."""
        app = entities.get("app")
        target = entities.get("target")
        return ParsedParams(
            tool_name="open_app",
            params={"target": app or target or ""},
            confidence=0.92,
            raw_entities=entities.to_dict(),
        )

    def _parse_close_app(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse CLOSE_APP parameters."""
        app = entities.get("app")
        target = entities.get("target")
        return ParsedParams(
            tool_name="close_app",
            params={"target": app or target or ""},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_search_youtube(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SEARCH_YOUTUBE parameters."""
        query = entities.get("query", "")
        return ParsedParams(
            tool_name="search_youtube",
            params={"query": query},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_search_on_platform(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SEARCH_ON_PLATFORM parameters."""
        query = entities.get("query", "")
        platform = entities.get("platform", "google")

        # Map platform to search URL
        platform_urls = {
            "reddit": f"https://reddit.com/search?q={query}",
            "github": f"https://github.com/search?q={query}",
            "wikipedia": f"https://wikipedia.org/wiki/Special:Search?search={query}",
            "stackoverflow": f"https://stackoverflow.com/search?q={query}",
            "amazon": f"https://amazon.com/s?k={query}",
            "imdb": f"https://imdb.com/find?q={query}",
            "spotify": f"https://open.spotify.com/search/{query}",
            "linkedin": f"https://linkedin.com/search/results/all/?keywords={query}",
            "google scholar": f"https://scholar.google.com/scholar?q={query}",
        }

        url = platform_urls.get(platform, f"https://google.com/search?q={query}")

        return ParsedParams(
            tool_name="web_search",
            params={"query": f"{query} site:{platform}", "url": url},
            confidence=0.93,
            raw_entities=entities.to_dict(),
        )

    def _parse_search_web(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SEARCH_WEB parameters."""
        query = entities.get("query", "")
        return ParsedParams(
            tool_name="web_search",
            params={"query": query},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_play_youtube(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse PLAY_YOUTUBE parameters."""
        query = entities.get("query", "")
        return ParsedParams(
            tool_name="play_youtube",
            params={"query": query},
            confidence=0.92,
            raw_entities=entities.to_dict(),
        )

    def _parse_play_spotify(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse PLAY_SPOTIFY parameters."""
        query = entities.get("query", "")
        return ParsedParams(
            tool_name="play_music",
            params={"query": f"{query} spotify"},
            confidence=0.92,
            raw_entities=entities.to_dict(),
        )

    def _parse_play_music(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse PLAY_MUSIC parameters."""
        query = entities.get("query", "")
        return ParsedParams(
            tool_name="play_youtube",
            params={"query": query},
            confidence=0.88,
            raw_entities=entities.to_dict(),
        )

    def _parse_get_weather(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse GET_WEATHER parameters."""
        city = entities.get("city", "")
        return ParsedParams(
            tool_name="get_weather",
            params={"city": city},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_get_news(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse GET_NEWS parameters."""
        topic = entities.get("topic", "")
        return ParsedParams(
            tool_name="finnhub_market_news",
            params={"topic": topic},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_system_status(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SYSTEM_STATUS parameters."""
        return ParsedParams(
            tool_name="get_system_stats",
            params={},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_volume_control(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse VOLUME_CONTROL parameters."""
        vol_action = entities.get("action", "up")
        value = entities.get("value")
        return ParsedParams(
            tool_name="volume_control",
            params={"action": vol_action, "value": int(value) if value else None},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_brightness_control(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse BRIGHTNESS_CONTROL parameters."""
        bright_action = entities.get("action", "up")
        value = entities.get("value")
        return ParsedParams(
            tool_name="brightness_control",
            params={"action": bright_action, "value": int(value) if value else None},
            confidence=0.93,
            raw_entities=entities.to_dict(),
        )

    def _parse_screenshot(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SCREENSHOT parameters."""
        return ParsedParams(
            tool_name="screenshot",
            params={},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_clipboard(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse CLIPBOARD parameters."""
        clip_action = entities.get("action", "get")
        text = entities.get("text")
        params = {"action": clip_action}
        if text:
            params["text"] = text
        return ParsedParams(
            tool_name="clipboard_manager",
            params=params,
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_system_power(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SYSTEM_POWER parameters."""
        power_action = entities.get("power_action", "shutdown")
        return ParsedParams(
            tool_name="system_power",
            params={"action": power_action},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_calculator(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse CALCULATOR parameters."""
        expression = entities.get("expression", "")
        return ParsedParams(
            tool_name="calculator",
            params={"expression": expression},
            confidence=0.92,
            raw_entities=entities.to_dict(),
        )

    def _parse_timer(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse TIMER parameters."""
        seconds = entities.get("seconds", "30")
        return ParsedParams(
            tool_name="timer",
            params={"seconds": int(seconds)},
            confidence=0.93,
            raw_entities=entities.to_dict(),
        )

    def _parse_daily_briefing(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse DAILY_BRIEFING parameters."""
        return ParsedParams(
            tool_name="get_daily_briefing",
            params={},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_save_memory(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SAVE_MEMORY parameters."""
        content = entities.get("content", "")
        return ParsedParams(
            tool_name="memory_save_permanent",
            params={"info": content, "category": "user_important"},
            confidence=0.94,
            raw_entities=entities.to_dict(),
        )

    def _parse_recall_memory(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse RECALL_MEMORY parameters."""
        query = entities.get("query", "")
        return ParsedParams(
            tool_name="memory_search",
            params={"query": query},
            confidence=0.88,
            raw_entities=entities.to_dict(),
        )

    def _parse_window_control(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse WINDOW_CONTROL parameters."""
        win_action = entities.get("action", "minimize")
        target = entities.get("target")
        params = {"action": win_action}
        if target:
            params["title"] = target
        return ParsedParams(
            tool_name="window_control",
            params=params,
            confidence=0.88,
            raw_entities=entities.to_dict(),
        )

    def _parse_screen_info(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SCREEN_INFO parameters."""
        return ParsedParams(
            tool_name="get_screen_info",
            params={},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_speed_test(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SPEED_TEST parameters."""
        return ParsedParams(
            tool_name="run_network_speed_test",
            params={},
            confidence=0.88,
            raw_entities=entities.to_dict(),
        )

    def _parse_type_text(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse TYPE_TEXT parameters."""
        text = entities.get("text", "")
        return ParsedParams(
            tool_name="type_text",
            params={"text": text},
            confidence=0.88,
            raw_entities=entities.to_dict(),
        )

    def _parse_mouse_control(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse MOUSE_CONTROL parameters."""
        mouse_action = entities.get("action", "click")
        x = entities.get("x", "0")
        y = entities.get("y", "0")
        return ParsedParams(
            tool_name="mouse_control",
            params={"action": mouse_action, "x": int(x), "y": int(y)},
            confidence=0.85,
            raw_entities=entities.to_dict(),
        )

    def _parse_joke(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse JOKE parameters."""
        return ParsedParams(
            tool_name="get_joke",
            params={},
            confidence=0.93,
            raw_entities=entities.to_dict(),
        )

    def _parse_quote(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse QUOTE parameters."""
        return ParsedParams(
            tool_name="get_quote",
            params={},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_coin_flip(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse COIN_FLIP parameters."""
        return ParsedParams(
            tool_name="flip_coin",
            params={},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_dice_roll(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse DICE_ROLL parameters."""
        sides = entities.get("sides", "6")
        return ParsedParams(
            tool_name="roll_dice",
            params={"sides": int(sides)},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_datetime(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse DATETIME parameters."""
        return ParsedParams(
            tool_name="get_datetime",
            params={},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_nasa_apod(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse NASA_APOD parameters."""
        return ParsedParams(
            tool_name="nasa_apod",
            params={},
            confidence=0.95,
            raw_entities=entities.to_dict(),
        )

    def _parse_nasa_mars(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse NASA_MARS parameters."""
        return ParsedParams(
            tool_name="nasa_mars_rover",
            params={"sol_or_latest": "latest"},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_iss_location(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse ISS_LOCATION parameters."""
        return ParsedParams(
            tool_name="nasa_iss",
            params={},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_stock_quote(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse STOCK_QUOTE parameters."""
        symbol = entities.get("symbol", "AAPL")
        return ParsedParams(
            tool_name="finnhub_quote",
            params={"symbol": symbol},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_random_fact(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse RANDOM_FACT parameters."""
        return ParsedParams(
            tool_name="random_fact",
            params={},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_ip_lookup(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse IP_LOOKUP parameters."""
        return ParsedParams(
            tool_name="ip_lookup",
            params={},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_nutrition_info(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse NUTRITION_INFO parameters."""
        query = entities.get("query", "")
        return ParsedParams(
            tool_name="nutrition_info",
            params={"query": query},
            confidence=0.85,
            raw_entities=entities.to_dict(),
        )

    def _parse_email_validate(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse EMAIL_VALIDATE parameters."""
        email = entities.get("email", "")
        return ParsedParams(
            tool_name="email_validate",
            params={"email": email},
            confidence=0.88,
            raw_entities=entities.to_dict(),
        )

    def _parse_exercises(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse EXERCISES parameters."""
        query = entities.get("query", "")
        return ParsedParams(
            tool_name="exercises",
            params={"query": query},
            confidence=0.85,
            raw_entities=entities.to_dict(),
        )

    def _parse_sentiment_analysis(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse SENTIMENT_ANALYSIS parameters."""
        text = entities.get("text", "")
        return ParsedParams(
            tool_name="sentiment_analysis",
            params={"text": text},
            confidence=0.82,
            raw_entities=entities.to_dict(),
        )

    def _parse_holidays(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse HOLIDAYS parameters."""
        country = entities.get("country", "IN")
        return ParsedParams(
            tool_name="global_holidays",
            params={"country_code": country},
            confidence=0.85,
            raw_entities=entities.to_dict(),
        )

    def _parse_plot_chart(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse PLOT_CHART parameters."""
        chart_type = entities.get("type", "bar")
        return ParsedParams(
            tool_name="plot_chart",
            params={"chart_type": chart_type, "title": "Chart", "labels": [], "values": []},
            confidence=0.80,
            raw_entities=entities.to_dict(),
        )

    def _parse_add_todo(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse ADD_TODO parameters."""
        task = entities.get("task", "")
        return ParsedParams(
            tool_name="memory_add_todo",
            params={"task": task},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_list_todos(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse LIST_TODOS parameters."""
        return ParsedParams(
            tool_name="memory_get_todos",
            params={},
            confidence=0.90,
            raw_entities=entities.to_dict(),
        )

    def _parse_add_note(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse ADD_NOTE parameters."""
        return ParsedParams(
            tool_name="memory_add_note",
            params={"title": "Quick Note", "content": entities.get("text", "")},
            confidence=0.88,
            raw_entities=entities.to_dict(),
        )

    def _parse_list_notes(self, entities: ExtractionResult, action: str | None = None) -> ParsedParams:
        """Parse LIST_NOTES parameters."""
        return ParsedParams(
            tool_name="memory_search_notes",
            params={"query": ""},
            confidence=0.88,
            raw_entities=entities.to_dict(),
        )


# Global instance
parameter_parser = ParameterParser()
