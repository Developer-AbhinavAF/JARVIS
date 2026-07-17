"""Provider Execution — Actually calls AI providers.

Handles HTTP requests, retries, response parsing for each provider.
"""

from __future__ import annotations

import json
import time
import logging
import asyncio
from typing import Any, AsyncIterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a provider call."""
    success: bool = False
    content: str = ""
    usage: dict[str, int] | None = None
    latency_ms: float = 0.0
    model: str = ""
    provider: str = ""
    error: str = ""
    raw: Any = None


class ProviderExecutor:
    """Executes requests against AI providers.

    Usage:
        executor = ProviderExecutor()
        result = await executor.execute("groq", "llama-3.3-70b-versatile", messages=[...])
    """

    async def execute(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> ExecutionResult:
        """Execute a chat completion request."""
        start = time.time()

        try:
            if provider == "ollama":
                return await self._execute_ollama(model, messages, **kwargs)
            elif provider == "anthropic":
                return await self._execute_anthropic(model, messages, max_tokens, temperature, tools, **kwargs)
            elif provider == "gemini":
                return await self._execute_gemini(model, messages, max_tokens, temperature, **kwargs)
            elif provider == "elevenlabs":
                return await self._execute_elevenlabs(model, kwargs.get("text", ""), **kwargs)
            elif provider == "tavily":
                return await self._execute_tavily(kwargs.get("query", ""), **kwargs)
            else:
                return await self._execute_openai_compatible(provider, model, messages, max_tokens, temperature, tools, **kwargs)
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                latency_ms=(time.time() - start) * 1000,
                provider=provider,
                model=model,
            )

    async def execute_stream(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Execute a streaming chat completion request."""
        try:
            if provider == "openai" or provider == "groq" or provider == "openrouter" or provider == "deepseek" or provider == "fireworks":
                async for chunk in self._stream_openai_compatible(provider, model, messages, max_tokens, temperature, tools, **kwargs):
                    yield chunk
            elif provider == "anthropic":
                async for chunk in self._stream_anthropic(model, messages, max_tokens, temperature, **kwargs):
                    yield chunk
            elif provider == "ollama":
                async for chunk in self._stream_ollama(model, messages, **kwargs):
                    yield chunk
            else:
                result = await self.execute(provider, model, messages, max_tokens, temperature, **kwargs)
                yield result.content
        except Exception as e:
            yield f"[Error: {e}]"

    async def _execute_openai_compatible(
        self, provider: str, model: str, messages: list[dict[str, str]],
        max_tokens: int, temperature: float, tools: list | None, **kwargs
    ) -> ExecutionResult:
        """Execute against OpenAI-compatible API."""
        import httpx

        config = kwargs.get("config")
        base_url = config.base_url if config else "https://api.openai.com/v1"
        api_key = config.api_key if config else ""

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"} if api_key else {}
        payload: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if tools:
            payload["tools"] = tools

        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return ExecutionResult(
            success=True, content=content, usage=usage,
            latency_ms=latency, model=model, provider=provider, raw=data,
        )

    async def _stream_openai_compatible(
        self, provider: str, model: str, messages: list[dict[str, str]],
        max_tokens: int, temperature: float, tools: list | None, **kwargs
    ) -> AsyncIterator[str]:
        """Stream from OpenAI-compatible API."""
        import httpx

        config = kwargs.get("config")
        base_url = config.base_url if config else "https://api.openai.com/v1"
        api_key = config.api_key if config else ""

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"} if api_key else {}
        payload: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature, "stream": True}

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{base_url}/chat/completions", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        line_data = line[6:].strip()
                        if line_data == "[DONE]":
                            return
                        try:
                            chunk = json.loads(line_data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue

    async def _execute_anthropic(
        self, model: str, messages: list[dict[str, str]],
        max_tokens: int, temperature: float, tools: list | None, **kwargs
    ) -> ExecutionResult:
        import httpx

        config = kwargs.get("config")
        api_key = config.api_key if config else ""

        # Convert messages format for Anthropic
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append(msg)

        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        payload: dict[str, Any] = {"model": model, "messages": anthropic_messages, "max_tokens": max_tokens, "temperature": temperature}
        if system_msg:
            payload["system"] = system_msg

        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        usage = {"prompt_tokens": data.get("usage", {}).get("input_tokens", 0), "completion_tokens": data.get("usage", {}).get("output_tokens", 0)}

        return ExecutionResult(success=True, content=content, usage=usage, latency_ms=latency, model=model, provider=provider, raw=data)

    async def _stream_anthropic(self, model: str, messages: list[dict[str, str]], max_tokens: int, temperature: float, **kwargs) -> AsyncIterator[str]:
        import httpx

        config = kwargs.get("config")
        api_key = config.api_key if config else ""

        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append(msg)

        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        payload: dict[str, Any] = {"model": model, "messages": anthropic_messages, "max_tokens": max_tokens, "temperature": temperature, "stream": True}
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", "https://api.anthropic.com/v1/messages", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json.JSONDecodeError:
                            continue

    async def _execute_gemini(self, model: str, messages: list[dict[str, str]], max_tokens: int, temperature: float, **kwargs) -> ExecutionResult:
        import httpx

        config = kwargs.get("config")
        api_key = config.api_key if config else ""

        contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages if m["role"] != "system"]

        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                json={"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}},
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000
        content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        usage_raw = data.get("usageMetadata", {})
        usage = {"prompt_tokens": usage_raw.get("promptTokenCount", 0), "completion_tokens": usage_raw.get("candidatesTokenCount", 0)}

        return ExecutionResult(success=True, content=content, usage=usage, latency_ms=latency, model=model, provider=provider, raw=data)

    async def _execute_ollama(self, model: str, messages: list[dict[str, str]], **kwargs) -> ExecutionResult:
        import httpx

        base_url = kwargs.get("config").base_url if kwargs.get("config") else "http://localhost:11434"

        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{base_url}/api/chat", json={"model": model, "messages": messages, "stream": False})
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000
        content = data.get("message", {}).get("content", "")
        usage = {"prompt_tokens": data.get("prompt_eval_count", 0), "completion_tokens": data.get("eval_count", 0)}

        return ExecutionResult(success=True, content=content, usage=usage, latency_ms=latency, model=model, provider="ollama", raw=data)

    async def _stream_ollama(self, model: str, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        import httpx

        base_url = kwargs.get("config").base_url if kwargs.get("config") else "http://localhost:11434"

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{base_url}/api/chat", json={"model": model, "messages": messages, "stream": True}) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                yield chunk["message"]["content"]
                        except json.JSONDecodeError:
                            continue

    async def _execute_elevenlabs(self, voice_id: str, text: str, **kwargs) -> ExecutionResult:
        import httpx

        config = kwargs.get("config")
        api_key = config.api_key if config else ""

        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key},
                json={"text": text, "model_id": "eleven_multilingual_v2"},
            )
            resp.raise_for_status()
            audio = resp.content

        latency = (time.time() - start) * 1000
        return ExecutionResult(success=True, content="[audio]", latency_ms=latency, model=voice_id, provider="elevenlabs", raw=audio)

    async def _execute_tavily(self, query: str, **kwargs) -> ExecutionResult:
        import httpx

        config = kwargs.get("config")
        api_key = config.api_key if config else ""

        start = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.tavily.com/search", json={"api_key": api_key, "query": query, "max_results": 5})
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start) * 1000
        results = data.get("results", [])
        content = "\n\n".join(f"**{r.get('title', '')}**\n{r.get('content', '')}" for r in results[:5])

        return ExecutionResult(success=True, content=content, latency_ms=latency, model="tavily", provider="tavily", raw=data)


# Global instance
provider_executor = ProviderExecutor()

__all__ = ["ProviderExecutor", "ExecutionResult", "provider_executor"]
