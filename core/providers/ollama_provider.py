"""core/providers/ollama_provider.py — Ollama provider implementation.

Supports local Ollama instances (including via ngrok tunnel).
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


class OllamaProvider(BaseProvider):
    """Provider implementation for Ollama."""
    
    # Ngrok warning bypass header is required for ngrok-free endpoints
    NGROK_HEADERS = {"ngrok-skip-browser-warning": "true"}
    
    def __init__(self, config: ProviderConfig, keys: List[ProviderKey]):
        super().__init__(config, keys)
        
        if httpx is None:
            raise RuntimeError("httpx is required for Ollama provider")
        
        self._client = None
        self._model = config.supported_models[0] if config.supported_models else "jarvis-agi"
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(120.0, connect=10.0)
            self._client = httpx.AsyncClient(
                timeout=timeout,
                verify=False,
                headers=self.NGROK_HEADERS,
                limits=httpx.Limits(
                    max_connections=4,
                    max_keepalive_connections=2,
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
        target_model = model or self._model
        
        try:
            client = self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/api/chat"
            
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_ctx": 16384,
                    "temperature": kwargs.get("temperature", 0.25),
                    "top_k": 10,
                    "top_p": 0.9,
                    "num_predict": kwargs.get("max_tokens", 2048),
                }
            }
            
            # Add tools if supported
            if "tools" in kwargs and self.config.supports_tools:
                payload["tools"] = kwargs["tools"]
            
            logger.info("[AI] Ollama → %s model=%s", url, target_model)
            
            response = await client.post(url, json=payload)
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                error_text = response.text[:200]
                logger.error("[AI] Ollama error %s: %s", response.status_code, error_text)
                
                # Check for ngrok tunnel offline
                ngrok_error_code = response.headers.get("Ngrok-Error-Code", "")
                is_tunnel_offline = (
                    ngrok_error_code == "ERR_NGROK_3200"
                    or "ERR_NGROK" in error_text
                    or ("endpoint" in error_text.lower() and "offline" in error_text.lower())
                )
                
                if response.status_code in (403, 404, 502, 503) and is_tunnel_offline:
                    self.config.available = False
                    logger.warning("[AI] Ollama tunnel OFFLINE")
                
                self.config.record_failure()
                
                return ProviderResponse(
                    success=False,
                    provider="ollama",
                    model=target_model,
                    latency_ms=latency_ms,
                    error=f"HTTP {response.status_code}: {error_text}",
                    error_category="server_error" if is_tunnel_offline else "unknown",
                )
            
            data = response.json()
            content = data.get("message", {}).get("content", "")
            
            if not content:
                content = data.get("content", "") or data.get("response", "")
            
            # Record success
            self.config.record_success()
            self.config.update_latency(latency_ms)
            
            logger.info("[AI] Ollama completed in %.1fms", latency_ms)
            
            return ProviderResponse(
                content=content,
                success=bool(content),
                provider="ollama",
                model=target_model,
                latency_ms=latency_ms,
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("[AI] Ollama exception: %s", e)
            
            self.config.record_failure()
            
            return ProviderResponse(
                success=False,
                provider="ollama",
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
        target_model = model or self._model
        
        try:
            client = self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/api/chat"
            
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": True,
                "options": {
                    "num_ctx": 16384,
                    "temperature": kwargs.get("temperature", 0.25),
                    "top_k": 10,
                    "top_p": 0.9,
                    "num_predict": kwargs.get("max_tokens", 2048),
                }
            }
            
            # Add tools if supported
            if "tools" in kwargs and self.config.supports_tools:
                payload["tools"] = kwargs["tools"]
            
            logger.info("[AI] Ollama → stream %s model=%s", url, target_model)
            
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = (await response.aread())[:200].decode()
                    logger.error("[AI] Ollama stream error %s: %s", response.status_code, error_text)
                    
                    # Check for ngrok tunnel offline
                    ngrok_error_code = response.headers.get("Ngrok-Error-Code", "")
                    is_tunnel_offline = (
                        ngrok_error_code == "ERR_NGROK_3200"
                        or "ERR_NGROK" in error_text
                        or ("endpoint" in error_text.lower() and "offline" in error_text.lower())
                    )
                    
                    if response.status_code in (403, 404, 502, 503) and is_tunnel_offline:
                        self.config.available = False
                        logger.warning("[AI] Ollama tunnel OFFLINE")
                    
                    self.config.record_failure()
                    
                    yield f"[Ollama error {response.status_code}]"
                    return
                
                token_count = 0
                first_token_time = None
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        message = data.get("message", {})
                        content = message.get("content", "")
                        
                        # Handle thinking tokens (model-internal)
                        thinking = message.get("thinking", "")
                        if thinking:
                            # Skip thinking tokens - they're model-internal
                            continue
                        
                        if content:
                            if first_token_time is None:
                                first_token_time = time.time()
                                ttft = (first_token_time - start_time) * 1000
                                logger.info("[AI] Ollama first token in %.0fms", ttft)
                            
                            token_count += 1
                            yield content
                    except json.JSONDecodeError:
                        continue
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Record success
                self.config.record_success()
                self.config.update_latency(latency_ms)
                
                logger.info("[AI] Ollama stream completed: %d tokens in %.1fms", 
                           token_count, latency_ms)
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("[AI] Ollama stream exception: %s", e)
            
            self.config.record_failure()
            
            yield f"[Ollama Error: {str(e)}]"
    
    async def check_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            client = self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/api/tags"
            
            response = await client.get(url, timeout=5.0)
            
            if response.status_code != 200:
                self.config.available = False
                return False
            
            data = response.json()
            models = data.get("models", [])
            
            # Check if our model is available
            model_available = any(
                self._model in m.get("name", "") 
                for m in models
            )
            
            self.config.available = model_available
            self.config.last_check_time = time.time()
            
            return model_available
            
        except Exception as e:
            logger.debug("[AI] Ollama availability check failed: %s", e)
            self.config.available = False
            return False
    
    async def pull_model(self) -> bool:
        """Pull the model if not available."""
        try:
            client = self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/api/pull"
            
            logger.info("[AI] Pulling Ollama model %s...", self._model)
            
            async with client.stream("POST", url, json={"name": self._model}, timeout=300.0) as response:
                async for _ in response.aiter_lines():
                    pass
            
            logger.info("[AI] Ollama model %s pulled successfully", self._model)
            return True
            
        except Exception as e:
            logger.warning("[AI] Failed to pull Ollama model %s: %s", self._model, e)
            return False
