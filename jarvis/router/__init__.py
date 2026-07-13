"""
JARVIS AI Router v3.0 — Multi-Provider Intelligent AI Gateway.

Replaces the former 9Router proxy with a direct, modular routing layer
that connects to 20+ AI providers natively. Every provider, model, and
capability is auto-registered and health-monitored.

Core exports:
    - AIRouter: main router instance (drop-in replacement for router_client)
    - RouterConfig: configuration dataclass
    - All provider classes for direct access
    - All exception types
"""

from .router import AIRouter
from .config import RouterConfig
from .models import (
    RouterResponse,
    RouterHealth,
    ProviderInfo,
    ModelInfo,
    CapabilityInfo,
    ChatRequest,
    EmbeddingRequest,
    StreamChunk,
    Capability,
    ProviderStatus,
    LoadBalanceStrategy,
    ProviderMetrics,
    RouterStats,
)
from .exceptions import (
    RouterError,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderServerError,
    ProviderNetworkError,
    ProviderEmptyResponseError,
    AllProvidersExhaustedError,
    ProviderModelNotFoundError,
    ProviderOfflineError,
    NoProviderForCapabilityError,
    NoProviderForModelError,
    RouterConfigurationError,
    RouterQuotaExceededError,
    StreamError,
    StreamInterruptedError,
    ToolCallError,
    ToolCallParseError,
    ValidationError,
    InvalidRequestError,
    InvalidResponseError,
    QuotaExceededError,
    DailyQuotaExceededError,
    MonthlyQuotaExceededError,
)
from .interfaces import BaseProvider
from .providers import (
    GroqProvider,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    OpenRouterProvider,
    FireworksProvider,
    DeepSeekProvider,
    MistralProvider,
    NvidiaNimProvider,
    SiliconFlowProvider,
    BytePlusProvider,
    HyperbolicProvider,
    CerebrasProvider,
    ChutesProvider,
    CohereProvider,
    VeniceProvider,
    VercelAIGatewayProvider,
    XiaomiMimoProvider,
    OllamaLocalProvider,
    OllamaCloudProvider,
    ElevenLabsProvider,
    TavilyProvider,
    get_all_provider_classes,
)
from .registry import ProviderRegistry, ModelRegistry, CapabilityRegistry
from .manager import RouterManager
from .selector import ProviderSelector
from .health import HealthManager
from .quota import QuotaManager
from .metrics import MetricsCollector
from .cache import RouterCache, LRUCache
from .streaming import StreamingManager
from .fallback import FallbackHandler
from .validator import RequestValidator
from .capabilities import CapabilityDetector
from .scheduler import BackgroundScheduler
from .benchmark import Benchmark
from .utils import Timer, safe_json_loads

router_client: AIRouter | None = None


def get_router() -> AIRouter:
    global router_client
    if router_client is None:
        router_client = AIRouter()
    return router_client


router_client = get_router()

__all__ = [
    "AIRouter", "router_client", "get_router",
    "RouterManager", "RouterConfig",
    "ProviderRegistry", "ModelRegistry", "CapabilityRegistry",
    "ProviderSelector", "HealthManager", "QuotaManager",
    "MetricsCollector", "RouterCache", "LRUCache",
    "StreamingManager", "FallbackHandler",
    "RequestValidator", "CapabilityDetector",
    "BackgroundScheduler", "Benchmark",
    "Timer", "safe_json_loads",
    "RouterResponse", "RouterHealth", "ProviderInfo",
    "ModelInfo", "CapabilityInfo", "ChatRequest",
    "EmbeddingRequest", "StreamChunk",
    "Capability", "ProviderStatus", "LoadBalanceStrategy",
    "ProviderMetrics", "RouterStats",
    "BaseProvider",
    "GroqProvider", "OpenAIProvider", "AnthropicProvider",
    "GeminiProvider", "OpenRouterProvider", "FireworksProvider",
    "DeepSeekProvider", "MistralProvider", "NvidiaNimProvider",
    "SiliconFlowProvider", "BytePlusProvider", "HyperbolicProvider",
    "CerebrasProvider", "ChutesProvider", "CohereProvider",
    "VeniceProvider", "VercelAIGatewayProvider", "XiaomiMimoProvider",
    "OllamaLocalProvider", "OllamaCloudProvider",
    "ElevenLabsProvider", "TavilyProvider",
    "get_all_provider_classes",
    "RouterError", "ProviderError", "ProviderTimeoutError",
    "ProviderRateLimitError", "ProviderAuthError",
    "ProviderServerError", "ProviderNetworkError",
    "ProviderEmptyResponseError", "ProviderModelNotFoundError",
    "ProviderOfflineError", "AllProvidersExhaustedError",
    "NoProviderForCapabilityError", "NoProviderForModelError",
    "RouterConfigurationError", "RouterQuotaExceededError",
    "StreamError", "StreamInterruptedError",
    "ToolCallError", "ToolCallParseError",
    "ValidationError", "InvalidRequestError", "InvalidResponseError",
    "QuotaExceededError", "DailyQuotaExceededError", "MonthlyQuotaExceededError",
]
