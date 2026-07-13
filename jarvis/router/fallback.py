from __future__ import annotations

import logging
from typing import Any, Callable, Iterator

from .models import RouterResponse, StreamChunk, ChatRequest, Capability
from .interfaces import BaseProvider
from .health import HealthManager
from .quota import QuotaManager
from .exceptions import (
    ProviderError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderTimeoutError,
    ProviderNetworkError,
    ProviderEmptyResponseError,
    ProviderOfflineError,
    ProviderModelNotFoundError,
    QuotaExceededError,
    AllProvidersExhaustedError,
)
from .config import RouterConfig

logger = logging.getLogger(__name__)


class FallbackHandler:
    """Smart fallback across providers.

    Never performs slow sequential retries.
    Skips unhealthy providers using health cache.
    Instantly switches to next available provider.
    """

    def __init__(
        self,
        config: RouterConfig | None = None,
        health_manager: HealthManager | None = None,
        quota_manager: QuotaManager | None = None,
    ) -> None:
        self.config = config or RouterConfig()
        self.health = health_manager or HealthManager(config)
        self.quota = quota_manager or QuotaManager(config)

    def _is_eligible(self, provider: BaseProvider) -> bool:
        if not provider.is_configured:
            return False
        if self.health.is_unhealthy(provider.name):
            return False
        if self.health.is_healthy(provider.name):
            return True
        health = self.health.get_health(provider.name)
        return health is None or health.available

    def execute_with_fallback(
        self,
        providers: list[BaseProvider],
        request: ChatRequest,
        execute_fn: Callable[[BaseProvider, ChatRequest], RouterResponse],
    ) -> RouterResponse:
        errors: list[str] = []
        max_attempts = min(self.config.fallback_max_providers, len(providers))

        for i, provider in enumerate(providers[:max_attempts]):
            if not self._is_eligible(provider):
                logger.debug("Skipping %s (not eligible)", provider.name)
                continue

            try:
                response = execute_fn(provider, request)
                self.health.record_success(provider.name)
                self.quota.record_success(provider.name)
                return response
            except ProviderRateLimitError as exc:
                self.quota.record_rate_limit(provider.name, retry_after=getattr(exc, 'retry_after', None))
                errors.append(f"{provider.name}: rate limited")
                continue
            except QuotaExceededError:
                self.quota.record_rate_limit(provider.name)
                errors.append(f"{provider.name}: quota exceeded")
                continue
            except ProviderAuthError:
                errors.append(f"{provider.name}: auth error")
                continue
            except ProviderModelNotFoundError:
                errors.append(f"{provider.name}: model not found")
                continue
            except ProviderTimeoutError:
                self.health.record_failure(provider.name)
                errors.append(f"{provider.name}: timeout")
                continue
            except ProviderEmptyResponseError:
                errors.append(f"{provider.name}: empty response")
                continue
            except (ProviderOfflineError, ConnectionError, OSError):
                self.health.record_failure(provider.name)
                errors.append(f"{provider.name}: offline")
                continue
            except ProviderError as exc:
                errors.append(f"{provider.name}: {exc}")
                continue
            except Exception as exc:
                errors.append(f"{provider.name}: unexpected error: {exc}")
                continue

        raise AllProvidersExhaustedError(
            f"All {len(providers)} provider(s) failed: {'; '.join(errors)}"
        )

    def execute_stream_with_fallback(
        self,
        providers: list[BaseProvider],
        request: ChatRequest,
        stream_fn: Callable[[BaseProvider, ChatRequest], Iterator[StreamChunk]],
    ) -> Iterator[StreamChunk]:
        errors: list[str] = []
        max_attempts = min(self.config.fallback_max_providers, len(providers))

        for i, provider in enumerate(providers[:max_attempts]):
            if not self._is_eligible(provider):
                continue

            try:
                yield from stream_fn(provider, request)
                self.health.record_success(provider.name)
                return
            except ProviderRateLimitError as exc:
                self.quota.record_rate_limit(provider.name, retry_after=getattr(exc, 'retry_after', None))
                errors.append(f"{provider.name}: rate limited")
                continue
            except (ProviderTimeoutError, ProviderNetworkError, ConnectionError) as exc:
                self.health.record_failure(provider.name)
                errors.append(f"{provider.name}: {exc}")
                continue
            except QuotaExceededError:
                self.quota.record_rate_limit(provider.name)
                errors.append(f"{provider.name}: quota exceeded")
                continue
            except ProviderError as exc:
                errors.append(f"{provider.name}: {exc}")
                continue
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                continue

        raise AllProvidersExhaustedError(
            f"Streaming failed across all providers: {'; '.join(errors)}"
        )
