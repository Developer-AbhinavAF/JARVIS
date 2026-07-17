"""Parameter builder for JARVIS NLP engine.

Converts extracted entities into tool-ready parameters.
Each intent has its own parameter schema that defines what
parameters the tool expects and how to map entities to them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .utils import Entity, NLPOutput


# ════════════════════════════════════════════════════════════════════
# PARAMETER SCHEMAS
# ════════════════════════════════════════════════════════════════════

@dataclass
class ParamSchema:
    """Defines expected parameters for an intent."""
    params: list[str]                # Required parameter names
    optional_params: list[str] = field(default_factory=list)
    defaults: dict[str, Any] = field(default_factory=dict)
    entity_map: dict[str, str] = field(default_factory=dict)  # entity_name -> param_name


# Parameter schemas for each intent
PARAMETER_SCHEMAS: dict[str, ParamSchema] = {
    "OPEN_WEBSITE": ParamSchema(
        params=["target"],
        entity_map={"website": "target", "url": "url", "target": "target"},
    ),
    "OPEN_APP": ParamSchema(
        params=["target"],
        entity_map={"app": "target", "target": "target"},
    ),
    "CLOSE_APP": ParamSchema(
        params=["target"],
        entity_map={"app": "target", "target": "target"},
    ),
    "SEARCH_WEB": ParamSchema(
        params=["query"],
        entity_map={"query": "query"},
    ),
    "SEARCH_ON_PLATFORM": ParamSchema(
        params=["query", "platform"],
        entity_map={"query": "query", "platform": "platform"},
    ),
    "SEARCH_YOUTUBE": ParamSchema(
        params=["query"],
        entity_map={"query": "query"},
    ),
    "PLAY_MUSIC": ParamSchema(
        params=["query"],
        entity_map={"query": "query", "song": "query"},
    ),
    "PLAY_YOUTUBE": ParamSchema(
        params=["query"],
        entity_map={"query": "query", "song": "query"},
    ),
    "PLAY_SPOTIFY": ParamSchema(
        params=["query"],
        entity_map={"query": "query", "song": "query"},
    ),
    "GET_WEATHER": ParamSchema(
        params=["city"],
        optional_params=["country"],
        entity_map={"city": "city", "location": "city"},
    ),
    "GET_NEWS": ParamSchema(
        params=[],
        optional_params=["topic"],
        defaults={"topic": "latest news"},
        entity_map={"topic": "topic"},
    ),
    "SYSTEM_STATUS": ParamSchema(
        params=[],
        defaults={},
    ),
    "VOLUME_CONTROL": ParamSchema(
        params=["action"],
        optional_params=["value"],
        entity_map={"action": "action", "value": "value"},
    ),
    "BRIGHTNESS_CONTROL": ParamSchema(
        params=["action"],
        optional_params=["value"],
        entity_map={"action": "action", "value": "value"},
    ),
    "SCREENSHOT": ParamSchema(
        params=[],
    ),
    "SYSTEM_POWER": ParamSchema(
        params=["action"],
        entity_map={"power_action": "action", "action": "action"},
    ),
    "CLIPBOARD": ParamSchema(
        params=["action"],
        optional_params=["text"],
        defaults={"action": "get"},
        entity_map={"action": "action", "text": "text"},
    ),
    "CALCULATOR": ParamSchema(
        params=["expression"],
        entity_map={"expression": "expression"},
    ),
    "TIMER": ParamSchema(
        params=["seconds"],
        entity_map={"seconds": "seconds"},
    ),
    "DATETIME": ParamSchema(
        params=[],
    ),
    "SAVE_MEMORY": ParamSchema(
        params=["content"],
        entity_map={"content": "content", "text": "content", "query": "content", "target": "content"},
    ),
    "RECALL_MEMORY": ParamSchema(
        params=["query"],
        entity_map={"query": "query"},
    ),
    "WINDOW_CONTROL": ParamSchema(
        params=["action"],
        optional_params=["target"],
        entity_map={"action": "action", "target": "title"},
    ),
    "JOKE": ParamSchema(params=[]),
    "QUOTE": ParamSchema(params=[]),
    "FLIP_COIN": ParamSchema(params=[]),
    "DICE_ROLL": ParamSchema(
        params=[],
        optional_params=["sides"],
        defaults={"sides": 6},
        entity_map={"sides": "sides"},
    ),
    "NASA_APOD": ParamSchema(params=[]),
    "NASA_MARS": ParamSchema(params=[]),
    "ISS_LOCATION": ParamSchema(params=[]),
    "STOCK_QUOTE": ParamSchema(
        params=["symbol"],
        entity_map={"symbol": "symbol"},
    ),
    "RANDOM_FACT": ParamSchema(params=[]),
    "IP_LOOKUP": ParamSchema(params=[]),
    "ADD_TODO": ParamSchema(
        params=["task"],
        entity_map={"task": "task", "content": "task"},
    ),
    "LIST_TODOS": ParamSchema(params=[]),
    "ADD_NOTE": ParamSchema(
        params=[],
        optional_params=["content"],
        entity_map={"text": "content", "content": "content"},
    ),
    "GREETING": ParamSchema(params=[]),
    "WEB_SEARCH": ParamSchema(
        params=["query"],
        entity_map={"query": "query"},
    ),
    "OPEN_FOLDER": ParamSchema(
        params=["path"],
        entity_map={"path": "path", "folder": "path"},
    ),
    "FILE_MANAGEMENT": ParamSchema(
        params=["action"],
        optional_params=["path"],
        entity_map={"action": "action", "path": "path"},
    ),
}


# ════════════════════════════════════════════════════════════════════
# PARAMETER BUILDER
# ════════════════════════════════════════════════════════════════════

class ParameterBuilder:
    """Converts entities to tool-ready parameters.

    For each intent, uses the parameter schema to map extracted entities
    to the exact parameter names the tool expects.
    """

    def __init__(self) -> None:
        self._schemas = PARAMETER_SCHEMAS

    def build(
        self,
        intent: str,
        entities: dict[str, Entity],
        context: dict[str, Any] | None = None,
        text: str = "",
    ) -> dict[str, Any]:
        """Build tool parameters from entities.

        Args:
            intent: The classified intent
            entities: Extracted entities
            context: Conversation context for fallback values
            text: Original normalized text for fallback extraction

        Returns:
            Dict of parameter_name -> value
        """
        schema = self._schemas.get(intent)
        if not schema:
            return self._build_generic(entities, text)

        params = {}

        # Map entities to parameters using schema
        for entity_name, param_name in schema.entity_map.items():
            if entity_name in entities:
                entity = entities[entity_name]
                value = entity.value if isinstance(entity, Entity) else str(entity)
                params[param_name] = value

        # Apply defaults for missing required params
        for param_name in schema.params:
            if param_name not in params:
                # Try context fallback
                if context and param_name in context:
                    params[param_name] = context[param_name]
                elif param_name in schema.defaults:
                    params[param_name] = schema.defaults[param_name]
                elif text:
                    # Last resort: try to extract from raw text
                    extracted = self._extract_from_text(param_name, text)
                    if extracted:
                        params[param_name] = extracted

        # Apply optional param defaults
        for param_name in schema.optional_params:
            if param_name not in params and param_name in schema.defaults:
                params[param_name] = schema.defaults[param_name]

        return params

    def _build_generic(self, entities: dict[str, Entity], text: str) -> dict[str, Any]:
        """Build parameters for unknown intents."""
        params = {}
        for name, entity in entities.items():
            value = entity.value if isinstance(entity, Entity) else str(entity)
            params[name] = value
        if not params and text:
            params["query"] = text
        return params

    def _extract_from_text(self, param_name: str, text: str) -> str | None:
        """Try to extract a parameter from raw text as last resort."""
        if param_name == "query":
            # Remove common prefixes
            for prefix in [
                "search for ", "search ", "look up ", "find ", "google ",
                "what is ", "who is ", "how to ", "tell me about ", "explain ",
            ]:
                if text.startswith(prefix):
                    return text[len(prefix):]
            return text

        if param_name == "target":
            # After action verb, the rest is the target
            for prefix in [
                "open ", "launch ", "start ", "run ", "close ", "kill ",
                "fire up ", "bring up ",
            ]:
                if text.startswith(prefix):
                    return text[len(prefix):]
            return text

        if param_name == "expression":
            return text

        return None

    def get_schema(self, intent: str) -> ParamSchema | None:
        """Get parameter schema for an intent."""
        return self._schemas.get(intent)

    def validate_params(self, intent: str, params: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate that required parameters are present.

        Returns:
            (is_valid, list_of_missing_params)
        """
        schema = self._schemas.get(intent)
        if not schema:
            return True, []  # No schema = no validation

        missing = []
        for param in schema.params:
            if param not in params or not params[param]:
                missing.append(param)

        return len(missing) == 0, missing
