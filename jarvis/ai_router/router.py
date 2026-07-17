"""Router — The AI Router & Model Orchestration Engine.

Routes every request to the best provider based on capability, speed, cost, health.
"""

from __future__ import annotations

import time
import logging
import asyncio
from typing import Any, AsyncIterator

from .models import (
    Capability, Route, RouteStatus, RouterRequest, RouterResponse,
    HealthScore, QuotaInfo, LoadBalanceStrategy,
)
from .config import RouterConfig, load_config, router_config
from .capabilities import CapabilityDetector, detector
from .providers import ProviderRegistry, get_registry
from .health import HealthMonitor, health_monitor
from .quota import QuotaManager, quota_manager
from .metrics import MetricsCollector, metrics_collector
from .load_balancer import LoadBalancer
from .fallback import FallbackManager
from .latency import LatencyPredictor, latency_predictor
from .streaming import StreamingAdapter, streaming_adapter
from .executor import ProviderExecutor, provider_executor

logger = logging.getLogger(__name__)


class AIRouter:
    """The central AI routing engine.

    Routes requests to the best provider based on:
    - Capability requirements
    - Provider health
    - Latency predictions
    - Quota availability
    - Cost optimization
    - Load balancing

    Usage:
        router = AIRouter()
        response = await router.route(RouterRequest(text="Hello", capability=Capability.CHAT))
        # or shorthand:
        response = await router.chat("Hello")
        response = await router.reason("Explain quantum computing")
        response = await router.search("latest AI news")
    """

    def __init__(self, config: RouterConfig | None = None):
        self.config = config or load_config()
        self.registry = get_registry(self.config)
        self.health = health_monitor
        self.quota = quota_manager
        self.metrics = metrics_collector
        self.load_balancer = LoadBalancer(LoadBalanceStrategy.ADAPTIVE)
        self.fallback = FallbackManager(max_retries=self.config.max_retries)
        self.latency = latency_predictor
        self.streaming = streaming_adapter
        self.executor = provider_executor
        self.detector = detector

        self._request_count = 0
        self._cache: dict[str, RouterResponse] = {}

        logger.info("AIRouter initialized: %d providers", len(self.registry.get_enabled_providers()))

    # ───────────────────────────────────────────────────────────────────
    # HIGH-LEVEL API
    # ───────────────────────────────────────────────────────────────────

    async def chat(
        self,
        text: str,
        model: str = "",
        provider: str = "",
        messages: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> RouterResponse:
        """Send a chat request."""
        req = RouterRequest(
            text=text,
            capability=Capability.CHAT,
            model_preference=model,
            provider_preference=provider,
            **kwargs,
        )
        return await self.route(req, messages=messages)

    async def reason(self, text: str, **kwargs: Any) -> RouterResponse:
        """Send a reasoning request."""
        req = RouterRequest(text=text, capability=Capability.REASONING, **kwargs)
        return await self.route(req)

    async def code(self, text: str, **kwargs: Any) -> RouterResponse:
        """Send a coding request."""
        req = RouterRequest(text=text, capability=Capability.CODING, **kwargs)
        return await self.route(req)

    async def vision(self, text: str, image_url: str = "", **kwargs: Any) -> RouterResponse:
        """Send a vision request."""
        req = RouterRequest(text=text, capability=Capability.VISION, requires_vision=True, **kwargs)
        return await self.route(req, image_url=image_url)

    async def search(self, query: str, **kwargs: Any) -> RouterResponse:
        """Send a search request via Tavily."""
        req = RouterRequest(text=query, capability=Capability.SEARCH, **kwargs)
        return await self.route(req)

    async def embed(self, text: str, **kwargs: Any) -> RouterResponse:
        """Get embeddings for text."""
        req = RouterRequest(text=text, capability=Capability.EMBEDDINGS, **kwargs)
        return await self.route(req)

    async def image(self, prompt: str, **kwargs: Any) -> RouterResponse:
        """Generate an image."""
        req = RouterRequest(text=prompt, capability=Capability.IMAGE_GENERATION, **kwargs)
        return await self.route(req)

    async def tts(self, text: str, voice_id: str = "", **kwargs: Any) -> RouterResponse:
        """Text to speech."""
        req = RouterRequest(text=text, capability=Capability.SPEECH, **kwargs)
        return await self.route(req, voice_id=voice_id)

    # ───────────────────────────────────────────────────────────────────
    # CORE ROUTING
    # ───────────────────────────────────────────────────────────────────

    async def route(
        self,
        request: RouterRequest,
        messages: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> RouterResponse:
        """Route a request to the best provider."""
        start = time.time()
        self._request_count += 1

        # 1. Capability detection (if not set)
        cap = request.capability
        if cap == Capability.CHAT:
            det_result = self.detector.detect(request.text, request.context)
            cap = det_result.primary

        # 2. Get candidate models
        models = self.registry.get_models(capability=cap)
        if not models:
            # Fallback: try chat models
            models = self.registry.get_models(capability=Capability.CHAT)
        if not models:
            return RouterResponse(error="No models available for requested capability")

        # 3. Filter by availability
        available = [m for m in models if self.registry.is_available(m.provider)]
        if not available:
            available = models  # Use all if none available

        # 4. Build messages
        if messages is None:
            messages = [{"role": "user", "content": request.text}]

        # 5. Load balancing: select best model
        health_scores = {p: self.health.get_score(p) for p in self.registry.get_all_providers()}
        quotas = {p: self.quota.get_quota(p) for p in self.registry.get_all_providers()}

        # 6. Execute with fallback
        route, response = await self._execute_with_fallback(
            request, available, messages, health_scores, quotas, **kwargs
        )

        # 7. Update metrics
        total_ms = (time.time() - start) * 1000
        route.latency_ms = total_ms
        self.metrics.record(route, response.usage)

        # 8. Update load balancer learning
        self.load_balancer.update_learning(
            route.provider, cap.value,
            success=route.status == RouteStatus.SUCCESS,
            latency_ms=total_ms,
        )

        # 9. Record latency prediction
        tokens_in = (response.usage or {}).get("prompt_tokens", 0)
        tokens_out = (response.usage or {}).get("completion_tokens", 0)
        self.latency.record(route.provider, total_ms, tokens=tokens_in + tokens_out)

        response.route = route
        return response

    async def _execute_with_fallback(
        self,
        request: RouterRequest,
        models: list,
        messages: list[dict[str, str]],
        health_scores: dict[str, HealthScore],
        quotas: dict[str, QuotaInfo],
        **kwargs: Any,
    ) -> tuple[Route, RouterResponse]:
        """Execute request with fallback chain."""
        # Select initial model via load balancer
        selected = self.load_balancer.select(
            models, health_scores, quotas,
            capability=request.capability,
            provider_preference=request.provider_preference,
        )
        if not selected:
            return Route(status=RouteStatus.FAILED), RouterResponse(error="No model selected")

        # Build fallback chain
        chain = self.fallback.build_chain(
            selected.provider, selected.model_id, models, health_scores, request.capability
        )

        # Try primary and fallbacks
        for attempt, option in enumerate(chain):
            if attempt > 0 and self.fallback.should_give_up(attempt, len(chain)):
                break

            # Check quota
            can_use, reason = self.quota.can_use(option.provider)
            if not can_use:
                logger.debug("Quota blocked %s: %s", option.provider, reason)
                continue

            # Check health
            health = self.health.get_score(option.provider)
            if health.status.value == "unhealthy":
                logger.debug("Health blocked %s (score=%.2f)", option.provider, health.score)
                continue

            # Execute
            config = self.registry.get_provider(option.provider)
            try:
                result = await self.executor.execute(
                    provider=option.provider,
                    model=option.model,
                    messages=messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    timeout=request.timeout,
                    config=config,
                    **{k: v for k, v in kwargs.items() if k not in ("config",)},
                )

                if result.success:
                    # Record success
                    self.health.record_success(option.provider, result.latency_ms)
                    self.quota.record_usage(option.provider, result.usage.get("prompt_tokens", 0) + result.usage.get("completion_tokens", 0))

                    route = Route(
                        provider=option.provider,
                        model=option.model,
                        capability=request.capability,
                        status=RouteStatus.SUCCESS if attempt == 0 else RouteStatus.FALLBACK,
                        latency_ms=result.latency_ms,
                        attempt=attempt + 1,
                        fallback_chain=[o.provider for o in chain[:attempt + 1]],
                    )
                    response = RouterResponse(
                        content=result.content,
                        route=route,
                        usage=result.usage or {},
                        raw_response=result.raw,
                    )
                    return route, response
                else:
                    # Record failure
                    self.health.record_failure(option.provider, result.error)
                    self.quota.record_failure(option.provider)
                    logger.warning("Provider %s failed: %s", option.provider, result.error)

            except Exception as e:
                self.health.record_failure(option.provider, str(e))
                logger.warning("Provider %s exception: %s", option.provider, e)

        # All failed
        route = Route(
            status=RouteStatus.FAILED,
            fallback_chain=[o.provider for o in chain],
            attempt=len(chain),
        )
        return route, RouterResponse(error="All providers failed")

    async def route_stream(
        self,
        request: RouterRequest,
        messages: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Route and stream a request."""
        if messages is None:
            messages = [{"role": "user", "content": request.text}]

        cap = request.capability
        if cap == Capability.CHAT:
            det_result = self.detector.detect(request.text, request.context)
            cap = det_result.primary

        models = self.registry.get_models(capability=cap)
        if not models:
            models = self.registry.get_models(capability=Capability.CHAT)

        health_scores = {p: self.health.get_score(p) for p in self.registry.get_all_providers()}
        quotas = {p: self.quota.get_quota(p) for p in self.registry.get_all_providers()}

        selected = self.load_balancer.select(
            models, health_scores, quotas, capability=cap,
            provider_preference=request.provider_preference,
        )
        if not selected:
            yield "[Error: No model available]"
            return

        config = self.registry.get_provider(selected.provider)

        try:
            async for chunk in self.executor.execute_stream(
                provider=selected.provider,
                model=selected.model_id,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                config=config,
                **{k: v for k, v in kwargs.items() if k not in ("config",)},
            ):
                yield chunk
        except Exception as e:
            yield f"[Error: {e}]"

    # ───────────────────────────────────────────────────────────────────
    # QUERIES
    # ───────────────────────────────────────────────────────────────────

    def get_available_models(self, capability: str | None = None) -> list[dict[str, Any]]:
        cap = Capability(capability) if capability else None
        models = self.registry.get_models(capability=cap)
        return [m.to_dict() for m in models if self.registry.is_available(m.provider)]

    def get_provider_health(self) -> dict[str, Any]:
        return self.health.get_stats()

    def get_provider_quota(self) -> dict[str, Any]:
        return self.quota.get_stats()

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics.get_all()

    def get_latency_predictions(self) -> dict[str, Any]:
        return self.latency.get_stats()

    def get_load_balancer_stats(self) -> dict[str, Any]:
        return self.load_balancer.get_stats()

    def get_fallback_stats(self) -> dict[str, Any]:
        return self.fallback.get_stats()

    def get_registry_stats(self) -> dict[str, Any]:
        return self.registry.get_stats()

    def get_system_health(self) -> dict[str, Any]:
        """Get overall router health."""
        healthy = self.health.get_healthy_providers()
        enabled = self.registry.get_enabled_providers()
        return {
            "total_providers": len(enabled),
            "healthy_providers": len(healthy),
            "total_requests": self._request_count,
            "registry": self.registry.get_registry_stats(),
            "health": self.health.get_stats(),
            "quota": self.quota.get_stats(),
            "metrics": self.metrics.get_all(),
            "latency": self.latency.get_stats(),
            "load_balancer": self.load_balancer.get_stats(),
            "fallback": self.fallback.get_stats(),
        }


# Singleton
_router: AIRouter | None = None


def get_router(config: RouterConfig | None = None) -> AIRouter:
    global _router
    if _router is None:
        _router = AIRouter(config)
    return _router


__all__ = ["AIRouter", "get_router"]
