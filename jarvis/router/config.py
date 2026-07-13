"""Router configuration — reads from environment variables with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .models import LoadBalanceStrategy


def _env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default).lower()).lower() in ("true", "1", "yes")


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class RouterConfig:
    """All configuration for the AI Router.

    Reads from environment variables; all values have sensible defaults
    so the router can function with zero configuration.
    """

    # ---- General ----
    default_provider: str = os.getenv("AI_DEFAULT_PROVIDER", "")
    default_model: str = os.getenv("AI_DEFAULT_MODEL", "")
    default_reasoning_model: str = os.getenv("AI_DEFAULT_REASONING_MODEL", "")
    default_vision_model: str = os.getenv("AI_DEFAULT_VISION_MODEL", "")
    default_embedding_model: str = os.getenv("AI_DEFAULT_EMBEDDING_MODEL", "")
    default_audio_model: str = os.getenv("AI_DEFAULT_AUDIO_MODEL", "")
    default_image_model: str = os.getenv("AI_DEFAULT_IMAGE_MODEL", "")

    # ---- Runtime ----
    stream: bool = _env_bool("AI_STREAM", True)
    timeout: float = _env_float("AI_TIMEOUT", 60.0)
    max_retries: int = _env_int("AI_MAX_RETRIES", 3)
    cache_enabled: bool = _env_bool("AI_CACHE", True)
    log_level: str = os.getenv("AI_LOG_LEVEL", "INFO")

    # ---- Load Balancing ----
    load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy(
        os.getenv("AI_LOAD_BALANCE", "auto_optimized")
    )
    round_robin_index: int = 0

    # ---- Health Checks ----
    health_check_interval: float = _env_float("AI_HEALTH_INTERVAL", 30.0)
    health_check_timeout: float = _env_float("AI_HEALTH_TIMEOUT", 5.0)
    health_ttl: float = _env_float("AI_HEALTH_TTL", 60.0)
    unhealthy_threshold: int = _env_int("AI_UNHEALTHY_THRESHOLD", 3)

    # ---- Quota ----
    quota_check_interval: float = _env_float("AI_QUOTA_INTERVAL", 60.0)

    # ---- Cache ----
    cache_max_size: int = _env_int("AI_CACHE_MAX_SIZE", 1000)
    cache_ttl_response: float = _env_float("AI_CACHE_TTL_RESPONSE", 300.0)
    cache_ttl_embedding: float = _env_float("AI_CACHE_TTL_EMBEDDING", 3600.0)
    cache_ttl_health: float = _env_float("AI_CACHE_TTL_HEALTH", 30.0)

    # ---- Fallback ----
    fallback_max_providers: int = _env_int("AI_FALLBACK_MAX", 10)

    # ---- Connection Pooling ----
    max_connections: int = _env_int("AI_MAX_CONNECTIONS", 100)
    max_keepalive: int = _env_int("AI_MAX_KEEPALIVE", 20)
    connection_timeout: float = _env_float("AI_CONNECT_TIMEOUT", 10.0)

    # ---- Provider API Keys (all empty by default, read from env) ----
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    groq_api_keys: list[str] = field(default_factory=lambda: [
        k for k in [
            os.getenv("GROQ_API_KEY_1", ""),
            os.getenv("GROQ_API_KEY_2", ""),
            os.getenv("GROQ_API_KEY_3", ""),
        ] if k
    ])
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    fireworks_api_key: str = os.getenv("FIREWORKS_API_KEY", "")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "")
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    siliconflow_api_key: str = os.getenv("SILICONFLOW_API_KEY", "")
    byteplus_api_key: str = os.getenv("BYTEPLUS_API_KEY", "")
    hyperbolic_api_key: str = os.getenv("HYPERBOLIC_API_KEY", "")
    cerebras_api_key: str = os.getenv("CEREBRAS_API_KEY", "")
    chutes_api_key: str = os.getenv("CHUTES_API_KEY", "")
    cohere_api_key: str = os.getenv("COHERE_API_KEY", "")
    venice_api_key: str = os.getenv("VENICE_API_KEY", "")
    vercel_ai_gateway_api_key: str = os.getenv("VERCEL_AI_GATEWAY_API_KEY", "")
    xiaomi_mimo_api_key: str = os.getenv("XIAOMI_MIMO_API_KEY", "")
    ollama_local_url: str = os.getenv("OLLAMA_LOCAL_URL", "http://localhost:11434")
    ollama_cloud_api_key: str = os.getenv("OLLAMA_CLOUD_API_KEY", "")
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

    def get_api_key(self, provider_name: str) -> str | None:
        """Get the API key for a provider by name."""
        key_map: dict[str, str] = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "gemini": self.gemini_api_key,
            "groq": self.groq_api_keys[0] if self.groq_api_keys else "",
            "openrouter": self.openrouter_api_key,
            "fireworks": self.fireworks_api_key,
            "deepseek": self.deepseek_api_key,
            "mistral": self.mistral_api_key,
            "nvidia": self.nvidia_api_key,
            "siliconflow": self.siliconflow_api_key,
            "byteplus": self.byteplus_api_key,
            "hyperbolic": self.hyperbolic_api_key,
            "cerebras": self.cerebras_api_key,
            "chutes": self.chutes_api_key,
            "cohere": self.cohere_api_key,
            "venice": self.venice_api_key,
            "vercel_ai_gateway": self.vercel_ai_gateway_api_key,
            "xiaomi_mimo": self.xiaomi_mimo_api_key,
            "ollama_local": self.ollama_local_url,
            "ollama_cloud": self.ollama_cloud_api_key,
            "elevenlabs": self.elevenlabs_api_key,
            "tavily": self.tavily_api_key,
        }
        return key_map.get(provider_name.lower())

    @property
    def enabled_providers(self) -> set[str]:
        """Return set of provider names that have API keys configured."""
        enabled: set[str] = set()
        if self.openai_api_key:
            enabled.add("openai")
        if self.anthropic_api_key:
            enabled.add("anthropic")
        if self.gemini_api_key:
            enabled.add("gemini")
        if self.groq_api_keys:
            enabled.add("groq")
        if self.openrouter_api_key:
            enabled.add("openrouter")
        if self.fireworks_api_key:
            enabled.add("fireworks")
        if self.deepseek_api_key:
            enabled.add("deepseek")
        if self.mistral_api_key:
            enabled.add("mistral")
        if self.nvidia_api_key:
            enabled.add("nvidia")
        if self.siliconflow_api_key:
            enabled.add("siliconflow")
        if self.byteplus_api_key:
            enabled.add("byteplus")
        if self.hyperbolic_api_key:
            enabled.add("hyperbolic")
        if self.cerebras_api_key:
            enabled.add("cerebras")
        if self.chutes_api_key:
            enabled.add("chutes")
        if self.cohere_api_key:
            enabled.add("cohere")
        if self.venice_api_key:
            enabled.add("venice")
        if self.vercel_ai_gateway_api_key:
            enabled.add("vercel_ai_gateway")
        if self.xiaomi_mimo_api_key:
            enabled.add("xiaomi_mimo")
        # Ollama local is always "enabled" (no API key needed, just a URL)
        enabled.add("ollama_local")
        if self.ollama_cloud_api_key:
            enabled.add("ollama_cloud")
        if self.elevenlabs_api_key:
            enabled.add("elevenlabs")
        if self.tavily_api_key:
            enabled.add("tavily")
        return enabled
