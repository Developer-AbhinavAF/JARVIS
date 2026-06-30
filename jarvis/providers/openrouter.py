from __future__ import annotations

import json
import logging
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

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "meta-llama/llama-3-8b-instruct"


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter LLM provider."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = OPENROUTER_BASE_URL,
        timeout: float = 15.0,
    ) -> None:
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })

    @property
    def name(self) -> str:
        return "openrouter"

    def _url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _generate_impl(self, messages: list[dict], **kwargs: Any) -> str:
        payload = self._build_payload(messages, stream=False, **kwargs)
        try:
            resp = self._session.post(self._url(), json=payload, timeout=self.timeout)
        except requests.Timeout:
            raise ProviderTimeoutError(f"OpenRouter timeout after {self.timeout}s")
        except requests.ConnectionError:
            raise ProviderError("OpenRouter connection refused")
        except requests.RequestException as e:
            raise ProviderError(f"OpenRouter network error: {e}")

        if resp.status_code == 429:
            raise ProviderRateLimitError("OpenRouter rate limited")
        if resp.status_code in (401, 403):
            raise ProviderAuthError("OpenRouter auth failure")
        if 500 <= resp.status_code < 600:
            raise ProviderServerError(f"OpenRouter HTTP {resp.status_code}")
        if resp.status_code != 200:
            raise ProviderError(f"OpenRouter HTTP {resp.status_code}")

        data = resp.json()
        if "choices" not in data or not data["choices"]:
            raise ProviderEmptyResponseError("OpenRouter returned empty choices")
        content = data["choices"][0].get("message", {}).get("content", "")
        if not content:
            raise ProviderEmptyResponseError("OpenRouter returned empty content")
        return content

    def _stream_impl(self, messages: list[dict], **kwargs: Any) -> Generator[str, None, None]:
        payload = self._build_payload(messages, stream=True, **kwargs)
        try:
            resp = self._session.post(self._url(), json=payload, timeout=self.timeout, stream=True)
        except requests.Timeout:
            raise ProviderTimeoutError(f"OpenRouter stream timeout after {self.timeout}s")
        except requests.ConnectionError:
            raise ProviderError("OpenRouter stream connection refused")
        except requests.RequestException as e:
            raise ProviderError(f"OpenRouter stream network error: {e}")

        if resp.status_code == 429:
            raise ProviderRateLimitError("OpenRouter stream rate limited")
        if resp.status_code in (401, 403):
            raise ProviderAuthError("OpenRouter stream auth failure")
        if 500 <= resp.status_code < 600:
            raise ProviderServerError(f"OpenRouter stream HTTP {resp.status_code}")

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
