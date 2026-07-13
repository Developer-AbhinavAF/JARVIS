"""JARVIS AI Router v3.0 — Backward-Compatible Interface.

This module replaces the old 9Router proxy with a direct multi-provider
AI router. The public API (NineRouterClient, RouterResponse, RouterHealth,
router_client, timing_*) is preserved exactly so existing code continues
to work without changes.

Internally, all requests are routed through the new `jarvis.router` module
which supports 20+ AI providers natively.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Generator

from jarvis.router import (
    AIRouter,
    RouterResponse,
    RouterHealth,
    get_router,
)

logger = logging.getLogger(__name__)

_timings: dict[str, float] = {}


def timing_reset() -> None:
    _timings.clear()


def timing_mark(label: str, started: float) -> None:
    _timings[label] = round((time.time() - started) * 1000, 1)


def timing_report() -> str:
    if not _timings:
        return ""
    total = sum(_timings.values())
    parts = " | ".join(f"{k}:{v}ms" for k, v in _timings.items())
    return f"[TIMING] {parts} | TOTAL:{total:.0f}ms"


class NineRouterClient:
    """Unified multi-provider AI client — drop-in replacement for 9Router.

    All AI requests pass through this single service. The router handles
    provider selection, failover, load balancing, health monitoring, and
    quota management across 20+ providers.

    Backward compatible with the old NineRouterClient interface.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._router = get_router()
        if base_url:
            self._router.config.default_provider = ""
        if model:
            self._router._default_model = model
        if timeout:
            self._router.config.timeout = timeout
        if max_retries:
            self._router.config.max_retries = max_retries

        self.base_url = self._build_base_url()
        self.model = model or self._router._default_model
        self.timeout = timeout or self._router.config.timeout
        self.max_retries = max_retries or self._router.config.max_retries
        self._last_health: RouterHealth | None = None
        self._health_ttl = 30.0

    def _build_base_url(self) -> str:
        providers = self._router.provider_registry.get_available()
        if providers:
            return providers[0].base_url
        return ""

    @property
    def client(self) -> Any:
        return self._router

    @property
    def async_client(self) -> Any:
        return self._router

    def health_check(self) -> RouterHealth:
        now = time.time()
        if self._last_health and (now - self._last_health.latency_ms / 1000) < self._health_ttl:
            return self._last_health
        health = self._router.health_check()
        self._last_health = health
        return health

    def is_available(self) -> bool:
        return self._router.is_available()

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict | None = None,
        stop: list[str] | None = None,
    ) -> str:
        return self._router.chat(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            stop=stop,
        )

    def chat_result(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict | None = None,
    ) -> RouterResponse:
        return self._router.chat_result(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
        )

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict | None = None,
    ) -> Generator[str, None, None]:
        yield from self._router.chat_stream(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
        )

    def embed(
        self,
        input_texts: str | list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        return self._router.embed(input_texts, model=model)

    def close(self) -> None:
        pass


router_client = NineRouterClient()
