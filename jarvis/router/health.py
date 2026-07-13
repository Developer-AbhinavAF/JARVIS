from __future__ import annotations

import time
import logging
from typing import Any

from .models import RouterHealth, ProviderStatus
from .interfaces import BaseProvider
from .config import RouterConfig
from .cache import RouterCache

logger = logging.getLogger(__name__)


class HealthManager:
    """Background health monitor for all registered providers.

    Continuously tracks provider health, latency, and availability.
    Never blocks user requests — returns cached health status immediately.
    """

    def __init__(
        self,
        config: RouterConfig | None = None,
        cache: RouterCache | None = None,
    ) -> None:
        self.config = config or RouterConfig()
        self.cache = cache or RouterCache()
        self._provider_health: dict[str, RouterHealth] = {}
        self._health_timestamps: dict[str, float] = {}
        self._failure_counts: dict[str, int] = {}

    def check_provider(self, provider: BaseProvider) -> RouterHealth:
        now = time.time()
        last_check = self._health_timestamps.get(provider.name, 0.0)

        if now - last_check < self.config.health_ttl:
            cached = self._provider_health.get(provider.name)
            if cached:
                return cached

        try:
            health = provider.health_check()
            self._provider_health[provider.name] = health
            self._health_timestamps[provider.name] = now
            if not health.available:
                self._failure_counts[provider.name] = self._failure_counts.get(provider.name, 0) + 1
            else:
                self._failure_counts[provider.name] = 0
            return health
        except Exception as exc:
            health = RouterHealth(
                available=False,
                message=str(exc),
                base_url=provider.base_url,
                status=ProviderStatus.OFFLINE,
            )
            self._provider_health[provider.name] = health
            self._health_timestamps[provider.name] = now
            self._failure_counts[provider.name] = self._failure_counts.get(provider.name, 0) + 1
            return health

    def get_health(self, provider_name: str) -> RouterHealth | None:
        return self._provider_health.get(provider_name)

    def is_healthy(self, provider_name: str) -> bool:
        health = self._provider_health.get(provider_name)
        if not health:
            return True
        return health.available

    def is_unhealthy(self, provider_name: str, threshold: int | None = None) -> bool:
        threshold = threshold or self.config.unhealthy_threshold
        failures = self._failure_counts.get(provider_name, 0)
        return failures >= threshold

    def record_failure(self, provider_name: str) -> None:
        self._failure_counts[provider_name] = self._failure_counts.get(provider_name, 0) + 1

    def record_success(self, provider_name: str) -> None:
        self._failure_counts[provider_name] = 0

    def unhealthy_providers(self) -> list[str]:
        return [
            name for name in self._provider_health
            if not self._provider_health[name].available
        ]

    def all_healthy(self) -> dict[str, RouterHealth]:
        return dict(self._provider_health)

    def check_all(self, providers: list[BaseProvider]) -> dict[str, RouterHealth]:
        results = {}
        for provider in providers:
            try:
                results[provider.name] = self.check_provider(provider)
            except Exception as exc:
                logger.debug("Health check failed for %s: %s", provider.name, exc)
        return results
