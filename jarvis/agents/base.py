"""Agent Base Infrastructure.

Provides the foundation for all JARVIS agents:
- AgentBase: Abstract base class every agent inherits
- AgentMessage: Structured inter-agent communication
- AgentHealth: Real-time health monitoring
- AgentCapability: Capability declarations for routing
"""

from __future__ import annotations

import time
import uuid
import logging
import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# ENUMS
# ════════════════════════════════════════════════════════════════════

class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    FAILED = "failed"
    OFFLINE = "offline"
    STARTING = "starting"


class AgentPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class MessageType(Enum):
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    CANCEL = "cancel"
    STATUS = "status"
    QUERY = "query"
    RESPONSE = "response"


# ════════════════════════════════════════════════════════════════════
# AGENT HEALTH
# ════════════════════════════════════════════════════════════════════

@dataclass
class AgentHealth:
    """Real-time health monitoring for an agent."""
    status: AgentStatus = AgentStatus.IDLE
    latency_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    total_count: int = 0
    last_error: str = ""
    last_active: float = 0.0
    current_task: str = ""

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 1.0
        return self.success_count / self.total_count

    @property
    def availability(self) -> bool:
        return self.status != AgentStatus.OFFLINE and self.status != AgentStatus.FAILED

    def record_success(self, latency_ms: float) -> None:
        self.success_count += 1
        self.total_count += 1
        self.latency_ms = latency_ms
        self.last_active = time.time()
        self.status = AgentStatus.IDLE
        self.current_task = ""

    def record_failure(self, error: str) -> None:
        self.failure_count += 1
        self.total_count += 1
        self.last_error = error
        self.last_active = time.time()
        self.status = AgentStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 1),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 3),
            "availability": self.availability,
            "last_error": self.last_error,
            "current_task": self.current_task,
        }


# ════════════════════════════════════════════════════════════════════
# AGENT MESSAGE
# ════════════════════════════════════════════════════════════════════

@dataclass
class AgentMessage:
    """Structured inter-agent communication message."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    source_agent: str = ""
    target_agent: str = ""
    task_id: str = ""
    message_type: MessageType = MessageType.TASK
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    priority: AgentPriority = AgentPriority.MEDIUM
    requires_response: bool = False
    timeout_seconds: float = 30.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "task_id": self.task_id,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "priority": self.priority.value,
        }


# ════════════════════════════════════════════════════════════════════
# AGENT CAPABILITY
# ════════════════════════════════════════════════════════════════════

@dataclass
class AgentCapability:
    """Declares what an agent can handle."""
    name: str = ""
    description: str = ""
    intent_patterns: list[str] = field(default_factory=list)
    entity_types: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    confidence_threshold: float = 0.5

    def matches(self, intent: str = "", entities: dict | None = None, text: str = "") -> float:
        """Calculate how well this capability matches a request."""
        score = 0.0

        if intent and intent in self.intent_patterns:
            score += 0.6

        if text:
            text_lower = text.lower()
            matched = sum(1 for kw in self.keywords if kw in text_lower)
            if self.keywords:
                score += min(0.4, matched / len(self.keywords) * 0.4)

        return min(1.0, score)


# ════════════════════════════════════════════════════════════════════
# AGENT BASE
# ════════════════════════════════════════════════════════════════════

class AgentBase(ABC):
    """Abstract base class for all JARVIS agents.

    Every agent must:
    - Have a unique name
    - Declare capabilities
    - Implement process() for task execution
    - Implement health() for monitoring
    """

    def __init__(
        self,
        name: str,
        priority: AgentPriority = AgentPriority.MEDIUM,
    ) -> None:
        self._name = name
        self._priority = priority
        self._health = AgentHealth()
        self._capabilities: list[AgentCapability] = []
        self._local_memory: dict[str, Any] = {}
        self._message_log: list[AgentMessage] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> AgentPriority:
        return self._priority

    @property
    def health(self) -> AgentHealth:
        return self._health

    @property
    def capabilities(self) -> list[AgentCapability]:
        return self._capabilities

    @property
    def is_available(self) -> bool:
        return self._health.availability and self._health.status != AgentStatus.BUSY

    def add_capability(self, cap: AgentCapability) -> None:
        self._capabilities.append(cap)

    def can_handle(self, intent: str = "", entities: dict | None = None, text: str = "") -> float:
        """Best capability match score across all declared capabilities."""
        if not self.is_available:
            return 0.0
        best = 0.0
        for cap in self._capabilities:
            score = cap.matches(intent, entities, text)
            if score > best:
                best = score
        return best

    async def process(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming task message. Must be implemented by subclasses."""
        raise NotImplementedError

    def process_sync(self, message: AgentMessage) -> AgentMessage:
        """Synchronous wrapper around process()."""
        t0 = time.perf_counter()
        self._health.status = AgentStatus.BUSY
        self._health.current_task = message.task_id or message.message_id
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(self.process(message))
            loop.close()
            ms = (time.perf_counter() - t0) * 1000
            self._health.record_success(ms)
            return result
        except Exception as e:
            self._health.record_failure(str(e))
            logger.error("Agent %s failed: %s", self._name, e)
            return AgentMessage(
                source_agent=self._name,
                target_agent=message.source_agent,
                task_id=message.task_id,
                message_type=MessageType.ERROR,
                payload={"error": str(e)},
            )

    def receive(self, message: AgentMessage) -> None:
        """Receive a message from the orchestrator."""
        self._message_log.append(message)

    def get_health(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "priority": self._priority.value,
            **self._health.to_dict(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "priority": self._priority.value,
            "health": self._health.to_dict(),
            "capabilities": len(self._capabilities),
            "local_memory_size": len(self._local_memory),
            "messages_received": len(self._message_log),
        }


# ════════════════════════════════════════════════════════════════════
# SINGLETONS
# ════════════════════════════════════════════════════════════════════

__all__ = [
    "AgentStatus", "AgentPriority", "MessageType",
    "AgentHealth", "AgentMessage", "AgentCapability", "AgentBase",
]
