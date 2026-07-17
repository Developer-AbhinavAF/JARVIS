"""AI Router — Model Orchestration Engine for JARVIS.

Routes every request to the best provider based on capability, speed, cost, health.

20+ providers: Groq, OpenAI, Anthropic, Gemini, OpenRouter, DeepSeek,
Cerebras, Mistral, NVIDIA NIM, Fireworks, Cohere, Ollama, ElevenLabs, Tavily...

Usage:
    from jarvis.ai_router import router

    # Chat
    response = await router.chat("Hello, how are you?")

    # Reasoning
    response = await router.reason("Explain quantum computing step by step")

    # Vision
    response = await router.vision("Describe this image", image_url="...")

    # Search
    response = await router.search("latest AI news")

    # Streaming
    async for chunk in router.route_stream(request):
        print(chunk, end="")
"""

from .models import (
    Capability, ProviderStatus, LoadBalanceStrategy, RouteStatus,
    Model, Route, RouterRequest, RouterResponse, HealthScore, QuotaInfo,
)
from .config import RouterConfig, ProviderConfig, load_config, router_config
from .capabilities import CapabilityDetector, CapabilityResult, detector
from .providers import ProviderRegistry, get_registry
from .health import HealthMonitor, health_monitor
from .quota import QuotaManager, quota_manager
from .metrics import MetricsCollector, metrics_collector
from .load_balancer import LoadBalancer
from .fallback import FallbackManager, FallbackChain
from .latency import LatencyPredictor, latency_predictor
from .streaming import StreamingAdapter, StreamEvent, StreamEventType, StreamBuffer, streaming_adapter
from .executor import ProviderExecutor, ExecutionResult, provider_executor
from .router import AIRouter, get_router

__all__ = [
    # Router
    "AIRouter", "get_router",
    # Config
    "RouterConfig", "ProviderConfig", "load_config", "router_config",
    # Models
    "Capability", "ProviderStatus", "LoadBalanceStrategy", "RouteStatus",
    "Model", "Route", "RouterRequest", "RouterResponse", "HealthScore", "QuotaInfo",
    # Modules
    "CapabilityDetector", "CapabilityResult", "detector",
    "ProviderRegistry", "get_registry",
    "HealthMonitor", "health_monitor",
    "QuotaManager", "quota_manager",
    "MetricsCollector", "metrics_collector",
    "LoadBalancer",
    "FallbackManager", "FallbackChain",
    "LatencyPredictor", "latency_predictor",
    "StreamingAdapter", "StreamEvent", "StreamEventType", "StreamBuffer", "streaming_adapter",
    "ProviderExecutor", "ExecutionResult", "provider_executor",
]
