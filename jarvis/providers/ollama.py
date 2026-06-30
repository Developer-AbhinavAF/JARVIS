from __future__ import annotations

import json
import logging
from typing import Any, Generator

import requests

from jarvis import config
from jarvis.providers.base import BaseLLMProvider
from jarvis.providers.exceptions import (
    ProviderEmptyResponseError,
    ProviderError,
    ProviderTimeoutError,
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider (final fallback)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        super().__init__()
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or config.OLLAMA_MODEL
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    @property
    def name(self) -> str:
        return "ollama"

    def _native_base(self) -> str:
        return self.base_url.replace("/v1", "")

    def _generate_impl(self, messages: list[dict], **kwargs: Any) -> str:
        payload = self._build_payload(messages, stream=False, **kwargs)
        url = f"{self._native_base()}/api/chat"
        try:
            resp = self._session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.Timeout:
            raise ProviderTimeoutError(f"Ollama timeout after {self.timeout}s")
        except requests.ConnectionError:
            raise ProviderError("Ollama connection refused — is it running?")
        except requests.RequestException as e:
            raise ProviderError(f"Ollama error: {e}")

        data = resp.json()
        content = data.get("message", {}).get("content", "")
        if content is None:
            raise ProviderEmptyResponseError("Ollama returned empty content")
        return content

    def _stream_impl(self, messages: list[dict], **kwargs: Any) -> Generator[str, None, None]:
        payload = self._build_payload(messages, stream=True, **kwargs)
        url = f"{self._native_base()}/api/chat"
        try:
            with self._session.post(url, json=payload, stream=True, timeout=self.timeout) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except requests.Timeout:
            raise ProviderTimeoutError(f"Ollama stream timeout after {self.timeout}s")
        except requests.ConnectionError:
            raise ProviderError("Ollama stream connection refused")
        except requests.RequestException as e:
            raise ProviderError(f"Ollama stream error: {e}")

    def _build_payload(self, messages: list[dict], *, stream: bool, **kwargs: Any) -> dict:
        token_limit = max(8, min(kwargs.get("max_tokens", 48), 48))
        num_ctx = max(512, min(config.OLLAMA_NUM_CTX, 2048))
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_ctx": num_ctx,
                "num_batch": config.OLLAMA_NUM_BATCH,
                "num_predict": token_limit,
                "temperature": kwargs.get("temperature", config.LLM_TEMPERATURE),
            },
            "keep_alive": -1,
        }
        fmt = kwargs.get("response_format")
        if fmt:
            payload["format"] = fmt
        return payload
