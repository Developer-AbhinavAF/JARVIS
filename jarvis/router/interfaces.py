"""Abstract base provider interface — every AI provider implements this."""

from __future__ import annotations

import json
import logging
import time
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator, Sequence

import httpx

from .models import (
    RouterResponse,
    RouterHealth,
    ProviderInfo,
    ChatRequest,
    EmbeddingRequest,
    StreamChunk,
    Capability,
    ProviderStatus,
)
from .exceptions import (
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderServerError,
    ProviderNetworkError,
    ProviderEmptyResponseError,
    ProviderModelNotFoundError,
    QuotaExceededError,
)
from .config import RouterConfig

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """Abstract base for all AI providers.

    Subclasses register themselves into the global provider registry
    by overriding the class-level metadata attributes and implementing
    the core abstract methods: chat, chat_stream, embed, and health_check.

    The base class provides:
    - httpx HTTP client with connection pooling
    - Error classification (4xx → auth/model, 5xx → server, etc.)
    - Unified response normalization
    - Automatic timeout handling
    """

    # ---- Class-level metadata (override in subclasses) ----
    name: str = "base"
    display_name: str = "Base Provider"
    base_url: str = ""
    api_key_env: str = ""
    priority: int = 100
    weight: float = 1.0
    capabilities: set[Capability] = set()
    supports_streaming: bool = False
    supports_vision: bool = False
    supports_tool_calling: bool = False
    supports_json_mode: bool = False
    supports_embeddings: bool = False
    supports_reasoning: bool = False
    max_context_length: int = 4096
    tags: list[str] = []

    # Known model families this provider serves
    _known_models: dict[str, dict[str, Any]] = {}

    def __init__(self, config: RouterConfig | None = None) -> None:
        self.config = config or RouterConfig()
        self._api_key: str | None = None
        self._http_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        self._last_health: RouterHealth | None = None
        self._health_ts: float = 0.0

    # ---- API Key Resolution ----
    @property
    def api_key(self) -> str | None:
        if self._api_key is None:
            self._api_key = self.config.get_api_key(self.name) or os.getenv(self.api_key_env, "")
        return self._api_key or None

    @property
    def is_configured(self) -> bool:
        """Returns True if provider has credentials configured."""
        return bool(self.api_key) or self.name.startswith("ollama_local")

    # ---- HTTP Clients ----
    @property
    def client(self) -> httpx.Client:
        if self._http_client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._http_client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.config.timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=self.config.max_keepalive,
                    max_connections=self.config.max_connections,
                ),
            )
        return self._http_client

    @property
    def async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.config.timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=self.config.max_keepalive,
                    max_connections=self.config.max_connections,
                ),
            )
        return self._async_client

    # ---- Public API ----
    @abstractmethod
    def chat(self, request: ChatRequest) -> RouterResponse:
        """Send a chat completion request and return normalized response."""
        ...

    @abstractmethod
    def chat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        """Send a streaming chat completion request."""
        ...

    @abstractmethod
    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        """Generate embeddings."""
        ...

    @abstractmethod
    def health_check(self) -> RouterHealth:
        """Check provider health."""
        ...

    # ---- Capability Query ----
    def has_capability(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def supports_model(self, model_name: str) -> bool:
        """Check if this provider supports a given model."""
        if model_name in self._known_models:
            return True
        # Fallback: check if model family matches
        family = model_name.lower().split("/")[-1].split(":")[0]
        for known in self._known_models:
            if family in known.lower() or known.lower() in family:
                return True
        return False

    def get_provider_info(self) -> ProviderInfo:
        """Build a ProviderInfo dataclass from this provider's metadata."""
        return ProviderInfo(
            name=self.name,
            display_name=self.display_name,
            base_url=self.base_url,
            api_key_env=self.api_key_env,
            priority=self.priority,
            weight=self.weight,
            enabled=self.is_configured,
            capabilities=self.capabilities,
            models=list(self._known_models.keys()),
            supports_streaming=self.supports_streaming,
            supports_vision=self.supports_vision,
            supports_tool_calling=self.supports_tool_calling,
            supports_json_mode=self.supports_json_mode,
            supports_embeddings=self.supports_embeddings,
            supports_reasoning=self.supports_reasoning,
            max_context_length=self.max_context_length,
            tags=self.tags,
        )

    # ---- Error Classification ----
    def _classify_error(self, exc: Exception) -> type:
        """Map exception to the appropriate ProviderError subclass."""
        if isinstance(exc, httpx.TimeoutException):
            return ProviderTimeoutError
        if isinstance(exc, httpx.HTTPStatusError):
            status = getattr(exc.response, "status_code", None)
            if status == 429:
                return ProviderRateLimitError
            if status in (401, 403):
                return ProviderAuthError
            if status == 402:
                return QuotaExceededError
            if status == 404:
                return ProviderModelNotFoundError
            if status is not None and 500 <= status < 600:
                return ProviderServerError
            if status is not None and 400 <= status < 500:
                return ProviderError
        if isinstance(exc, (httpx.ConnectError, httpx.NetworkError, httpx.RequestError, ConnectionError)):
            return ProviderNetworkError
        if isinstance(exc, (KeyError, IndexError, TypeError, ValueError)):
            return ProviderEmptyResponseError
        return ProviderError if isinstance(exc, Exception) else type(exc)

    def _raise_provider_error(self, exc: Exception) -> None:
        error_cls = self._classify_error(exc)
        msg = self._format_error_message(exc)
        if error_cls is ProviderRateLimitError and isinstance(exc, httpx.HTTPStatusError):
            resp_headers = getattr(exc.response, "headers", {})
            retry_after_str = resp_headers.get("retry-after") or resp_headers.get("Retry-After")
            retry_after = float(retry_after_str) if retry_after_str else None
            raise ProviderRateLimitError(f"[{self.name}] {msg}", retry_after=retry_after) from exc
        raise error_cls(f"[{self.name}] {msg}") from exc

    def _format_error_message(self, exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            response = getattr(exc, "response", None)
            if response is not None:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        for key in ("error", "message", "detail", "description"):
                            val = data.get(key)
                            if val:
                                if isinstance(val, dict):
                                    return json.dumps(val)
                                return str(val)
                        return json.dumps(data)
                except Exception:
                    pass
                try:
                    text = response.text
                    if text:
                        snippet = text[:500]
                        return snippet
                except Exception:
                    pass
        return str(exc)

    def _build_response(
        self,
        content: str,
        model: str,
        latency_ms: float,
        tokens_used: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        tool_calls: list[dict[str, Any]] | None = None,
        finish_reason: str = "stop",
    ) -> RouterResponse:
        return RouterResponse(
            text=content,
            model=model,
            provider=self.name,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    # ---- Lifecycle ----
    def close(self) -> None:
        if self._http_client:
            self._http_client.close()
            self._http_client = None
        if self._async_client:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._async_client.aclose())
                else:
                    loop.run_until_complete(self._async_client.aclose())
            except Exception:
                pass
            self._async_client = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name!r}, enabled={self.is_configured})>"
