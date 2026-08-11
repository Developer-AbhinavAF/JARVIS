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
import time
from typing import Any, Dict, List, AsyncGenerator, Optional
from dataclasses import dataclass, field

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


@dataclass
class ToolCall:
    """Parsed native tool call from LLM response."""
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    call_id: Optional[str] = None


@dataclass
class LLMResult:
    """Complete result from an LLM call — text content plus any tool calls."""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    done: bool = False


class BrainAdapter:
    """Provider-agnostic LLM interface."""

    DEFAULT_OLLAMA_URL = "https://kiersten-nonpunishable-carry.ngrok-free.dev"
    DEFAULT_MODEL = "jarvis-agi"

    OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "60"))
    OLLAMA_CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "10"))

    def __init__(self, provider: str = "ollama", model: str | None = None):
        if model is None:
            model = self.DEFAULT_MODEL
        self.provider = os.getenv("JARVIS_LLM_PROVIDER", provider).lower()
        self.primary_model = (
            os.getenv("JARVIS_LLM_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or model
        )
        self.fallback_model = os.getenv("JARVIS_LLM_FALLBACK", self.DEFAULT_MODEL)
        self._warmed_up = False
        self._last_ollama_error: str = ""
        self._ollama_offline: bool = False
        self._http_client = None
        logger.info(
            "[JARVIS] Model: %s | Base URL: %s | Runtime system prompt: disabled",
            self.primary_model,
            self._ollama_url(),
        )

    @staticmethod
    def _ollama_url() -> str:
        url = (
            os.getenv("OLLAMA_BASE_URL")
            or os.getenv("OLLAMA_HOST")
            or BrainAdapter.DEFAULT_OLLAMA_URL
        )
        return url.rstrip("/")

    async def warmup(self) -> bool:
        import httpx
        try:
            logger.info(
                "Warming up LLM provider (%s) on %s with %s...",
                self.provider, self._ollama_url(), self.primary_model,
            )
            warmup_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"ngrok-skip-browser-warning": "true"},
            )
            try:
                payload = {
                    "model": self.primary_model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": True,
                    "options": {"num_ctx": 4096, "num_predict": 8},
                }
                url = self._ollama_url() + "/api/chat"
                async with warmup_client.stream("POST", url, json=payload) as response:
                    async for _ in response.aiter_lines():
                        pass
            finally:
                try:
                    await warmup_client.aclose()
                except Exception:
                    pass
            self._warmed_up = True
            logger.info("LLM Provider warmup completed.")
            return True
        except Exception as e:
            logger.warning("Warmup failed (continuing): %s", e)
            return False

    def _get_http_client(self):
        if self._http_client is None or self._http_client.is_closed:
            import httpx
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.OLLAMA_TIMEOUT, connect=self.OLLAMA_CONNECT_TIMEOUT),
                headers={"ngrok-skip-browser-warning": "true"},
                limits=httpx.Limits(
                    max_connections=4,
                    max_keepalive_connections=2,
                    keepalive_expiry=60,
                ),
            )
        return self._http_client

    def _ingest_tool_call_fragments(
        self,
        entries: Any,
        accumulator: Dict,
    ) -> None:
        """Accumulate streamed tool-call fragments (Ollama + OpenAI-compatible).

        Entries arrive split across chunks keyed by an optional `index`.
        We merge name + id + partial arguments per slot and flush valid
        ToolCall objects at stream end.
        """
        if not entries:
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            function = entry.get("function") or {}
            if not isinstance(function, dict):
                continue
            idx = entry.get("index", 0)
            slot = accumulator.setdefault(
                idx,
                {"name": "", "arguments": "", "call_id": ""},
            )
            if function.get("name"):
                slot["name"] = function["name"]
            if entry.get("id"):
                slot["call_id"] = entry["id"]
            arg_fragment = function.get("arguments")
            if arg_fragment is not None:
                if isinstance(arg_fragment, dict):
                    slot["arguments"] = json.dumps(arg_fragment)
                else:
                    slot["arguments"] += str(arg_fragment)

    def _flush_tool_call_slots(
        self,
        sink: Dict,
        target: List[ToolCall],
    ) -> None:
        """Convert accumulated fragments into ToolCall objects."""
        for idx in sorted(sink.keys()):
            slot = sink[idx]
            name = str(slot.get("name") or "").strip()
            arguments: Dict[str, Any] = {}
            if slot.get("arguments"):
                try:
                    parsed = json.loads(slot["arguments"])
                    if isinstance(parsed, dict):
                        arguments = parsed
                except json.JSONDecodeError:
                    logger.warning(
                        "Discarding malformed tool-call arguments for '%s'",
                        name,
                    )
                    continue
            if not name:
                continue
            target.append(
                ToolCall(
                    name=name,
                    arguments=arguments,
                    call_id=slot.get("call_id") or None,
                )
            )
        sink.clear()

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.25,
        max_tokens: int = 2048,
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_call_sink: Optional[List[ToolCall]] = None,
    ) -> AsyncGenerator[str, None]:
        target_model = model or self.primary_model

        # Tunnel offline → go straight to Groq
        if self.provider == "ollama" and self._ollama_offline:
            logger.warning("Ollama offline, using Groq fallback")
            async for token in self._stream_groq(messages, self._groq_model_name(target_model), temperature, max_tokens, tools=tools, tool_call_sink=tool_call_sink):
                yield token
            return

        if self.provider == "ollama":
            ollama_failed = False
            async for token in self._stream_ollama(messages, target_model, temperature, max_tokens, options, tools=tools, tool_call_sink=tool_call_sink):
                if token.startswith("[Ollama"):
                    ollama_failed = True
                    continue
                yield token
            if ollama_failed or self._ollama_offline:
                logger.warning("Ollama failed, falling back to Groq")
                async for token in self._stream_groq(messages, self._groq_model_name(target_model), temperature, max_tokens, tools=tools, tool_call_sink=tool_call_sink):
                    yield token
        elif self.provider == "groq":
            async for token in self._stream_groq(messages, self._groq_model_name(target_model), temperature, max_tokens, tools=tools, tool_call_sink=tool_call_sink):
                yield token
        else:
            ollama_failed = False
            async for token in self._stream_ollama(messages, target_model, temperature, max_tokens, options, tools=tools, tool_call_sink=tool_call_sink):
                if token.startswith("[Ollama"):
                    ollama_failed = True
                    continue
                yield token
            if ollama_failed:
                async for token in self._stream_groq(messages, self._groq_model_name(target_model), temperature, max_tokens, tools=tools, tool_call_sink=tool_call_sink):
                    yield token

    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.25,
        max_tokens: int = 2048,
    ) -> LLMResult:
        """Send a request to the LLM with native tool schemas.

        Returns an LLMResult containing any text content and/or tool calls.
        This is the primary entry point for the agent loop.
        """
        target_model = model or self.primary_model
        full_text = ""
        tool_calls: List[ToolCall] = []
        native_sink: Dict[int, Dict[str, str]] = {}

        # Use streaming to collect the full response.
        async for token in self.chat_stream(
            messages, model=target_model, temperature=temperature,
            max_tokens=max_tokens, tools=tools,
            tool_call_sink=native_sink,
        ):
            if token.startswith("[") and ("Error" in token or "error" in token or "offline" in token):
                return LLMResult(content="", provider=self.provider, model=target_model, done=False)
            full_text += token

        self._flush_tool_call_slots(native_sink, tool_calls)
        if tool_calls:
            logger.info(
                "Native tool calls captured: %s",
                [f"{tc.name}({tc.arguments})" for tc in tool_calls],
            )

        # Fallback: the provider may have emitted tool calls as plain text
        # JSON instead of structured chunks. Only execute when the parsed
        # call is a KNOWN tool with VALID arguments — otherwise the text
        # remains ordinary model output.
        if not tool_calls and full_text.strip():
            from core.toolcall_parser import tool_call_parser
            text_calls = tool_call_parser.parse_text(full_text)
            if text_calls:
                logger.info(
                    "Text-emitted tool calls parsed: %s",
                    [f"{tc.name}({tc.arguments})" for tc in text_calls],
                )
                tool_calls.extend(text_calls)

        return LLMResult(
            content=full_text,
            tool_calls=tool_calls,
            provider=self.provider,
            model=target_model,
            done=True,
        )

    @staticmethod
    def _groq_model_name(ollama_model: str) -> str:
        if not ollama_model:
            return "llama-3.1-8b-instant"
        if "qwen" in ollama_model.lower():
            return "llama-3.1-8b-instant"
        return ollama_model

    async def _stream_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_call_sink: Optional[Dict[int, Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        url = self._ollama_url() + "/api/chat"
        start = time.time()
        try:
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
            if tools:
                payload["tools"] = tools

            logger.info("OLLAMA → %s model=%s", url, model)
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    body_snippet = ""
                    try:
                        body_snippet = (await response.aread()).decode("utf-8", errors="replace")[:512]
                    except Exception:
                        pass
                    ngrok_error_code = response.headers.get("Ngrok-Error-Code", "")
                    self._last_ollama_error = f"HTTP {response.status_code}: {body_snippet}"
                    is_tunnel_offline = (
                        ngrok_error_code == "ERR_NGROK_3200"
                        or "ERR_NGROK" in body_snippet
                        or ("endpoint" in body_snippet.lower() and "offline" in body_snippet.lower())
                    )
                    if response.status_code in (403, 404, 502, 503) and is_tunnel_offline:
                        self._ollama_offline = True
                        logger.warning("Ollama tunnel OFFLINE (HTTP %s). Falling back to Groq.", response.status_code)
                        yield f"[Ollama tunnel offline — falling back to Groq]"
                        return
                    logger.error("Ollama error %s: %s", response.status_code, body_snippet[:200])
                    yield f"[Ollama error {response.status_code}]"
                    return

                self._ollama_offline = False
                token_count = 0
                first_token_time = None
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        message = data.get("message", {}) or {}
                        if tool_call_sink is not None and message.get("tool_calls"):
                            self._ingest_tool_call_fragments(
                                message.get("tool_calls"),
                                tool_call_sink,
                            )
                        token = message.get("content", "")
                        if token:
                            if first_token_time is None:
                                first_token_time = time.time()
                                logger.info("OLLAMA first token in %.1fs", first_token_time - start)
                            token_count += 1
                            yield token
                    except Exception:
                        continue
                elapsed = time.time() - start
                logger.info("OLLAMA done: %d tokens in %.1fs (%.1f tok/s)", token_count, elapsed, token_count / max(elapsed, 0.01))
        except Exception as e:
            elapsed = time.time() - start
            logger.error("Ollama error after %.1fs: %s", elapsed, e)
            self._last_ollama_error = str(e)
            yield f"[Ollama Error: {e}]"

    async def _stream_groq(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_call_sink: Optional[Dict[int, Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            yield "Groq API key missing."
            return

        model = model or "llama-3.1-8b-instant"
        if ":" in model and "llama" not in model.lower():
            model = "llama-3.1-8b-instant"

        start = time.time()
        try:
            import httpx
            url = "https://api.groq.com/openai/v1/chat/completions"
            groq_headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }
            if tools:
                payload["tools"] = tools

            logger.info("GROQ → %s model=%s", url, model)
            client = self._get_http_client()
            async with client.stream(
                "POST", url, headers=groq_headers, json=payload,
                timeout=httpx.Timeout(60.0, connect=10.0),
            ) as response:
                if response.status_code != 200:
                    body = ""
                    try:
                        body = (await response.aread()).decode()[:512]
                    except Exception:
                        pass
                    logger.error("Groq error %s: %s", response.status_code, body[:200])
                    yield f"[Groq error {response.status_code}]"
                    return

                token_count = 0
                first_token_time = None
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0].get("delta", {}) or {}
                            if tool_call_sink is not None and delta.get("tool_calls"):
                                self._ingest_tool_call_fragments(
                                    delta.get("tool_calls"),
                                    tool_call_sink,
                                )
                            token = delta.get("content", "")
                            if token:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                    logger.info("GROQ first token in %.1fs", first_token_time - start)
                                token_count += 1
                                yield token
                        except Exception:
                            continue
                elapsed = time.time() - start
                logger.info("GROQ done: %d tokens in %.1fs", token_count, elapsed)
        except Exception as e:
            elapsed = time.time() - start
            logger.error("Groq error after %.1fs: %s", elapsed, e)
            yield f"[Groq Error: {e}]"
