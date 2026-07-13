from __future__ import annotations

import logging
from typing import Any

from .router import AIRouter
from .config import RouterConfig
from .models import RouterResponse
from .registry import ProviderRegistry, ModelRegistry, CapabilityRegistry
from .selector import ProviderSelector
from .fallback import FallbackHandler
from .health import HealthManager
from .quota import QuotaManager
from .metrics import MetricsCollector
from .cache import RouterCache

logger = logging.getLogger(__name__)


class RouterManager:
    """High-level manager for the AI Router.

    Provides convenience methods for common operations.
    """

    def __init__(self, router: AIRouter | None = None):
        self.router = router or AIRouter()

    @property
    def config(self) -> RouterConfig:
        return self.router.config

    @property
    def provider_registry(self) -> ProviderRegistry:
        return self.router.provider_registry

    @property
    def model_registry(self) -> ModelRegistry:
        return self.router.model_registry

    @property
    def capability_registry(self) -> CapabilityRegistry:
        return self.router.capability_registry

    @property
    def selector(self) -> ProviderSelector:
        return self.router.selector

    @property
    def fallback(self) -> FallbackHandler:
        return self.router.fallback

    @property
    def health(self) -> HealthManager:
        return self.router.health

    @property
    def quota(self) -> QuotaManager:
        return self.router.quota

    @property
    def metrics(self) -> MetricsCollector:
        return self.router.metrics

    @property
    def cache(self) -> RouterCache:
        return self.router.cache

    def enabled_providers(self) -> list[str]:
        return list(self.provider_registry.provider_names)

    def configured_providers(self) -> list[str]:
        return [p.name for p in self.provider_registry.get_all().values() if p.is_configured]

    def summary(self) -> dict[str, Any]:
        return {
            "total_providers": self.provider_registry.total_providers,
            "configured_providers": len(self.configured_providers()),
            "total_models": self.model_registry.total_models,
            "providers": self.configured_providers(),
            "stats": self.metrics.summary(),
        }
