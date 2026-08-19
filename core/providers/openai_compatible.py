"""core/providers/openai_compatible.py — OpenAI-compatible provider implementation.

Supports providers that use the OpenAI API format:
- Groq
- OpenRouter
- DeepSeek
- xAI
- Cerebras
- NVIDIA
- Mistral
- OpenAI
- Google (via OpenAI-compatible endpoint)
"""

from __future__ import annotations

import logging
import time
import json
from typing import AsyncGenerator, Dict, List, Any, Optional

try:
    import httpx
except ImportError:
    httpx = None

from core.provider_registry import (
    BaseProvider,
    ProviderConfig,
    ProviderKey,
    ProviderResponse,
    Capability,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseProvider):
    """Provider implementation for OpenAI-compatible APIs."""
    
    def __init__(self, config: ProviderConfig, keys: List[ProviderKey]):
        super().__init__(config, keys)
        
        if httpx is None:
            raise RuntimeError("httpx is required for OpenAI-compatible providers")
        
        self._client = None
        self._client_lock = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(60.0, connect=10.0)
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                    keepalive_expiry=60,
                ),
            )
        return self._client
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "",
        **kwargs
    ) -> ProviderResponse:
        """Execute a non-streaming chat request."""
        start_time = time.time()
        
        # Select model
        target_model = model or (self.config.supported_models[0] if self.config.supported_models else "")
        
        # Get available key
        key = self.current_key
        if not key:
            return ProviderResponse(
                success=False,
                provider=self.config.provider_name,
                model=target_model,
                error="No available API keys",
                error_category="auth_error",
            )
        
        try:
            client = self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {key.key_value}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": False,
            }
            
            # Add optional parameters
            if "temperature" in kwargs:
                payload["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                payload["max_tokens"] = kwargs["max_tokens"]
            if "tools" in kwargs:
                payload["tools"] = kwargs["tools"]
            
            logger.info("[AI] %s → %s model=%s", self.config.provider_name, url, target_model)
            
            response = await client.post(url, headers=headers, json=payload)
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                error_text = response.text[:200]
                logger.error("[AI] %s error %s: %s", self.config.provider_name, response.status_code, error_text)
                
                # Categorize error
                error_category = "unknown"
                if response.status_code == 429:
                    error_category = "rate_limit"
                elif response.status_code in (401, 403):
                    error_category = "auth_error"
                elif response.status_code >= 500:
                    error_category = "server_error"
                
                key.record_failure(error_category)
                self.config.record_failure()
                
                return ProviderResponse(
                    success=False,
                    provider=self.config.provider_name,
                    model=target_model,
                    latency_ms=latency_ms,
                    error=f"HTTP {response.status_code}: {error_text}",
                    error_category=error_category,
                )
            
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Record success
            key.record_success()
            self.config.record_success()
            self.config.update_latency(latency_ms)
            
            logger.info("[AI] %s completed in %.1fms", self.config.provider_name, latency_ms)
            
            return ProviderResponse(
                content=content,
                success=True,
                provider=self.config.provider_name,
                model=target_model,
                latency_ms=latency_ms,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=data.get("choices", [{}])[0].get("finish_reason", ""),
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("[AI] %s exception: %s", self.config.provider_name, e)
            
            key.record_failure("unknown")
            self.config.record_failure()
            
            return ProviderResponse(
                success=False,
                provider=self.config.provider_name,
                model=target_model,
                latency_ms=latency_ms,
                error=str(e),
                error_category="unknown",
            )
    
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        model: str = "",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Execute a streaming chat request."""
        start_time = time.time()
        
        # Select model
        target_model = model or (self.config.supported_models[0] if self.config.supported_models else "")
        
        # Get available key
        key = self.current_key
        if not key:
            yield f"[Error: No available API keys for {self.config.provider_name}]"
            return
        
        try:
            client = self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {key.key_value}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": True,
            }
            
            # Add optional parameters
            if "temperature" in kwargs:
                payload["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                payload["max_tokens"] = kwargs["max_tokens"]
            if "tools" in kwargs:
                payload["tools"] = kwargs["tools"]
            
            logger.info("[AI] %s → stream %s model=%s", self.config.provider_name, url, target_model)
            
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = (await response.aread())[:200].decode()
                    logger.error("[AI] %s stream error %s: %s", self.config.provider_name, response.status_code, error_text)
                    
                    # Categorize error
                    error_category = "unknown"
                    if response.status_code == 429:
                        error_category = "rate_limit"
                    elif response.status_code in (401, 403):
                        error_category = "auth_error"
                    elif response.status_code >= 500:
                        error_category = "server_error"
                    
                    key.record_failure(error_category)
                    self.config.record_failure()
                    
                    yield f"[Error: HTTP {response.status_code}]"
                    return
                
                token_count = 0
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                token_count += 1
                                yield content
                        except json.JSONDecodeError:
                            continue
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Record success
                key.record_success()
                self.config.record_success()
                self.config.update_latency(latency_ms)
                
                logger.info("[AI] %s stream completed: %d tokens in %.1fms", 
                           self.config.provider_name, token_count, latency_ms)
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("[AI] %s stream exception: %s", self.config.provider_name, e)
            
            key.record_failure("unknown")
            self.config.record_failure()
            
            yield f"[Error: {str(e)}]"
    
    async def check_available(self) -> bool:
        """Check if the provider is available."""
        key = self.current_key
        if not key:
            return False
        
        try:
            client = self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/models"
            
            headers = {
                "Authorization": f"Bearer {key.key_value}",
            }
            
            response = await client.get(url, timeout=5.0)
            is_available = response.status_code == 200
            
            self.config.available = is_available
            self.config.last_check_time = time.time()
            
            return is_available
            
        except Exception as e:
            logger.debug("[AI] %s availability check failed: %s", self.config.provider_name, e)
            self.config.available = False
            return False
