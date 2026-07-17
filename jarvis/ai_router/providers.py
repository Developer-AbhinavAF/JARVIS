"""Provider Registry — Manages all 20+ AI providers.

Each provider registers its models, capabilities, and configuration.
"""

from __future__ import annotations

import logging
from typing import Any
from dataclasses import dataclass, field

from .models import Model, Capability, ProviderStatus, HealthScore, QuotaInfo
from .config import RouterConfig, ProviderConfig, router_config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# MODEL CATALOG — Every model JARVIS knows about
# ═══════════════════════════════════════════════════════════════════════

_MODEL_CATALOG: dict[str, list[dict[str, Any]]] = {
    "groq": [
        {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "caps": [Capability.CHAT, Capability.CODING, Capability.REASONING, Capability.TOOL_USE], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B", "caps": [Capability.CHAT], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "caps": [Capability.CHAT, Capability.CODING], "ctx": 32768, "vision": False, "streaming": True},
        {"id": "gemma2-9b-it", "name": "Gemma 2 9B", "caps": [Capability.CHAT], "ctx": 8192, "vision": False, "streaming": True},
    ],
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.REASONING, Capability.TOOL_USE], "ctx": 128000, "vision": True, "streaming": True},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.TOOL_USE], "ctx": 128000, "vision": True, "streaming": True},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.TOOL_USE], "ctx": 128000, "vision": True, "streaming": True},
        {"id": "o1", "name": "o1", "caps": [Capability.CHAT, Capability.REASONING, Capability.CODING], "ctx": 200000, "vision": True, "streaming": True},
        {"id": "o1-mini", "name": "o1 Mini", "caps": [Capability.CHAT, Capability.REASONING, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "o3-mini", "name": "o3 Mini", "caps": [Capability.CHAT, Capability.REASONING, Capability.CODING], "ctx": 200000, "vision": False, "streaming": True},
        {"id": "dall-e-3", "name": "DALL·E 3", "caps": [Capability.IMAGE_GENERATION], "ctx": 0, "vision": False, "streaming": False},
        {"id": "whisper-1", "name": "Whisper", "caps": [Capability.AUDIO], "ctx": 0, "vision": False, "streaming": False},
        {"id": "text-embedding-3-large", "name": "Embedding 3 Large", "caps": [Capability.EMBEDDINGS], "ctx": 0, "vision": False, "streaming": False},
    ],
    "anthropic": [
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.REASONING, Capability.TOOL_USE], "ctx": 200000, "vision": True, "streaming": True},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.TOOL_USE], "ctx": 200000, "vision": True, "streaming": True},
        {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.REASONING, Capability.TOOL_USE], "ctx": 200000, "vision": True, "streaming": True},
    ],
    "gemini": [
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.REASONING, Capability.TOOL_USE], "ctx": 1000000, "vision": True, "streaming": True},
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.TOOL_USE], "ctx": 1000000, "vision": True, "streaming": True},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.TOOL_USE], "ctx": 1000000, "vision": True, "streaming": True},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.REASONING], "ctx": 2000000, "vision": True, "streaming": True},
        {"id": "imagen-3.0-generate-001", "name": "Imagen 3", "caps": [Capability.IMAGE_GENERATION], "ctx": 0, "vision": False, "streaming": False},
    ],
    "openrouter": [
        {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.REASONING, Capability.TOOL_USE], "ctx": 200000, "vision": True, "streaming": True},
        {"id": "openai/gpt-4o", "name": "GPT-4o", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.TOOL_USE], "ctx": 128000, "vision": True, "streaming": True},
        {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "caps": [Capability.CHAT, Capability.VISION, Capability.CODING, Capability.REASONING], "ctx": 1000000, "vision": True, "streaming": True},
        {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "caps": [Capability.CHAT, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "caps": [Capability.CHAT, Capability.REASONING, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
    ],
    "deepseek": [
        {"id": "deepseek-chat", "name": "DeepSeek Chat", "caps": [Capability.CHAT, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "caps": [Capability.CHAT, Capability.REASONING, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
    ],
    "cerebras": [
        {"id": "llama-3.3-70b", "name": "Llama 3.3 70B", "caps": [Capability.CHAT, Capability.CODING, Capability.REASONING], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "llama-3.1-8b", "name": "Llama 3.1 8B", "caps": [Capability.CHAT], "ctx": 128000, "vision": False, "streaming": True},
    ],
    "mistral": [
        {"id": "mistral-large-latest", "name": "Mistral Large", "caps": [Capability.CHAT, Capability.CODING, Capability.REASONING, Capability.TOOL_USE], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "mistral-small-latest", "name": "Mistral Small", "caps": [Capability.CHAT, Capability.CODING, Capability.TOOL_USE], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "codestral-latest", "name": "Codestral", "caps": [Capability.CODING], "ctx": 32000, "vision": False, "streaming": True},
    ],
    "nvidia_nim": [
        {"id": "meta/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "caps": [Capability.CHAT, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "nvidia/llama-3.1-nemotron-70b-instruct", "name": "Nemotron 70B", "caps": [Capability.CHAT, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
    ],
    "fireworks": [
        {"id": "accounts/fireworks/models/llama-v3p3-70b-instruct", "name": "Llama 3.3 70B", "caps": [Capability.CHAT, Capability.CODING, Capability.TOOL_USE], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "accounts/fireworks/models/deepseek-r1", "name": "DeepSeek R1", "caps": [Capability.CHAT, Capability.REASONING, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
    ],
    "cohere": [
        {"id": "command-r-plus-08-2024", "name": "Command R+", "caps": [Capability.CHAT, Capability.TOOL_USE, Capability.SEARCH], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "command-r-08-2024", "name": "Command R", "caps": [Capability.CHAT, Capability.TOOL_USE], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "embed-english-v3.0", "name": "Embed English v3", "caps": [Capability.EMBEDDINGS], "ctx": 0, "vision": False, "streaming": False},
    ],
    "elevenlabs": [
        {"id": "eleven_multilingual_v2", "name": "Multilingual V2", "caps": [Capability.SPEECH], "ctx": 0, "vision": False, "streaming": True},
        {"id": "eleven_flash_v2_5", "name": "Flash V2.5", "caps": [Capability.SPEECH], "ctx": 0, "vision": False, "streaming": True},
    ],
    "ollama": [
        {"id": "llama3.3", "name": "Llama 3.3", "caps": [Capability.CHAT, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "llama3.1", "name": "Llama 3.1", "caps": [Capability.CHAT, Capability.CODING], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "gemma2", "name": "Gemma 2", "caps": [Capability.CHAT], "ctx": 8192, "vision": False, "streaming": True},
        {"id": "deepseek-r1", "name": "DeepSeek R1", "caps": [Capability.CHAT, Capability.REASONING], "ctx": 128000, "vision": False, "streaming": True},
        {"id": "llava", "name": "LLaVA", "caps": [Capability.CHAT, Capability.VISION], "ctx": 128000, "vision": True, "streaming": True},
        {"id": "nomic-embed-text", "name": "Nomic Embed", "caps": [Capability.EMBEDDINGS], "ctx": 0, "vision": False, "streaming": False},
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER REGISTRY
# ═══════════════════════════════════════════════════════════════════════

class ProviderRegistry:
    """Central registry of all AI providers and their models.

    Usage:
        registry = ProviderRegistry(config)
        models = registry.get_models(Capability.CHAT)
        provider = registry.get_provider("groq")
    """

    def __init__(self, config: RouterConfig | None = None):
        self.config = config or router_config
        self._providers: dict[str, ProviderConfig] = {}
        self._models: dict[str, list[Model]] = {}
        self._health: dict[str, HealthScore] = {}
        self._quota: dict[str, QuotaInfo] = {}
        self._load_models()

    def _load_models(self):
        """Load all models from the catalog."""
        for provider_name, model_list in _MODEL_CATALOG.items():
            prov_config = self.config.providers.get(provider_name)
            self._providers[provider_name] = prov_config or ProviderConfig(name=provider_name)
            self._health[provider_name] = HealthScore(provider=provider_name)
            self._quota[provider_name] = QuotaInfo(provider=provider_name)

            self._models[provider_name] = []
            for m in model_list:
                model = Model(
                    model_id=m["id"],
                    provider=provider_name,
                    display_name=m["name"],
                    capabilities=m.get("caps", [Capability.CHAT]),
                    context_window=m.get("ctx", 4096),
                    supports_streaming=m.get("streaming", True),
                    supports_vision=m.get("vision", False),
                    enabled=prov_config.enabled if prov_config else True,
                )
                self._models[provider_name].append(model)

        logger.info("ProviderRegistry loaded: %d providers, %d models",
                     len(self._providers), sum(len(v) for v in self._models.values()))

    def get_provider(self, name: str) -> ProviderConfig | None:
        return self._providers.get(name)

    def get_models(self, capability: Capability | None = None, provider: str | None = None) -> list[Model]:
        """Get all models, optionally filtered by capability and provider."""
        results = []
        providers = [provider] if provider else self._providers.keys()
        for pname in providers:
            for m in self._models.get(pname, []):
                if not m.enabled:
                    continue
                if capability and capability not in m.capabilities:
                    continue
                results.append(m)
        return results

    def get_best_model(self, capability: Capability, provider: str | None = None) -> Model | None:
        """Get the best model for a capability, optionally from a specific provider."""
        models = self.get_models(capability=capability, provider=provider)
        if not models:
            return None
        # Prefer higher priority provider, then more capable model
        return sorted(models, key=lambda m: (
            -self._providers.get(m.provider, ProviderConfig()).priority if m.provider in self._providers else 0,
            -len(m.capabilities),
        ))[0]

    def get_provider_models(self, provider_name: str) -> list[Model]:
        return self._models.get(provider_name, [])

    def get_all_providers(self) -> list[str]:
        return list(self._providers.keys())

    def get_enabled_providers(self) -> list[str]:
        return [name for name, p in self._providers.items() if p.enabled]

    def get_health(self, provider: str) -> HealthScore:
        return self._health.get(provider, HealthScore(provider=provider))

    def update_health(self, provider: str, health: HealthScore):
        self._health[provider] = health

    def get_quota(self, provider: str) -> QuotaInfo:
        return self._quota.get(provider, QuotaInfo(provider=provider))

    def update_quota(self, provider: str, quota: QuotaInfo):
        self._quota[provider] = quota

    def is_available(self, provider: str) -> bool:
        """Check if provider is enabled, healthy, and has quota."""
        prov = self._providers.get(provider)
        if not prov or not prov.enabled:
            return False
        health = self._health.get(provider)
        if health and health.status == ProviderStatus.UNHEALTHY:
            return False
        quota = self._quota.get(provider)
        if quota and not quota.available:
            return False
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        total_models = sum(len(v) for v in self._models.values())
        return {
            "providers": len(self._providers),
            "enabled": len([p for p in self._providers.values() if p.enabled]),
            "total_models": total_models,
            "capabilities": len(set(
                cap.value
                for models in self._models.values()
                for m in models
                for cap in m.capabilities
            )),
        }

    def get_registry_stats(self) -> dict[str, Any]:
        return self.get_stats()


_registry: ProviderRegistry | None = None


def get_registry(config: RouterConfig | None = None) -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry(config)
    return _registry


__all__ = ["ProviderRegistry", "get_registry", "_MODEL_CATALOG"]
