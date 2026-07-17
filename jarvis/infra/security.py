"""Security Layer — Protects sensitive data and controls capabilities.

API keys, tokens, passwords, permissions, audit logs, encryption.
"""

from __future__ import annotations

import os
import re
import time
import json
import base64
import hashlib
import logging
import threading
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    FILE_ACCESS = "file_access"
    TOOL_USE = "tool_use"
    API_ACCESS = "api_access"
    SETTINGS_CHANGE = "settings_change"
    DATA_EXPORT = "data_export"
    SYSTEM_COMMAND = "system_command"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: float = 0.0
    action: str = ""
    resource: str = ""
    permission: Permission = Permission.READ
    risk_level: RiskLevel = RiskLevel.LOW
    allowed: bool = True
    reason: str = ""
    user: str = ""


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    require_confirmation: list[str] = field(default_factory=lambda: ["system_command", "file_access", "data_export"])
    blocked_patterns: list[str] = field(default_factory=lambda: [
        r'password\s*[:=]', r'api[_-]?key\s*[:=]', r'secret\s*[:=]',
        r'token\s*[:=]', r'credential',
    ])
    max_audit_entries: int = 10000
    encryption_key: str = ""


class SecurityLayer:
    """Protects sensitive data and controls capabilities.

    Usage:
        security = SecurityLayer()
        security.store_secret("OPENAI_API_KEY", "sk-...")
        key = security.get_secret("OPENAI_API_KEY")
        security.audit("tool_use", "web_search", Permission.TOOL_USE)
    """

    def __init__(self, policy: SecurityPolicy | None = None):
        self._policy = policy or SecurityPolicy()
        self._secrets: dict[str, str] = {}
        self._audit_log: list[AuditEntry] = []
        self._permissions: dict[str, set[Permission]] = {}
        self._lock = threading.Lock()

    def store_secret(self, name: str, value: str):
        """Store a secret (API key, token, etc.)."""
        encoded = base64.b64encode(value.encode()).decode()
        self._secrets[name] = encoded
        logger.debug("Secret stored: %s", name)

    def get_secret(self, name: str) -> str:
        """Retrieve a secret."""
        encoded = self._secrets.get(name, "")
        if encoded:
            return base64.b64decode(encoded.encode()).decode()
        return os.environ.get(name, "")

    def has_secret(self, name: str) -> bool:
        return name in self._secrets or name in os.environ

    def remove_secret(self, name: str):
        self._secrets.pop(name, None)

    def is_sensitive(self, text: str) -> bool:
        """Check if text contains sensitive data."""
        for pattern in self._policy.blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        # Check for common secret patterns
        if re.search(r'sk-[a-zA-Z0-9]{20,}', text):
            return True
        if re.search(r'ghp_[a-zA-Z0-9]{36}', text):
            return True
        if re.search(r'xoxb-[a-zA-Z0-9-]+', text):
            return True
        return False

    def sanitize(self, text: str) -> str:
        """Remove sensitive data from text."""
        sanitized = text
        # Remove API key patterns
        sanitized = re.sub(r'sk-[a-zA-Z0-9]{20,}', '[REDACTED]', sanitized)
        sanitized = re.sub(r'ghp_[a-zA-Z0-9]{36}', '[REDACTED]', sanitized)
        sanitized = re.sub(r'xoxb-[a-zA-Z0-9-]+', '[REDACTED]', sanitized)
        # Remove key-value patterns
        for pattern in self._policy.blocked_patterns:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        return sanitized

    def grant_permission(self, resource: str, permission: Permission):
        with self._lock:
            if resource not in self._permissions:
                self._permissions[resource] = set()
            self._permissions[resource].add(permission)

    def check_permission(self, resource: str, permission: Permission) -> bool:
        with self._lock:
            perms = self._permissions.get(resource, set())
            return permission in perms

    def audit(
        self,
        action: str,
        resource: str,
        permission: Permission = Permission.READ,
        risk_level: RiskLevel = RiskLevel.LOW,
        allowed: bool = True,
        reason: str = "",
        user: str = "system",
    ) -> AuditEntry:
        """Log an audit entry."""
        entry = AuditEntry(
            timestamp=time.time(),
            action=action,
            resource=resource,
            permission=permission,
            risk_level=risk_level,
            allowed=allowed,
            reason=reason,
            user=user,
        )
        with self._lock:
            self._audit_log.append(entry)
            if len(self._audit_log) > self._policy.max_audit_entries:
                self._audit_log = self._audit_log[-self._policy.max_audit_entries:]

        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            logger.warning("AUDIT [%s] %s %s: %s (allowed=%s)", risk_level.value, action, resource, reason, allowed)

        return entry

    def needs_confirmation(self, action: str) -> bool:
        return action in self._policy.require_confirmation

    def get_audit_log(
        self,
        action: str | None = None,
        risk_level: RiskLevel | None = None,
        limit: int = 50,
    ) -> list[AuditEntry]:
        with self._lock:
            entries = list(self._audit_log)
        if action:
            entries = [e for e in entries if e.action == action]
        if risk_level:
            entries = [e for e in entries if e.risk_level == risk_level]
        return entries[-limit:]

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            entries = list(self._audit_log)
        return {
            "secrets_stored": len(self._secrets),
            "audit_entries": len(entries),
            "denied": sum(1 for e in entries if not e.allowed),
            "high_risk": sum(1 for e in entries if e.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)),
        }


# Global instance
security_layer = SecurityLayer()

__all__ = ["SecurityLayer", "SecurityPolicy", "Permission", "RiskLevel", "AuditEntry", "security_layer"]
