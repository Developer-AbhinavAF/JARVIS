"""Scalable tool registry, router, executor, permissions, and analytics."""

from __future__ import annotations

import inspect
import json
import logging
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from jarvis import config
from jarvis.api_services import api_services
from jarvis.memory_os import os_memory
from jarvis.nlp_pipeline import NLPResult, nlp_pipeline

logger = logging.getLogger(__name__)


class ToolPermission(str, Enum):
    READ_ONLY = "read_only"
    NETWORK = "network"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    SYSTEM = "system"
    AUTOMATION = "automation"
    SENSITIVE = "sensitive"


@dataclass
class ToolSpec:
    name: str
    description: str
    category: str
    handler: Callable[..., Any]
    permissions: set[ToolPermission] = field(default_factory=lambda: {ToolPermission.READ_ONLY})
    parameters: dict[str, Any] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    enabled: bool = True
    timeout_seconds: float | None = None
    cache_ttl_seconds: int = 0
    requires_confirmation: bool = False

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("handler", None)
        data["permissions"] = [permission.value for permission in self.permissions]
        return data


@dataclass
class ToolRoute:
    tool_name: str
    arguments: dict[str, Any]
    confidence: float
    reason: str


@dataclass
class ToolResult:
    tool_name: str
    ok: bool
    result: Any
    error: str = ""
    latency_ms: float = 0.0
    cached: bool = False
    permission_denied: bool = False


class ToolRegistry:
    """Registry designed for hundreds or thousands of tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._aliases: dict[str, str] = {}
        self._lock = threading.RLock()
        self._legacy_loaded = False

    def register(self, spec: ToolSpec) -> None:
        with self._lock:
            self._tools[spec.name] = spec
            for alias in spec.aliases:
                self._aliases[alias.lower()] = spec.name

    def register_function(
        self,
        name: str,
        handler: Callable[..., Any],
        *,
        description: str = "",
        category: str = "general",
        permissions: set[ToolPermission] | None = None,
        aliases: list[str] | None = None,
        timeout_seconds: float | None = None,
        cache_ttl_seconds: int = 0,
        requires_confirmation: bool = False,
    ) -> None:
        self.register(
            ToolSpec(
                name=name,
                description=description or inspect.getdoc(handler) or name,
                category=category,
                handler=handler,
                permissions=permissions or {ToolPermission.READ_ONLY},
                parameters=self._signature_schema(handler),
                aliases=aliases or [],
                timeout_seconds=timeout_seconds,
                cache_ttl_seconds=cache_ttl_seconds,
                requires_confirmation=requires_confirmation,
            )
        )

    def get(self, name: str) -> ToolSpec | None:
        with self._lock:
            canonical = self._aliases.get(name.lower(), name)
            return self._tools.get(canonical)

    def list(self, *, category: str | None = None, include_disabled: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            items = []
            for spec in self._tools.values():
                if category and spec.category != category:
                    continue
                if not include_disabled and not spec.enabled:
                    continue
                items.append(spec.public_dict())
            return sorted(items, key=lambda item: (item["category"], item["name"]))

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        query_terms = set(query.lower().split())
        scored: list[tuple[int, ToolSpec]] = []
        with self._lock:
            for spec in self._tools.values():
                haystack = " ".join([spec.name, spec.description, spec.category, *spec.aliases]).lower()
                score = sum(1 for term in query_terms if term in haystack)
                if score:
                    scored.append((score, spec))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [spec.public_dict() for _, spec in scored[:limit]]

    def load_legacy_tools(self) -> None:
        """Import existing jarvis.tools once and wrap its callable dictionary."""

        if self._legacy_loaded:
            return
        with self._lock:
            if self._legacy_loaded:
                return
            try:
                from jarvis.tools import TOOL_REGISTRY

                for name, handler in TOOL_REGISTRY.items():
                    if name in self._tools or not callable(handler):
                        continue
                    permission = self._infer_permission(name)
                    self.register_function(
                        name,
                        handler,
                        category=self._infer_category(name),
                        permissions=permission,
                        timeout_seconds=config.TOOL_TIMEOUT_SECONDS,
                        requires_confirmation=ToolPermission.SYSTEM in permission,
                    )
                self._legacy_loaded = True
                logger.info("Loaded %s legacy tools into production registry", len(TOOL_REGISTRY))
            except Exception as exc:
                logger.warning("Legacy tool loading failed: %s", exc)

    def _signature_schema(self, handler: Callable[..., Any]) -> dict[str, Any]:
        try:
            signature = inspect.signature(handler)
        except (TypeError, ValueError):
            return {}
        schema = {}
        for name, parameter in signature.parameters.items():
            if name.startswith("_"):
                continue
            schema[name] = {
                "required": parameter.default is inspect._empty,
                "default": None if parameter.default is inspect._empty else parameter.default,
                "type": getattr(parameter.annotation, "__name__", str(parameter.annotation))
                if parameter.annotation is not inspect._empty
                else "any",
            }
        return schema

    def _infer_category(self, name: str) -> str:
        if any(part in name for part in ["nasa", "iss", "space"]):
            return "nasa"
        if any(part in name for part in ["stock", "finnhub", "crypto", "forex", "financial"]):
            return "finance"
        if any(part in name for part in ["memory", "todo", "note", "briefing"]):
            return "memory"
        if any(part in name for part in ["document", "pdf", "docx"]):
            return "documents"
        if any(part in name for part in ["open", "close", "mouse", "keyboard", "volume", "process"]):
            return "system"
        if any(part in name for part in ["web", "youtube", "weather", "search"]):
            return "web"
        return "general"

    def _infer_permission(self, name: str) -> set[ToolPermission]:
        if any(part in name for part in ["open_app", "close_app", "kill", "mouse", "keyboard", "volume"]):
            return {ToolPermission.SYSTEM}
        if any(part in name for part in ["web", "youtube", "weather", "nasa", "finnhub", "search", "news"]):
            return {ToolPermission.NETWORK}
        if any(part in name for part in ["read_document", "list_documents", "search_documents"]):
            return {ToolPermission.FILE_READ}
        return {ToolPermission.READ_ONLY}


class ToolAnalytics:
    """Durable low-cost tool monitoring."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or str(config.TOOL_ANALYTICS_DB_PATH)
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    error TEXT NOT NULL,
                    cached INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_events_name_time ON tool_events(tool_name, timestamp)")
            conn.commit()

    def record(self, result: ToolResult) -> None:
        if not config.ENABLE_TOOL_ANALYTICS:
            return
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tool_events (timestamp, tool_name, ok, latency_ms, error, cached)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    result.tool_name,
                    int(result.ok),
                    result.latency_ms,
                    result.error[:500],
                    int(result.cached),
                ),
            )
            conn.commit()

    def summary(self, limit: int = 20) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT tool_name,
                       COUNT(*) AS calls,
                       SUM(ok) AS successes,
                       AVG(latency_ms) AS avg_latency_ms,
                       MAX(timestamp) AS last_called
                FROM tool_events
                GROUP BY tool_name
                ORDER BY calls DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]


class ToolExecutor:
    """Executes tools with permissions, timeouts, caching, and analytics."""

    def __init__(self, registry: ToolRegistry, analytics: ToolAnalytics | None = None) -> None:
        self.registry = registry
        self.analytics = analytics or ToolAnalytics()
        self._pool = ThreadPoolExecutor(max_workers=max(1, config.TOOL_EXECUTOR_WORKERS))
        self._cache: dict[str, tuple[float, ToolResult]] = {}
        self._lock = threading.RLock()

    def execute(self, name: str, arguments: dict[str, Any] | None = None, *, allow_sensitive: bool = False) -> ToolResult:
        spec = self.registry.get(name)
        if not spec:
            return ToolResult(name, False, None, f"Tool '{name}' not found.")
        if not spec.enabled:
            return ToolResult(name, False, None, f"Tool '{name}' is disabled.")
        denied = self._permission_denied(spec, allow_sensitive=allow_sensitive)
        if denied:
            result = ToolResult(spec.name, False, None, denied, permission_denied=True)
            self.analytics.record(result)
            return result

        args = arguments or {}
        cache_key = self._cache_key(spec.name, args)
        cached = self._get_cached(cache_key, spec.cache_ttl_seconds)
        if cached:
            return cached

        started = time.time()
        future = self._pool.submit(spec.handler, **args)
        try:
            value = future.result(timeout=spec.timeout_seconds or config.TOOL_TIMEOUT_SECONDS)
            result = ToolResult(spec.name, True, value, latency_ms=(time.time() - started) * 1000)
        except FutureTimeout:
            future.cancel()
            result = ToolResult(spec.name, False, None, "Tool timed out.", latency_ms=(time.time() - started) * 1000)
        except Exception as exc:
            logger.exception("Tool failed: %s", spec.name)
            result = ToolResult(spec.name, False, None, str(exc), latency_ms=(time.time() - started) * 1000)

        if spec.cache_ttl_seconds > 0 and result.ok:
            with self._lock:
                self._cache[cache_key] = (time.time(), result)
        self.analytics.record(result)
        return result

    def _permission_denied(self, spec: ToolSpec, *, allow_sensitive: bool) -> str:
        if ToolPermission.NETWORK in spec.permissions and not config.ENABLE_NETWORK_TOOLS:
            return "Network tools are disabled."
        if ToolPermission.SYSTEM in spec.permissions and not config.ENABLE_SYSTEM_TOOLS:
            return "System tools are disabled."
        if spec.requires_confirmation and not allow_sensitive:
            return "This tool requires confirmation before execution."
        if ToolPermission.SENSITIVE in spec.permissions and not allow_sensitive:
            return "Sensitive tool execution requires confirmation."
        return ""

    def _cache_key(self, name: str, args: dict[str, Any]) -> str:
        return f"{name}:{json.dumps(args, sort_keys=True, default=str)}"

    def _get_cached(self, key: str, ttl: int) -> ToolResult | None:
        if ttl <= 0:
            return None
        with self._lock:
            item = self._cache.get(key)
            if not item:
                return None
            created, result = item
            if time.time() - created > ttl:
                self._cache.pop(key, None)
                return None
            return ToolResult(result.tool_name, result.ok, result.result, result.error, result.latency_ms, cached=True)


class ToolRouter:
    """Fast deterministic router before any LLM is asked."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def route(self, message: str, nlp: NLPResult | None = None) -> ToolRoute | None:
        nlp = nlp or nlp_pipeline.process(message)
        text = nlp.normalized_text

        if text.startswith(("remember ", "save this ", "save that ", "note ")):
            content = text
            for prefix in ["remember ", "save this ", "save that ", "note "]:
                if content.startswith(prefix):
                    content = content[len(prefix) :].strip()
                    break
            return ToolRoute("memory_add", {"content": content, "category": "preference"}, 0.92, "Explicit memory command")

        if any(marker in text for marker in ["search memory", "find in memory", "what do you remember"]):
            query = text.replace("search memory", "").replace("find in memory", "").replace("what do you remember", "").strip()
            return ToolRoute("memory_search", {"query": query or message}, 0.86, "Memory search command")

        if nlp.intent == "web_search" and nlp.entities.get("query"):
            return ToolRoute("web_search", {"query": nlp.entities["query"]}, 0.9, "NLP web_search intent")
        if nlp.intent == "youtube_play" and nlp.entities.get("query"):
            return ToolRoute("youtube_search", {"query": nlp.entities["query"]}, 0.84, "NLP YouTube intent")

        if text.startswith(("weather ", "weather in ", "forecast ")):
            city = text.replace("weather in", "").replace("weather", "").replace("forecast", "").strip() or "Mumbai"
            return ToolRoute("weather_current", {"city": city}, 0.82, "Weather command")

        if text.startswith(("stock ", "quote ", "price of ")):
            symbol = text.replace("stock", "").replace("quote", "").replace("price of", "").strip().upper() or "AAPL"
            return ToolRoute("finance_quote", {"symbol": symbol}, 0.8, "Finance quote command")

        if "nasa apod" in text or "astronomy picture" in text:
            return ToolRoute("nasa_apod", {}, 0.87, "NASA APOD command")

        if text.startswith(("open ", "launch ")):
            target = text.replace("launch ", "").replace("open ", "").strip()
            return ToolRoute("open_app", {"target": target}, 0.78, "System open command")

        return None


def _format_api_response(response: Any) -> str:
    if hasattr(response, "ok") and hasattr(response, "data"):
        if not response.ok:
            return response.error
        return json.dumps(response.data, indent=2, ensure_ascii=True)[: config.MAX_SNIPPET_CHARS]
    return str(response)


def build_default_registry(load_legacy: bool = True) -> ToolRegistry:
    registry = ToolRegistry()

    def memory_add(content: str, category: str = "knowledge", source: str = "user", importance: float = 0.7) -> str:
        record = os_memory.add(content, category=category, source=source, importance=importance)
        return f"Saved memory {record.id}: {record.summary}"

    def memory_search(query: str, category: str = "", limit: int = 5) -> str:
        categories = [category] if category else None
        results = os_memory.search(query, categories=categories, limit=limit)
        if not results:
            return "No relevant memories found."
        return "\n".join(f"- [{item['category']}] {item['summary']} ({item['id']})" for item in results)

    def web_search(query: str, max_results: int = 5) -> str:
        response = api_services.tavily.search(query, max_results=max_results)
        if response.ok:
            return _format_api_response(response)
        try:
            from jarvis.tools import web_search as legacy_web_search

            return legacy_web_search(query)
        except ImportError:
            return response.error or "Web search is unavailable because the requests package is not installed."

    def youtube_search(query: str, max_results: int = 5) -> str:
        return _format_api_response(api_services.youtube.search(query, max_results=max_results))

    def weather_current(city: str = "Mumbai") -> str:
        return _format_api_response(api_services.openweather.current(city))

    def finance_quote(symbol: str = "AAPL") -> str:
        primary = api_services.finnhub.quote(symbol)
        if primary.ok:
            return _format_api_response(primary)
        return _format_api_response(api_services.alpha_vantage.quote(symbol))

    def nasa_apod() -> str:
        return _format_api_response(api_services.nasa.apod())

    registry.register_function(
        "memory_add",
        memory_add,
        description="Save an important memory with category, source, tags, and importance.",
        category="memory",
        permissions={ToolPermission.READ_ONLY},
        aliases=["remember", "save_memory"],
    )
    registry.register_function(
        "memory_search",
        memory_search,
        description="Search personal memory, knowledge, project, research, and document memory.",
        category="memory",
        permissions={ToolPermission.READ_ONLY},
        aliases=["find_memory"],
        cache_ttl_seconds=30,
    )
    registry.register_function(
        "web_search",
        web_search,
        description="Search the web using Tavily, with fallback to existing web search.",
        category="research",
        permissions={ToolPermission.NETWORK},
        cache_ttl_seconds=120,
    )
    registry.register_function(
        "youtube_search",
        youtube_search,
        description="Search YouTube videos through the YouTube Data API.",
        category="media",
        permissions={ToolPermission.NETWORK},
        cache_ttl_seconds=300,
    )
    registry.register_function(
        "weather_current",
        weather_current,
        description="Get current weather through OpenWeather.",
        category="weather",
        permissions={ToolPermission.NETWORK},
        cache_ttl_seconds=300,
    )
    registry.register_function(
        "finance_quote",
        finance_quote,
        description="Get a stock or crypto quote through Finnhub or Alpha Vantage.",
        category="finance",
        permissions={ToolPermission.NETWORK},
        cache_ttl_seconds=60,
    )
    registry.register_function(
        "nasa_apod",
        nasa_apod,
        description="Get NASA Astronomy Picture of the Day.",
        category="nasa",
        permissions={ToolPermission.NETWORK},
        cache_ttl_seconds=1800,
    )

    if load_legacy:
        registry.load_legacy_tools()
    return registry


default_tool_registry = build_default_registry(load_legacy=False)
default_tool_router = ToolRouter(default_tool_registry)
default_tool_executor = ToolExecutor(default_tool_registry)
