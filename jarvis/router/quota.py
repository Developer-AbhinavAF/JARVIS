from __future__ import annotations

import time
import random
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .config import RouterConfig

logger = logging.getLogger(__name__)


@dataclass
class QuotaState:
    """Tracks quota usage for a single provider."""
    rpm: int = 0
    tpm: int = 0
    daily_usage: int = 0
    monthly_usage: int = 0
    credits_remaining: float = 0.0
    last_reset_rpm: float = field(default_factory=time.time)
    last_reset_tpm: float = field(default_factory=time.time)
    last_reset_daily: float = field(default_factory=time.time)
    rate_limited_until: float = 0.0
    consecutive_429s: int = 0


class QuotaManager:
    """Tracks and enforces API quota limits across providers."""

    def __init__(self, config: RouterConfig | None = None):
        self.config = config or RouterConfig()
        self._quotas: dict[str, QuotaState] = defaultdict(QuotaState)
        self._limits: dict[str, dict[str, int]] = {}

    def set_limits(
        self,
        provider: str,
        rpm: int = 0,
        tpm: int = 0,
        daily: int = 0,
        monthly: int = 0,
    ) -> None:
        self._limits[provider] = {
            "rpm": rpm,
            "tpm": tpm,
            "daily": daily,
            "monthly": monthly,
        }

    def record_request(
        self,
        provider: str,
        tokens: int = 0,
    ) -> None:
        quota = self._quotas[provider]
        now = time.time()

        if now - quota.last_reset_rpm > 60:
            quota.rpm = 0
            quota.last_reset_rpm = now
        if now - quota.last_reset_tpm > 60:
            quota.tpm = 0
            quota.last_reset_tpm = now
        if now - quota.last_reset_daily > 86400:
            quota.daily_usage = 0
            quota.last_reset_daily = now

        quota.rpm += 1
        quota.tpm += tokens
        quota.daily_usage += tokens
        quota.monthly_usage += tokens

    def record_rate_limit(self, provider: str, retry_after: float | None = None) -> None:
        quota = self._quotas[provider]
        quota.consecutive_429s += 1
        if retry_after is not None:
            jitter = random.uniform(0, 5)
            backoff = retry_after + jitter
        else:
            backoff = min((2 ** quota.consecutive_429s) * 5, 120)
            jitter = random.uniform(0, backoff * 0.1)
            backoff += jitter
        quota.rate_limited_until = time.time() + backoff
        logger.warning("Provider %s rate limited, backing off %ds", provider, int(backoff))

    def record_success(self, provider: str) -> None:
        self._quotas[provider].consecutive_429s = 0

    def is_rate_limited(self, provider: str) -> bool:
        quota = self._quotas[provider]
        if time.time() < quota.rate_limited_until:
            return True

        limits = self._limits.get(provider, {})
        if limits.get("rpm") and quota.rpm >= limits["rpm"]:
            return True
        if limits.get("tpm") and quota.tpm >= limits["tpm"]:
            return True
        if limits.get("daily") and quota.daily_usage >= limits["daily"]:
            return True
        return False

    def get_quota(self, provider: str) -> QuotaState:
        return self._quotas[provider]

    def summary(self) -> dict[str, Any]:
        return {
            name: {
                "rpm": q.rpm,
                "tpm": q.tpm,
                "daily_usage": q.daily_usage,
                "consecutive_429s": q.consecutive_429s,
                "is_rate_limited": self.is_rate_limited(name),
            }
            for name, q in self._quotas.items()
        }
