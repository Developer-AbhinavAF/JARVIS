from __future__ import annotations

import logging
import threading
import time
from typing import Any, Generator

from jarvis import config as app_config
from jarvis.providers.base import BaseLLMProvider
from jarvis.providers.exceptions import AllProvidersExhaustedError, ProviderError
from jarvis.providers.groq import GroqProvider
from jarvis.providers.ollama import OllamaProvider
from jarvis.providers.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


class LLMManager:
    """Manages provider fallback chain with health tracking and cooldowns.

    Order: Groq (3 keys) → OpenRouter → Ollama (local)
    """

    def __init__(self, providers: list[BaseLLMProvider] | None = None) -> None:
        self.providers = providers or self._build_default_chain()
        self._current_provider: BaseLLMProvider | None = None
        self._lock = threading.Lock()

    @staticmethod
    def _build_default_chain() -> list[BaseLLMProvider]:
        chain: list[BaseLLMProvider] = []

        groq_keys = [
            app_config.GROQ_API_KEY,
            app_config.GROQ_API_KEY2,
            app_config.GROQ_API_KEY3,
        ]
        valid_keys = [k.strip() for k in groq_keys if k and len(k.strip()) > 10]
        if valid_keys:
            chain.append(GroqProvider(
                api_keys=valid_keys,
                timeout=app_config.PROVIDER_TIMEOUT,
            ))
            logger.info("Groq provider added (%d keys)", len(valid_keys))

        if app_config.OPENROUTER_API_KEY and len(app_config.OPENROUTER_API_KEY) > 10:
            chain.append(OpenRouterProvider(
                api_key=app_config.OPENROUTER_API_KEY,
                timeout=app_config.PROVIDER_TIMEOUT + 5,
            ))
            logger.info("OpenRouter provider added")

        chain.append(OllamaProvider(
            timeout=max(app_config.OLLAMA_TIMEOUT_SECONDS, 30),
        ))
        logger.info("Ollama provider added (final fallback)")

        return chain

    @property
    def current_provider(self) -> str:
        if self._current_provider:
            return self._current_provider.name
        return "none"

    def health_summary(self) -> list[dict]:
        return [p.health() for p in self.providers]

    def generate(self, messages: list[dict], **kwargs: Any) -> str:
        last_error: Exception | None = None
        for provider in self._iter_available():
            try:
                logger.info("Using %s provider", provider.name)
                result = provider.generate(messages, **kwargs)
                self._current_provider = provider
                return result
            except ProviderError as e:
                last_error = e
                logger.warning("%s failed: %s — switching", provider.name, e)
                provider.mark_unavailable(str(e), app_config.PROVIDER_COOLDOWN_SECONDS)
                continue
        raise AllProvidersExhaustedError(
            f"All providers failed. Last error: {last_error}"
        ) from last_error

    def stream(self, messages: list[dict], **kwargs: Any) -> Generator[str, None, None]:
        last_error: Exception | None = None
        for provider in self._iter_available():
            try:
                logger.info("Using %s provider (stream)", provider.name)
                self._current_provider = provider
                yield from provider.stream(messages, **kwargs)
                return
            except ProviderError as e:
                last_error = e
                logger.warning("%s stream failed: %s — switching", provider.name, e)
                provider.mark_unavailable(str(e), app_config.PROVIDER_COOLDOWN_SECONDS)
                continue
        raise AllProvidersExhaustedError(
            f"All providers failed. Last error: {last_error}"
        ) from last_error

    def warmup_ollama(self) -> None:
        """Pre-load the Ollama model so first request doesn't pay the load penalty."""
        for p in self.providers:
            if isinstance(p, OllamaProvider) and p.is_available():
                try:
                    p._generate_impl(
                        [{"role": "user", "content": "hi"}],
                        max_tokens=1, temperature=0.3,
                    )
                    logger.info("Ollama model pre-warmed successfully")
                except Exception as e:
                    logger.warning("Ollama warmup failed (will load on first request): %s", e)
                break

    def _iter_available(self):
        """Yield available providers, respecting cooldowns, with backoff delay logging."""
        found_one = False
        for provider in self.providers:
            if not provider.is_available():
                remaining = max(0, provider.stats.cooldown_until - time.time())
                if remaining > 0:
                    logger.debug("Skipping %s (cooldown %.0fs left)", provider.name, remaining)
                    continue
            found_one = True
            yield provider
        if not found_one:
            logger.error("No providers available — all in cooldown")


_default_manager: LLMManager | None = None
_manager_lock = threading.Lock()


def get_default_manager() -> LLMManager:
    global _default_manager
    if _default_manager is None:
        with _manager_lock:
            if _default_manager is None:
                _default_manager = LLMManager()
                _default_manager.warmup_ollama()
    return _default_manager
