from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from jarvis.router_service import router_client

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    latency_ms: float
    tokens_used: int = 0
    cached: bool = False


class MultiLLMManager:
    """Multi-LLM manager — all requests routed through the AI Router.

    The router handles provider selection, failover, and load balancing
    across 20+ providers. This class is kept for API compatibility.
    """

    def __init__(self) -> None:
        self.client = router_client
        self.response_cache: dict[str, LLMResponse] = {}
        self.cache_enabled = True
        self.cache_ttl = 300

    def get_available_providers(self) -> list[str]:
        return ["router"]

    def chat(
        self,
        messages: list[dict],
        preferred_provider: str | None = None,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> LLMResponse:
        cache_key = self._get_cache_key(messages)
        if use_cache and self.cache_enabled:
            cached = self._get_cached(cache_key)
            if cached:
                cached.cached = True
                return cached

        try:
            start = time.time()
            text = self.client.chat(
                messages,
                max_tokens=kwargs.get("max_tokens", 1024),
                temperature=kwargs.get("temperature", 0.7),
                response_format=kwargs.get("response_format"),
            )
            latency = (time.time() - start) * 1000

            response = LLMResponse(
                text=text,
                model=self.client.model or "router-default",
                provider="router",
                latency_ms=latency,
            )

            if use_cache and self.cache_enabled:
                self._cache_response(cache_key, response)

            return response

        except Exception as e:
            logger.error("Router request failed: %s", e)
            raise RuntimeError(f"All AI providers failed: {e}") from e

    def _get_cache_key(self, messages: list[dict]) -> str:
        content = json.dumps(messages, sort_keys=True)
        return str(hash(content))

    def _get_cached(self, key: str) -> LLMResponse | None:
        if key not in self.response_cache:
            return None
        return self.response_cache[key]

    def _cache_response(self, key: str, response: LLMResponse) -> None:
        self.response_cache[key] = response
        if len(self.response_cache) > 100:
            oldest = next(iter(self.response_cache))
            del self.response_cache[oldest]

    def get_stats(self) -> dict[str, Any]:
        return {
            "router": {
                "name": "AI Router v3.0",
                "status": "active",
                "providers": len(self.client._router.provider_registry.get_available()),
            }
        }

    def clear_cache(self) -> None:
        self.response_cache.clear()


multi_llm = MultiLLMManager()
