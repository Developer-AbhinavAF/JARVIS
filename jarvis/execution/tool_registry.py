"""Tool Registry — Every tool registers itself.

If a tool is not registered, it cannot be executed.
Each tool has: name, description, parameters, execute fn, verify fn.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    APP = "app"
    FILE = "file"
    WEB = "web"
    SYSTEM = "system"
    SEARCH = "search"
    MEMORY = "memory"
    MEDIA = "media"
    VISION = "vision"
    COMMUNICATION = "communication"
    UNKNOWN = "unknown"


@dataclass
class ToolResult:
    """Standardized tool execution result."""
    success: bool = False
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    execution_time_ms: float = 0.0
    tool_name: str = ""
    verified: bool = False
    verification_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": round(self.execution_time_ms, 1),
            "tool_name": self.tool_name,
            "verified": self.verified,
            "verification_time_ms": round(self.verification_time_ms, 1),
        }


@dataclass
class ToolDef:
    """Definition of a registered tool."""
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.UNKNOWN
    parameters: dict[str, str] = field(default_factory=dict)  # param_name -> type description
    execute: Callable[..., Any] | None = None
    verify: Callable[..., bool] | None = None
    priority: int = 50
    enabled: bool = True
    timeout_seconds: float = 10.0
    requires_confirmation: bool = False

    def matches_intent(self, intent: str, entities: dict[str, Any] | None = None) -> float:
        """Score how well this tool matches a given intent. 0.0-1.0."""
        intent_lower = intent.lower().replace("_", " ").replace("-", " ")
        name_lower = self.name.lower().replace("_", " ").replace("-", " ")

        # Direct name match
        if name_lower in intent_lower or intent_lower in name_lower:
            return 1.0

        # Word overlap
        name_words = set(name_lower.split())
        intent_words = set(intent_lower.split())
        if name_words and intent_words:
            overlap = len(name_words & intent_words)
            if overlap > 0:
                return 0.5 + (overlap / max(len(name_words), len(intent_words))) * 0.5

        # Description match
        desc_words = set(self.description.lower().split())
        if desc_words and intent_words:
            overlap = len(desc_words & intent_words)
            if overlap > 0:
                return 0.3 + (overlap / max(len(desc_words), len(intent_words))) * 0.4

        return 0.0


class ToolRegistry:
    """Central registry of all tools.

    Usage:
        registry = ToolRegistry()
        registry.register("open_chrome", open_chrome_fn, verify=verify_chrome_fn)
        tool = registry.get("open_chrome")
        results = registry.find_tools("open youtube")
    """

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        execute: Callable[..., Any],
        description: str = "",
        category: ToolCategory = ToolCategory.UNKNOWN,
        parameters: dict[str, str] | None = None,
        verify: Callable[..., bool] | None = None,
        priority: int = 50,
        enabled: bool = True,
        timeout_seconds: float = 10.0,
        requires_confirmation: bool = False,
    ):
        with self._lock:
            self._tools[name] = ToolDef(
                name=name,
                description=description,
                category=category,
                parameters=parameters or {},
                execute=execute,
                verify=verify,
                priority=priority,
                enabled=enabled,
                timeout_seconds=timeout_seconds,
                requires_confirmation=requires_confirmation,
            )
        logger.debug("Tool registered: %s", name)

    def unregister(self, name: str):
        with self._lock:
            self._tools.pop(name, None)

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def get_all(self) -> dict[str, ToolDef]:
        return dict(self._tools)

    def get_enabled(self) -> list[ToolDef]:
        return [t for t in self._tools.values() if t.enabled]

    def get_by_category(self, category: ToolCategory) -> list[ToolDef]:
        return [t for t in self._tools.values() if t.category == category and t.enabled]

    def find_tools(self, query: str, limit: int = 5) -> list[tuple[ToolDef, float]]:
        """Find tools matching a query, sorted by score."""
        query_lower = query.lower().replace("_", " ").replace("-", " ")
        results: list[tuple[ToolDef, float]] = []

        for tool in self._tools.values():
            if not tool.enabled:
                continue
            score = tool.matches_intent(query)
            # Boost by priority (lower = higher priority)
            score += (100 - min(tool.priority, 100)) * 0.001
            if score > 0.1:
                results.append((tool, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def find_best(self, query: str) -> ToolDef | None:
        """Find the best matching tool for a query."""
        results = self.find_tools(query, limit=1)
        return results[0][0] if results else None

    def get_stats(self) -> dict[str, Any]:
        categories = {}
        for tool in self._tools.values():
            cat = tool.category.value
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total": len(self._tools),
            "enabled": sum(1 for t in self._tools.values() if t.enabled),
            "categories": categories,
        }


# Global instance
tool_registry = ToolRegistry()

__all__ = ["ToolRegistry", "ToolDef", "ToolResult", "ToolCategory", "tool_registry"]
