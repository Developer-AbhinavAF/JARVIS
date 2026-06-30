"""Centralized LLM provider service for JARVIS.

Fast-path version: uses native Ollama API directly, no OpenAI client overhead,
no slow health checks on every call, minimal retries, low context windows.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Iterable

import requests

from jarvis import config

logger = logging.getLogger(__name__)


class LLMServiceUnavailable(RuntimeError):
    """Raised when the configured local LLM service cannot be reached."""


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


# Per-request timing accumulator (thread-local to be safe in async contexts)
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
    """Provider-neutral LLM facade using native Ollama API."""

    provider_name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or config.OLLAMA_MODEL
        self.timeout = timeout or config.OLLAMA_TIMEOUT_SECONDS
        self._last_health: LLMHealth | None = None
        self._health_ttl = 30.0
        # Reusable session for connection pooling
        self._session = requests.Session()
        # Set default timeout per-request so it doesn't hang
        self._session.headers.update({"Content-Type": "application/json"})

    @property
    def client(self) -> Any:
        """Minimal client stub - we use native API directly."""
        return object()

    def _native_ollama_base(self) -> str:
        if self.base_url.endswith("/v1"):
            return self.base_url[:-3]
        return self.base_url

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
        """Fast health check - cached for 30s, short timeout."""
        now = time.time()
        if self._last_health and (now - self._last_health.latency_ms / 1000) < self._health_ttl:
            return self._last_health

        start = time.time()
        url = f"{self._native_ollama_base()}/api/tags"
        try:
            resp = self._session.get(url, timeout=3)
            latency = (time.time() - start) * 1000
            if resp.status_code != 200:
                health = LLMHealth(available=False, message=f"HTTP {resp.status_code}", base_url=self.base_url, model=self.model, latency_ms=latency)
            else:
                health = LLMHealth(available=True, message="ok", base_url=self.base_url, model=self.model, latency_ms=latency)
            self._last_health = health
            return health
        except requests.RequestException as exc:
            health = LLMHealth(available=False, message=str(exc), base_url=self.base_url, model=self.model, latency_ms=(time.time() - start) * 1000)
            self._last_health = health
            return health

    def is_available(self) -> bool:
        return self.health_check().available

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
        token_limit = max(8, min(max_tokens or config.LLM_MAX_TOKENS, 48))
        num_ctx = max(512, min(config.OLLAMA_NUM_CTX, 2048))

        prepared = self._prepare_messages(messages)

        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": prepared,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
                "num_batch": config.OLLAMA_NUM_BATCH,
                "num_predict": token_limit,
                "temperature": temperature if temperature is not None else config.LLM_TEMPERATURE,
            },
            "keep_alive": -1,
        }
        if response_format:
            payload["format"] = response_format

        url = f"{self._native_ollama_base()}/api/chat"

        try:
            start = time.time()
            resp = self._session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000
            text = data.get("message", {}).get("content", "")
            timing_mark("token_gen", start)
            return LLMResult(text=text, model=selected_model, provider=self.provider_name, latency_ms=latency)
        except Exception as exc:
            raise LLMServiceUnavailable(f"Ollama generation failed: {exc}") from exc

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
        token_limit = max(8, min(max_tokens or config.LLM_MAX_TOKENS, 48))
        num_ctx = max(512, min(config.OLLAMA_NUM_CTX, 2048))

        url = f"{self._native_ollama_base()}/api/chat"
        prepared = self._prepare_messages(messages)

        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": prepared,
            "stream": True,
            "options": {
                "num_ctx": num_ctx,
                "num_batch": config.OLLAMA_NUM_BATCH,
                "num_predict": token_limit,
                "temperature": temperature if temperature is not None else config.LLM_TEMPERATURE,
            },
            "keep_alive": -1,
        }
        if response_format:
            payload["format"] = response_format

        try:
            with self._session.post(url, json=payload, stream=True, timeout=self.timeout) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            raise LLMServiceUnavailable(f"Ollama streaming failed: {exc}") from exc


llm_service = LLMService()
