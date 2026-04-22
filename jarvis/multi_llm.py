"""jarvis.multi_llm

Multi-LLM support with OpenAI, Anthropic, Groq, and local models.
Fallback chain and intelligent routing.
"""

from __future__ import annotations

import functools
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable

from jarvis.error_handler import retry_with_backoff, rate_limiter_groq
from jarvis.secure_storage import APIKeyManager

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    text: str
    model: str
    provider: str
    latency_ms: float
    tokens_used: int = 0
    cached: bool = False


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, name: str, model: str) -> None:
        self.name = name
        self.model = model
        self.last_error: Exception | None = None
        self.success_count = 0
        self.error_count = 0
    
    @abstractmethod
    def chat(self, messages: list[dict], **kwargs: Any) -> LLMResponse:
        """Send chat request to LLM."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass
    
    def get_stats(self) -> dict:
        """Get provider statistics."""
        total = self.success_count + self.error_count
        return {
            "name": self.name,
            "model": self.model,
            "success_rate": self.success_count / total if total > 0 else 0,
            "total_calls": total,
            "last_error": str(self.last_error) if self.last_error else None,
        }


class GroqProvider(BaseLLMProvider):
    """Groq LLM provider."""
    
    def __init__(self, model: str = "llama-3.1-8b-instant") -> None:
        super().__init__("Groq", model)
        self.client = None
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize Groq client."""
        try:
            from groq import Groq
            api_key = APIKeyManager.get_key("GROQ_API_KEY")
            if api_key:
                self.client = Groq(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to init Groq: {e}")
    
    def is_available(self) -> bool:
        return self.client is not None
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def chat(self, messages: list[dict], **kwargs: Any) -> LLMResponse:
        """Chat with Groq."""
        if not self.client:
            raise RuntimeError("Groq client not initialized")
        
        # Rate limiting
        if not rate_limiter_groq.can_call():
            wait = rate_limiter_groq.get_wait_time()
            logger.warning(f"Groq rate limit reached, waiting {wait:.1f}s")
            time.sleep(wait)
        
        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 1024),
            )
            rate_limiter_groq.record_call()
            
            latency = (time.time() - start) * 1000
            self.success_count += 1
            
            return LLMResponse(
                text=response.choices[0].message.content,
                model=self.model,
                provider="Groq",
                latency_ms=latency,
                tokens_used=response.usage.total_tokens if response.usage else 0,
            )
        except Exception as e:
            self.error_count += 1
            self.last_error = e
            raise


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, model: str = "gpt-4") -> None:
        super().__init__("OpenAI", model)
        self.client = None
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize OpenAI client."""
        try:
            import openai
            api_key = APIKeyManager.get_key("OPENAI_API_KEY")
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to init OpenAI: {e}")
    
    def is_available(self) -> bool:
        return self.client is not None
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def chat(self, messages: list[dict], **kwargs: Any) -> LLMResponse:
        """Chat with OpenAI."""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        
        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 1024),
            )
            
            latency = (time.time() - start) * 1000
            self.success_count += 1
            
            return LLMResponse(
                text=response.choices[0].message.content,
                model=self.model,
                provider="OpenAI",
                latency_ms=latency,
                tokens_used=response.usage.total_tokens if response.usage else 0,
            )
        except Exception as e:
            self.error_count += 1
            self.last_error = e
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider."""
    
    def __init__(self, model: str = "claude-3-sonnet-20240229") -> None:
        super().__init__("Anthropic", model)
        self.client = None
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize Anthropic client."""
        try:
            import anthropic
            api_key = APIKeyManager.get_key("ANTHROPIC_API_KEY")
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to init Anthropic: {e}")
    
    def is_available(self) -> bool:
        return self.client is not None
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def chat(self, messages: list[dict], **kwargs: Any) -> LLMResponse:
        """Chat with Anthropic."""
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")
        
        # Convert messages to Anthropic format
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                chat_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        start = time.time()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 1024),
                temperature=kwargs.get("temperature", 0.7),
                system=system_msg,
                messages=chat_messages,
            )
            
            latency = (time.time() - start) * 1000
            self.success_count += 1
            
            return LLMResponse(
                text=response.content[0].text,
                model=self.model,
                provider="Anthropic",
                latency_ms=latency,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else 0,
            )
        except Exception as e:
            self.error_count += 1
            self.last_error = e
            raise


class LocalLLMProvider(BaseLLMProvider):
    """Local LLM via Ollama or similar."""
    
    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434") -> None:
        super().__init__("Local", model)
        self.base_url = base_url
        self._available = self._check_available()
    
    def _check_available(self) -> bool:
        """Check if local LLM is running."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def is_available(self) -> bool:
        return self._available
    
    def chat(self, messages: list[dict], **kwargs: Any) -> LLMResponse:
        """Chat with local LLM via Ollama."""
        try:
            import requests
            
            # Convert messages to prompt
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            
            start = time.time()
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            
            latency = (time.time() - start) * 1000
            self.success_count += 1
            
            return LLMResponse(
                text=data.get("response", ""),
                model=self.model,
                provider="Local (Ollama)",
                latency_ms=latency,
            )
        except Exception as e:
            self.error_count += 1
            self.last_error = e
            raise


class MultiLLMManager:
    """Manager for multiple LLM providers with fallback."""
    
    def __init__(self) -> None:
        self.providers: dict[str, BaseLLMProvider] = {}
        self.provider_order: list[str] = []
        self.response_cache: dict[str, LLMResponse] = {}
        self.cache_enabled = True
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize all providers
        self._init_providers()
    
    def _init_providers(self) -> None:
        """Initialize all LLM providers."""
        # Priority order
        self.providers["groq"] = GroqProvider()
        self.providers["openai"] = OpenAIProvider()
        self.providers["anthropic"] = AnthropicProvider()
        self.providers["local"] = LocalLLMProvider()
        
        # Order by priority
        self.provider_order = ["groq", "openai", "anthropic", "local"]
    
    def get_available_providers(self) -> list[str]:
        """Get list of available providers."""
        return [name for name, provider in self.providers.items() if provider.is_available()]
    
    def chat(
        self,
        messages: list[dict],
        preferred_provider: str | None = None,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Chat with fallback chain.
        
        Args:
            messages: List of message dicts with role and content
            preferred_provider: Preferred provider name
            use_cache: Whether to use response caching
            **kwargs: Additional parameters for LLM
        """
        # Check cache
        if use_cache and self.cache_enabled:
            cache_key = self._get_cache_key(messages)
            cached = self._get_cached(cache_key)
            if cached:
                cached.cached = True
                return cached
        
        # Try providers in order
        providers_to_try = self._get_provider_order(preferred_provider)
        
        for provider_name in providers_to_try:
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_available():
                continue
            
            try:
                logger.info(f"Trying {provider_name}...")
                response = provider.chat(messages, **kwargs)
                
                # Cache successful response
                if use_cache and self.cache_enabled:
                    self._cache_response(cache_key, response)
                
                return response
                
            except Exception as e:
                logger.warning(f"{provider_name} failed: {e}")
                continue
        
        # All providers failed
        raise RuntimeError("All LLM providers failed")
    
    def _get_provider_order(self, preferred: str | None) -> list[str]:
        """Get provider order with preferred first."""
        order = self.provider_order.copy()
        if preferred and preferred in order:
            order.remove(preferred)
            order.insert(0, preferred)
        return order
    
    def _get_cache_key(self, messages: list[dict]) -> str:
        """Generate cache key from messages."""
        content = json.dumps(messages, sort_keys=True)
        return str(hash(content))
    
    def _get_cached(self, key: str) -> LLMResponse | None:
        """Get cached response if not expired."""
        if key not in self.response_cache:
            return None
        
        # Check TTL
        # (Simplified - in production use proper cache with timestamps)
        return self.response_cache[key]
    
    def _cache_response(self, key: str, response: LLMResponse) -> None:
        """Cache a response."""
        self.response_cache[key] = response
        
        # Limit cache size
        if len(self.response_cache) > 100:
            # Remove oldest (first added)
            oldest = next(iter(self.response_cache))
            del self.response_cache[oldest]
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics for all providers."""
        return {
            name: provider.get_stats()
            for name, provider in self.providers.items()
        }
    
    def clear_cache(self) -> None:
        """Clear response cache."""
        self.response_cache.clear()


# Global Multi-LLM manager
multi_llm = MultiLLMManager()
