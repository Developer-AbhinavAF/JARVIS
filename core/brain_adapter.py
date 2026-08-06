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

    # Default to qwen2.5:14b on the ngrok tunnel — matches .env defaults.
    DEFAULT_OLLAMA_URL = "https://kiersten-nonpunishable-carry.ngrok-free.dev"
    DEFAULT_MODEL = "qwen2.5:14b"

    # Long timeout for first response — the cloud GPU + qwen2.5:14b can
    # take 60-90s on a cold start while the model is loaded into VRAM.
    # After the first response, subsequent calls are usually <5s.
    OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "180"))
    OLLAMA_CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "15"))

    def __init__(self, provider: str = "ollama", model: str | None = None):
        if model is None:
            model = self.DEFAULT_MODEL
        self.provider = os.getenv("JARVIS_LLM_PROVIDER", provider).lower()
        # Priority: JARVIS_LLM_MODEL > OLLAMA_MODEL > passed-in default
        self.primary_model = (
            os.getenv("JARVIS_LLM_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or model
        )
        self.fallback_model = os.getenv("JARVIS_LLM_FALLBACK", self.DEFAULT_MODEL)
        self._warmed_up = False
        # Track the last Ollama error so we can decide to fall back to cloud
        # APIs when the tunnel is offline (ERR_NGROK_3200 / 403 / 404).
        self._last_ollama_error: str = ""
        self._ollama_offline: bool = False
        # Reuse a single httpx client across all requests — avoids a fresh
        # TCP + TLS + ngrok handshake on every chat call (~2-4s saved).
        self._http_client = None

    @staticmethod
    def _ollama_url() -> str:
        """Resolve the Ollama endpoint.

        Prefer OLLAMA_BASE_URL (the canonical name in .env) and fall back to
        OLLAMA_HOST (legacy) so both names work and we don't silently hit
        a stale default if the env var is unset.
        """
        url = (
            os.getenv("OLLAMA_BASE_URL")
            or os.getenv("OLLAMA_HOST")
            or BrainAdapter.DEFAULT_OLLAMA_URL
        )
        return url.rstrip("/")

    async def warmup(self) -> bool:
        """Send a tiny warmup request so the first real chat isn't slow.

        Cloud GPU qwen2.5:14b warmup of the model into VRAM can take 60–90s,
        so we cap the wait at OLLAMA_TIMEOUT and continue regardless —
        the warmup is best-effort.

        NOTE: We use a dedicated client (not the shared one) so warming up
        in a background thread's event loop doesn't poison the shared client
        for the main thread.
        """
        import httpx
        try:
            logger.info(
                "Warming up LLM provider (%s) on %s with %s...",
                self.provider,
                self._ollama_url(),
                self.primary_model,
            )
            warmup_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.OLLAMA_TIMEOUT, connect=self.OLLAMA_CONNECT_TIMEOUT),
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
            logger.warning(f"Warmup failed (continuing): {e}")
            return False

    def _get_http_client(self):
        """Return a shared httpx client (created lazily, reused across calls).

        CRITICAL: Callers MUST be in the same event loop as the original
        caller that first triggered client creation. The warmup deliberately
        uses its own client so it doesn't poison this shared one for the
        main loop.
        """
        if self._http_client is None or self._http_client.is_closed:
            import httpx
            self._http_client = httpx.AsyncClient(
                # Generous timeout for first response after cold start.
                timeout=httpx.Timeout(self.OLLAMA_TIMEOUT, connect=self.OLLAMA_CONNECT_TIMEOUT),
                headers={"ngrok-skip-browser-warning": "true"},
                limits=httpx.Limits(
                    max_connections=4,
                    max_keepalive_connections=2,
                    keepalive_expiry=60,
                ),
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
        """Stream text tokens from active provider.

        If the configured provider is `ollama` and the tunnel has been
        detected offline (ngrok 403/404 with ERR_NGROK_3200), we transparently
        fall back to Groq (fastest cloud provider in the env) so the user
        still gets an answer instead of a hang.
        """
        target_model = model or self.primary_model

        # Cloud-API fallback path: tunnel is offline → use Groq.
        if self.provider == "ollama" and self._ollama_offline:
            logger.warning(
                "Ollama tunnel offline (last error: %s). Falling back to cloud API.",
                self._last_ollama_error,
            )
            async for token in self._stream_groq(messages, target_model, temperature, max_tokens):
                yield token
            return

        if self.provider == "ollama":
            # If the tunnel is detected offline mid-stream, fall through to
            # Groq so the user still gets an answer instead of just the
            # diagnostic message. Note: Groq uses different model names —
            # swap qwen2.5:14b (Ollama) for llama-3.1-8b-instant (Groq).
            ollama_failed = False
            async for token in self._stream_ollama(messages, target_model, temperature, max_tokens, options):
                if token.startswith("[Ollama tunnel offline") or token.startswith("[Ollama Error"):
                    ollama_failed = True
                    continue
                yield token
                return
            if ollama_failed or self._ollama_offline:
                logger.warning(
                    "Ollama tunnel offline (last error: %s). Falling back to cloud API.",
                    self._last_ollama_error,
                )
                fallback_model = self._groq_model_name(target_model)
                async for token in self._stream_groq(messages, fallback_model, temperature, max_tokens):
                    yield token
        elif self.provider == "groq":
            fallback_model = self._groq_model_name(target_model)
            async for token in self._stream_groq(messages, fallback_model, temperature, max_tokens):
                yield token
        else:
            # Unknown provider — try Ollama first, then Groq on failure.
            ollama_failed = False
            async for token in self._stream_ollama(messages, target_model, temperature, max_tokens, options):
                if token.startswith("[Ollama") or token.startswith("[Ollama tunnel offline"):
                    ollama_failed = True
                    continue
                yield token
                return
            if ollama_failed:
                fallback_model = self._groq_model_name(target_model)
                async for token in self._stream_groq(messages, fallback_model, temperature, max_tokens):
                    yield token

    @staticmethod
    def _groq_model_name(ollama_model: str) -> str:
        """Map an Ollama model name to its Groq equivalent.

        Groq doesn't host qwen2.5:14b — its supported chat models are
        llama-3.x, mixtral, gemma. Pick the closest fast model for the
        fallback so users still get a sensible answer when the tunnel
        is offline.
        """
        if not ollama_model:
            return "llama-3.1-8b-instant"
        # Anything qwen-* → llama-3.1-8b-instant (fast, similar quality).
        if "qwen" in ollama_model.lower():
            return "llama-3.1-8b-instant"
        # Otherwise, let _stream_groq fall through to its own default.
        return ollama_model

    async def _stream_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream from Ollama via ngrok tunnel with a persistent connection.

        Yields tokens as they arrive. If the tunnel is offline (ngrok
        ERR_NGROK_3200 → 403/404) or the model is missing, yields a clear
        diagnostic token so the caller can fall back to a cloud provider
        instead of leaving the user staring at an empty response.
        """
        url = self._ollama_url() + "/api/chat"
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

            logger.debug("Ollama request → %s model=%s", url, model)
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    body_snippet = ""
                    try:
                        body_snippet = (await response.aread()).decode("utf-8", errors="replace")[:1024]
                    except Exception:
                        pass
                    # ngrok injects an Ngrok-Error-Code header on offline
                    # responses — use it as the authoritative signal before
                    # we try to pattern-match the HTML body.
                    ngrok_error_code = response.headers.get("Ngrok-Error-Code", "")
                    self._last_ollama_error = f"HTTP {response.status_code}: {body_snippet}"
                    # ngrok returns 403 / 404 when the tunnel is offline.
                    # Treat any 4xx with Ngrok-Error-Code=ERR_NGROK_3200 or
                    # the offline HTML as "tunnel is down" so we flag the
                    # adapter and fall back to a cloud provider next call.
                    is_tunnel_offline = (
                        ngrok_error_code == "ERR_NGROK_3200"
                        or "ERR_NGROK" in body_snippet
                        or "endpoint" in body_snippet.lower() and "offline" in body_snippet.lower()
                    )
                    if response.status_code in (403, 404, 502, 503) and is_tunnel_offline:
                        self._ollama_offline = True
                        logger.warning(
                            "Ollama tunnel offline at %s (HTTP %s, ngrok_code=%s). "
                            "Subsequent calls will fall back to a cloud provider until "
                            "the tunnel is reachable again.",
                            self._ollama_url(),
                            response.status_code,
                            ngrok_error_code or "n/a",
                        )
                        yield (
                            f"[Ollama tunnel offline ({self._ollama_url()}) — "
                            f"start the ngrok tunnel on your cloud GPU or set "
                            f"OLLAMA_BASE_URL to a reachable endpoint. "
                            f"Falling back to cloud API.]"
                        )
                        return
                    yield f"[Ollama error {response.status_code}: {body_snippet}]"
                    return

                # 200 OK — clear offline flag.
                self._ollama_offline = False
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
            logger.error("Ollama stream error: %s", e)
            self._last_ollama_error = str(e)
            yield f"[Ollama Error: {e}]"

    async def _stream_groq(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream from Groq API.

        `model` is expected to be a Groq-compatible model name; the chat
        layer is responsible for mapping Ollama names via _groq_model_name.
        """
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            yield "Groq API key missing. Please configure GROQ_API_KEY."
            return

        # Groq supports a fixed set of chat models — reject anything that
        # obviously isn't a Groq model (e.g. an Ollama name leaked through).
        model = model or "llama-3.1-8b-instant"
        if ":" in model and "llama" not in model.lower():
            # Looks like an Ollama tag — swap to the default Groq model.
            logger.info("Mapping non-Groq model %r → llama-3.1-8b-instant", model)
            model = "llama-3.1-8b-instant"

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

            client = self._get_http_client()
            async with client.stream(
                "POST",
                url,
                headers=groq_headers,
                json=payload,
                # Groq is fast (<10s typical) but the cloud can be slow on
                # cold paths — 90s is generous.
                timeout=httpx.Timeout(90.0, connect=10.0),
            ) as response:
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
