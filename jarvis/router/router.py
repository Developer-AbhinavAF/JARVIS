from __future__ import annotations

import time
import logging
from typing import Any, Generator

from .config import RouterConfig
from .models import (
    RouterResponse,
    RouterHealth,
    ChatRequest,
    EmbeddingRequest,
    StreamChunk,
    Capability,
    LoadBalanceStrategy,
    ProviderStatus,
)
from .interfaces import BaseProvider
from .exceptions import (
    RouterError,
    ProviderError,
    AllProvidersExhaustedError,
    NoProviderForModelError,
    NoProviderForCapabilityError,
)
from .registry import ProviderRegistry, ModelRegistry, CapabilityRegistry
from .health import HealthManager
from .quota import QuotaManager
from .metrics import MetricsCollector
from .cache import RouterCache
from .selector import ProviderSelector
from .fallback import FallbackHandler
from .validator import RequestValidator
from .streaming import StreamingManager
from .capabilities import CapabilityDetector
from .scheduler import BackgroundScheduler
from .benchmark import Benchmark
from .providers import get_all_provider_classes

logger = logging.getLogger(__name__)


class AIRouter:
    """Intelligent multi-provider AI Router — the heart of JARVIS v3.0.

    Every request passes through:
    Router → Capability Detection → Provider Selection → Model Selection
    → Health Validation → Quota Validation → Execution → Response → Return

    Supports 20+ providers with auto-registration, health monitoring,
    smart fallback, caching, metrics, and auto-learning.
    """

    def __init__(
        self,
        config: RouterConfig | None = None,
        auto_register: bool = True,
    ) -> None:
        self.config = config or RouterConfig()
        self.validator = RequestValidator()
        self.capability_detector = CapabilityDetector()
        self.cache = RouterCache(self.config)
        self.health = HealthManager(self.config, self.cache)
        self.quota = QuotaManager(self.config)
        self.metrics = MetricsCollector()
        self.provider_registry = ProviderRegistry(self.config)
        self.model_registry = ModelRegistry(self.provider_registry)
        self.capability_registry = CapabilityRegistry(self.provider_registry)
        self.selector = ProviderSelector(self.provider_registry, self.health, self.quota)
        self.fallback = FallbackHandler(self.config, self.health, self.quota)
        self.streaming = StreamingManager()
        self.benchmark = Benchmark()
        self.scheduler = BackgroundScheduler()

        self._default_model = self.config.default_model
        self._default_provider = self.config.default_provider

        if auto_register:
            self._auto_register()

    def _auto_register(self) -> None:
        """Auto-discover and register all available providers."""
        provider_classes = get_all_provider_classes()
        self.provider_registry.register_all(provider_classes)
        self.model_registry.build_from_providers()
        self.capability_registry.build_from_providers()

        configured = self.provider_registry.total_providers
        total = len(provider_classes)
        logger.info(
            "Router initialized: %d/%d providers configured, %d models registered",
            configured, total, self.model_registry.total_models,
        )

    def _build_chat_request(self, **kwargs: Any) -> ChatRequest:
        return ChatRequest(
            messages=kwargs.get("messages", []),
            model=kwargs.get("model") or self._default_model,
            max_tokens=kwargs.get("max_tokens"),
            temperature=kwargs.get("temperature"),
            stream=kwargs.get("stream", False),
            response_format=kwargs.get("response_format"),
            tools=kwargs.get("tools"),
            tool_choice=kwargs.get("tool_choice"),
            stop=kwargs.get("stop"),
        )

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
        request = self._build_chat_request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            stop=stop,
        )
        response = self.chat_result(**request.__dict__)
        return response.text

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
        request = self._build_chat_request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            stream=False,
        )

        self.validator.validate_chat_request(request)

        cache_key = self._cache_key(request)
        if self.config.cache_enabled:
            cached = self.cache.get_response(cache_key)
            if cached:
                cached.cached = True
                return cached

        capabilities = self.capability_detector.detect(request)

        if request.model:
            providers = self.selector.select_for_model(request.model)
            if not providers:
                providers = self.selector.select(request=request)
        else:
            providers = self.selector.select(request=request)

        if not providers:
            raise NoProviderForModelError(f"No provider available for model={request.model}")

        def execute(provider: BaseProvider, req: ChatRequest) -> RouterResponse:
            return provider.chat(req)

        try:
            response = self.fallback.execute_with_fallback(providers, request, execute)
        except AllProvidersExhaustedError as exc:
            raise AllProvidersExhaustedError(str(exc)) from exc

        self.metrics.record_request(
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            tokens_used=response.tokens_used,
        )

        if self.config.cache_enabled:
            self.cache.set_response(cache_key, response)

        return response

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
        request = self._build_chat_request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            stream=True,
        )

        self.validator.validate_chat_request(request)

        if request.model:
            providers = self.selector.select_for_model(request.model)
            if not providers:
                providers = self.selector.select(request=request)
        else:
            providers = self.selector.select(request=request)

        if not providers:
            raise NoProviderForModelError(f"No provider available for model={request.model}")

        def execute_stream(provider: BaseProvider, req: ChatRequest) -> Generator[StreamChunk, None, None]:
            yield from provider.chat_stream(req)

        collected: list[str] = []
        response_provider = ""
        response_model = ""

        try:
            for chunk in self.fallback.execute_stream_with_fallback(providers, request, execute_stream):
                if chunk.content:
                    collected.append(chunk.content)
                    yield chunk.content
                if chunk.provider:
                    response_provider = chunk.provider
                if chunk.model:
                    response_model = chunk.model
        except AllProvidersExhaustedError as exc:
            raise AllProvidersExhaustedError(str(exc)) from exc

        if response_provider:
            self.metrics.record_request(
                provider=response_provider,
                model=response_model or request.model or "unknown",
                latency_ms=0,
                tokens_used=len("".join(collected)) // 4,
            )

    def embed(
        self,
        input_texts: str | list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        if isinstance(input_texts, str):
            input_texts = [input_texts]

        request = EmbeddingRequest(input_texts=input_texts, model=model)
        self.validator.validate_embedding_request(request)

        cache_key = f"embed:{model}:{hash(tuple(input_texts))}"
        if self.config.cache_enabled:
            cached = self.cache.get_embedding(cache_key)
            if cached:
                return cached

        providers = self.selector.select_for_capability(Capability.EMBEDDING)
        if not providers:
            providers = self.provider_registry.get_available()

        if not providers:
            raise NoProviderForCapabilityError("No embedding-capable provider available")

        start = time.time()
        last_error: Exception | None = None

        for provider in providers:
            if not provider.supports_embeddings:
                continue
            try:
                result = provider.embed(request)
                self.metrics.record_embedding(provider.name)
                if self.config.cache_enabled:
                    self.cache.set_embedding(cache_key, result)
                return result
            except Exception as exc:
                last_error = exc
                continue

        raise AllProvidersExhaustedError(f"Embedding failed on all providers: {last_error}")

    def health_check(self) -> RouterHealth:
        providers = self.provider_registry.get_available()
        healthy_count = 0
        total_latency = 0.0
        messages: list[str] = []

        for provider in providers[:5]:
            health = self.health.check_provider(provider)
            if health.available:
                healthy_count += 1
                total_latency += health.latency_ms

        if not providers:
            return RouterHealth(
                available=False,
                message="No providers configured",
                status=ProviderStatus.OFFLINE,
            )

        avg_latency = total_latency / max(healthy_count, 1)
        all_healthy = healthy_count == len(providers)
        return RouterHealth(
            available=healthy_count > 0,
            message=f"{healthy_count}/{len(providers)} providers healthy",
            latency_ms=avg_latency,
            status=ProviderStatus.ONLINE if all_healthy else ProviderStatus.DEGRADED,
        )

    def is_available(self) -> bool:
        return len(self.provider_registry.get_available()) > 0

    def get_providers(self) -> list[dict[str, Any]]:
        return [p.get_provider_info() for p in self.provider_registry.get_all().values()]

    def get_stats(self) -> dict[str, Any]:
        return self.metrics.summary()

    def close(self) -> None:
        self.scheduler.stop()
        self.provider_registry.close_all()

    def _cache_key(self, request: ChatRequest) -> str:
        import hashlib, json
        raw = json.dumps({
            "model": request.model,
            "messages": request.messages,
            "tools": request.tools,
            "response_format": request.response_format,
        }, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()
