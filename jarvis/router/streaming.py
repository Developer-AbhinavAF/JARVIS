from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Iterator

from .models import StreamChunk, ChatRequest
from .interfaces import BaseProvider
from .exceptions import StreamError, StreamInterruptedError

logger = logging.getLogger(__name__)


class StreamingManager:
    """Unified streaming interface across all providers.

    Normalizes streaming responses so the frontend never knows
    which provider is streaming.
    """

    @staticmethod
    def stream_chat(
        provider: BaseProvider,
        request: ChatRequest,
    ) -> Iterator[StreamChunk]:
        try:
            yield from provider.chat_stream(request)
        except Exception as exc:
            raise StreamError(f"Streaming failed on {provider.name}: {exc}") from exc

    @staticmethod
    async def stream_chat_async(
        provider: BaseProvider,
        request: ChatRequest,
    ) -> AsyncIterator[StreamChunk]:
        try:
            for chunk in provider.chat_stream(request):
                yield chunk
        except Exception as exc:
            raise StreamError(f"Async streaming failed on {provider.name}: {exc}") from exc

    @staticmethod
    def collect_stream(stream: Iterator[StreamChunk]) -> str:
        parts: list[str] = []
        for chunk in stream:
            if chunk.content:
                parts.append(chunk.content)
        return "".join(parts)

    @staticmethod
    def stream_to_sse(stream: Iterator[StreamChunk]) -> Iterator[str]:
        for chunk in stream:
            data: dict[str, Any] = {"content": chunk.content}
            if chunk.finish_reason:
                data["finish_reason"] = chunk.finish_reason
            if chunk.tool_calls:
                data["tool_calls"] = chunk.tool_calls
            yield f"data: {json.dumps(data)}\n\n"
        yield "data: [DONE]\n\n"

    @staticmethod
    def normalize_openai_chunk(data: dict[str, Any]) -> StreamChunk:
        choices = data.get("choices", [])
        if not choices:
            return StreamChunk()
        delta = choices[0].get("delta", {})
        return StreamChunk(
            content=delta.get("content", ""),
            tool_calls=delta.get("tool_calls"),
            finish_reason=choices[0].get("finish_reason"),
            model=data.get("model", ""),
        )
