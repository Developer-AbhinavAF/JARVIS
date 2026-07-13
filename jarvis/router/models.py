"""Data models for the JARVIS AI Router v3.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from datetime import datetime


# =============================================================================
# Enums
# =============================================================================

class Capability(str, Enum):
    """Known AI capabilities that providers may support."""
    CHAT = "chat"
    REASONING = "reasoning"
    VISION = "vision"
    OCR = "ocr"
    IMAGE_GENERATION = "image_generation"
    EMBEDDING = "embedding"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    TOOL_CALLING = "tool_calling"
    FUNCTION_CALLING = "function_calling"
    JSON_OUTPUT = "json_output"
    LONG_CONTEXT = "long_context"
    STREAMING = "streaming"
    AUDIO = "audio"
    CODE_GENERATION = "code_generation"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    RERANKING = "reranking"
    SEARCH = "search"
    RESEARCH = "research"
    STRUCTURED_OUTPUT = "structured_output"


class ProviderStatus(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


class LoadBalanceStrategy(str, Enum):
    PRIORITY = "priority"
    WEIGHTED = "weighted"
    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    LEAST_LOADED = "least_loaded"
    CAPABILITY_BASED = "capability_based"
    RANDOM_WEIGHTED = "random_weighted"
    AUTO_OPTIMIZED = "auto_optimized"


# =============================================================================
# Core Data Classes
# =============================================================================

@dataclass
class RouterResponse:
    """Unified response from any AI provider."""
    text: str
    model: str
    provider: str
    latency_ms: float
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached: bool = False
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str = "stop"


@dataclass
class RouterHealth:
    """Health status for a provider or the router itself."""
    available: bool
    message: str
    base_url: str = ""
    model: str = ""
    latency_ms: float = 0.0
    success_rate: float = 1.0
    status: ProviderStatus = ProviderStatus.UNKNOWN


@dataclass
class ProviderInfo:
    """Metadata for a registered AI provider."""
    name: str
    display_name: str
    base_url: str
    api_key_env: str
    priority: int = 100
    weight: float = 1.0
    enabled: bool = True
    status: ProviderStatus = ProviderStatus.UNKNOWN
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0
    total_failures: int = 0
    quota_rpm: int = 0
    quota_tpm: int = 0
    current_rpm: int = 0
    current_tpm: int = 0
    models: list[str] = field(default_factory=list)
    capabilities: set[Capability] = field(default_factory=set)
    supports_streaming: bool = False
    supports_vision: bool = False
    supports_tool_calling: bool = False
    supports_json_mode: bool = False
    supports_embeddings: bool = False
    supports_reasoning: bool = False
    max_context_length: int = 4096
    last_checked: float = 0.0
    tags: list[str] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return self.status in (ProviderStatus.ONLINE, ProviderStatus.DEGRADED)

    @property
    def is_available(self) -> bool:
        return self.enabled and self.is_healthy


@dataclass
class ModelInfo:
    """Metadata for a registered model."""
    name: str
    display_name: str
    family: str  # gpt, claude, gemini, llama, qwen, deepseek, mistral, command, etc.
    capabilities: set[Capability] = field(default_factory=set)
    providers: list[str] = field(default_factory=list)  # provider names offering this model
    max_tokens: int = 4096
    supports_streaming: bool = False
    supports_vision: bool = False
    supports_tool_calling: bool = False
    supports_json_mode: bool = False
    supports_reasoning: bool = False
    is_reasoning_model: bool = False
    is_vision_model: bool = False
    is_embedding_model: bool = False
    is_audio_model: bool = False
    is_image_model: bool = False
    is_speech_model: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class CapabilityInfo:
    """Description of a capability and which providers/models support it."""
    name: str
    providers: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    default_provider: str | None = None
    default_model: str | None = None


@dataclass
class ChatRequest:
    """Normalized chat request passed to the router."""
    messages: list[dict[str, Any]]
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool = False
    response_format: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    stop: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingRequest:
    """Normalized embedding request."""
    input_texts: list[str]
    model: str | None = None
    dimensions: int | None = None


@dataclass
class StreamChunk:
    """Single chunk from a streaming response."""
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str | None = None
    model: str = ""
    provider: str = ""
    index: int = 0


@dataclass
class ProviderMetrics:
    """Runtime metrics for a provider."""
    name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    last_latency_ms: float = 0.0
    avg_tokens_per_sec: float = 0.0
    stream_success_rate: float = 1.0
    tool_call_success_rate: float = 1.0
    vision_success_rate: float = 1.0
    embedding_requests: int = 0
    last_request_time: float = 0.0
    error_counts: dict[str, int] = field(default_factory=dict)

    @property
    def avg_latency_ms(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests

    @property
    def success_rate(self) -> float:
        total = self.successful_requests + self.failed_requests
        if total == 0:
            return 1.0
        return self.successful_requests / total


@dataclass
class RouterStats:
    """Aggregate router statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cached_requests: int = 0
    avg_latency_ms: float = 0.0
    provider_stats: dict[str, ProviderMetrics] = field(default_factory=dict)
    uptime_start: float = field(default_factory=lambda: datetime.now().timestamp())

    @property
    def success_rate(self) -> float:
        total = self.successful_requests + self.failed_requests
        if total == 0:
            return 1.0
        return self.successful_requests / total
