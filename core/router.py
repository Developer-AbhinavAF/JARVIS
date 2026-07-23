"""router — AI Provider Router with Ollama first-class support.

Priority: API Providers → Ollama → Error
Never shows provider failures to the user.
"""

from __future__ import annotations

import os
import json
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator
from pathlib import Path
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RouterResponse:
    content: str = ""
    success: bool = False
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    error: str = ""


@dataclass
class ProviderInfo:
    name: str
    base_url: str
    api_key: str
    models: list[str] = field(default_factory=list)
    priority: int = 50
    enabled: bool = True
    latency_ms: float = 0.0
    error_count: int = 0


class BaseProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], model: str = "", **kwargs) -> RouterResponse:
        ...

    @abstractmethod
    async def chat_stream(self, messages: list[dict[str, str]], model: str = "", **kwargs) -> AsyncGenerator[str, None]:
        ...


class OpenAICompatibleProvider(BaseProvider):
    def __init__(self, info: ProviderInfo) -> None:
        self.info = info
        self._client = httpx.AsyncClient(timeout=60.0, verify=False)

    async def chat(self, messages: list[dict[str, str]], model: str = "", **kwargs) -> RouterResponse:
        start = time.time()
        model = model or (self.info.models[0] if self.info.models else "gpt-3.5-turbo")
        try:
            resp = await self._client.post(
                f"{self.info.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.info.api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "stream": False, **kwargs},
            )
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            self.info.latency_ms = (time.time() - start) * 1000
            return RouterResponse(content=content, success=True, provider=self.info.name, model=model, latency_ms=self.info.latency_ms)
        except Exception as e:
            self.info.error_count += 1
            return RouterResponse(error=str(e), provider=self.info.name)

    async def chat_stream(self, messages: list[dict[str, str]], model: str = "", **kwargs) -> AsyncGenerator[str, None]:
        model = model or (self.info.models[0] if self.info.models else "gpt-3.5-turbo")
        try:
            async with self._client.stream(
                "POST",
                f"{self.info.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.info.api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "stream": True, **kwargs},
                timeout=120.0,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str and data_str != "[DONE]":
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.debug("Stream error from %s: %s", self.info.name, e)


class OllamaProvider(BaseProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3:1.7b-q4_k_m") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model  # QWEN3:1.7B Q4_K_M as primary
        self._client = httpx.AsyncClient(timeout=120.0, verify=False)

    async def chat(self, messages: list[dict[str, str]], model: str = "", **kwargs) -> RouterResponse:
        start = time.time()
        model = model or self.model
        try:
            logger.info(f"Sending to Ollama: model={model}, messages={len(messages)}")
            logger.info(f"Message preview: {messages[0]['content'][:100] if messages else 'none'}")
            resp = await self._client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False, **kwargs},
            )
            data = resp.json()
            logger.info(f"Ollama raw response status: {resp.status_code}")
            logger.info(f"Ollama raw response keys: {data.keys()}")
            logger.info(f"Ollama raw response: {data}")
            content = data.get("message", {}).get("content", "")
            logger.info(f"Ollama extracted content: '{content}'")
            if not content:
                logger.warning("Ollama returned empty content, trying to extract from different path")
                # Try alternative extraction methods
                if "content" in data:
                    content = data["content"]
                elif "response" in data:
                    content = data["response"]
            latency_ms = (time.time() - start) * 1000
            return RouterResponse(content=content, success=bool(content), provider="ollama", model=model, latency_ms=latency_ms)
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return RouterResponse(error=str(e), provider="ollama")

    async def chat_stream(self, messages: list[dict[str, str]], model: str = "", **kwargs) -> AsyncGenerator[str, None]:
        model = model or self.model
        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": True, **kwargs},
                timeout=120.0,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            msg = chunk.get("message", {})
                            content = msg.get("content", "")
                            thinking = msg.get("thinking", "")
                            if thinking:
                                yield f"\x00{thinking}"
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.debug("Ollama stream error: %s", e)

    async def check_available(self) -> bool:
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            if resp.status_code != 200:
                return False
            models = resp.json().get("models", [])
            for m in models:
                if self.model in m.get("name", ""):
                    return True
            return False
        except Exception:
            return False

    async def pull_model(self) -> bool:
        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                timeout=300.0,
            ) as resp:
                async for _ in resp.aiter_lines():
                    pass
            return True
        except Exception as e:
            logger.warning("Failed to pull Ollama model %s: %s", self.model, e)
            return False


class AIRouter:
    def __init__(self) -> None:
        self._providers: list[BaseProvider] = []
        self._ollama: OllamaProvider | None = None
        self._lock = threading.Lock()
        self._init_providers()

    def _init_providers(self) -> None:
        # Initialize Ollama FIRST as primary (QWEN3:1.7B Q4_K_M)
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b-q4_k_m")
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._ollama = OllamaProvider(base_url=ollama_url, model=ollama_model)
        
        # Groq as secondary
        groq_models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]
        groq_base = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

        groq_keys = [
            ("groq-1", os.getenv("GROQ_API_KEY", ""), 10),
            ("groq-2", os.getenv("GROQ_API_KEY_2", ""), 20),
            ("groq-3", os.getenv("GROQ_API_KEY_3", ""), 30),
        ]
        for name, key, priority in groq_keys:
            if key:
                self._providers.append(OpenAICompatibleProvider(ProviderInfo(name, groq_base, key, groq_models, priority=priority)))

        mistral_key = os.getenv("MISTRAL_API_KEY", "")
        if mistral_key:
            self._providers.append(OpenAICompatibleProvider(ProviderInfo("mistral", os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1"), mistral_key, ["mistral-large-latest"], priority=40)))

        fallback_providers = [
            ProviderInfo("openai", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), os.getenv("OPENAI_API_KEY", ""), ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"], priority=50),
            ProviderInfo("anthropic", os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"), os.getenv("ANTHROPIC_API_KEY", ""), ["claude-3-5-sonnet-20241022"], priority=60),
            ProviderInfo("openrouter", os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"), os.getenv("OPENROUTER_API_KEY", ""), ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"], priority=70),
            ProviderInfo("deepseek", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"), os.getenv("DEEPSEEK_API_KEY", ""), ["deepseek-chat"], priority=80),
            ProviderInfo("google", os.getenv("GOOGLE_AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"), os.getenv("GOOGLE_API_KEY", ""), ["gemini-2.0-flash"], priority=90),
        ]
        for p in fallback_providers:
            if p.api_key:
                self._providers.append(OpenAICompatibleProvider(p))

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    async def chat(self, messages: list[dict[str, str]] | str, model: str = "", **kwargs) -> RouterResponse:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        for provider in sorted(self._providers, key=lambda p: p.info.priority):
            try:
                result = await provider.chat(messages, model=model, **kwargs)
                if result.success:
                    return result
            except Exception as e:
                logger.debug("Provider %s failed: %s", provider.info.name, e)

        if self._ollama:
            try:
                result = await self._ollama.chat(messages, model=model, **kwargs)
                if result.success:
                    return result
            except Exception as e:
                logger.debug("Ollama failed: %s", e)

        return RouterResponse(content="I'm sorry, I couldn't process that request.", error="All providers exhausted", success=False)

    async def chat_stream(self, messages: list[dict[str, str]] | str, model: str = "", **kwargs) -> AsyncGenerator[str, None]:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        for provider in sorted(self._providers, key=lambda p: p.info.priority):
            try:
                async for chunk in provider.chat_stream(messages, model=model, **kwargs):
                    yield chunk
                return
            except Exception as e:
                logger.debug("Provider %s stream failed: %s", provider.info.name, e)

        if self._ollama:
            try:
                async for chunk in self._ollama.chat_stream(messages, model=model, **kwargs):
                    yield chunk
                return
            except Exception:
                pass

        yield "I'm sorry, I couldn't process that request."

    async def chat_simple(self, text: str, model: str = "", **kwargs) -> str:
        result = await self.chat(text, model=model, **kwargs)
        return result.content

    async def check_ollama(self) -> bool:
        if self._ollama:
            return await self._ollama.check_available()
        return False

    async def ensure_ollama_model(self) -> bool:
        if self._ollama:
            available = await self._ollama.check_available()
            if not available:
                logger.info("Pulling Ollama model %s...", self._ollama.model)
                return await self._ollama.pull_model()
            return True
        return False


router = AIRouter()
