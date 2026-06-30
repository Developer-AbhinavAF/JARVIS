"""Entity extraction engine for JARVIS NLP.

Extracts structured entities from user input based on intent.
Strips command words and platform names automatically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from jarvis.intent_types import Intent


@dataclass
class ExtractedEntity:
    """Represents an extracted entity."""

    name: str
    value: str
    raw_value: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityExtractionResult:
    """Result of entity extraction."""

    intent: Intent
    entities: dict[str, ExtractedEntity] = field(default_factory=dict)
    raw_text: str = ""
    cleaned_text: str = ""

    def get_entity(self, name: str) -> ExtractedEntity | None:
        return self.entities.get(name)

    def get_primary_query(self) -> str:
        for key in ["query", "song", "location", "topic", "symbol", "file", "website", "content"]:
            if entity := self.entities.get(key):
                return entity.value
        return ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.name,
            "entities": {
                key: {
                    "value": entity.value,
                    "raw_value": entity.raw_value,
                    "confidence": entity.confidence,
                    "metadata": entity.metadata,
                }
                for key, entity in self.entities.items()
            },
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
        }


class CommandWordStripper:
    """Removes command and connector words from user text."""

    COMMAND_PREFIXES = [
        "what do you know about",
        "do you know",
        "look for",
        "search for",
        "find me",
        "go to",
        "what is",
        "how to",
        "how do i",
        "tell me",
        "latest",
        "current",
        "search",
        "find",
        "look",
        "google",
        "play",
        "watch",
        "start",
        "open",
        "launch",
        "visit",
        "show",
        "display",
        "tell",
        "give",
        "weather",
        "news",
        "analyze",
        "describe",
        "read",
        "summarize",
        "save",
        "remember",
        "store",
        "keep",
        "add",
        "recall",
        "learn",
        "study",
        "process",
    ]

    TRAILING_CONNECTORS = [
        "on youtube",
        "on yt",
        "on spotify",
        "on google",
        "on wikipedia",
        "on github",
        "for me",
        "to memory",
        "for later",
    ]

    @classmethod
    def strip_command_words(cls, text: str) -> str:
        cleaned = text.strip()
        for prefix in sorted(cls.COMMAND_PREFIXES, key=len, reverse=True):
            pattern = rf"^{re.escape(prefix)}\s+"
            updated = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            if updated != cleaned:
                cleaned = updated.strip()
                break
        return cleaned

    @classmethod
    def strip_platform_names(cls, text: str) -> str:
        cleaned = text.strip()
        for suffix in sorted(cls.TRAILING_CONNECTORS, key=len, reverse=True):
            cleaned = re.sub(rf"\s+{re.escape(suffix)}$", "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(
            r"\s+(?:on|from|at|in|for|of)\s+(?:youtube|yt|spotify|google|wikipedia|github)(?:\s+|$)",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def clean_text(cls, text: str) -> str:
        return cls.strip_platform_names(cls.strip_command_words(text))


class EntityExtractor:
    """Extracts entities from user input based on intent."""

    def extract(self, text: str, intent: Intent) -> EntityExtractionResult:
        raw_text = text.strip()
        result = EntityExtractionResult(
            intent=intent,
            raw_text=raw_text,
            cleaned_text=raw_text,
        )

        extractor_method = getattr(self, f"_extract_{intent.name.lower()}", None)
        if extractor_method:
            extractor_method(raw_text, result)
        else:
            self._extract_generic(raw_text, result)

        return result

    def _set_entity(
        self,
        result: EntityExtractionResult,
        name: str,
        value: str,
        raw_value: str,
        confidence: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        result.entities[name] = ExtractedEntity(
            name=name,
            value=value.strip(),
            raw_value=raw_value,
            confidence=confidence,
            metadata=metadata or {},
        )
        result.cleaned_text = value.strip()

    def _extract_generic(self, text: str, result: EntityExtractionResult) -> None:
        cleaned = CommandWordStripper.clean_text(text)
        if cleaned:
            self._set_entity(result, "query", cleaned, text, 0.8)

    def _extract_open_website(self, text: str, result: EntityExtractionResult) -> None:
        websites = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "github": "https://github.com",
            "spotify": "https://spotify.com",
            "netflix": "https://netflix.com",
            "amazon": "https://amazon.com",
            "linkedin": "https://linkedin.com",
            "reddit": "https://reddit.com",
            "twitter": "https://x.com",
            "instagram": "https://instagram.com",
            "facebook": "https://facebook.com",
            "wikipedia": "https://wikipedia.org",
        }
        text_lower = text.lower()
        for site_name, url in websites.items():
            if site_name in text_lower:
                self._set_entity(result, "website", site_name, text, 0.95, {"url": url})
                return
        self._extract_generic(text, result)

    def _extract_search_youtube(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(?:search|find|look\s+for)?\s*(.+?)\s+on\s+(?:youtube|yt)\s*$", text, re.IGNORECASE)
        query = match.group(1).strip() if match else CommandWordStripper.clean_text(text)
        if query:
            self._set_entity(result, "query", query, text, 0.95)

    def _extract_search_web(self, text: str, result: EntityExtractionResult) -> None:
        cleaned = CommandWordStripper.clean_text(text)
        if cleaned:
            self._set_entity(result, "query", cleaned, text, 0.9)

    def _extract_search_wikipedia(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(?:search|find|look\s+for)?\s*(.+?)\s+on\s+wikipedia\s*$", text, re.IGNORECASE)
        query = match.group(1).strip() if match else CommandWordStripper.clean_text(text)
        if query:
            self._set_entity(result, "query", query, text, 0.92)

    def _extract_search_github(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(?:search|find)?\s*(.+?)\s+on\s+github\s*$", text, re.IGNORECASE)
        query = match.group(1).strip() if match else CommandWordStripper.clean_text(text)
        if query:
            self._set_entity(result, "query", query, text, 0.92)

    def _extract_play_youtube(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"^(?:play|watch|start)?\s*(.+?)(?:\s+on\s+youtube)?\s*$", text, re.IGNORECASE)
        query = match.group(1).strip() if match else CommandWordStripper.clean_text(text)
        if query:
            self._set_entity(result, "song", query, text, 0.93)

    def _extract_play_spotify(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(?:play)?\s*(.+?)\s+on\s+spotify\s*$", text, re.IGNORECASE)
        song = match.group(1).strip() if match else CommandWordStripper.clean_text(text)
        if song:
            self._set_entity(result, "song", song, text, 0.94)

    def _extract_get_weather(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(?:weather|forecast)\s+(?:in|at|for|of)\s+(.+?)(?:\s+now|\s+today|$)", text, re.IGNORECASE)
        location = match.group(1).strip() if match else CommandWordStripper.clean_text(text)
        if location:
            self._set_entity(result, "location", location, text, 0.96)

    def _extract_get_news(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(?:news|headlines)(?:\s+(?:about|on|in|regarding)\s+(.+))?", text, re.IGNORECASE)
        topic = match.group(1).strip() if match and match.group(1) else "latest news"
        self._set_entity(result, "topic", topic, text, 0.9 if topic != "latest news" else 0.75)

    def _extract_get_stock(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(?:stock\s+)?price\s+(?:of\s+)?([A-Za-z]{1,10})", text, re.IGNORECASE)
        if not match:
            match = re.search(r"\b([A-Za-z]{1,10})\b(?=\s+(?:stock|price|ticker))", text, re.IGNORECASE)
        symbol = match.group(1).upper() if match else CommandWordStripper.clean_text(text).upper()
        if symbol:
            self._set_entity(result, "symbol", symbol, text, 0.92)

    def _extract_get_crypto(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(?:crypto|coin|token|price)\s+(?:for|of)?\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
        if not match:
            match = re.search(r"^([A-Za-z0-9_-]+)\s+(?:crypto|coin)\s+price", text, re.IGNORECASE)
        coin = match.group(1).lower() if match else CommandWordStripper.clean_text(text).lower()
        if coin:
            self._set_entity(result, "symbol", coin, text, 0.9)

    def _extract_get_nasa_apod(self, text: str, result: EntityExtractionResult) -> None:
        self._set_entity(result, "topic", "nasa apod", text, 0.98)

    def _extract_read_document(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(.+\.(?:pdf|doc|docx|txt|md))", text, re.IGNORECASE)
        file_name = match.group(1).strip() if match else CommandWordStripper.clean_text(text)
        if file_name:
            self._set_entity(result, "file", file_name, text, 0.94)

    def _extract_analyze_image(self, text: str, result: EntityExtractionResult) -> None:
        match = re.search(r"(.+\.(?:png|jpg|jpeg|gif|webp))", text, re.IGNORECASE)
        file_name = match.group(1).strip() if match else CommandWordStripper.clean_text(text)
        if file_name:
            self._set_entity(result, "file", file_name, text, 0.94)

    def _extract_save_memory(self, text: str, result: EntityExtractionResult) -> None:
        cleaned = CommandWordStripper.clean_text(text)
        content = cleaned or text.strip()
        self._set_entity(result, "content", content, text, 0.9)

    def _extract_recall_memory(self, text: str, result: EntityExtractionResult) -> None:
        cleaned = CommandWordStripper.clean_text(text)
        topic = cleaned or text.strip()
        self._set_entity(result, "topic", topic, text, 0.88)

    def _extract_learn(self, text: str, result: EntityExtractionResult) -> None:
        cleaned = CommandWordStripper.clean_text(text)
        content = cleaned or text.strip()
        self._set_entity(result, "content", content, text, 0.88)

    def _extract_chat(self, text: str, result: EntityExtractionResult) -> None:
        self._extract_generic(text, result)


entity_extractor = EntityExtractor()


def extract_entities(text: str, intent: Intent) -> EntityExtractionResult:
    """Convenience wrapper for entity extraction."""

    return entity_extractor.extract(text, intent)
