"""Learning Safety — Prevents learning sensitive information.

Never learn:
  Passwords, API Keys, Tokens, Private Credentials,
  Sensitive Information, Financial Info, Auth Data

Sensitive information must never enter long-term memory.
"""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = [
    re.compile(r"(?:password|passwd|pwd)\s*[=:]\s*\S+", re.I),
    re.compile(r"(?:api[_-]?key|apikey)\s*[=:]\s*\S+", re.I),
    re.compile(r"(?:token|secret|auth)\s*[=:]\s*\S+", re.I),
    re.compile(r"sk[_-][a-zA-Z0-9]{20,}"),
    re.compile(r"(?:bearer|basic)\s+[a-zA-Z0-9._-]+", re.I),
    re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b"),  # credit card
    re.compile(r"\b\d{3}[\s.-]?\d{2}[\s.-]?\d{4}\b"),  # SSN
    re.compile(r"(?:ssh-rsa|ssh-ed25519|ecdsa)\s+[a-zA-Z0-9+/=]+"),
]

SENSITIVE_KEYS = frozenset({
    "password", "passwd", "pwd", "api_key", "apikey", "secret",
    "token", "auth", "credentials", "private_key", "access_token",
    "refresh_token", "session_token", "encryption_key", "ssn",
    "credit_card", "bank_account", "routing_number",
})


class LearningSafety:
    """Validates data before it enters long-term memory."""

    def __init__(self) -> None:
        self._blocked_count: int = 0

    def is_safe(self, text: str) -> bool:
        """Check if text contains sensitive information."""
        if not text:
            return True

        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                self._blocked_count += 1
                logger.warning("Blocked sensitive content: %s...", text[:50])
                return False
        return True

    def is_safe_dict(self, data: dict[str, Any]) -> bool:
        """Check if a dictionary contains sensitive keys."""
        for key in data:
            if key.lower() in SENSITIVE_KEYS:
                self._blocked_count += 1
                logger.warning("Blocked sensitive key: %s", key)
                return False
            val = data[key]
            if isinstance(val, str) and not self.is_safe(val):
                return False
        return True

    def sanitize(self, text: str) -> str:
        """Remove sensitive patterns from text."""
        result = text
        for pattern in SENSITIVE_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result

    def get_stats(self) -> dict[str, Any]:
        return {"blocked_count": self._blocked_count}


learning_safety = LearningSafety()

__all__ = ["LearningSafety", "learning_safety"]
