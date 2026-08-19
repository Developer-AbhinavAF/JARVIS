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


@dataclass
class ToolCandidateEvent(BaseEvent):
    """Emitted when candidate tools are identified for a query."""
    candidates: list = field(default_factory=list)
    query: str = ""

    def __post_init__(self):
        self.event_type = "tool_candidates"


@dataclass
class ImageResultEvent(BaseEvent):
    """Emitted when a visual result (image/video) is retrieved and should be rendered."""
    source: str = ""
    title: str = ""
    description: str = ""
    image_url: str = ""
    thumbnail_url: str = ""
    local_path: str = ""
    source_url: str = ""
    media_type: str = "image"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = "image_result"


@dataclass
class ImageGalleryEvent(BaseEvent):
    """Emitted when multiple image results are returned (e.g. NASA search)."""
    source: str = ""
    query: str = ""
    results: list = field(default_factory=list)
    count: int = 0

    def __post_init__(self):
        self.event_type = "image_gallery"


@dataclass
class FileResultEvent(BaseEvent):
    """Emitted when a file operation produces a result."""
    file_path: str = ""
    operation: str = ""
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = "file_result"


@dataclass
class CodeExecutionEvent(BaseEvent):
    """Emitted when code is generated and executed as a fallback."""
    language: str = ""
    code: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    success: bool = False
    verification: str = ""

    def __post_init__(self):
        self.event_type = "code_execution"


@dataclass
class ExecuteEvent(BaseEvent):
    """Emitted when <execute> tag command execution completes."""
    execution_type: str = ""
    command: str = ""
    status: str = ""  # success, failed
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    error: Optional[str] = None

    def __post_init__(self):
        self.event_type = "execute"
