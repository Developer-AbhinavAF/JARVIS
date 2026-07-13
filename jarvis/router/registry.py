"""Provider, Model, and Capability registries with auto-registration."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from .models import (
    ProviderInfo, ModelInfo, CapabilityInfo, Capability, ProviderStatus
)
from .interfaces import BaseProvider
from .config import RouterConfig

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Auto-registering registry of all AI providers.

    Each provider instance registers itself into this singleton.
    Provides query methods: by name, by model, by capability, by status.
    """

    def __init__(self, config: RouterConfig | None = None) -> None:
        self.config = config or RouterConfig()
        self._providers: dict[str, BaseProvider] = {}
        self._by_model: dict[str, list[str]] = defaultdict(list)  # model → [provider_names]
        self._by_capability: dict[Capability, list[str]] = defaultdict(list)
        self._by_tag: dict[str, list[str]] = defaultdict(list)
        self._initialized = False

    def register(self, provider: BaseProvider) -> None:
        """Register a provider instance."""
        name = provider.name.lower()
        if name in self._providers:
            logger.debug("Provider %s already registered, skipping", name)
            return

        self._providers[name] = provider

        # Index models
        for model_name in provider._known_models:
            self._by_model[model_name.lower()].append(name)

        # Index capabilities
        for cap in provider.capabilities:
            self._by_capability[cap].append(name)

        # Index tags
        for tag in provider.tags:
            self._by_tag[tag.lower()].append(name)

        logger.debug("Registered provider: %s (models=%d, capabilities=%d)",
                     name, len(provider._known_models), len(provider.capabilities))

    def register_all(self, provider_classes: list[type[BaseProvider]]) -> None:
        """Instantiate and register a list of provider classes."""
        for cls in provider_classes:
            try:
                instance = cls(self.config)
                # Only register if configured with credentials
                if instance.is_configured:
                    self.register(instance)
                else:
                    logger.debug("Skipping %s — not configured (no API key)", cls.name)
            except Exception as exc:
                logger.warning("Failed to register provider %s: %s", getattr(cls, 'name', cls.__name__), exc)

    def get(self, name: str) -> BaseProvider | None:
        return self._providers.get(name.lower())

    def get_all(self) -> dict[str, BaseProvider]:
        return dict(self._providers)

    def get_available(self) -> list[BaseProvider]:
        """Return all configured and healthy providers."""
        return [p for p in self._providers.values() if p.is_configured]

    def get_by_model(self, model_name: str) -> list[BaseProvider]:
        """Return providers that support a specific model."""
        name_lower = model_name.lower()
        provider_names = self._by_model.get(name_lower, [])
        if not provider_names:
            # Fuzzy match: check if any provider supports a similar model
            for prov_name, prov in self._providers.items():
                if prov.supports_model(model_name):
                    provider_names.append(prov_name)
        return [self._providers[n] for n in provider_names if n in self._providers]

    def get_by_capability(self, capability: Capability) -> list[BaseProvider]:
        """Return providers that support a capability."""
        names = self._by_capability.get(capability, [])
        return [self._providers[n] for n in names if n in self._providers]

    def get_by_tag(self, tag: str) -> list[BaseProvider]:
        names = self._by_tag.get(tag.lower(), [])
        return [self._providers[n] for n in names if n in self._providers]

    def get_healthy(self) -> list[BaseProvider]:
        """Return providers currently reporting healthy."""
        return [p for p in self._providers.values() if p.is_configured]

    def get_provider_infos(self) -> list[ProviderInfo]:
        return [p.get_provider_info() for p in self._providers.values()]

    def find_provider_for_model(self, model_name: str) -> BaseProvider | None:
        """Find the best provider for a given model name."""
        candidates = self.get_by_model(model_name)
        if not candidates:
            return None
        # Sort by priority (lowest = highest priority)
        candidates.sort(key=lambda p: p.priority)
        return candidates[0]

    @property
    def provider_names(self) -> list[str]:
        return sorted(self._providers.keys())

    @property
    def total_providers(self) -> int:
        return len(self._providers)

    def unregister(self, name: str) -> None:
        name = name.lower()
        if name in self._providers:
            del self._providers[name]
            # Clean up indices
            for model, names in self._by_model.items():
                if name in names:
                    names.remove(name)
            for cap, names in self._by_capability.items():
                if name in names:
                    names.remove(name)

    def close_all(self) -> None:
        for prov in self._providers.values():
            try:
                prov.close()
            except Exception:
                pass
        self._providers.clear()
        self._by_model.clear()
        self._by_capability.clear()


class ModelRegistry:
    """Registry tracking all known models across providers.

    Maps model families and individual models to their available providers.
    Supports capability-based model lookup.
    """

    def __init__(self, provider_registry: ProviderRegistry) -> None:
        self._provider_registry = provider_registry
        self._models: dict[str, ModelInfo] = {}
        self._by_family: dict[str, list[str]] = defaultdict(list)

    def register(self, model_info: ModelInfo) -> None:
        name = model_info.name.lower()
        if name in self._models:
            existing = self._models[name]
            existing.providers.extend(
                p for p in model_info.providers if p not in existing.providers
            )
        else:
            self._models[name] = model_info

        if model_info.family:
            self._by_family[model_info.family.lower()].append(name)

    def build_from_providers(self) -> None:
        """Auto-build model registry from all registered providers."""
        for name, provider in self._provider_registry.get_all().items():
            for model_name, meta in provider._known_models.items():
                info = ModelInfo(
                    name=model_name,
                    display_name=model_name,
                    family=meta.get("family", "unknown"),
                    capabilities=provider.capabilities,
                    providers=[name],
                    max_tokens=meta.get("max_tokens", 4096),
                    supports_streaming=provider.supports_streaming,
                    supports_vision=meta.get("vision", False),
                    supports_tool_calling=meta.get("tool_calling", provider.supports_tool_calling),
                    supports_json_mode=provider.supports_json_mode,
                    supports_reasoning=meta.get("reasoning", provider.supports_reasoning),
                    is_reasoning_model=meta.get("reasoning", False),
                    is_vision_model=meta.get("vision", False),
                    is_embedding_model=meta.get("embedding", False),
                    is_audio_model=meta.get("audio", False),
                    is_image_model=meta.get("image", False),
                )
                self.register(info)

    def get(self, name: str) -> ModelInfo | None:
        return self._models.get(name.lower())

    def get_by_family(self, family: str) -> list[ModelInfo]:
        names = self._by_family.get(family.lower(), [])
        return [self._models[n] for n in names if n in self._models]

    def find_providers_for_model(self, model_name: str) -> list[str]:
        """Return provider names offering a specific model."""
        info = self.get(model_name)
        if info:
            return info.providers
        # Fuzzy: check by family
        family = model_name.lower().split("/")[-1].split(":")[0]
        for m_name, m_info in self._models.items():
            if family in m_name or family in m_info.family:
                return m_info.providers
        return []

    @property
    def all_models(self) -> dict[str, ModelInfo]:
        return dict(self._models)

    @property
    def total_models(self) -> int:
        return len(self._models)


class CapabilityRegistry:
    """Registry tracking which capabilities are available and where."""

    def __init__(self, provider_registry: ProviderRegistry) -> None:
        self._provider_registry = provider_registry
        self._capabilities: dict[Capability, CapabilityInfo] = {}

    def build_from_providers(self) -> None:
        """Build capability registry from provider data."""
        self._capabilities.clear()
        for cap in Capability:
            providers = self._provider_registry.get_by_capability(cap)
            models: list[str] = []
            for prov in providers:
                for model_name, meta in prov._known_models.items():
                    if cap in prov.capabilities:
                        models.append(model_name)

            self._capabilities[cap] = CapabilityInfo(
                name=cap.value,
                providers=[p.name for p in providers],
                models=models,
                default_provider=providers[0].name if providers else None,
                default_model=models[0] if models else None,
            )

    def get(self, capability: Capability) -> CapabilityInfo:
        return self._capabilities.get(capability, CapabilityInfo(name=capability.value))

    def get_default_provider(self, capability: Capability) -> str | None:
        info = self.get(capability)
        return info.default_provider

    def get_default_model(self, capability: Capability) -> str | None:
        info = self.get(capability)
        return info.default_model

    def has_capability(self, capability: Capability) -> bool:
        info = self.get(capability)
        return len(info.providers) > 0

    @property
    def all_capabilities(self) -> dict[Capability, CapabilityInfo]:
        return dict(self._capabilities)
