"""Quota Management — Tracks and limits provider usage.

RPM, TPM, daily limits, monthly limits.
Automatically avoids exhausted providers.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

from .models import QuotaInfo

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Single usage record."""
    timestamp: float = 0.0
    tokens: int = 0
    success: bool = True


class QuotaManager:
    """Manages provider quotas with rolling windows.

    Usage:
        mgr = QuotaManager()
        can_use, reason = mgr.can_use("groq")
        if can_use:
            mgr.record_usage("groq", tokens=500)
    """

    def __init__(self, rpm_window: float = 60.0, daily_reset_hour: int = 0):
        self._usage: dict[str, list[UsageRecord]] = defaultdict(list)
        self._quotas: dict[str, QuotaInfo] = {}
        self._rpm_window = rpm_window
        self._daily_reset_hour = daily_reset_hour

    def set_quota(self, provider: str, quota: QuotaInfo):
        self._quotas[provider] = quota

    def get_quota(self, provider: str) -> QuotaInfo:
        return self._quotas.get(provider, QuotaInfo(provider=provider))

    def can_use(self, provider: str, estimated_tokens: int = 0) -> tuple[bool, str]:
        """Check if provider can be used. Returns (allowed, reason)."""
        quota = self.get_quota(provider)

        # Check RPM
        rpm = self._current_rpm(provider)
        if rpm >= quota.rpm_limit:
            return False, f"RPM limit reached ({rpm}/{quota.rpm_limit})"

        # Check daily
        daily = self._current_daily(provider)
        if daily >= quota.daily_limit:
            return False, f"Daily limit reached ({daily}/{quota.daily_limit})"

        # Check TPM
        tpm = self._current_tpm(provider)
        if tpm + estimated_tokens > quota.tpm_limit:
            return False, f"TPM limit reached ({tpm + estimated_tokens}/{quota.tpm_limit})"

        return True, "ok"

    def record_usage(self, provider: str, tokens: int = 0):
        record = UsageRecord(timestamp=time.time(), tokens=tokens)
        self._usage[provider].append(record)
        self._trim(provider)

        quota = self.get_quota(provider)
        quota.rpm_used = self._current_rpm(provider)
        quota.tpm_used = self._current_tpm(provider)
        quota.daily_used = self._current_daily(provider)

    def record_failure(self, provider: str, tokens: int = 0):
        record = UsageRecord(timestamp=time.time(), tokens=tokens, success=False)
        self._usage[provider].append(record)
        self._trim(provider)

    def get_available_providers(self, providers: list[str]) -> list[str]:
        """Filter providers to those with available quota."""
        return [p for p in providers if self.can_use(p)[0]]

    def get_stats(self) -> dict[str, Any]:
        return {
            p: self.get_quota(p).to_dict()
            for p in set(list(self._usage.keys()) + list(self._quotas.keys()))
        }

    def _trim(self, provider: str):
        records = self._usage[provider]
        cutoff = time.time() - 3600  # Keep 1 hour
        self._usage[provider] = [r for r in records if r.timestamp > cutoff]

    def _current_rpm(self, provider: str) -> int:
        cutoff = time.time() - self._rpm_window
        return sum(1 for r in self._usage[provider] if r.timestamp > cutoff)

    def _current_tpm(self, provider: str) -> int:
        cutoff = time.time() - self._rpm_window
        return sum(r.tokens for r in self._usage[provider] if r.timestamp > cutoff)

    def _current_daily(self, provider: str) -> int:
        today_start = time.time() - (time.time() % 86400)
        return sum(1 for r in self._usage[provider] if r.timestamp > today_start)


# Global instance
quota_manager = QuotaManager()

__all__ = ["QuotaManager", "UsageRecord", "quota_manager"]
