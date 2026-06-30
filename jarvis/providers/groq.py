from __future__ import annotations

import json
import logging
import time
from typing import Any, Generator

import requests

from jarvis.providers.base import BaseLLMProvider
from jarvis.providers.exceptions import (
    ProviderAuthError,
    ProviderEmptyResponseError,
    ProviderError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.1-8b-instant"


class GroqProvider(BaseLLMProvider):
    """Groq LLM provider with automatic multi-key fallback."""

    def __init__(
        self,
        api_keys: list[str],
        model: str = DEFAULT_MODEL,
        base_url: str = GROQ_BASE_URL,
        timeout: float = 10.0,
    ) -> None:
        super().__init__()
        self.api_keys = [k for k in api_keys if k and len(k) > 10]
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._key_index = 0

    @property
    def name(self) -> str:
        return "groq"

    def _url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _headers(self, key: str) -> dict:
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def _request(self, payload: dict, stream: bool = False) -> requests.Response:
        last_error: Exception | None = None
        keys_tried: list[str] = []

        for i in range(len(self.api_keys)):
            idx = (self._key_index + i) % len(self.api_keys)
            key = self.api_keys[idx]
            keys_tried.append(key[:12] + "...")

            try:
                resp = self._session.post(
                    self._url(),
                    json=payload,
                    headers=self._headers(key),
                    timeout=self.timeout,
                    stream=stream,
                )
                if resp.status_code == 200:
                    self._key_index = idx
                    return resp
                if resp.status_code == 429:
                    logger.warning("Groq key %s rate limited", key[:12])
                    last_error = ProviderRateLimitError(f"Groq rate limited (key {i+1})")
                    continue
                if resp.status_code in (401, 403):
                    logger.warning("Groq key %s auth failed", key[:12])
                    last_error = ProviderAuthError(f"Groq auth failure (key {i+1})")
                    continue
                if 500 <= resp.status_code < 600:
                    last_error = ProviderServerError(f"Groq HTTP {resp.status_code} (key {i+1})")
                    continue
                last_error = ProviderError(f"Groq HTTP {resp.status_code} (key {i+1})")
                continue
            except requests.Timeout:
                last_error = ProviderTimeoutError(f"Groq timeout after {self.timeout}s (key {i+1})")
                continue
            except requests.ConnectionError:
                last_error = ProviderError(f"Groq connection refused (key {i+1})")
                continue
            except requests.RequestException as e:
                last_error = ProviderError(f"Groq network error: {e} (key {i+1})")
                continue

        raise last_error or ProviderError("All Groq keys exhausted")

    def _generate_impl(self, messages: list[dict], **kwargs: Any) -> str:
        payload = self._build_payload(messages, stream=False, **kwargs)
        resp = self._request(payload)
        data = resp.json()
        if "choices" not in data or not data["choices"]:
            raise ProviderEmptyResponseError("Groq returned empty choices")
        content = data["choices"][0].get("message", {}).get("content", "")
        if not content:
            raise ProviderEmptyResponseError("Groq returned empty content")
        return content

    def _stream_impl(self, messages: list[dict], **kwargs: Any) -> Generator[str, None, None]:
        payload = self._build_payload(messages, stream=True, **kwargs)
        resp = self._request(payload, stream=True)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith(b"data: "):
                chunk = line[6:]
                if chunk.strip() == b"[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    def _build_payload(self, messages: list[dict], *, stream: bool, **kwargs: Any) -> dict:
        payload: dict[str, Any] = {
            "model": kwargs.get("model") or self.model,
            "messages": messages,
            "stream": stream,
            "temperature": kwargs.get("temperature", 0.5),
            "max_tokens": kwargs.get("max_tokens", 48),
        }
        fmt = kwargs.get("response_format")
        if fmt:
            payload["response_format"] = fmt
        return payload
