"""core/provider_registry.py — Multi-Provider AI Orchestration System for JARVIS vNext++.

This module implements a capability-based provider routing system with:
- Centralized provider management
- Multi-key support with rotation
- Capability-based routing
- Health monitoring and fallback
- Configuration hot reload

Architecture:
    User Request
        ↓
    Capability Detection
        ↓
    ProviderRegistry (selects best provider)
        ↓
    Provider Execution
        ↓
    Result normalization
        ↓
    Response
"""

from __future__ import annotations

import os
import json
import time
import logging
import hashlib
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, AsyncGenerator
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ============================================================================
# CAPABILITIES
# ============================================================================

class Capability(Enum):
    """AI provider capabilities."""
    GENERAL_CHAT = "general_chat"
    REASONING = "reasoning"
    CODING = "coding"
    VISION = "vision"
    IMAGE_ANALYSIS = "image_analysis"
    DOCUMENT_ANALYSIS = "document_analysis"
    WEB_SEARCH = "web_search"
    TOOL_CALLING = "tool_calling"
    STRUCTURED_OUTPUT = "structured_output"
    LONG_CONTEXT = "long_context"
    FAST_RESPONSE = "fast_response"
    IMAGE_GENERATION = "image_generation"
    VIDEO_ANALYSIS = "video_analysis"
    OBJECT_DETECTION = "object_detection"
    GEOLOCATION = "geolocation"
    MAPS = "maps"
    MOVIES = "movies"
    COUNTRY_INFORMATION = "country_information"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"


# ============================================================================
# PROVIDER METADATA
# ============================================================================

@dataclass
class ProviderKey:
    """Represents a single API key for a provider."""
    key_id: str
    key_value: str
    priority: int = 0
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    cooldown_until: Optional[float] = None
    last_success_time: Optional[float] = None
    request_count: int = 0
    
    @property
    def is_available(self) -> bool:
        """Check if this key is available (not in cooldown)."""
        if self.cooldown_until is None:
            return True
        return time.time() > self.cooldown_until
    
    @property
    def health_score(self) -> float:
        """Calculate health score (0.0-1.0) based on recent performance."""
        if self.request_count == 0:
            return 1.0
        
        failure_rate = self.failure_count / max(self.request_count, 1)
        
        # Penalize high failure rates
        base_score = 1.0 - failure_rate
        
        # Additional penalty if recently failed
        if self.last_failure_time:
            time_since_failure = time.time() - self.last_failure_time
            if time_since_failure < 300:  # 5 minutes
                base_score *= 0.5
            elif time_since_failure < 3600:  # 1 hour
                base_score *= 0.8
        
        return max(0.0, min(1.0, base_score))
    
    def record_success(self) -> None:
        """Record a successful request."""
        self.request_count += 1
        self.last_success_time = time.time()
        self.failure_count = max(0, self.failure_count - 1)  # Decay failures
    
    def record_failure(self, error_category: str = "unknown") -> None:
        """Record a failed request."""
        self.request_count += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        # Set cooldown based on error category
        cooldowns = {
            "rate_limit": 300,  # 5 minutes
            "timeout": 60,      # 1 minute
            "auth_error": 600,  # 10 minutes
            "server_error": 120, # 2 minutes
            "unknown": 30,      # 30 seconds
        }
        cooldown = cooldowns.get(error_category, 30)
        self.cooldown_until = time.time() + cooldown


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    provider_name: str
    base_url: str
    provider_type: str  # "openai_compatible", "ollama", "anthropic", "google", etc.
    capabilities: Set[Capability] = field(default_factory=set)
    supported_models: List[str] = field(default_factory=list)
    priority: int = 50
    enabled: bool = True
    
    # Performance metrics
    latency_ms: float = 0.0
    average_latency_ms: float = 0.0
    request_count: int = 0
    
    # Feature flags
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_images: bool = False
    supports_reasoning: bool = False
    supports_structured_output: bool = False
    
    # Health status
    available: bool = True
    last_check_time: Optional[float] = None
    consecutive_failures: int = 0
    
    def update_latency(self, latency_ms: float) -> None:
        """Update rolling average latency."""
        self.request_count += 1
        if self.average_latency_ms == 0:
            self.average_latency_ms = latency_ms
        else:
            # Exponential moving average
            alpha = 0.2
            self.average_latency_ms = (alpha * latency_ms + 
                                      (1 - alpha) * self.average_latency_ms)
        self.latency_ms = latency_ms
    
    def record_failure(self) -> None:
        """Record a provider-level failure."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.available = False
            logger.warning("Provider %s marked unavailable after %d consecutive failures",
                         self.provider_name, self.consecutive_failures)
    
    def record_success(self) -> None:
        """Record a provider-level success."""
        self.consecutive_failures = 0
        self.available = True


# ============================================================================
# BASE PROVIDER INTERFACE
# ============================================================================

class BaseProvider(ABC):
    """Abstract base class for all AI providers."""
    
    def __init__(self, config: ProviderConfig, keys: List[ProviderKey]):
        self.config = config
        self.keys = keys
        self._current_key_index = 0
    
    @property
    def current_key(self) -> Optional[ProviderKey]:
        """Get the current best available key."""
        available_keys = [k for k in self.keys if k.is_available]
        if not available_keys:
            return None
        
        # Sort by health score, then priority
        available_keys.sort(key=lambda k: (-k.health_score, -k.priority))
        return available_keys[0]
    
    def rotate_key(self) -> Optional[ProviderKey]:
        """Rotate to the next available key."""
        available_keys = [k for k in self.keys if k.is_available]
        if not available_keys:
            return None
        
        # Move to next key in rotation
        self._current_key_index = (self._current_key_index + 1) % len(available_keys)
        return available_keys[self._current_key_index]
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "",
        **kwargs
    ) -> "ProviderResponse":
        """Execute a non-streaming chat request."""
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        model: str = "",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Execute a streaming chat request."""
        pass
    
    @abstractmethod
    async def check_available(self) -> bool:
        """Check if the provider is available."""
        pass
    
    def supports_capability(self, capability: Capability) -> bool:
        """Check if this provider supports a given capability."""
        return capability in self.config.capabilities


@dataclass
class ProviderResponse:
    """Standardized response from any provider."""
    content: str = ""
    success: bool = False
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    error: str = ""
    error_category: str = "unknown"
    tokens_used: int = 0
    finish_reason: str = ""


# ============================================================================
# PROVIDER REGISTRY
# ============================================================================

class ProviderRegistry:
    """Central registry for all AI providers with capability-based routing."""
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._provider_configs: Dict[str, ProviderConfig] = {}
        self._capability_index: Dict[Capability, List[str]] = {}
        self._config_fingerprint: str = ""
        self._last_config_check: float = 0
        
        # Load providers from environment
        self._load_from_environment()
    
    def _load_from_environment(self) -> None:
        """Load provider configurations from environment variables."""
        logger.info("Loading provider configurations from environment")
        
        # Load Ollama
        self._load_ollama_provider()
        
        # Load Groq (with multi-key support)
        self._load_groq_provider()
        
        # Load OpenAI
        self._load_openai_provider()
        
        # Load Anthropic
        self._load_anthropic_provider()
        
        # Load Google Gemini
        self._load_google_provider()
        
        # Load OpenRouter
        self._load_openrouter_provider()
        
        # Load Mistral
        self._load_mistral_provider()
        
        # Load DeepSeek
        self._load_deepseek_provider()
        
        # Load xAI
        self._load_xai_provider()
        
        # Load Cerebras
        self._load_cerebras_provider()
        
        # Load NVIDIA
        self._load_nvidia_provider()
        
        # Rebuild capability index
        self._rebuild_capability_index()
        
        # Update fingerprint
        self._update_config_fingerprint()
        
        logger.info("Loaded %d providers", len(self._providers))
    
    def _load_ollama_provider(self) -> None:
        """Load Ollama provider configuration."""
        ollama_url = os.getenv("OLLAMA_BASE_URL", 
                              os.getenv("OLLAMA_HOST", 
                                       "https://kiersten-nonpunishable-carry.ngrok-free.dev"))
        ollama_model = os.getenv("OLLAMA_MODEL", "jarvis-agi")
        
        if not ollama_url:
            return
        
        config = ProviderConfig(
            provider_name="ollama",
            base_url=ollama_url,
            provider_type="ollama",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.REASONING,
                Capability.CODING,
                Capability.TOOL_CALLING,
                Capability.STRUCTURED_OUTPUT,
            },
            supported_models=[ollama_model],
            priority=10,  # Lowest priority (last resort)
            supports_streaming=True,
            supports_tools=True,
            supports_images=False,  # Can be enabled if vision model is available
        )
        
        # Ollama doesn't use API keys
        keys = [ProviderKey(key_id="default", key_value="")]
        
        self._register_provider(config, keys)
    
    def _load_groq_provider(self) -> None:
        """Load Groq provider with multi-key support."""
        groq_base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        groq_models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]
        
        keys = []
        for i in range(1, 4):  # Support up to 3 keys
            key = os.getenv(f"GROQ_API_KEY_{i}" if i > 1 else "GROQ_API_KEY", "")
            if key:
                keys.append(ProviderKey(
                    key_id=f"groq-{i}",
                    key_value=key,
                    priority=i * 10
                ))
        
        if not keys:
            logger.info("No Groq API keys configured")
            return
        
        config = ProviderConfig(
            provider_name="groq",
            base_url=groq_base_url,
            provider_type="openai_compatible",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.REASONING,
                Capability.CODING,
                Capability.TOOL_CALLING,
                Capability.FAST_RESPONSE,
            },
            supported_models=groq_models,
            priority=20,  # High priority
            supports_streaming=True,
            supports_tools=True,
            supports_images=False,
        )
        
        self._register_provider(config, keys)
    
    def _load_openai_provider(self) -> None:
        """Load OpenAI provider."""
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return
        
        config = ProviderConfig(
            provider_name="openai",
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            provider_type="openai_compatible",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.REASONING,
                Capability.CODING,
                Capability.VISION,
                Capability.TOOL_CALLING,
                Capability.STRUCTURED_OUTPUT,
            },
            supported_models=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            priority=50,
            supports_streaming=True,
            supports_tools=True,
            supports_images=True,
            supports_reasoning=True,
            supports_structured_output=True,
        )
        
        keys = [ProviderKey(key_id="openai-1", key_value=openai_key, priority=10)]
        self._register_provider(config, keys)
    
    def _load_anthropic_provider(self) -> None:
        """Load Anthropic Claude provider."""
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            return
        
        config = ProviderConfig(
            provider_name="anthropic",
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
            provider_type="anthropic",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.REASONING,
                Capability.CODING,
                Capability.LONG_CONTEXT,
                Capability.STRUCTURED_OUTPUT,
            },
            supported_models=["claude-3-5-sonnet-20241022", "claude-3-opus"],
            priority=40,
            supports_streaming=True,
            supports_tools=True,
            supports_images=False,
            supports_reasoning=True,
            supports_structured_output=True,
        )
        
        keys = [ProviderKey(key_id="anthropic-1", key_value=anthropic_key, priority=10)]
        self._register_provider(config, keys)
    
    def _load_google_provider(self) -> None:
        """Load Google Gemini provider."""
        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            return
        
        config = ProviderConfig(
            provider_name="google",
            base_url=os.getenv("GOOGLE_AI_BASE_URL", 
                             "https://generativelanguage.googleapis.com/v1beta/openai"),
            provider_type="openai_compatible",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.REASONING,
                Capability.CODING,
                Capability.VISION,
                Capability.VIDEO_ANALYSIS,
            },
            supported_models=["gemini-2.0-flash", "gemini-1.5-pro"],
            priority=35,
            supports_streaming=True,
            supports_tools=True,
            supports_images=True,
            supports_reasoning=True,
        )
        
        keys = [ProviderKey(key_id="google-1", key_value=google_key, priority=10)]
        self._register_provider(config, keys)
    
    def _load_openrouter_provider(self) -> None:
        """Load OpenRouter provider."""
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            return
        
        config = ProviderConfig(
            provider_name="openrouter",
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            provider_type="openai_compatible",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.REASONING,
                Capability.CODING,
                Capability.VISION,
            },
            supported_models=["openai/gpt-4o", "anthropic/claude-3.5-sonnet"],
            priority=45,
            supports_streaming=True,
            supports_tools=True,
            supports_images=True,
        )
        
        keys = [ProviderKey(key_id="openrouter-1", key_value=openrouter_key, priority=10)]
        self._register_provider(config, keys)
    
    def _load_mistral_provider(self) -> None:
        """Load Mistral provider."""
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if not mistral_key:
            return
        
        config = ProviderConfig(
            provider_name="mistral",
            base_url=os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1"),
            provider_type="openai_compatible",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.CODING,
                Capability.FAST_RESPONSE,
            },
            supported_models=["mistral-large-latest", "mistral-medium"],
            priority=30,
            supports_streaming=True,
            supports_tools=True,
        )
        
        keys = [ProviderKey(key_id="mistral-1", key_value=mistral_key, priority=10)]
        self._register_provider(config, keys)
    
    def _load_deepseek_provider(self) -> None:
        """Load DeepSeek provider."""
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_key:
            return
        
        config = ProviderConfig(
            provider_name="deepseek",
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            provider_type="openai_compatible",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.CODING,
                Capability.REASONING,
            },
            supported_models=["deepseek-chat"],
            priority=55,
            supports_streaming=True,
            supports_tools=True,
        )
        
        keys = [ProviderKey(key_id="deepseek-1", key_value=deepseek_key, priority=10)]
        self._register_provider(config, keys)
    
    def _load_xai_provider(self) -> None:
        """Load xAI (Grok) provider."""
        xai_key = os.getenv("XAI_API_KEY")
        if not xai_key:
            return
        
        config = ProviderConfig(
            provider_name="xai",
            base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
            provider_type="openai_compatible",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.REASONING,
            },
            supported_models=["grok-beta"],
            priority=60,
            supports_streaming=True,
            supports_tools=True,
        )
        
        keys = [ProviderKey(key_id="xai-1", key_value=xai_key, priority=10)]
        self._register_provider(config, keys)
    
    def _load_cerebras_provider(self) -> None:
        """Load Cerebras provider."""
        cerebras_key = os.getenv("CEREBRAS_API_KEY")
        if not cerebras_key:
            return
        
        config = ProviderConfig(
            provider_name="cerebras",
            base_url=os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
            provider_type="openai_compatible",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.FAST_RESPONSE,
            },
            supported_models=["llama3.1-70b"],
            priority=25,
            supports_streaming=True,
            supports_tools=True,
        )
        
        keys = [ProviderKey(key_id="cerebras-1", key_value=cerebras_key, priority=10)]
        self._register_provider(config, keys)
    
    def _load_nvidia_provider(self) -> None:
        """Load NVIDIA provider."""
        nvidia_key = os.getenv("NVIDIA_API_KEY")
        if not nvidia_key:
            return
        
        config = ProviderConfig(
            provider_name="nvidia",
            base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            provider_type="openai_compatible",
            capabilities={
                Capability.GENERAL_CHAT,
                Capability.FAST_RESPONSE,
            },
            supported_models=["meta/llama-3.1-405b-instruct"],
            priority=28,
            supports_streaming=True,
            supports_tools=True,
        )
        
        keys = [ProviderKey(key_id="nvidia-1", key_value=nvidia_key, priority=10)]
        self._register_provider(config, keys)
    
    def _register_provider(self, config: ProviderConfig, keys: List[ProviderKey]) -> None:
        """Register a provider with the registry."""
        self._provider_configs[config.provider_name] = config
        
        # Create provider instance based on type
        provider = self._create_provider_instance(config, keys)
        if provider:
            self._providers[config.provider_name] = provider
            logger.info("Registered provider: %s with %d keys", 
                       config.provider_name, len(keys))
    
    def _create_provider_instance(self, config: ProviderConfig, keys: List[ProviderKey]) -> Optional[BaseProvider]:
        """Create a provider instance based on configuration."""
        # Import provider implementations
        try:
            from core.providers.openai_compatible import OpenAICompatibleProvider
            from core.providers.ollama_provider import OllamaProvider
            from core.providers.anthropic_provider import AnthropicProvider
        except ImportError:
            # If provider implementations don't exist yet, return None
            logger.warning("Provider implementations not yet available")
            return None
        
        if config.provider_type == "ollama":
            return OllamaProvider(config, keys)
        elif config.provider_type == "anthropic":
            return AnthropicProvider(config, keys)
        elif config.provider_type == "openai_compatible":
            return OpenAICompatibleProvider(config, keys)
        else:
            logger.warning("Unknown provider type: %s", config.provider_type)
            return None
    
    def _rebuild_capability_index(self) -> None:
        """Rebuild the capability-to-providers index."""
        self._capability_index.clear()
        for provider_name, config in self._provider_configs.items():
            for capability in config.capabilities:
                if capability not in self._capability_index:
                    self._capability_index[capability] = []
                self._capability_index[capability].append(provider_name)
        
        # Sort providers within each capability by priority
        for capability, providers in self._capability_index.items():
            providers.sort(key=lambda p: self._provider_configs[p].priority)
    
    def _update_config_fingerprint(self) -> None:
        """Calculate fingerprint of current configuration."""
        # Simple hash of provider names and key counts
        fingerprint_data = []
        for name, config in sorted(self._provider_configs.items()):
            provider = self._providers.get(name)
            key_count = len(provider.keys) if provider else 0
            fingerprint_data.append(f"{name}:{config.enabled}:{key_count}")
        
        fingerprint_str = "|".join(fingerprint_data)
        self._config_fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()
        self._last_config_check = time.time()
    
    def check_config_changed(self) -> bool:
        """Check if configuration has changed since last check."""
        current_fingerprint = self._calculate_current_fingerprint()
        changed = current_fingerprint != self._config_fingerprint
        if changed:
            logger.info("Configuration change detected")
            self._config_fingerprint = current_fingerprint
        return changed
    
    def _calculate_current_fingerprint(self) -> str:
        """Calculate fingerprint of current environment configuration."""
        fingerprint_data = []
        
        # Check all environment variables for API keys
        env_vars = ["GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3",
                   "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
                   "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "DEEPSEEK_API_KEY",
                   "XAI_API_KEY", "CEREBRAS_API_KEY", "NVIDIA_API_KEY",
                   "OLLAMA_BASE_URL", "OLLAMA_MODEL"]
        
        for var in sorted(env_vars):
            value = os.getenv(var, "")
            # Hash the value to avoid storing actual keys
            if value:
                hashed = hashlib.sha256(value.encode()).hexdigest()[:8]
                fingerprint_data.append(f"{var}:{hashed}")
            else:
                fingerprint_data.append(f"{var}:empty")
        
        fingerprint_str = "|".join(fingerprint_data)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def reload_if_changed(self) -> bool:
        """Reload provider configuration if it has changed."""
        if self.check_config_changed():
            logger.info("Reloading provider configuration")
            self._providers.clear()
            self._provider_configs.clear()
            self._load_from_environment()
            return True
        return False
    
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """Get a provider by name."""
        return self._providers.get(provider_name)
    
    def get_providers_for_capability(self, capability: Capability) -> List[BaseProvider]:
        """Get all providers that support a given capability."""
        provider_names = self._capability_index.get(capability, [])
        return [self._providers[name] for name in provider_names if name in self._providers]
    
    def get_available_providers(self) -> List[BaseProvider]:
        """Get all currently available providers."""
        return [p for p in self._providers.values() if p.config.available]
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        status = {}
        for name, config in self._provider_configs.items():
            provider = self._providers.get(name)
            status[name] = {
                "enabled": config.enabled,
                "available": config.available,
                "capabilities": [c.value for c in config.capabilities],
                "priority": config.priority,
                "latency_ms": config.average_latency_ms,
                "request_count": config.request_count,
                "keys_count": len(provider.keys) if provider else 0,
                "available_keys": len([k for k in provider.keys if k.is_available]) if provider else 0,
            }
        return status
    
    def record_provider_success(self, provider_name: str, latency_ms: float) -> None:
        """Record a successful request for a provider."""
        config = self._provider_configs.get(provider_name)
        if config:
            config.record_success()
            config.update_latency(latency_ms)
    
    def record_provider_failure(self, provider_name: str, error_category: str = "unknown") -> None:
        """Record a failed request for a provider."""
        config = self._provider_configs.get(provider_name)
        if config:
            config.record_failure()
    
    def record_key_success(self, provider_name: str, key_id: str) -> None:
        """Record a successful request for a specific key."""
        provider = self._providers.get(provider_name)
        if provider:
            for key in provider.keys:
                if key.key_id == key_id:
                    key.record_success()
                    break
    
    def record_key_failure(self, provider_name: str, key_id: str, error_category: str = "unknown") -> None:
        """Record a failed request for a specific key."""
        provider = self._providers.get(provider_name)
        if provider:
            for key in provider.keys:
                if key.key_id == key_id:
                    key.record_failure(error_category)
                    break


# Global instance
provider_registry = ProviderRegistry()
