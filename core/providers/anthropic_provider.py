"""core/providers/anthropic_provider.py — Anthropic Claude provider implementation.

Supports Anthropic's Claude models with their native API format.
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


class AnthropicProvider(BaseProvider):
    """Provider implementation for Anthropic Claude."""
    
    def __init__(self, config: ProviderConfig, keys: List[ProviderKey]):
        super().__init__(config, keys)
        
        if httpx is None:
            raise RuntimeError("httpx is required for Anthropic provider")
        
        self._client = None
        self._anthropic_version = "2023-06-01"
    
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
    
    def _convert_messages_to_anthropic_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-style messages to Anthropic format."""
        anthropic_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                # Anthropic handles system messages separately
                continue
            elif role == "assistant":
                anthropic_messages.append({
                    "role": "assistant",
                    "content": content,
                })
            else:  # user
                anthropic_messages.append({
                    "role": "user",
                    "content": content,
                })
        
        return anthropic_messages
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "",
        **kwargs
    ) -> ProviderResponse:
        """Execute a non-streaming chat request."""
        start_time = time.time()
        
        # Select model
        target_model = model or (self.config.supported_models[0] if self.config.supported_models else "claude-3-5-sonnet-20241022")
        
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
            url = f"{self.config.base_url.rstrip('/')}/messages"
            
            headers = {
                "x-api-key": key.key_value,
                "anthropic-version": self._anthropic_version,
                "Content-Type": "application/json",
            }
            
            # Extract system message
            system_message = ""
            openai_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                else:
                    openai_messages.append(msg)
            
            # Convert to Anthropic format
            anthropic_messages = self._convert_messages_to_anthropic_format(openai_messages)
            
            payload = {
                "model": target_model,
                "messages": anthropic_messages,
                "max_tokens": kwargs.get("max_tokens", 2048),
            }
            
            if system_message:
                payload["system"] = system_message
            
            if "temperature" in kwargs:
                payload["temperature"] = kwargs["temperature"]
            
            # Add tools if supported
            if "tools" in kwargs and self.config.supports_tools:
                payload["tools"] = kwargs["tools"]
            
            logger.info("[AI] Anthropic → %s model=%s", url, target_model)
            
            response = await client.post(url, headers=headers, json=payload)
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                error_text = response.text[:200]
                logger.error("[AI] Anthropic error %s: %s", response.status_code, error_text)
                
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
            content = data.get("content", [{}])[0].get("text", "")
            
            # Record success
            key.record_success()
            self.config.record_success()
            self.config.update_latency(latency_ms)
            
            logger.info("[AI] Anthropic completed in %.1fms", latency_ms)
            
            return ProviderResponse(
                content=content,
                success=True,
                provider=self.config.provider_name,
                model=target_model,
                latency_ms=latency_ms,
                tokens_used=data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                finish_reason=data.get("stop_reason", ""),
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("[AI] Anthropic exception: %s", self.config.provider_name, e)
            
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
        target_model = model or (self.config.supported_models[0] if self.config.supported_models else "claude-3-5-sonnet-20241022")
        
        # Get available key
        key = self.current_key
        if not key:
            yield f"[Error: No available API keys for {self.config.provider_name}]"
            return
        
        try:
            client = self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/messages"
            
            headers = {
                "x-api-key": key.key_value,
                "anthropic-version": self._anthropic_version,
                "Content-Type": "application/json",
            }
            
            # Extract system message
            system_message = ""
            openai_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                else:
                    openai_messages.append(msg)
            
            # Convert to Anthropic format
            anthropic_messages = self._convert_messages_to_anthropic_format(openai_messages)
            
            payload = {
                "model": target_model,
                "messages": anthropic_messages,
                "max_tokens": kwargs.get("max_tokens", 2048),
                "stream": True,
            }
            
            if system_message:
                payload["system"] = system_message
            
            if "temperature" in kwargs:
                payload["temperature"] = kwargs["temperature"]
            
            # Add tools if supported
            if "tools" in kwargs and self.config.supports_tools:
                payload["tools"] = kwargs["tools"]
            
            logger.info("[AI] Anthropic → stream %s model=%s", url, target_model)
            
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = (await response.aread())[:200].decode()
                    logger.error("[AI] Anthropic stream error %s: %s", response.status_code, error_text)
                    
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
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                text = delta.get("text", "")
                                if text:
                                    token_count += 1
                                    yield text
                        except json.JSONDecodeError:
                            continue
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Record success
                key.record_success()
                self.config.record_success()
                self.config.update_latency(latency_ms)
                
                logger.info("[AI] Anthropic stream completed: %d tokens in %.1fms", 
                           token_count, latency_ms)
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("[AI] Anthropic stream exception: %s", self.config.provider_name, e)
            
            key.record_failure("unknown")
            self.config.record_failure()
            
            yield f"[Error: {str(e)}]"
    
    async def check_available(self) -> bool:
        """Check if Anthropic is available."""
        key = self.current_key
        if not key:
            return False
        
        try:
            client = self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/messages"
            
            headers = {
                "x-api-key": key.key_value,
                "anthropic-version": self._anthropic_version,
            }
            
            # Send a minimal request to check availability
            response = await client.post(
                url,
                headers=headers,
                json={
                    "model": self.config.supported_models[0] if self.config.supported_models else "claude-3-5-sonnet-20241022",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 10,
                },
                timeout=5.0
            )
            
            is_available = response.status_code == 200
            
            self.config.available = is_available
            self.config.last_check_time = time.time()
            
            return is_available
            
        except Exception as e:
            logger.debug("[AI] Anthropic availability check failed: %s", self.config.provider_name, e)
            self.config.available = False
            return False
