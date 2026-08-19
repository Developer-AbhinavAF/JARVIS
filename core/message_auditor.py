"""core/message_auditor.py — Message Payload Auditor for JARVIS vNext++.

Provides safe debugging/auditing of the final outgoing model request to detect
system prompt collisions and verify message construction.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MessageAudit:
    """Safe audit summary of message payload."""
    system_count: int
    user_count: int
    assistant_count: int
    tool_count: int
    total_count: int
    system_sizes: List[int]
    collision_detected: bool
    collision_source: Optional[str]
    warnings: List[str]


class MessageAuditor:
    """Audits message payloads for system prompt collisions and construction issues."""

    def __init__(self):
        self._collision_sources = {
            "core/prompt_assembler.py": "prompt_assembler.assemble()",
            "core/brain.py": "brain._build_system_prompt()",
            "core/qwen3_brain.py": "qwen3_brain._build_system_prompt()",
            "core/memory_human.py": "memory summary generation",
            "core/jarvis_core.py": "agent loop memory write notes",
        }
        
        # Also support direct function names as keys
        self._collision_function_names = {
            "prompt_assembler.assemble()": "core/prompt_assembler.py",
            "brain._build_system_prompt()": "core/brain.py",
            "qwen3_brain._build_system_prompt()": "core/qwen3_brain.py",
            "memory summary generation": "core/memory_human.py",
            "agent loop memory write notes": "core/jarvis_core.py",
        }

    def audit_messages(
        self,
        messages: List[Dict[str, Any]],
        source: str = "unknown"
    ) -> MessageAudit:
        """Safely audit message payload without exposing sensitive content.

        Args:
            messages: List of message dicts with 'role' and 'content'
            source: Source function/file for collision detection

        Returns:
            MessageAudit with safe summary only
        """
        system_count = 0
        user_count = 0
        assistant_count = 0
        tool_count = 0
        system_sizes = []
        warnings = []
        collision_detected = False
        collision_source = None

        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            content_size = len(content) if content else 0

            if role == "system":
                system_count += 1
                system_sizes.append(content_size)
                
                # Detect potential collisions - ANY system message from known sources
                if source in self._collision_sources or source in self._collision_function_names:
                    collision_detected = True
                    collision_source = self._collision_function_names.get(source, self._collision_sources.get(source, source))
                    warnings.append(f"System message from known source: {collision_source}")
                
                # Detect multiple system messages
                if system_count > 1:
                    collision_detected = True
                    collision_source = source
                    warnings.append(f"Multiple system messages detected (count: {system_count})")
                
                # Detect large system prompts that might duplicate Modelfile
                if content_size > 2000:
                    warnings.append(f"Large system message detected ({content_size} chars) - possible Modelfile duplication")
                
            elif role == "user":
                user_count += 1
            elif role == "assistant":
                assistant_count += 1
            elif role == "tool":
                tool_count += 1
            else:
                warnings.append(f"Unknown message role: {role}")

        total_count = len(messages)

        if collision_detected:
            logger.warning(
                "[MESSAGE_AUDITOR] SYSTEM PROMPT COLLISION DETECTED - Source: %s, System messages: %d",
                collision_source,
                system_count
            )

        return MessageAudit(
            system_count=system_count,
            user_count=user_count,
            assistant_count=assistant_count,
            tool_count=tool_count,
            total_count=total_count,
            system_sizes=system_sizes,
            collision_detected=collision_detected,
            collision_source=collision_source,
            warnings=warnings,
        )

    def log_audit(self, audit: MessageAudit, context: str = "") -> None:
        """Log audit summary safely without exposing sensitive content."""
        logger.info(
            "[MESSAGE_AUDITOR] %s - SYSTEM: %d, USER: %d, ASSISTANT: %d, TOOL: %d, TOTAL: %d",
            context,
            audit.system_count,
            audit.user_count,
            audit.assistant_count,
            audit.tool_count,
            audit.total_count,
        )

        if audit.warnings:
            for warning in audit.warnings:
                logger.warning("[MESSAGE_AUDITOR] WARNING: %s", warning)

        if audit.collision_detected:
            logger.error(
                "[MESSAGE_AUDITOR] COLLISION DETECTED from %s",
                audit.collision_source
            )


message_auditor = MessageAuditor()