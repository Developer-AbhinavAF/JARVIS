"""core/safety.py — Advanced Safety & Confirmation Layer for JARVIS vNext++.

Intercepts high-risk operations (file deletion, system shutdown, registry edits,
PowerShell execution, network resets) and requires explicit confirmation.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


HIGH_RISK_TOOLS = {
    "delete_file",
    "remove_directory",
    "system_shutdown",
    "system_restart",
    "execute_powershell",
    "modify_registry",
    "file_overwrite",
}


@dataclass
class PendingConfirmation:
    confirmation_id: str
    tool_name: str
    args: Dict[str, Any]
    created_at: float = time.time()
    ttl_seconds: float = 30.0

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


class SafetyLayer:
    """Manages high-risk tool execution safety."""

    def __init__(self):
        self._pending: Dict[str, PendingConfirmation] = {}

    def is_high_risk(self, tool_name: str, args: Dict[str, Any] = None) -> bool:
        """Check if tool action is high-risk."""
        return tool_name.lower().strip() in HIGH_RISK_TOOLS

    def request_confirmation(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Create pending confirmation token."""
        token = f"confirm_{tool_name}_{int(time.time())}"
        self._pending[token] = PendingConfirmation(
            confirmation_id=token, tool_name=tool_name, args=args
        )
        logger.warning(f"High-risk action '{tool_name}' requires user confirmation ({token})")
        return token

    def confirm_action(self, token: str) -> bool:
        """Validate and confirm high-risk action token."""
        pending = self._pending.get(token)
        if not pending:
            return False
        if pending.is_expired():
            del self._pending[token]
            logger.warning(f"Confirmation token {token} expired.")
            return False
        del self._pending[token]
        return True


safety_layer = SafetyLayer()
