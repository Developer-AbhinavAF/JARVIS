"""Router Config — Environment-driven configuration.

Never hardcode values. All provider API keys loaded dynamically.
"""

from __future__ import annotations

import os
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_int(key: str, default: int = 0) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


@dataclass
class ProviderConfig:
    """Configuration for a single provider."""
    name: str = ""
    api_key: str = ""
    base_url: str = ""
    enabled: bool = True
    priority: int = 5          # 1=highest
    max_rpm: int = 60
    max_tpm: int = 100000
    max_daily_requests: int = 10000
    timeout_seconds: float = 30.0
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_tools: bool = True
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    models: list[str] = field(default_factory=list)


@dataclass
class RouterConfig:
    """Global router configuration."""
    # Defaults
    default_provider: str = ""
    default_model: str = ""
    default_reasoning_model: str = ""
    default_vision_model: str = ""
    default_image_model: str = ""
    default_audio_model: str = ""
    default_embedding_model: str = ""

    # Router behavior
    max_retries: int = 3
    fallback_enabled: bool = True
    health_check_interval: float = 300.0    # 5 minutes
    metrics_retention: float = 3600.0       # 1 hour
    overhead_budget_ms: float = 30.0

    # Provider configs
    providers: dict[str, ProviderConfig] = field(default_factory=dict)


def load_config() -> RouterConfig:
    """Load configuration from environment variables."""
    config = RouterConfig(
        default_provider=_env("AI_DEFAULT_PROVIDER", "groq"),
        default_model=_env("AI_DEFAULT_MODEL", ""),
        default_reasoning_model=_env("AI_DEFAULT_REASONING_MODEL", ""),
        default_vision_model=_env("AI_DEFAULT_VISION_MODEL", ""),
        default_image_model=_env("AI_DEFAULT_IMAGE_MODEL", ""),
        default_audio_model=_env("AI_DEFAULT_AUDIO_MODEL", ""),
        default_embedding_model=_env("AI_DEFAULT_EMBEDDING_MODEL", ""),
    )

    # Load provider API keys
    provider_keys = {
        "groq": ("AI_GROQ_API_KEY", "https://api.groq.com/openai/v1", True, False),
        "openai": ("AI_OPENAI_API_KEY", "https://api.openai.com/v1", True, True),
        "anthropic": ("AI_ANTHROPIC_API_KEY", "https://api.anthropic.com/v1", True, False),
        "gemini": ("AI_GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta", True, True),
        "openrouter": ("AI_OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", True, False),
        "deepseek": ("AI_DEEPSEEK_API_KEY", "https://api.deepseek.com/v1", True, False),
        "cerebras": ("AI_CEREBRAS_API_KEY", "https://api.cerebras.ai/v1", True, False),
        "mistral": ("AI_MISTRAL_API_KEY", "https://api.mistral.ai/v1", True, False),
        "nvidia_nim": ("AI_NVIDIA_NIM_API_KEY", "https://integrate.api.nvidia.com/v1", False, False),
        "fireworks": ("AI_FIREWORKS_API_KEY", "https://api.fireworks.ai/inference/v1", True, False),
        "cohere": ("AI_COHERE_API_KEY", "https://api.cohere.com/v2", True, False),
        "ollama": ("AI_OLLAMA_URL", "http://localhost:11434", True, False),
        "elevenlabs": ("AI_ELEVENLABS_API_KEY", "https://api.elevenlabs.io/v1", False, False),
        "tavily": ("AI_TAVILY_API_KEY", "https://api.tavily.com", False, False),
    }

    for name, (env_key, base_url, supports_streaming, supports_vision) in provider_keys.items():
        api_key = _env(env_key, "")
        config.providers[name] = ProviderConfig(
            name=name,
            api_key=api_key,
            base_url=base_url,
            enabled=bool(api_key) or name == "ollama",
            supports_streaming=supports_streaming,
            supports_vision=supports_vision,
        )

    # Override defaults from env
    for prov in config.providers.values():
        prov.max_rpm = _env_int(f"AI_{prov.name.upper()}_MAX_RPM", 60)
        prov.max_tpm = _env_int(f"AI_{prov.name.upper()}_MAX_TPM", 100000)

    return config


router_config = load_config()

__all__ = ["RouterConfig", "ProviderConfig", "load_config", "router_config"]
