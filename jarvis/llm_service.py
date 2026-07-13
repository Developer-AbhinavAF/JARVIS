from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Iterable

import requests

from jarvis import config
from jarvis.router_service import router_client

logger = logging.getLogger(__name__)


class LLMServiceUnavailable(RuntimeError):
    """Raised when the AI Router service cannot be reached."""


@dataclass
class LLMHealth:
    available: bool
    message: str
    base_url: str
    model: str
    latency_ms: float = 0.0


@dataclass
class LLMResult:
    text: str
    model: str
    provider: str
    latency_ms: float
    tokens_used: int = 0


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


class LLMService:
    """Provider-neutral LLM facade — all AI routed through multi-provider router."""

    provider_name = "router"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = base_url or ""
        self.model = model or config.AI_MODEL
        self.timeout = timeout or config.AI_TIMEOUT
        self._last_health: LLMHealth | None = None
        self._health_ttl = 30.0
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        api_key = getattr(config, 'AI_API_KEY', '')
        if api_key:
            self._session.headers.update({"Authorization": f"Bearer {api_key}"})

    @property
    def client(self) -> Any:
        return router_client

    def _prepare_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        if not messages:
            return messages

        budget = max(config.LLM_PROMPT_MAX_CHARS, 2000)

        total_chars = 0
        for item in messages:
            total_chars += len(item.get("content", ""))

        if total_chars <= budget:
            return messages

        prepared: list[dict[str, str]] = []
        remaining = budget

        for item in reversed(messages):
            role = item.get("role", "user")
            content = str(item.get("content", ""))
            if not content:
                continue
            if len(content) > remaining:
                content = content[-remaining:]
                if role != "system":
                    content = "[trimmed]\n" + content
            prepared.append({"role": role, "content": content})
            remaining -= len(content)
            if remaining <= 0:
                break

        prepared.reverse()
        return prepared or messages[-1:]

    def health_check(self) -> LLMHealth:
        return LLMHealth(available=True, message="ok", base_url=self.base_url, model=self.model, latency_ms=0)

    def is_available(self) -> bool:
        return True

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> str | Iterable[str]:
        if stream:
            return self.stream(messages, model=model, max_tokens=max_tokens, temperature=temperature, response_format=response_format)
        result = self.generate_result(messages, model=model, max_tokens=max_tokens, temperature=temperature, response_format=response_format)
        return result.text

    def generate_result(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResult:
        selected_model = model or self.model
        token_limit = max(8, min(max_tokens or config.LLM_MAX_TOKENS, 256000))
        prepared = self._prepare_messages(messages)

        try:
            start = time.time()
            text = router_client.chat(
                prepared,
                model=selected_model or None,
                max_tokens=token_limit,
                temperature=temperature if temperature is not None else config.LLM_TEMPERATURE,
                response_format=response_format,
            )
            latency = (time.time() - start) * 1000
            timing_mark("token_gen", start)
            return LLMResult(
                text=text,
                model=selected_model or "router-default",
                provider=self.provider_name,
                latency_ms=latency,
            )
        except Exception as exc:
            raise LLMServiceUnavailable(f"Router generation failed: {exc}") from exc

    def stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> Iterable[str]:
        selected_model = model or self.model
        token_limit = max(8, min(max_tokens or config.LLM_MAX_TOKENS, 256000))
        prepared = self._prepare_messages(messages)

        try:
            for token in router_client.chat_stream(
                prepared,
                model=selected_model or None,
                max_tokens=token_limit,
                temperature=temperature if temperature is not None else config.LLM_TEMPERATURE,
                response_format=response_format,
            ):
                yield token
        except Exception as exc:
            raise LLMServiceUnavailable(f"Router streaming failed: {exc}") from exc


llm_service = LLMService()
