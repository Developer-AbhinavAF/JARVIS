"""All AI provider implementations for the JARVIS Router.

Architecture:
    BaseProvider (interfaces.py)
    └── OpenAICompatibleProvider  ← Groq, OpenRouter, DeepSeek, Fireworks, etc.
    └── AnthropicProvider         ← Custom Anthropic API
    └── GeminiProvider            ← Custom Gemini API
    └── CohereProvider            ← Custom Cohere API
    └── NvidiaNimProvider         ← Custom NVIDIA NIM API
    └── ElevenLabsProvider        ← TTS/Speech
    └── TavilyProvider            ← Search

New providers can be added by subclassing OpenAICompatibleProvider
and setting name, base_url, api_key_env, and _known_models.
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Iterator

import httpx

from .interfaces import BaseProvider
from .models import (
    RouterResponse,
    RouterHealth,
    ChatRequest,
    EmbeddingRequest,
    StreamChunk,
    Capability,
    ProviderStatus,
)
from .exceptions import (
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderServerError,
    ProviderNetworkError,
    ProviderEmptyResponseError,
    ProviderModelNotFoundError,
    AllProvidersExhaustedError,
)
from .config import RouterConfig

logger = logging.getLogger(__name__)


# ============================================================================
# OpenAI-Compatible Provider Base
# ============================================================================

class OpenAICompatibleProvider(BaseProvider):
    """Base for all providers using OpenAI-compatible /chat/completions API.

    Subclasses only need to set:
        name, display_name, base_url, api_key_env
        _known_models: dict of model_name → {max_tokens, capabilities, ...}
    """

    # Override in subclasses
    supports_streaming: bool = True
    supports_tool_calling: bool = True
    supports_json_mode: bool = True
    capabilities: set[Capability] = {Capability.CHAT, Capability.STREAMING}

    def chat(self, request: ChatRequest) -> RouterResponse:
        start = time.time()
        payload = self._build_chat_payload(request, stream=False)

        try:
            resp = self.client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_response(data, start)
        except Exception as exc:
            self._raise_provider_error(exc)

    def chat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        payload = self._build_chat_payload(request, stream=True)

        try:
            with self.client.stream("POST", "/chat/completions", json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    text_line = line.decode("utf-8") if isinstance(line, bytes) else line
                    if text_line.startswith("data: "):
                        chunk = text_line[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(chunk)
                            choices = chunk_data.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            yield StreamChunk(
                                content=content,
                                model=chunk_data.get("model", ""),
                                provider=self.name,
                                finish_reason=choices[0].get("finish_reason"),
                                tool_calls=delta.get("tool_calls"),
                            )
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            self._raise_provider_error(exc)

    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        payload: dict[str, Any] = {
            "input": request.input_texts,
        }
        if request.model:
            payload["model"] = request.model
        elif self.config.default_embedding_model:
            payload["model"] = self.config.default_embedding_model

        try:
            resp = self.client.post("/embeddings", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data.get("data", [])]
        except Exception as exc:
            self._raise_provider_error(exc)

    def health_check(self) -> RouterHealth:
        now = time.time()
        if self._last_health and (now - self._health_ts) < self.config.health_ttl:
            return self._last_health

        start = time.time()
        try:
            resp = self.client.get("/models", timeout=self.config.health_check_timeout)
            latency = (time.time() - start) * 1000
            if resp.status_code == 200:
                health = RouterHealth(
                    available=True,
                    message="ok",
                    base_url=self.base_url,
                    model="",
                    latency_ms=latency,
                    status=ProviderStatus.ONLINE,
                )
            else:
                health = RouterHealth(
                    available=False,
                    message=f"HTTP {resp.status_code}",
                    base_url=self.base_url,
                    model="",
                    latency_ms=latency,
                    status=ProviderStatus.DEGRADED,
                )
            self._last_health = health
            self._health_ts = now
            return health
        except Exception as exc:
            health = RouterHealth(
                available=False,
                message=str(exc),
                base_url=self.base_url,
                model="",
                latency_ms=(time.time() - start) * 1000,
                status=ProviderStatus.OFFLINE,
            )
            self._last_health = health
            self._health_ts = now
            return health

    # ---- Internal Helpers ----

    def _build_chat_payload(self, request: ChatRequest, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": request.messages,
            "stream": stream,
        }
        model_name = request.model or self.config.default_model or next(iter(self._known_models), "default")
        payload["model"] = model_name

        if request.max_tokens is not None:
            model_meta = self._known_models.get(model_name, {})
            model_max = model_meta.get("max_tokens")
            if model_max is not None:
                payload["max_tokens"] = min(request.max_tokens, model_max)
            else:
                payload["max_tokens"] = min(request.max_tokens, 4096)
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.response_format:
            payload["response_format"] = request.response_format
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.stop:
            payload["stop"] = request.stop
        return payload

    def _parse_response(self, data: dict[str, Any], start: float) -> RouterResponse:
        latency = (time.time() - start) * 1000
        choice = data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content", "")
        usage = data.get("usage", {})
        return self._build_response(
            content=content,
            model=data.get("model", ""),
            latency_ms=latency,
            tokens_used=usage.get("total_tokens", 0),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            tool_calls=message.get("tool_calls"),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    def _raise_provider_error(self, exc: Exception) -> None:
        error_cls = self._classify_error(exc)
        msg = self._format_error_message(exc)
        if error_cls is ProviderRateLimitError and isinstance(exc, httpx.HTTPStatusError):
            resp_headers = getattr(exc.response, "headers", {})
            retry_after_str = resp_headers.get("retry-after") or resp_headers.get("Retry-After")
            retry_after = float(retry_after_str) if retry_after_str else None
            raise ProviderRateLimitError(f"[{self.name}] {msg}", retry_after=retry_after) from exc
        raise error_cls(f"[{self.name}] {msg}") from exc


# ============================================================================
# INDIVIDUAL PROVIDER IMPLEMENTATIONS
# ============================================================================

# ---------- Groq ----------
class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    display_name = "Groq"
    base_url = "https://api.groq.com/openai/v1"
    api_key_env = "GROQ_API_KEY"
    priority = 10  # High priority — fastest inference
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.TOOL_CALLING,
        Capability.JSON_OUTPUT, Capability.CODE_GENERATION, Capability.FUNCTION_CALLING,
        Capability.STRUCTURED_OUTPUT,
    }
    supports_tool_calling = True
    supports_json_mode = True
    max_context_length = 131072
    tags = ["fast", "open-source", "inference"]
    _known_models = {
        "llama-3.3-70b-versatile": {"max_tokens": 8192, "family": "llama"},
        "llama-3.1-8b-instant": {"max_tokens": 8192, "family": "llama"},
        "mixtral-8x7b-32768": {"max_tokens": 32768, "family": "mistral"},
        "gemma2-9b-it": {"max_tokens": 8192, "family": "gemma"},
        "qwen-2.5-32b": {"max_tokens": 8192, "family": "qwen"},
        "qwen-2.5-coder-32b": {"max_tokens": 8192, "family": "qwen"},
        "deepseek-r1-distill-llama-70b": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
        "deepseek-r1-distill-qwen-32b": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
    }


# ---------- OpenAI ----------
class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    display_name = "OpenAI"
    base_url = "https://api.openai.com/v1"
    api_key_env = "OPENAI_API_KEY"
    priority = 20
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.TOOL_CALLING,
        Capability.VISION, Capability.EMBEDDING, Capability.JSON_OUTPUT,
        Capability.CODE_GENERATION, Capability.REASONING, Capability.STRUCTURED_OUTPUT,
        Capability.FUNCTION_CALLING, Capability.IMAGE_GENERATION,
    }
    supports_streaming = True
    supports_vision = True
    supports_tool_calling = True
    supports_json_mode = True
    supports_embeddings = True
    supports_reasoning = True
    max_context_length = 200000
    tags = ["enterprise", "multimodal", "reasoning"]
    _known_models = {
        "gpt-4o": {"max_tokens": 16384, "family": "gpt", "vision": True, "reasoning": False},
        "gpt-4o-mini": {"max_tokens": 16384, "family": "gpt", "vision": True},
        "gpt-4-turbo": {"max_tokens": 4096, "family": "gpt", "vision": True},
        "gpt-4": {"max_tokens": 4096, "family": "gpt"},
        "gpt-3.5-turbo": {"max_tokens": 4096, "family": "gpt"},
        "o1": {"max_tokens": 16384, "family": "gpt", "reasoning": True},
        "o1-mini": {"max_tokens": 16384, "family": "gpt", "reasoning": True},
        "o3-mini": {"max_tokens": 16384, "family": "gpt", "reasoning": True},
        "text-embedding-3-large": {"max_tokens": 8191, "family": "embedding", "embedding": True},
        "text-embedding-3-small": {"max_tokens": 8191, "family": "embedding", "embedding": True},
        "text-embedding-ada-002": {"max_tokens": 8191, "family": "embedding", "embedding": True},
    }


# ---------- Anthropic ----------
class AnthropicProvider(BaseProvider):
    name = "anthropic"
    display_name = "Anthropic"
    base_url = "https://api.anthropic.com/v1"
    api_key_env = "ANTHROPIC_API_KEY"
    priority = 15
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.TOOL_CALLING,
        Capability.VISION, Capability.CODE_GENERATION, Capability.REASONING,
        Capability.LONG_CONTEXT, Capability.FUNCTION_CALLING, Capability.STRUCTURED_OUTPUT,
    }
    supports_streaming = True
    supports_vision = True
    supports_tool_calling = True
    supports_json_mode = False  # Anthropic uses structured content blocks
    supports_reasoning = True
    max_context_length = 200000
    tags = ["enterprise", "long-context", "safety", "coding"]
    _known_models = {
        "claude-3-5-sonnet-20241022": {"max_tokens": 8192, "family": "claude", "vision": True},
        "claude-3-5-haiku-20241022": {"max_tokens": 8192, "family": "claude", "vision": True},
        "claude-3-opus-20240229": {"max_tokens": 4096, "family": "claude", "vision": True},
        "claude-3-sonnet-20240229": {"max_tokens": 4096, "family": "claude", "vision": True},
        "claude-3-haiku-20240307": {"max_tokens": 4096, "family": "claude", "vision": True},
    }

    @property
    def client(self) -> httpx.Client:
        if self._http_client is None:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key or "",
                "anthropic-version": "2023-06-01",
            }
            self._http_client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.config.timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=self.config.max_keepalive,
                    max_connections=self.config.max_connections,
                ),
            )
        return self._http_client

    def chat(self, request: ChatRequest) -> RouterResponse:
        start = time.time()
        payload = self._build_anthropic_payload(request, stream=False)
        try:
            resp = self.client.post("/messages", json=payload)
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000
            content_blocks = data.get("content", [])
            text = ""
            tool_calls = []
            for block in content_blocks:
                if block.get("type") == "text":
                    text += block.get("text", "")
                elif block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    })
            usage = data.get("usage", {})
            return self._build_response(
                content=text,
                model=data.get("model", ""),
                latency_ms=latency,
                tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                tool_calls=tool_calls or None,
                finish_reason=data.get("stop_reason", "stop"),
            )
        except Exception as exc:
            self._raise_provider_error(exc)

    def chat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        payload = self._build_anthropic_payload(request, stream=True)
        try:
            with self.client.stream("POST", "/messages", json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    text_line = line.decode("utf-8") if isinstance(line, bytes) else line
                    if text_line.startswith("data: "):
                        chunk = text_line[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        try:
                            event = json.loads(chunk)
                            event_type = event.get("type", "")
                            if event_type == "content_block_delta":
                                delta = event.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield StreamChunk(
                                        content=delta.get("text", ""),
                                        model=event.get("model", ""),
                                        provider=self.name,
                                    )
                            elif event_type == "message_stop":
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            self._raise_provider_error(exc)

    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        raise NotImplementedError("Anthropic does not support embeddings")

    def health_check(self) -> RouterHealth:
        now = time.time()
        if self._last_health and (now - self._health_ts) < self.config.health_ttl:
            return self._last_health
        start = time.time()
        try:
            # Anthropic doesn't have a dedicated health endpoint;
            # use a minimal message to check availability
            test_payload = {
                "model": next(iter(self._known_models), "claude-3-haiku-20240307"),
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "ping"}],
            }
            resp = self.client.post("/messages", json=test_payload,
                                   timeout=self.config.health_check_timeout)
            latency = (time.time() - start) * 1000
            available = resp.status_code == 200
            health = RouterHealth(
                available=available,
                message="ok" if available else f"HTTP {resp.status_code}",
                base_url=self.base_url,
                model="",
                latency_ms=latency,
                status=ProviderStatus.ONLINE if available else ProviderStatus.DEGRADED,
            )
            self._last_health = health
            self._health_ts = now
            return health
        except Exception as exc:
            health = RouterHealth(
                available=False,
                message=str(exc),
                base_url=self.base_url,
                model="",
                latency_ms=(time.time() - start) * 1000,
                status=ProviderStatus.OFFLINE,
            )
            self._last_health = health
            self._health_ts = now
            return health

    def _build_anthropic_payload(self, request: ChatRequest, stream: bool) -> dict[str, Any]:
        # Convert OpenAI-style messages to Anthropic format
        system_prompts = []
        messages = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_prompts.append(content if isinstance(content, str) else str(content))
            else:
                if isinstance(content, str):
                    messages.append({"role": role, "content": content})
                elif isinstance(content, list):
                    # Convert OpenAI content blocks to Anthropic format
                    blocks = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                blocks.append({"type": "text", "text": block["text"]})
                            elif block.get("type") == "image_url":
                                blocks.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": block["image_url"]["url"].split(",")[-1],
                                    }
                                })
                    messages.append({"role": role, "content": blocks})
                else:
                    messages.append({"role": role, "content": str(content)})

        model_name = request.model or next(iter(self._known_models))
        model_meta = self._known_models.get(model_name, {})
        model_max = model_meta.get("max_tokens", 4096)
        max_tokens_val = min(request.max_tokens, model_max) if request.max_tokens is not None else min(4096, model_max)
        max_tokens_val = max(max_tokens_val, 1)

        payload: dict[str, Any] = {
            "model": model_name,
            "max_tokens": max_tokens_val,
            "messages": messages,
            "stream": stream,
        }
        if system_prompts:
            payload["system"] = "\n".join(system_prompts)
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            anthropic_tools = []
            for tool in request.tools:
                func = tool.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name", tool.get("name", "")),
                    "description": func.get("description", tool.get("description", "")),
                    "input_schema": func.get("parameters", tool.get("parameters", {})),
                })
            payload["tools"] = anthropic_tools
        return payload

    def _raise_provider_error(self, exc: Exception) -> None:
        error_cls = self._classify_error(exc)
        msg = self._format_error_message(exc)
        if error_cls is ProviderRateLimitError and isinstance(exc, httpx.HTTPStatusError):
            resp_headers = getattr(exc.response, "headers", {})
            retry_after_str = resp_headers.get("retry-after") or resp_headers.get("Retry-After")
            retry_after = float(retry_after_str) if retry_after_str else None
            raise ProviderRateLimitError(f"[{self.name}] {msg}", retry_after=retry_after) from exc
        raise error_cls(f"[{self.name}] {msg}") from exc


# ---------- Gemini ----------
class GeminiProvider(BaseProvider):
    name = "gemini"
    display_name = "Google Gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    api_key_env = "GEMINI_API_KEY"
    priority = 20
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.VISION, Capability.TOOL_CALLING,
        Capability.EMBEDDING, Capability.CODE_GENERATION, Capability.LONG_CONTEXT,
        Capability.FUNCTION_CALLING, Capability.STRUCTURED_OUTPUT,
    }
    supports_streaming = True
    supports_vision = True
    supports_tool_calling = True
    supports_json_mode = True
    supports_embeddings = True
    max_context_length = 2000000  # Gemini 2.0 has 2M context
    tags = ["google", "multimodal", "long-context"]
    _known_models = {
        "gemini-2.0-flash": {"max_tokens": 8192, "family": "gemini", "vision": True},
        "gemini-2.0-flash-lite": {"max_tokens": 8192, "family": "gemini", "vision": True},
        "gemini-2.0-pro": {"max_tokens": 8192, "family": "gemini", "vision": True, "reasoning": True},
        "gemini-1.5-pro": {"max_tokens": 8192, "family": "gemini", "vision": True},
        "gemini-1.5-flash": {"max_tokens": 8192, "family": "gemini", "vision": True},
        "text-embedding-004": {"max_tokens": 2048, "family": "embedding", "embedding": True},
    }

    def _api_url(self, model: str, stream: bool = False) -> str:
        model_id = model or next(iter(self._known_models))
        suffix = "streamGenerateContent" if stream else "generateContent"
        key = self.api_key or ""
        return f"/models/{model_id}:{suffix}?key={key}"

    def chat(self, request: ChatRequest) -> RouterResponse:
        start = time.time()
        payload = self._build_gemini_payload(request)
        model = request.model or next(iter(self._known_models))
        try:
            resp = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": self.api_key or ""},
                json=payload,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000
            candidates = data.get("candidates", [])
            text = ""
            tool_calls = []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        text += part["text"]
                    if "functionCall" in part:
                        fc = part["functionCall"]
                        tool_calls.append({
                            "id": fc.get("name", ""),
                            "type": "function",
                            "function": {
                                "name": fc.get("name", ""),
                                "arguments": json.dumps(fc.get("args", {})),
                            },
                        })
            usage = data.get("usageMetadata", {})
            return self._build_response(
                content=text,
                model=model,
                latency_ms=latency,
                tokens_used=usage.get("totalTokenCount", 0),
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                tool_calls=tool_calls or None,
                finish_reason=candidates[0].get("finishReason", "STOP") if candidates else "STOP",
            )
        except Exception as exc:
            self._raise_provider_error(exc)

    def chat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        payload = self._build_gemini_payload(request)
        model = request.model or next(iter(self._known_models))
        try:
            with httpx.stream(
                "POST",
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent",
                params={"key": self.api_key or "", "alt": "sse"},
                json=payload,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"},
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    text_line = line.decode("utf-8") if isinstance(line, bytes) else line
                    if text_line.startswith("data: "):
                        chunk = text_line[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk)
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        yield StreamChunk(
                                            content=part["text"],
                                            model=model,
                                            provider=self.name,
                                        )
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            self._raise_provider_error(exc)

    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        model = request.model or "text-embedding-004"
        embeddings = []
        for text in request.input_texts:
            try:
                resp = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent",
                    params={"key": self.api_key or ""},
                    json={"model": f"models/{model}", "content": {"parts": [{"text": text}]}},
                    timeout=self.config.timeout,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                values = data.get("embedding", {}).get("values", [])
                embeddings.append(values)
            except Exception as exc:
                self._raise_provider_error(exc)
        return embeddings

    def health_check(self) -> RouterHealth:
        now = time.time()
        if self._last_health and (now - self._health_ts) < self.config.health_ttl:
            return self._last_health
        start = time.time()
        try:
            model = next(iter(self._known_models))
            resp = httpx.get(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}",
                params={"key": self.api_key or ""},
                timeout=self.config.health_check_timeout,
            )
            latency = (time.time() - start) * 1000
            available = resp.status_code == 200
            health = RouterHealth(
                available=available,
                message="ok" if available else f"HTTP {resp.status_code}",
                base_url=self.base_url,
                model=model,
                latency_ms=latency,
                status=ProviderStatus.ONLINE if available else ProviderStatus.DEGRADED,
            )
            self._last_health = health
            self._health_ts = now
            return health
        except Exception as exc:
            health = RouterHealth(
                available=False, message=str(exc), base_url=self.base_url,
                model="", latency_ms=(time.time() - start) * 1000,
                status=ProviderStatus.OFFLINE,
            )
            self._last_health = health
            self._health_ts = now
            return health

    def _build_gemini_payload(self, request: ChatRequest) -> dict[str, Any]:
        contents = []
        system_instruction = None
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            gemini_role = "user" if role in ("user", "system") else "model"
            if role == "system":
                system_instruction = {"parts": [{"text": str(content)}]}
            else:
                parts = [{"text": str(content)}]
                # Handle image content if present (for vision)
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "image_url":
                                parts.append({
                                    "inlineData": {
                                        "mimeType": "image/jpeg",
                                        "data": item["image_url"].get("url", "").split(",")[-1]
                                    }
                                })
                            elif item.get("type") == "text":
                                parts.append({"text": item["text"]})
                        else:
                            parts.append({"text": str(item)})
                contents.append({"role": gemini_role, "parts": parts})

        payload: dict[str, Any] = {"contents": contents}
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        generation_config: dict[str, Any] = {}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if generation_config:
            payload["generationConfig"] = generation_config

        if request.tools:
            gemini_tools = []
            for tool in request.tools:
                func = tool.get("function", {})
                gemini_tools.append({
                    "functionDeclarations": [{
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {}),
                    }]
                })
            payload["tools"] = gemini_tools
        return payload

    def _raise_provider_error(self, exc: Exception) -> None:
        error_cls = self._classify_error(exc)
        msg = self._format_error_message(exc)
        if error_cls is ProviderRateLimitError and isinstance(exc, httpx.HTTPStatusError):
            resp_headers = getattr(exc.response, "headers", {})
            retry_after_str = resp_headers.get("retry-after") or resp_headers.get("Retry-After")
            retry_after = float(retry_after_str) if retry_after_str else None
            raise ProviderRateLimitError(f"[{self.name}] {msg}", retry_after=retry_after) from exc
        raise error_cls(f"[{self.name}] {msg}") from exc


# ---------- All OpenAI-Compatible Providers ----------
# These all share the same API format, just different base URLs and model lists.

class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    display_name = "OpenRouter"
    base_url = "https://openrouter.ai/api/v1"
    api_key_env = "OPENROUTER_API_KEY"
    priority = 25
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.TOOL_CALLING,
        Capability.VISION, Capability.CODE_GENERATION, Capability.FUNCTION_CALLING,
        Capability.JSON_OUTPUT, Capability.STRUCTURED_OUTPUT,
    }
    supports_streaming = True
    supports_vision = True
    supports_tool_calling = True
    supports_json_mode = True
    max_context_length = 200000
    tags = ["aggregator", "multi-model", "unified"]
    _known_models = {
        "openai/gpt-4o": {"max_tokens": 16384, "family": "gpt", "vision": True},
        "openai/gpt-4o-mini": {"max_tokens": 16384, "family": "gpt", "vision": True},
        "anthropic/claude-3.5-sonnet": {"max_tokens": 8192, "family": "claude", "vision": True},
        "google/gemini-2.0-flash": {"max_tokens": 8192, "family": "gemini", "vision": True},
        "meta-llama/llama-3.3-70b-instruct": {"max_tokens": 8192, "family": "llama"},
        "deepseek/deepseek-r1": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
        "qwen/qwen-2.5-72b-instruct": {"max_tokens": 8192, "family": "qwen"},
        "mistralai/mistral-large": {"max_tokens": 8192, "family": "mistral"},
    }


class FireworksProvider(OpenAICompatibleProvider):
    name = "fireworks"
    display_name = "Fireworks AI"
    base_url = "https://api.fireworks.ai/inference/v1"
    api_key_env = "FIREWORKS_API_KEY"
    priority = 30
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.TOOL_CALLING,
        Capability.CODE_GENERATION, Capability.FUNCTION_CALLING,
    }
    supports_streaming = True
    supports_tool_calling = True
    max_context_length = 131072
    tags = ["fast", "open-source", "inference"]
    _known_models = {
        "accounts/fireworks/models/llama-v3p3-70b-instruct": {"max_tokens": 8192, "family": "llama"},
        "accounts/fireworks/models/mixtral-8x22b-instruct": {"max_tokens": 8192, "family": "mistral"},
        "accounts/fireworks/models/qwen2p5-72b-instruct": {"max_tokens": 8192, "family": "qwen"},
        "accounts/fireworks/models/deepseek-r1": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
    }


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
    display_name = "DeepSeek"
    base_url = "https://api.deepseek.com/v1"
    api_key_env = "DEEPSEEK_API_KEY"
    priority = 20
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.CODE_GENERATION,
        Capability.REASONING, Capability.TOOL_CALLING, Capability.FUNCTION_CALLING,
        Capability.JSON_OUTPUT, Capability.STRUCTURED_OUTPUT,
    }
    supports_streaming = True
    supports_tool_calling = True
    supports_json_mode = True
    supports_reasoning = True
    max_context_length = 131072
    tags = ["reasoning", "coding", "math"]
    _known_models = {
        "deepseek-chat": {"max_tokens": 8192, "family": "deepseek"},
        "deepseek-reasoner": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
    }


class MistralProvider(OpenAICompatibleProvider):
    name = "mistral"
    display_name = "Mistral AI"
    base_url = "https://api.mistral.ai/v1"
    api_key_env = "MISTRAL_API_KEY"
    priority = 25
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.TOOL_CALLING,
        Capability.EMBEDDING, Capability.VISION, Capability.CODE_GENERATION,
        Capability.FUNCTION_CALLING, Capability.JSON_OUTPUT, Capability.STRUCTURED_OUTPUT,
    }
    supports_streaming = True
    supports_vision = True
    supports_tool_calling = True
    supports_json_mode = True
    supports_embeddings = True
    max_context_length = 131072
    tags = ["european", "open-source", "multimodal"]
    _known_models = {
        "mistral-large-latest": {"max_tokens": 8192, "family": "mistral"},
        "mistral-medium-latest": {"max_tokens": 8192, "family": "mistral"},
        "mistral-small-latest": {"max_tokens": 8192, "family": "mistral"},
        "pixtral-large-latest": {"max_tokens": 8192, "family": "mistral", "vision": True},
        "codestral-latest": {"max_tokens": 8192, "family": "mistral", "code": True},
        "mistral-embed": {"max_tokens": 8192, "family": "embedding", "embedding": True},
    }


class NvidiaNimProvider(BaseProvider):
    """NVIDIA NIM — uses OpenAI-compatible API but with custom auth and URL structure."""
    name = "nvidia"
    display_name = "NVIDIA NIM"
    base_url = "https://integrate.api.nvidia.com/v1"
    api_key_env = "NVIDIA_API_KEY"
    priority = 30
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.EMBEDDING,
        Capability.CODE_GENERATION, Capability.TOOL_CALLING, Capability.FUNCTION_CALLING,
    }
    supports_streaming = True
    supports_tool_calling = True
    supports_embeddings = True
    max_context_length = 131072
    tags = ["nvidia", "enterprise", "gpu"]
    _known_models = {
        "nvidia/llama-3.1-nemotron-70b-instruct": {"max_tokens": 8192, "family": "llama"},
        "nvidia/nemotron-4-340b-instruct": {"max_tokens": 4096, "family": "nemotron"},
    }

    def chat(self, request: ChatRequest) -> RouterResponse:
        return self._openai_compat_chat(request)

    def chat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        return self._openai_compat_stream(request)

    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        return self._openai_compat_embed(request)

    def health_check(self) -> RouterHealth:
        now = time.time()
        if self._last_health and (now - self._health_ts) < self.config.health_ttl:
            return self._last_health
        start = time.time()
        try:
            resp = httpx.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.config.health_check_timeout,
            )
            latency = (time.time() - start) * 1000
            available = resp.status_code == 200
            health = RouterHealth(
                available=available,
                message="ok" if available else f"HTTP {resp.status_code}",
                base_url=self.base_url,
                latency_ms=latency,
                status=ProviderStatus.ONLINE if available else ProviderStatus.DEGRADED,
            )
            self._last_health = health
            self._health_ts = now
            return health
        except Exception as exc:
            health = RouterHealth(
                available=False, message=str(exc), base_url=self.base_url,
                latency_ms=(time.time() - start) * 1000, status=ProviderStatus.OFFLINE,
            )
            self._last_health = health
            self._health_ts = now
            return health

    def _openai_compat_chat(self, request: ChatRequest) -> RouterResponse:
        start = time.time()
        payload = self._build_payload(request, stream=False)
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=self.config.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000
            choice = data["choices"][0]
            message = choice.get("message", {})
            usage = data.get("usage", {})
            return self._build_response(
                content=message.get("content", ""),
                model=data.get("model", ""),
                latency_ms=latency,
                tokens_used=usage.get("total_tokens", 0),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                tool_calls=message.get("tool_calls"),
                finish_reason=choice.get("finish_reason", "stop"),
            )
        except Exception as exc:
            self._raise_provider_error(exc)

    def _openai_compat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        payload = self._build_payload(request, stream=True)
        try:
            with httpx.stream(
                "POST", f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=self.config.timeout,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    text_line = line.decode("utf-8") if isinstance(line, bytes) else line
                    if text_line.startswith("data: "):
                        chunk = text_line[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                yield StreamChunk(
                                    content=delta.get("content", ""),
                                    model=data.get("model", ""),
                                    provider=self.name,
                                    finish_reason=choices[0].get("finish_reason"),
                                )
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            self._raise_provider_error(exc)

    def _openai_compat_embed(self, request: EmbeddingRequest) -> list[list[float]]:
        payload = {"input": request.input_texts}
        if request.model:
            payload["model"] = request.model
        try:
            resp = httpx.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=self.config.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data.get("data", [])]
        except Exception as exc:
            self._raise_provider_error(exc)

    def _build_payload(self, request: ChatRequest, stream: bool) -> dict[str, Any]:
        model_name = request.model or next(iter(self._known_models))
        payload: dict[str, Any] = {
            "messages": request.messages,
            "stream": stream,
            "model": model_name,
        }
        if request.max_tokens is not None:
            model_meta = self._known_models.get(model_name, {})
            model_max = model_meta.get("max_tokens")
            if model_max is not None:
                payload["max_tokens"] = min(request.max_tokens, model_max)
            else:
                payload["max_tokens"] = min(request.max_tokens, 4096)
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = request.tool_choice or "auto"
        return payload

    def _raise_provider_error(self, exc: Exception) -> None:
        error_cls = self._classify_error(exc)
        msg = self._format_error_message(exc)
        if error_cls is ProviderRateLimitError and isinstance(exc, httpx.HTTPStatusError):
            resp_headers = getattr(exc.response, "headers", {})
            retry_after_str = resp_headers.get("retry-after") or resp_headers.get("Retry-After")
            retry_after = float(retry_after_str) if retry_after_str else None
            raise ProviderRateLimitError(f"[{self.name}] {msg}", retry_after=retry_after) from exc
        raise error_cls(f"[{self.name}] {msg}") from exc


# ---- Remaining OpenAI-Compatible Providers (compact) ----

class SiliconFlowProvider(OpenAICompatibleProvider):
    name = "siliconflow"
    display_name = "SiliconFlow"
    base_url = "https://api.siliconflow.cn/v1"
    api_key_env = "SILICONFLOW_API_KEY"
    priority = 35
    capabilities = {Capability.CHAT, Capability.STREAMING, Capability.CODE_GENERATION, Capability.EMBEDDING}
    supports_streaming = True
    supports_embeddings = True
    max_context_length = 131072
    tags = ["china", "open-source"]
    _known_models = {
        "deepseek-ai/DeepSeek-R1": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
        "Qwen/Qwen2.5-72B-Instruct": {"max_tokens": 8192, "family": "qwen"},
        "Pro/DeepSeek-V3": {"max_tokens": 8192, "family": "deepseek"},
    }


class BytePlusProvider(OpenAICompatibleProvider):
    name = "byteplus"
    display_name = "BytePlus ModelArk"
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    api_key_env = "BYTEPLUS_API_KEY"
    priority = 40
    capabilities = {Capability.CHAT, Capability.STREAMING, Capability.CODE_GENERATION}
    supports_streaming = True
    max_context_length = 131072
    tags = ["china", "bytedance"]
    _known_models = {
        "deepseek-r1-0528": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
        "deepseek-v3-0324": {"max_tokens": 8192, "family": "deepseek"},
        "doubao-1.5-pro-256k": {"max_tokens": 8192, "family": "doubao"},
    }


class HyperbolicProvider(OpenAICompatibleProvider):
    name = "hyperbolic"
    display_name = "Hyperbolic"
    base_url = "https://api.hyperbolic.xyz/v1"
    api_key_env = "HYPERBOLIC_API_KEY"
    priority = 35
    capabilities = {Capability.CHAT, Capability.STREAMING, Capability.CODE_GENERATION}
    supports_streaming = True
    max_context_length = 131072
    tags = ["decentralized", "gpu"]
    _known_models = {
        "deepseek-ai/DeepSeek-R1": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
        "meta-llama/Llama-3.3-70B-Instruct": {"max_tokens": 8192, "family": "llama"},
        "Qwen/Qwen2.5-72B-Instruct": {"max_tokens": 8192, "family": "qwen"},
    }


class CerebrasProvider(OpenAICompatibleProvider):
    name = "cerebras"
    display_name = "Cerebras"
    base_url = "https://api.cerebras.ai/v1"
    api_key_env = "CEREBRAS_API_KEY"
    priority = 30
    capabilities = {Capability.CHAT, Capability.STREAMING, Capability.CODE_GENERATION, Capability.TOOL_CALLING}
    supports_streaming = True
    supports_tool_calling = True
    max_context_length = 8192
    tags = ["hardware", "fast", "wafer-scale"]
    _known_models = {
        "llama3.1-8b": {"max_tokens": 8192, "family": "llama"},
        "llama3.1-70b": {"max_tokens": 8192, "family": "llama"},
    }


class ChutesProvider(OpenAICompatibleProvider):
    name = "chutes"
    display_name = "Chutes AI"
    base_url = "https://api.chutes.ai/v1"
    api_key_env = "CHUTES_API_KEY"
    priority = 40
    capabilities = {Capability.CHAT, Capability.STREAMING, Capability.CODE_GENERATION}
    supports_streaming = True
    max_context_length = 32768
    tags = ["decentralized", "community"]
    _known_models = {
        "deepseek-ai/DeepSeek-R1": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
    }


class CohereProvider(BaseProvider):
    name = "cohere"
    display_name = "Cohere"
    base_url = "https://api.cohere.com/v2"
    api_key_env = "COHERE_API_KEY"
    priority = 30
    weight = 1.0
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.EMBEDDING,
        Capability.RERANKING, Capability.TOOL_CALLING, Capability.FUNCTION_CALLING,
    }
    supports_streaming = True
    supports_tool_calling = True
    supports_embeddings = True
    max_context_length = 131072
    tags = ["enterprise", "reranking", "embeddings"]
    _known_models = {
        "command-r-plus": {"max_tokens": 4096, "family": "command", "tool_calling": True},
        "command-r": {"max_tokens": 4096, "family": "command", "tool_calling": True},
        "command": {"max_tokens": 4096, "family": "command"},
        "embed-english-v3.0": {"max_tokens": 512, "family": "embedding", "embedding": True},
        "embed-multilingual-v3.0": {"max_tokens": 512, "family": "embedding", "embedding": True},
    }

    def chat(self, request: ChatRequest) -> RouterResponse:
        start = time.time()
        model = request.model or "command-r-plus"
        messages = [{"role": m.get("role", "user"), "message": m.get("content", "")} for m in request.messages]
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        try:
            resp = httpx.post(
                f"{self.base_url}/chat",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=self.config.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000
            text = data.get("text", "")
            return self._build_response(
                content=text,
                model=model,
                latency_ms=latency,
                tokens_used=data.get("meta", {}).get("billed_units", {}).get("input_tokens", 0)
                          + data.get("meta", {}).get("billed_units", {}).get("output_tokens", 0),
            )
        except Exception as exc:
            self._raise_provider_error(exc)

    def chat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        model = request.model or "command-r-plus"
        messages = [{"role": m.get("role", "user"), "message": m.get("content", "")} for m in request.messages]
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        try:
            with httpx.stream(
                "POST", f"{self.base_url}/chat",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=self.config.timeout,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    text_line = line.decode("utf-8") if isinstance(line, bytes) else line
                    try:
                        data = json.loads(text_line)
                        event_type = data.get("event_type", "")
                        if event_type == "text-generation":
                            yield StreamChunk(
                                content=data.get("text", ""),
                                model=model,
                                provider=self.name,
                            )
                        elif event_type == "stream-end":
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            self._raise_provider_error(exc)

    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        model = request.model or "embed-english-v3.0"
        embeddings = []
        for text in request.input_texts:
            try:
                resp = httpx.post(
                    f"{self.base_url}/embed",
                    json={"model": model, "texts": [text], "input_type": "search_document"},
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=self.config.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                if "embeddings" in data:
                    embeddings.extend(data["embeddings"])
            except Exception as exc:
                self._raise_provider_error(exc)
        return embeddings

    def health_check(self) -> RouterHealth:
        now = time.time()
        if self._last_health and (now - self._health_ts) < self.config.health_ttl:
            return self._last_health
        start = time.time()
        try:
            resp = httpx.get(
                f"https://api.cohere.com/v1/check-api-key",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.config.health_check_timeout,
            )
            latency = (time.time() - start) * 1000
            available = resp.status_code == 200
            health = RouterHealth(
                available=available,
                message="ok" if available else f"HTTP {resp.status_code}",
                base_url=self.base_url,
                latency_ms=latency,
                status=ProviderStatus.ONLINE if available else ProviderStatus.DEGRADED,
            )
            self._last_health = health
            self._health_ts = now
            return health
        except Exception as exc:
            health = RouterHealth(
                available=False, message=str(exc), base_url=self.base_url,
                latency_ms=(time.time() - start) * 1000, status=ProviderStatus.OFFLINE,
            )
            self._last_health = health
            self._health_ts = now
            return health

    def _raise_provider_error(self, exc: Exception) -> None:
        error_cls = self._classify_error(exc)
        msg = self._format_error_message(exc)
        if error_cls is ProviderRateLimitError and isinstance(exc, httpx.HTTPStatusError):
            resp_headers = getattr(exc.response, "headers", {})
            retry_after_str = resp_headers.get("retry-after") or resp_headers.get("Retry-After")
            retry_after = float(retry_after_str) if retry_after_str else None
            raise ProviderRateLimitError(f"[{self.name}] {msg}", retry_after=retry_after) from exc
        raise error_cls(f"[{self.name}] {msg}") from exc


class VeniceProvider(OpenAICompatibleProvider):
    name = "venice"
    display_name = "Venice AI"
    base_url = "https://api.venice.ai/api/v1"
    api_key_env = "VENICE_API_KEY"
    priority = 40
    capabilities = {Capability.CHAT, Capability.STREAMING, Capability.CODE_GENERATION}
    supports_streaming = True
    max_context_length = 32768
    tags = ["privacy", "uncensored"]
    _known_models = {
        "llama-3.3-70b": {"max_tokens": 8192, "family": "llama"},
        "deepseek-r1-671b": {"max_tokens": 8192, "family": "deepseek", "reasoning": True},
    }


class VercelAIGatewayProvider(OpenAICompatibleProvider):
    name = "vercel_ai_gateway"
    display_name = "Vercel AI Gateway"
    base_url = "https://api.ai-gateway.vercel.sh/v1"
    api_key_env = "VERCEL_AI_GATEWAY_API_KEY"
    priority = 35
    capabilities = {Capability.CHAT, Capability.STREAMING, Capability.TOOL_CALLING}
    supports_streaming = True
    supports_tool_calling = True
    max_context_length = 131072
    tags = ["vercel", "gateway", "edge"]
    _known_models = {
        "openai/gpt-4o": {"max_tokens": 16384, "family": "gpt", "vision": True},
        "anthropic/claude-3.5-sonnet": {"max_tokens": 8192, "family": "claude"},
    }


class XiaomiMimoProvider(OpenAICompatibleProvider):
    name = "xiaomi_mimo"
    display_name = "Xiaomi Mimo"
    base_url = "https://api.xiaomimimo.com/v1"
    api_key_env = "XIAOMI_MIMO_API_KEY"
    priority = 45
    capabilities = {Capability.CHAT, Capability.STREAMING}
    supports_streaming = True
    max_context_length = 8192
    tags = ["xiaomi", "mobile"]
    _known_models = {
        "mimo-chat": {"max_tokens": 8192, "family": "mimo"},
    }


class OllamaLocalProvider(OpenAICompatibleProvider):
    name = "ollama_local"
    display_name = "Ollama (Local)"
    base_url = "http://localhost:11434/v1"
    api_key_env = "OLLAMA_LOCAL_URL"
    priority = 50  # Lower priority — local fallback
    capabilities = {
        Capability.CHAT, Capability.STREAMING, Capability.EMBEDDING,
        Capability.CODE_GENERATION, Capability.TOOL_CALLING,
    }
    supports_streaming = True
    supports_tool_calling = True
    supports_embeddings = True
    max_context_length = 131072
    tags = ["local", "offline", "privacy"]

    def __init__(self, config: RouterConfig | None = None):
        super().__init__(config)
        # Override base_url from config
        if self.config.ollama_local_url:
            self.base_url = self.config.ollama_local_url.rstrip("/") + "/v1"

    @property
    def is_configured(self) -> bool:
        return True  # Local Ollama is always "configured" (no API key)

    @property
    def api_key(self) -> str | None:
        return None  # Local Ollama doesn't need an API key

    @property
    def client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
                timeout=self.config.timeout,
            )
        return self._http_client

    _known_models = {
        "llama3.2": {"max_tokens": 131072, "family": "llama"},
        "llama3.1:8b": {"max_tokens": 131072, "family": "llama"},
        "qwen2.5:7b": {"max_tokens": 32768, "family": "qwen"},
        "deepseek-r1:8b": {"max_tokens": 32768, "family": "deepseek", "reasoning": True},
        "mistral": {"max_tokens": 32768, "family": "mistral"},
        "codestral": {"max_tokens": 32768, "family": "mistral", "code": True},
        "nomic-embed-text": {"max_tokens": 8192, "family": "embedding", "embedding": True},
    }


class OllamaCloudProvider(OpenAICompatibleProvider):
    name = "ollama_cloud"
    display_name = "Ollama Cloud"
    base_url = "https://api.ollama.com/v1"
    api_key_env = "OLLAMA_CLOUD_API_KEY"
    priority = 40
    capabilities = {Capability.CHAT, Capability.STREAMING, Capability.CODE_GENERATION}
    supports_streaming = True
    max_context_length = 32768
    tags = ["cloud", "open-source"]
    _known_models = {
        "llama3.2:70b": {"max_tokens": 32768, "family": "llama"},
        "qwen2.5:32b": {"max_tokens": 32768, "family": "qwen"},
    }


class ElevenLabsProvider(BaseProvider):
    """Text-to-Speech and Speech-to-Text provider."""
    name = "elevenlabs"
    display_name = "ElevenLabs"
    base_url = "https://api.elevenlabs.io/v1"
    api_key_env = "ELEVENLABS_API_KEY"
    priority = 30
    capabilities = {Capability.TEXT_TO_SPEECH, Capability.SPEECH_TO_TEXT, Capability.AUDIO}
    max_context_length = 5000
    tags = ["audio", "tts", "voice"]

    def chat(self, request: ChatRequest) -> RouterResponse:
        raise NotImplementedError("ElevenLabs is not a chat provider. Use tts() or stt().")

    def chat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        raise NotImplementedError("ElevenLabs does not support chat streaming.")

    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        raise NotImplementedError("ElevenLabs does not support embeddings.")

    def health_check(self) -> RouterHealth:
        now = time.time()
        if self._last_health and (now - self._health_ts) < self.config.health_ttl:
            return self._last_health
        start = time.time()
        try:
            resp = httpx.get(
                f"{self.base_url}/user",
                headers={"xi-api-key": self.api_key or ""},
                timeout=self.config.health_check_timeout,
            )
            latency = (time.time() - start) * 1000
            available = resp.status_code == 200
            health = RouterHealth(
                available=available,
                message="ok" if available else f"HTTP {resp.status_code}",
                base_url=self.base_url,
                latency_ms=latency,
                status=ProviderStatus.ONLINE if available else ProviderStatus.DEGRADED,
            )
            self._last_health = health
            self._health_ts = now
            return health
        except Exception as exc:
            health = RouterHealth(
                available=False, message=str(exc), base_url=self.base_url,
                latency_ms=(time.time() - start) * 1000, status=ProviderStatus.OFFLINE,
            )
            self._last_health = health
            self._health_ts = now
            return health


class TavilyProvider(BaseProvider):
    """AI-powered search provider."""
    name = "tavily"
    display_name = "Tavily"
    base_url = "https://api.tavily.com"
    api_key_env = "TAVILY_API_KEY"
    priority = 30
    capabilities = {Capability.SEARCH, Capability.RESEARCH}
    tags = ["search", "research", "web"]

    def chat(self, request: ChatRequest) -> RouterResponse:
        raise NotImplementedError("Tavily is a search provider. Use search().")

    def chat_stream(self, request: ChatRequest) -> Iterator[StreamChunk]:
        raise NotImplementedError("Tavily does not support chat streaming.")

    def embed(self, request: EmbeddingRequest) -> list[list[float]]:
        raise NotImplementedError("Tavily does not support embeddings.")

    def search(self, query: str, max_results: int = 5, search_depth: str = "basic") -> dict[str, Any]:
        """Perform a web search using Tavily."""
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/search",
                json=payload,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            self._raise_provider_error(exc)

    def health_check(self) -> RouterHealth:
        now = time.time()
        if self._last_health and (now - self._health_ts) < self.config.health_ttl:
            return self._last_health
        start = time.time()
        try:
            resp = httpx.post(
                f"{self.base_url}/search",
                json={"api_key": self.api_key, "query": "test", "max_results": 1},
                timeout=self.config.health_check_timeout,
                headers={"Content-Type": "application/json"},
            )
            latency = (time.time() - start) * 1000
            available = resp.status_code in (200, 400)  # 400 means auth ok but bad query
            health = RouterHealth(
                available=available,
                message="ok" if available else f"HTTP {resp.status_code}",
                base_url=self.base_url,
                latency_ms=latency,
                status=ProviderStatus.ONLINE if available else ProviderStatus.DEGRADED,
            )
            self._last_health = health
            self._health_ts = now
            return health
        except Exception as exc:
            health = RouterHealth(
                available=False, message=str(exc), base_url=self.base_url,
                latency_ms=(time.time() - start) * 1000, status=ProviderStatus.OFFLINE,
            )
            self._last_health = health
            self._health_ts = now
            return health

    def _raise_provider_error(self, exc: Exception) -> None:
        error_cls = self._classify_error(exc)
        msg = self._format_error_message(exc)
        if error_cls is ProviderRateLimitError and isinstance(exc, httpx.HTTPStatusError):
            resp_headers = getattr(exc.response, "headers", {})
            retry_after_str = resp_headers.get("retry-after") or resp_headers.get("Retry-After")
            retry_after = float(retry_after_str) if retry_after_str else None
            raise ProviderRateLimitError(f"[{self.name}] {msg}", retry_after=retry_after) from exc
        raise error_cls(f"[{self.name}] {msg}") from exc


# ============================================================================
# Auto-export all provider classes for easy registration
# ============================================================================

_all_providers: list[type[BaseProvider]] = [
    GroqProvider,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    OpenRouterProvider,
    FireworksProvider,
    DeepSeekProvider,
    MistralProvider,
    NvidiaNimProvider,
    SiliconFlowProvider,
    BytePlusProvider,
    HyperbolicProvider,
    CerebrasProvider,
    ChutesProvider,
    CohereProvider,
    VeniceProvider,
    VercelAIGatewayProvider,
    XiaomiMimoProvider,
    OllamaLocalProvider,
    OllamaCloudProvider,
    ElevenLabsProvider,
    TavilyProvider,
]


def get_all_provider_classes() -> list[type[BaseProvider]]:
    """Return all registered provider classes.

    New providers can be added to the _all_providers list above.
    """
    return list(_all_providers)
