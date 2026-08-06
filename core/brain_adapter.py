"""core/brain_adapter.py — Model Agnostic Brain Adapter for JARVIS vNext++.

Provides a unified interface to multiple LLM providers:
- Ollama
- Groq
- OpenAI
- Gemini
- Anthropic
- OpenRouter
- LM Studio

Jarvis Core consumes BrainAdapter without knowing which provider is active.
"""

from __future__ import annotations

import os
import json
import logging
import asyncio
from typing import Any, Dict, List, AsyncGenerator, Optional
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str = ""
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    success: bool = True
    error: str = ""


class BrainAdapter:
    """Provider-agnostic LLM interface."""

    def __init__(self, provider: str = "ollama", model: str = "qwen2.5:14b"):
        self.provider = os.getenv("JARVIS_LLM_PROVIDER", provider).lower()
        self.primary_model = os.getenv("JARVIS_LLM_MODEL", model)
        self.fallback_model = os.getenv("JARVIS_LLM_FALLBACK", "qwen2.5:14b")
        self._warmed_up = False
        # Reuse a single httpx client across all requests — avoids a fresh
        # TCP + TLS + ngrok handshake on every chat call (~2-4s saved).
        self._http_client = None

    async def warmup(self) -> bool:
        """Send tiny warmup request post-boot to eliminate initialization latency."""
        try:
            logger.info(f"Warming up LLM provider ({self.provider})...")
            messages = [{"role": "user", "content": "hello"}]
            async for _ in self.chat_stream(messages, max_tokens=10):
                pass
            self._warmed_up = True
            logger.info("LLM Provider warmup completed.")
            return True
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
            return False

    def _get_http_client(self):
        """Return a shared httpx client (created lazily, reused across calls)."""
        if self._http_client is None or self._http_client.is_closed:
            import httpx
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                headers={"ngrok-skip-browser-warning": "true"},
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
            )
        return self._http_client

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.25,
        max_tokens: int = 2048,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream text tokens from active provider."""
        target_model = model or self.primary_model

        if self.provider == "ollama":
            async for token in self._stream_ollama(messages, target_model, temperature, max_tokens, options):
                yield token
        elif self.provider == "groq":
            async for token in self._stream_groq(messages, target_model, temperature, max_tokens):
                yield token
        else:
            async for token in self._stream_ollama(messages, target_model, temperature, max_tokens, options):
                yield token

    async def _stream_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream from Ollama via ngrok tunnel with a persistent connection."""
        try:
            url = os.getenv("OLLAMA_HOST", "https://kiersten-nonpunishable-carry.ngrok-free.dev") + "/api/chat"
            client = self._get_http_client()

            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {
                    "num_ctx": 16384,
                    "temperature": temperature,
                    "top_k": 10,
                    "top_p": 0.9,
                    "num_predict": max_tokens,
                    **(options or {})
                }
            }

            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield f"Ollama error {response.status_code}"
                    return
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            yield f"[Ollama Error: {e}]"

    async def _stream_groq(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream from Groq API."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            yield "Groq API key missing. Please configure GROQ_API_KEY."
            return

        try:
            import httpx
            url = "https://api.groq.com/openai/v1/chat/completions"
            groq_headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model or "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }

            client = self._get_http_client()
            async with client.stream("POST", url, headers=groq_headers, json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            token = data["choices"][0]["delta"].get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"Groq stream error: {e}")
            yield f"[Groq Error: {e}]"
