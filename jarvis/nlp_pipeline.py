"""Fast multi-stage NLP pipeline for local JARVIS intent handling."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class NLPResult:
    raw_text: str
    normalized_text: str
    intent: str
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    conversation_state: dict[str, Any] = field(default_factory=dict)
    action: str | None = None
    memory_relevance: float = 0.0
    should_remember: bool = False


class ConversationStateTracker:
    """Small in-memory state tracker for conversational references."""

    def __init__(self) -> None:
        self.last_intent: str | None = None
        self.last_entities: dict[str, Any] = {}
        self.last_topic: str | None = None
        self.updated_at: str | None = None

    def update(self, result: NLPResult) -> None:
        self.last_intent = result.intent
        self.last_entities = result.entities
        self.last_topic = result.entities.get("topic") or result.entities.get("query") or self.last_topic
        self.updated_at = datetime.now().isoformat()

    def snapshot(self) -> dict[str, Any]:
        return {
            "last_intent": self.last_intent,
            "last_entities": self.last_entities,
            "last_topic": self.last_topic,
            "updated_at": self.updated_at,
        }


class AdvancedNLPPipeline:
    """Intent, entity, context, action, and memory relevance detector."""

    def __init__(self) -> None:
        self.state = ConversationStateTracker()
        self.intent_patterns: list[tuple[str, float, list[str]]] = [
            ("open_website", 0.93, [
                r"\b(open|launch|go to|visit)\s+(youtube|google|gmail|github|spotify|netflix)\b",
                r"\b(can you|please|could you)\s+(open|launch|go to|visit)\s+(youtube|google|gmail|github|spotify|netflix)\b",
            ]),
            ("open_app", 0.91, [
                r"\b(open|launch|start|run)\s+(?:the\s+)?(?:app\s+)?([a-z0-9_ .-]+)\b",
            ]),
            ("youtube_play", 0.9, [
                r"\b(play|watch|show)\b.*\b(youtube|video|lecture)\b",
                r"\bi want to watch\b.*\b(video|lecture)\b",
            ]),
            ("web_search", 0.84, [
                r"\b(search|look up|find|google)\b",
                r"\bwhat is\b|\bwho is\b|\bhow to\b|\bwhy does\b",
            ]),
            ("system_status", 0.88, [
                r"\b(system status|system stats|computer status|cpu usage|memory usage|ram usage)\b",
            ]),
            ("daily_briefing", 0.88, [
                r"\b(daily briefing|morning briefing|brief me|start my day)\b",
            ]),
            ("screenshot", 0.9, [
                r"\b(take|capture|grab)\s+(?:a\s+)?screenshot\b",
            ]),
            ("calculator", 0.9, [
                r"\b(calculate|calc|compute)\b",
                r"^(?:what is\s+)?[0-9\s()+\-*/x÷.]+$",
            ]),
            ("weather", 0.86, [
                r"\b(weather|forecast|temperature)\b",
            ]),
            ("joke", 0.85, [
                r"\b(tell me a joke|make me laugh|joke)\b",
            ]),
            ("quote", 0.85, [
                r"\b(inspirational quote|motivat(e|ional) me|quote of the day|give me a quote)\b",
            ]),
            ("remember", 0.94, [
                r"\b(remember this|remember that|learn this|save this|save this for later|this is important)\b",
            ]),
            ("file_manage", 0.78, [
                r"\b(create|delete|move|copy|rename|find)\b.*\b(file|folder|document)\b",
            ]),
            ("automation", 0.78, [
                r"\b(automate|workflow|routine|schedule|run in background)\b",
            ]),
            ("chat", 0.55, [r".+"]),
        ]

    def process(self, text: str) -> NLPResult:
        normalized = self._normalize(text)
        intent, confidence = self._classify_intent(normalized)
        entities = self._extract_entities(normalized, intent)
        context = self._understand_context(normalized, entities)
        action = self._detect_action(intent, entities)
        memory_relevance = self._memory_relevance(normalized, intent)

        result = NLPResult(
            raw_text=text,
            normalized_text=normalized,
            intent=intent,
            confidence=confidence,
            entities=entities,
            context=context,
            conversation_state=self.state.snapshot(),
            action=action,
            memory_relevance=memory_relevance,
            should_remember=memory_relevance >= 0.7 or intent == "remember",
        )
        self.state.update(result)
        return result

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    def _classify_intent(self, text: str) -> tuple[str, float]:
        for intent, confidence, patterns in self.intent_patterns:
            for pattern in patterns:
                if re.search(pattern, text):
                    return intent, confidence
        return "chat", 0.5

    def _extract_entities(self, text: str, intent: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}

        url_match = re.search(r"https?://[^\s]+", text)
        if url_match:
            entities["url"] = url_match.group(0)

        known_sites = ["youtube", "google", "gmail", "github", "spotify", "netflix"]
        for site in known_sites:
            if re.search(rf"\b{site}\b", text):
                entities["site"] = site
                break

        app_match = re.search(r"\b(?:open|launch|start|run)\s+(?:the\s+)?(?:app\s+)?([a-z0-9_ .-]+)$", text)
        if app_match:
            entities["app"] = app_match.group(1).strip()

        if intent == "youtube_play":
            query = text
            for phrase in ["play", "watch", "show", "on youtube", "youtube", "i want to watch"]:
                query = query.replace(phrase, " ")
            entities["query"] = re.sub(r"\s+", " ", query).strip() or "video"
            entities["site"] = "youtube"

        if intent == "calculator":
            expression = text
            for phrase in ["calculate", "calc", "compute", "what is"]:
                expression = re.sub(rf"^\s*{re.escape(phrase)}\s+", "", expression).strip()
            entities["expression"] = expression.replace("x", "*").replace("÷", "/")

        weather_match = re.search(r"\b(?:weather|forecast|temperature)\s+(?:in|at|for)\s+(.+)$", text)
        if weather_match:
            entities["location"] = weather_match.group(1).strip()

        if intent == "web_search" and "query" not in entities:
            query = text
            for prefix in ["search for", "search", "look up", "find", "google"]:
                if query.startswith(prefix):
                    query = query[len(prefix):].strip()
            entities["query"] = query

        topic_match = re.search(r"\b(?:about|on|regarding)\s+(.+)$", text)
        if topic_match:
            entities["topic"] = topic_match.group(1).strip()

        if re.search(r"\b(it|that|this|same|again)\b", text):
            entities["has_reference"] = True
            if self.state.last_topic:
                entities["resolved_reference"] = self.state.last_topic

        return entities

    def _understand_context(self, text: str, entities: dict[str, Any]) -> dict[str, Any]:
        return {
            "is_follow_up": bool(entities.get("has_reference")),
            "resolved_topic": entities.get("resolved_reference") or entities.get("topic") or entities.get("query"),
            "is_incomplete_command": text in {"open", "play", "search", "remember"},
        }

    def _detect_action(self, intent: str, entities: dict[str, Any]) -> str | None:
        if intent == "open_website" and entities.get("site") == "youtube":
            return "ACTION:OPEN_YOUTUBE"
        if intent == "open_website" and entities.get("site") == "google":
            return "ACTION:OPEN_WEBSITE|https://google.com"
        if intent == "open_app" and entities.get("app"):
            return f"ACTION:OPEN_APP|{entities['app']}"
        if intent == "youtube_play":
            query = entities.get("query", "video")
            return f"ACTION:OPEN_WEBSITE|https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        if intent == "web_search" and entities.get("query"):
            return f"ACTION:SEARCH_WEB|{entities['query']}"
        return None

    def _memory_relevance(self, text: str, intent: str) -> float:
        if intent == "remember":
            return 0.95

        high_value = [
            "i prefer",
            "my preference",
            "my project",
            "important",
            "always",
            "never",
            "my goal",
            "i am learning",
            "correction",
            "actually",
        ]
        low_value = ["hello", "hi", "thanks", "thank you", "ok", "lol", "good morning"]

        if text in low_value or len(text) < 12:
            return 0.05
        if any(marker in text for marker in high_value):
            return 0.78
        if len(text.split()) > 28:
            return 0.45
        return 0.2


nlp_pipeline = AdvancedNLPPipeline()
