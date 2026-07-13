"""Entity extraction for JARVIS NLP pipeline.

Extracts structured entities (query, target, platform, etc.) from user input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .synonyms import resolve_platform, resolve_app


@dataclass
class Entity:
    """A single extracted entity."""
    name: str
    value: str
    raw_value: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Result of entity extraction."""
    entities: dict[str, Entity] = field(default_factory=dict)
    raw_text: str = ""
    cleaned_text: str = ""

    def get(self, name: str, default: str | None = None) -> str | None:
        """Get entity value by name."""
        entity = self.entities.get(name)
        return entity.value if entity else default

    def has(self, name: str) -> bool:
        """Check if entity exists."""
        return name in self.entities

    def to_dict(self) -> dict[str, Any]:
        """Convert to plain dict."""
        return {
            name: {
                "value": e.value,
                "raw": e.raw_value,
                "confidence": e.confidence,
                "meta": e.metadata,
            }
            for name, e in self.entities.items()
        }


class EntityExtractor:
    """Extracts entities from user input based on intent patterns."""

    # Known website → URL mapping
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
        "x.com": "https://x.com",
        "instagram": "https://instagram.com",
        "facebook": "https://facebook.com",
        "netflix": "https://netflix.com",
        "spotify": "https://open.spotify.com",
        "amazon": "https://amazon.com",
        "linkedin": "https://linkedin.com",
        "whatsapp": "https://web.whatsapp.com",
        "wikipedia": "https://wikipedia.org",
        "chatgpt": "https://chatgpt.com",
        "claude": "https://claude.ai",
        "discord": "https://discord.com",
        "twitch": "https://twitch.tv",
    }

    # Known apps → process names
    APPS: dict[str, str] = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "mozilla firefox": "firefox.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "vscode": "code.exe",
        "vs code": "code.exe",
        "visual studio code": "code.exe",
        "cursor": "cursor.exe",
        "discord": "Discord.exe",
        "steam": "steam.exe",
        "spotify": "Spotify.exe",
        "whatsapp": "WhatsApp.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "settings": "ms-settings:",
        "control panel": "control.exe",
        "task manager": "taskmgr.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "terminal": "wt.exe",
        "calculator": "calc.exe",
        "notepad": "notepad.exe",
        "paint": "mspaint.exe",
        "obs": "obs64.exe",
        "obs studio": "obs64.exe",
        "word": "winword.exe",
        "microsoft word": "winword.exe",
        "excel": "excel.exe",
        "microsoft excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "microsoft powerpoint": "powerpnt.exe",
        "outlook": "outlook.exe",
        "teams": "teams.exe",
        "microsoft teams": "teams.exe",
        "zoom": "zoom.exe",
        "slack": "slack.exe",
        "skype": "skype.exe",
        "vlc": "vlc.exe",
        "telegram": "Telegram.exe",
        "sublime": "sublime_text.exe",
        "sublime text": "sublime_text.exe",
        "notepad++": "notepad++.exe",
        "snipping tool": "SnippingTool.exe",
        "wordpad": "wordpad.exe",
        "onenote": "onenote.exe",
    }

    def extract(self, text: str, intent: str, match: re.Match | None = None) -> ExtractionResult:
        """Extract entities from text based on intent.

        Args:
            text: Normalized user input
            intent: Classified intent
            match: Regex match object from pattern matching

        Returns:
            ExtractionResult with extracted entities
        """
        result = ExtractionResult(raw_text=text, cleaned_text=text)

        # Extract from regex match groups first
        if match:
            self._extract_from_match(match, result)

        # Intent-specific extraction
        extractor = getattr(self, f"_extract_{intent.lower()}", None)
        if extractor:
            extractor(text, result)
        else:
            self._extract_generic(text, result)

        return result

    def _extract_from_match(self, match: re.Match, result: ExtractionResult) -> None:
        """Extract entities from regex named groups."""
        try:
            groups = match.groupdict()
            for name, value in groups.items():
                if value is not None and value.strip():
                    result.entities[name] = Entity(
                        name=name,
                        value=value.strip(),
                        raw_value=value,
                        confidence=0.95,
                    )
        except Exception:
            pass

    def _extract_generic(self, text: str, result: ExtractionResult) -> None:
        """Generic entity extraction."""
        if not result.has("query"):
            # Try to extract query by removing common prefixes
            query = text
            for prefix in [
                "search for ", "search ", "look up ", "find ", "google ",
                "tell me about ", "what is ", "who is ", "how to ", "explain ",
            ]:
                if query.startswith(prefix):
                    query = query[len(prefix):]
                    break
            if query.strip():
                result.entities["query"] = Entity(
                    name="query",
                    value=query.strip(),
                    raw_value=text,
                    confidence=0.85,
                )

    def _extract_open_website(self, text: str, result: ExtractionResult) -> None:
        """Extract website entities for OPEN_WEBSITE intent."""
        target = result.get("target")
        if target:
            # Resolve platform name
            canonical = resolve_platform(target) or target.lower()
            url = self.WEBSITES.get(canonical)
            if url:
                result.entities["website"] = Entity(
                    name="website",
                    value=canonical,
                    raw_value=target,
                    confidence=0.95,
                    metadata={"url": url},
                )
                result.entities["url"] = Entity(
                    name="url",
                    value=url,
                    raw_value=target,
                    confidence=0.95,
                )
                return

        # Check for URL
        url = result.get("url")
        if url:
            result.entities["website"] = Entity(
                name="website",
                value=url,
                raw_value=url,
                confidence=0.95,
                metadata={"url": url},
            )

    def _extract_open_app(self, text: str, result: ExtractionResult) -> None:
        """Extract application entities for OPEN_APP intent."""
        target = result.get("target")
        if target:
            canonical = resolve_app(target) or target.lower()
            process = self.APPS.get(canonical)
            if process:
                result.entities["app"] = Entity(
                    name="app",
                    value=canonical,
                    raw_value=target,
                    confidence=0.95,
                    metadata={"process": process},
                )
            else:
                result.entities["app"] = Entity(
                    name="app",
                    value=canonical,
                    raw_value=target,
                    confidence=0.85,
                )

    def _extract_close_app(self, text: str, result: ExtractionResult) -> None:
        """Extract application entities for CLOSE_APP intent."""
        target = result.get("target")
        if target:
            canonical = resolve_app(target) or target.lower()
            result.entities["app"] = Entity(
                name="app",
                value=canonical,
                raw_value=target,
                confidence=0.90,
            )

    def _extract_search_youtube(self, text: str, result: ExtractionResult) -> None:
        """Extract search query for YouTube search."""
        query = result.get("query")
        if query:
            result.entities["query"] = Entity(
                name="query",
                value=query,
                raw_value=query,
                confidence=0.95,
            )

    def _extract_search_on_platform(self, text: str, result: ExtractionResult) -> None:
        """Extract search query and platform for platform-specific search."""
        query = result.get("query")
        platform = result.get("platform")
        if query:
            result.entities["query"] = Entity(
                name="query",
                value=query,
                raw_value=query,
                confidence=0.93,
            )
        if platform:
            canonical = resolve_platform(platform) or platform.lower()
            result.entities["platform"] = Entity(
                name="platform",
                value=canonical,
                raw_value=platform,
                confidence=0.93,
            )

    def _extract_search_web(self, text: str, result: ExtractionResult) -> None:
        """Extract search query for web search."""
        query = result.get("query")
        if not query:
            # Fallback: try to extract query from text
            query = text
            for prefix in [
                "search for ", "search ", "look up ", "find ", "google ",
                "tell me about ", "what is ", "who is ", "how to ", "explain ",
                "what are ", "how do ", "why is ", "why does ",
            ]:
                if query.startswith(prefix):
                    query = query[len(prefix):]
                    break
        if query and query.strip():
            result.entities["query"] = Entity(
                name="query",
                value=query.strip(),
                raw_value=text,
                confidence=0.90,
            )

    def _extract_play_youtube(self, text: str, result: ExtractionResult) -> None:
        """Extract song/video query for YouTube play."""
        query = result.get("query")
        if query:
            result.entities["query"] = Entity(
                name="query",
                value=query,
                raw_value=query,
                confidence=0.92,
            )

    def _extract_play_spotify(self, text: str, result: ExtractionResult) -> None:
        """Extract song query for Spotify play."""
        query = result.get("query")
        if query:
            result.entities["query"] = Entity(
                name="query",
                value=query,
                raw_value=query,
                confidence=0.92,
            )

    def _extract_play_music(self, text: str, result: ExtractionResult) -> None:
        """Extract song query for generic music play."""
        query = result.get("query")
        if query:
            result.entities["query"] = Entity(
                name="query",
                value=query,
                raw_value=query,
                confidence=0.88,
            )

    def _extract_get_weather(self, text: str, result: ExtractionResult) -> None:
        """Extract city for weather lookup."""
        city = result.get("city")
        if city:
            result.entities["city"] = Entity(
                name="city",
                value=city,
                raw_value=city,
                confidence=0.95,
            )
        else:
            # Fallback
            city_match = re.search(r"(?:weather|forecast|temperature)\s+(?:in|at|for|of)\s+(.+?)(?:\s+now|\s+today|\s*$)", text)
            if city_match:
                result.entities["city"] = Entity(
                    name="city",
                    value=city_match.group(1).strip(),
                    raw_value=city_match.group(1).strip(),
                    confidence=0.90,
                )

    def _extract_get_news(self, text: str, result: ExtractionResult) -> None:
        """Extract topic for news lookup."""
        topic = result.get("topic")
        if topic:
            result.entities["topic"] = Entity(
                name="topic",
                value=topic,
                raw_value=topic,
                confidence=0.90,
            )
        else:
            result.entities["topic"] = Entity(
                name="topic",
                value="latest news",
                raw_value=text,
                confidence=0.75,
            )

    def _extract_system_power(self, text: str, result: ExtractionResult) -> None:
        """Extract power action."""
        action = None
        if "shutdown" in text or "shut down" in text or "power off" in text:
            action = "shutdown"
        elif "restart" in text or "reboot" in text:
            action = "restart"
        elif "sleep" in text or "hibernate" in text:
            action = "sleep"
        elif "lock" in text:
            action = "lock"
        elif "logout" in text or "log out" in text:
            action = "logout"
        elif "cancel" in text:
            action = "cancel"

        if action:
            result.entities["power_action"] = Entity(
                name="power_action",
                value=action,
                raw_value=text,
                confidence=0.95,
            )

    def _extract_volume_control(self, text: str, result: ExtractionResult) -> None:
        """Extract volume action and value."""
        action = None
        if "up" in text or "increase" in text or "raise" in text or "louder" in text:
            action = "up"
        elif "down" in text or "decrease" in text or "lower" in text or "softer" in text:
            action = "down"
        elif "mute" in text or "silence" in text:
            action = "mute"
        elif "unmute" in text or "unsilence" in text:
            action = "unmute"

        value_match = re.search(r"(\d+)", text)
        value = int(value_match.group(1)) if value_match else None

        if action:
            result.entities["action"] = Entity(name="action", value=action, raw_value=text, confidence=0.95)
        if value is not None:
            result.entities["value"] = Entity(name="value", value=str(value), raw_value=text, confidence=0.90)

    def _extract_brightness_control(self, text: str, result: ExtractionResult) -> None:
        """Extract brightness action and value."""
        action = None
        if "up" in text or "increase" in text or "raise" in text or "brighter" in text:
            action = "up"
        elif "down" in text or "decrease" in text or "lower" in text or "dimmer" in text:
            action = "down"

        value_match = re.search(r"(\d+)", text)
        value = int(value_match.group(1)) if value_match else None

        if action:
            result.entities["action"] = Entity(name="action", value=action, raw_value=text, confidence=0.93)
        if value is not None:
            result.entities["value"] = Entity(name="value", value=str(value), raw_value=text, confidence=0.90)

    def _extract_calculator(self, text: str, result: ExtractionResult) -> None:
        """Extract mathematical expression."""
        expression = result.get("expression")
        if not expression:
            expression = text
            for prefix in ["calculate ", "calc ", "compute ", "solve ", "evaluate ", "what is ", "what's "]:
                if expression.startswith(prefix):
                    expression = expression[len(prefix):]
                    break
        if expression:
            # Clean expression
            expression = expression.replace("x", "*").replace("×", "*").replace("÷", "/")
            result.entities["expression"] = Entity(
                name="expression",
                value=expression.strip(),
                raw_value=text,
                confidence=0.92,
            )

    def _extract_timer(self, text: str, result: ExtractionResult) -> None:
        """Extract timer duration."""
        seconds = result.get("seconds")
        if seconds:
            # Parse to seconds
            num = int(re.search(r"(\d+)", seconds).group(1)) if re.search(r"(\d+)", seconds) else 30
            if "minute" in seconds or "min" in seconds:
                num *= 60
            elif "hour" in seconds or "hr" in seconds:
                num *= 3600
            result.entities["seconds"] = Entity(
                name="seconds",
                value=str(num),
                raw_value=seconds,
                confidence=0.93,
            )
        else:
            num_match = re.search(r"(\d+)", text)
            if num_match:
                num = int(num_match.group(1))
                if "minute" in text or "min" in text:
                    num *= 60
                elif "hour" in text or "hr" in text:
                    num *= 3600
                result.entities["seconds"] = Entity(
                    name="seconds",
                    value=str(num),
                    raw_value=text,
                    confidence=0.90,
                )

    def _extract_save_memory(self, text: str, result: ExtractionResult) -> None:
        """Extract content to save to memory."""
        content = text
        for prefix in ["remember ", "save ", "store ", "keep ", "note "]:
            if content.startswith(prefix):
                content = content[len(prefix):]
                break
        for suffix in [" this", " that", " to memory", " for me", " for later"]:
            if content.endswith(suffix):
                content = content[:-len(suffix)]
                break
        if content.strip():
            result.entities["content"] = Entity(
                name="content",
                value=content.strip(),
                raw_value=text,
                confidence=0.94,
            )

    def _extract_recall_memory(self, text: str, result: ExtractionResult) -> None:
        """Extract query for memory recall."""
        query = result.get("query")
        if not query:
            query = text
            for prefix in [
                "recall ", "what do you know about ", "what do i know about ",
                "tell me about ", "search memory ", "find in memory ",
            ]:
                if query.startswith(prefix):
                    query = query[len(prefix):]
                    break
        if query and query.strip():
            result.entities["query"] = Entity(
                name="query",
                value=query.strip(),
                raw_value=text,
                confidence=0.88,
            )

    def _extract_stock_quote(self, text: str, result: ExtractionResult) -> None:
        """Extract stock symbol."""
        symbol = result.get("symbol")
        if not symbol:
            symbol_match = re.search(r"(?:stock|share|price|quote)\s+(?:price|of|for|info)?\s*(\w+)", text)
            if symbol_match:
                symbol = symbol_match.group(1)
            else:
                words = text.split()
                for w in reversed(words):
                    if w.isalpha() and len(w) <= 5:
                        symbol = w
                        break
        if symbol:
            result.entities["symbol"] = Entity(
                name="symbol",
                value=symbol.upper(),
                raw_value=symbol,
                confidence=0.90,
            )

    def _extract_type_text(self, text: str, result: ExtractionResult) -> None:
        """Extract text to type."""
        text_to_type = result.get("text")
        if not text_to_type:
            text_to_type = text
            for prefix in ["type ", "write ", "enter ", "input "]:
                if text_to_type.startswith(prefix):
                    text_to_type = text_to_type[len(prefix):]
                    break
        if text_to_type and text_to_type.strip():
            result.entities["text"] = Entity(
                name="text",
                value=text_to_type.strip().strip("'\""),
                raw_value=text,
                confidence=0.88,
            )

    def _extract_clipboard(self, text: str, result: ExtractionResult) -> None:
        """Extract clipboard action."""
        action = None
        if "copy" in text:
            action = "copy"
        elif "paste" in text or "get" in text or "show" in text or "read" in text or "what" in text:
            action = "get"
        elif "clear" in text or "empty" in text:
            action = "clear"
        else:
            action = "get"

        result.entities["action"] = Entity(
            name="action",
            value=action,
            raw_value=text,
            confidence=0.90,
        )

        if action == "copy":
            # Extract text to copy
            copy_text = re.search(r"copy\s+['\"]?(.+?)['\"]?\s*(?:to|on|clipboard)?\s*$", text)
            if copy_text:
                result.entities["text"] = Entity(
                    name="text",
                    value=copy_text.group(1).strip(),
                    raw_value=text,
                    confidence=0.85,
                )


# Global instance
entity_extractor = EntityExtractor()
