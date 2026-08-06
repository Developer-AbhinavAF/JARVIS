"""core/events.py — Unified Event System for JARVIS vNext++.

All client interfaces (CLI, Desktop UI, REST/SSE API, Speech Mode, Mobile, Web)
consume the exact same event stream emitted by Jarvis Core.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class BaseEvent:
    event_type: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThinkingEvent(BaseEvent):
    """Emitted by ThinkingMiddleware when model emits reasoning tokens."""
    text: str = ""
    phase: str = "Reasoning"

    def __post_init__(self):
        self.event_type = "thinking"


@dataclass
class PlannerEvent(BaseEvent):
    """Emitted when Planner builds or updates an execution plan."""
    goal: str = ""
    steps: list = field(default_factory=list)
    profile: str = "NORMAL"
    confidence: float = 1.0

    def __post_init__(self):
        self.event_type = "planner"


@dataclass
class MemoryEvent(BaseEvent):
    """Emitted on memory lookups and hits."""
    action: str = "search"
    tier: str = "Facts"
    key: str = ""
    value: Any = None

    def __post_init__(self):
        self.event_type = "memory"


@dataclass
class VisionEvent(BaseEvent):
    """Emitted during OCR or image analysis."""
    action: str = "capture"
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = "vision"


@dataclass
class ExecutionEvent(BaseEvent):
    """Emitted when tool or skill execution begins/updates."""
    target_name: str = ""
    status: str = "started"  # started, executing, completed, failed
    args: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = "execution"


@dataclass
class VerificationEvent(BaseEvent):
    """Emitted when execution state is verified."""
    target_name: str = ""
    verified: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = "verification"


@dataclass
class ReflectionEvent(BaseEvent):
    """Emitted when Reflection Engine reflects on complex task execution."""
    task: str = ""
    success: bool = True
    lessons: list = field(default_factory=list)

    def __post_init__(self):
        self.event_type = "reflection"


@dataclass
class LearningEvent(BaseEvent):
    """Emitted when Learning Engine records a failure or pattern update."""
    failure_reason: str = ""
    pattern_updated: str = ""

    def __post_init__(self):
        self.event_type = "learning"


@dataclass
class SpeechEvent(BaseEvent):
    """Emitted when Speech engine synthesizes/plays audio."""
    text: str = ""
    status: str = "speaking"

    def __post_init__(self):
        self.event_type = "speech"


@dataclass
class FinalResponseToken(BaseEvent):
    """Emitted during response text streaming."""
    token: str = ""

    def __post_init__(self):
        self.event_type = "response_token"


@dataclass
class FinalResponse(BaseEvent):
    """Emitted when natural response is complete."""
    text: str = ""
    confidence: float = 1.0

    def __post_init__(self):
        self.event_type = "final_response"
