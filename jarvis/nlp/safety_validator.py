"""Safety validator for JARVIS NLP.

Validates actions before execution to prevent dangerous operations.
Checks for dangerous files, system folders, delete operations,
registry edits, power commands, network commands, and package installs.

Only asks confirmation when actually necessary.
Never asks for safe actions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# ════════════════════════════════════════════════════════════════════
# DANGEROUS PATTERNS
# ════════════════════════════════════════════════════════════════════

# System folders that should never be modified
_SYSTEM_FOLDERS: set[str] = {
    "c:\\windows", "c:\\program files", "c:\\program files (x86)",
    "/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc",
    "/var", "/root", "c:\\system32", "c:\\drivers",
}

# Destructive operations
_DESTRUCTIVE_INTENTS: set[str] = {
    "SYSTEM_POWER", "SHUTDOWN", "RESTART", "SLEEP",
    "DELETE_FILE", "DELETE_FOLDER", "FILE_MANAGEMENT",
    "UNINSTALL_APP",
}

# Power commands that need confirmation
_POWER_COMMANDS: set[str] = {
    "shutdown", "restart", "reboot", "hibernate",
    "logoff", "lock", "sleep",
}

# Dangerous file extensions
_DANGEROUS_EXTENSIONS: set[str] = {
    ".exe", ".bat", ".cmd", ".com", ".msi", ".reg",
    ".sys", ".drv", ".dll", ".scr", ".pif",
}

# Registry patterns
_REGISTRY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"hkey_", re.IGNORECASE),
    re.compile(r"registry", re.IGNORECASE),
    re.compile(r"regedit", re.IGNORECASE),
]

# Package manager commands
_PACKAGE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(pip|npm|yarn|cargo|apt|brew|choco|winget)\s+(install|uninstall|remove)\b", re.IGNORECASE),
    re.compile(r"\b(install|uninstall|remove)\s+(package|module|library)\b", re.IGNORECASE),
]

# Network commands that modify firewall/network
_NETWORK_MODIFY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(firewall|iptables|netsh)\b", re.IGNORECASE),
    re.compile(r"\b(block|allow)\s+(port|ip|traffic)\b", re.IGNORECASE),
]


# ════════════════════════════════════════════════════════════════════
# SAFETY LEVELS
# ════════════════════════════════════════════════════════════════════

class SafetyLevel:
    SAFE = "safe"                  # Execute immediately
    LOW_RISK = "low_risk"          # Execute, but log
    MEDIUM_RISK = "medium_risk"    # Execute with caution flag
    HIGH_RISK = "high_risk"        # Ask confirmation
    BLOCKED = "blocked"            # Refuse execution


@dataclass
class SafetyCheck:
    """Result of a safety validation check."""
    level: str
    is_safe: bool
    requires_confirmation: bool
    risks: list[str]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "is_safe": self.is_safe,
            "requires_confirmation": self.requires_confirmation,
            "risks": self.risks,
            "message": self.message,
        }


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

class SafetyValidator:
    """Validates actions before execution to prevent dangerous operations.

    Checks multiple safety signals and returns a SafetyCheck with the
    appropriate safety level and any risks detected.
    """

    def validate(
        self,
        intent: str,
        entities: dict[str, Any],
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> SafetyCheck:
        """Validate the safety of an action before execution.

        Parameters
        ----------
        intent:
            The classified intent string.
        entities:
            Extracted entities from the NLP pipeline.
        parameters:
            Parameters that will be passed to the handler.
        context:
            Optional conversation context.

        Returns
        -------
        SafetyCheck with safety level and risk details.
        """
        risks: list[str] = []

        # 1. Check intent-level risks
        intent_risks = self._check_intent_risks(intent)
        risks.extend(intent_risks)

        # 2. Check entity/parameter risks
        entity_risks = self._check_entity_risks(entities, parameters)
        risks.extend(entity_risks)

        # 3. Check path/file risks
        path_risks = self._check_path_risks(entities, parameters)
        risks.extend(path_risks)

        # 4. Check text-based risks (registry, network, packages)
        text_risks = self._check_text_risks(entities, parameters)
        risks.extend(text_risks)

        # Determine safety level
        if not risks:
            return SafetyCheck(
                level=SafetyLevel.SAFE,
                is_safe=True,
                requires_confirmation=False,
                risks=[],
                message="",
            )

        # Check for blocked operations
        if any("BLOCKED" in r for r in risks):
            return SafetyCheck(
                level=SafetyLevel.BLOCKED,
                is_safe=False,
                requires_confirmation=False,
                risks=risks,
                message="This operation has been blocked for safety reasons.",
            )

        # High risk: power commands, destructive operations on system paths
        high_risk_keywords = {"POWER", "SYSTEM_PATH", "REGISTRY", "FIREWALL"}
        is_high = any(
            any(kw in r for kw in high_risk_keywords)
            for r in risks
        )

        if is_high:
            return SafetyCheck(
                level=SafetyLevel.HIGH_RISK,
                is_safe=True,
                requires_confirmation=True,
                risks=risks,
                message=self._generate_confirmation_message(intent, risks),
            )

        # Medium risk: file deletion, app uninstall
        medium_risk_keywords = {"DELETE", "UNINSTALL", "PACKAGE"}
        is_medium = any(
            any(kw in r for kw in medium_risk_keywords)
            for r in risks
        )

        if is_medium:
            return SafetyCheck(
                level=SafetyLevel.MEDIUM_RISK,
                is_safe=True,
                requires_confirmation=False,
                risks=risks,
                message="",
            )

        # Low risk: just informational
        return SafetyCheck(
            level=SafetyLevel.LOW_RISK,
            is_safe=True,
            requires_confirmation=False,
            risks=risks,
            message="",
        )

    def is_destructive(self, intent: str, parameters: dict[str, Any] | None = None) -> bool:
        """Quick check if an intent is destructive."""
        if intent in _DESTRUCTIVE_INTENTS:
            return True
        if parameters:
            path = str(parameters.get("path", "")).lower()
            for sys_folder in _SYSTEM_FOLDERS:
                if path.startswith(sys_folder):
                    return True
        return False

    # ── internal checks ─────────────────────────────────────────────

    def _check_intent_risks(self, intent: str) -> list[str]:
        """Check risks from the intent itself."""
        risks = []
        if intent in ("SHUTDOWN", "RESTART", "SYSTEM_POWER"):
            risks.append("POWER: System power command detected")
        if intent == "DELETE_FILE":
            risks.append("DELETE: File deletion operation")
        if intent == "FILE_MANAGEMENT":
            risks.append("DELETE: File management operation may include deletion")
        if intent == "UNINSTALL_APP":
            risks.append("UNINSTALL: Application uninstallation")
        return risks

    def _check_entity_risks(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any],
    ) -> list[str]:
        """Check risks from entities and parameters."""
        risks = []
        target = str(
            entities.get("target", "")
            or parameters.get("target", "")
            or parameters.get("path", "")
        ).lower()

        # Check for dangerous file extensions
        for ext in _DANGEROUS_EXTENSIONS:
            if target.endswith(ext):
                risks.append(f"DANGEROUS_FILE: File has dangerous extension ({ext})")
                break

        return risks

    def _check_path_risks(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any],
    ) -> list[str]:
        """Check risks from file/folder paths."""
        risks = []
        path = str(
            entities.get("path", "")
            or parameters.get("path", "")
            or entities.get("target", "")
        ).lower()

        if not path:
            return risks

        for sys_folder in _SYSTEM_FOLDERS:
            if path.startswith(sys_folder) or sys_folder in path:
                risks.append(f"SYSTEM_PATH: Operation targets system folder ({sys_folder})")
                break

        return risks

    def _check_text_risks(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any],
    ) -> list[str]:
        """Check for registry, network, and package risks in text."""
        risks = []
        text = " ".join(str(v) for v in entities.values()).lower()
        text += " " + " ".join(str(v) for v in parameters.values()).lower()

        for pattern in _REGISTRY_PATTERNS:
            if pattern.search(text):
                risks.append("REGISTRY: Registry operation detected")
                break

        for pattern in _NETWORK_MODIFY_PATTERNS:
            if pattern.search(text):
                risks.append("FIREWALL: Network modification detected")
                break

        for pattern in _PACKAGE_PATTERNS:
            if pattern.search(text):
                risks.append("PACKAGE: Package installation/modification detected")
                break

        return risks

    @staticmethod
    def _generate_confirmation_message(intent: str, risks: list[str]) -> str:
        """Generate a user-friendly confirmation message."""
        risk_descriptions = {
            "POWER": "This will shut down/restart your computer.",
            "SYSTEM_PATH": "This operation targets a system folder.",
            "REGISTRY": "This modifies the Windows registry.",
            "FIREWALL": "This modifies network/firewall settings.",
        }

        for risk in risks:
            for keyword, description in risk_descriptions.items():
                if keyword in risk:
                    return f"{description} Are you sure you want to proceed?"

        return "This action may have significant effects. Should I proceed?"
