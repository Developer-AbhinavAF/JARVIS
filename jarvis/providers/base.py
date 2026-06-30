from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generator

from jarvis.providers.exceptions import ProviderError

logger = logging.getLogger(__name__)


@dataclass
class ProviderStats:
    available: bool = True
    cooldown_until: float = 0.0
    avg_latency_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    total_requests: int = 0
    last_failure: str = ""
    consecutive_failures: int = 0


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self) -> None:
        self.stats = ProviderStats()

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def _generate_impl(self, messages: list[dict], **kwargs: Any) -> str:
        ...

    @abstractmethod
    def _stream_impl(self, messages: list[dict], **kwargs: Any) -> Generator[str, None, None]:
        ...

    def generate(self, messages: list[dict], **kwargs: Any) -> str:
        t0 = time.time()
        try:
            result = self._generate_impl(messages, **kwargs)
            self._record_success(time.time() - t0)
            return result
        except ProviderError:
            self._record_failure(time.time() - t0)
            raise

    def stream(self, messages: list[dict], **kwargs: Any) -> Generator[str, None, None]:
        t0 = time.time()
        try:
            yield from self._stream_impl(messages, **kwargs)
            self._record_success(time.time() - t0)
        except ProviderError:
            self._record_failure(time.time() - t0)
            raise

    def is_available(self) -> bool:
        if not self.stats.available:
            if time.time() >= self.stats.cooldown_until:
                self.stats.available = True
                logger.info("%s cooldown expired, marked available again", self.name)
        return self.stats.available

    def health(self) -> dict:
        return {
            "name": self.name,
            "available": self.is_available(),
            "avg_latency_ms": round(self.stats.avg_latency_ms, 1),
            "success_count": self.stats.success_count,
            "failure_count": self.stats.failure_count,
            "total_requests": self.stats.total_requests,
            "last_failure": self.stats.last_failure,
        }

    def mark_unavailable(self, reason: str, cooldown: float = 60.0) -> None:
        self.stats.available = False
        self.stats.cooldown_until = time.time() + cooldown
        self.stats.last_failure = reason

    def _record_success(self, elapsed: float) -> None:
        latency = elapsed * 1000
        n = self.stats.success_count
        self.stats.avg_latency_ms = (self.stats.avg_latency_ms * n + latency) / (n + 1)
        self.stats.success_count += 1
        self.stats.total_requests += 1
        self.stats.consecutive_failures = 0

    def _record_failure(self, elapsed: float) -> None:
        self.stats.failure_count += 1
        self.stats.total_requests += 1
        self.stats.consecutive_failures += 1
