"""Streaming — Unified streaming interface for all providers.

Text, audio, image, event streaming with async iterators.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Iterator
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    DONE = "done"
    METADATA = "metadata"


@dataclass
class StreamEvent:
    """A single streaming event."""
    type: StreamEventType = StreamEventType.TEXT
    content: str = ""
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


class StreamBuffer:
    """Accumulates streamed content."""

    def __init__(self):
        self._chunks: list[str] = []
        self._events: list[StreamEvent] = []
        self._complete = False
        self._error = ""

    def add_chunk(self, chunk: str):
        self._chunks.append(chunk)

    def add_event(self, event: StreamEvent):
        self._events.append(event)
        if event.type == StreamEventType.DONE:
            self._complete = True
        elif event.type == StreamEventType.ERROR:
            self._error = event.content
            self._complete = True

    @property
    def content(self) -> str:
        return "".join(self._chunks)

    @property
    def events(self) -> list[StreamEvent]:
        return list(self._events)

    @property
    def is_complete(self) -> bool:
        return self._complete

    @property
    def error(self) -> str:
        return self._error

    def clear(self):
        self._chunks.clear()
        self._events.clear()
        self._complete = False
        self._error = ""


class StreamingAdapter:
    """Adapts provider-specific streams to unified interface.

    Usage:
        adapter = StreamingAdapter()
        async for event in adapter.wrap_stream(provider_stream, "openai"):
            if event.type == StreamEventType.TEXT:
                print(event.content, end="")
    """

    async def wrap_stream(
        self,
        raw_stream: AsyncIterator[Any],
        provider: str,
    ) -> AsyncIterator[StreamEvent]:
        """Wrap a raw provider stream into unified StreamEvents."""
        if provider == "openai" or provider == "groq" or provider == "openrouter":
            async for event in self._wrap_openai_stream(raw_stream):
                yield event
        elif provider == "anthropic":
            async for event in self._wrap_anthropic_stream(raw_stream):
                yield event
        elif provider == "gemini":
            async for event in self._wrap_gemini_stream(raw_stream):
                yield event
        elif provider == "ollama":
            async for event in self._wrap_ollama_stream(raw_stream):
                yield event
        else:
            async for event in self._wrap_generic_stream(raw_stream):
                yield event

    async def _wrap_openai_stream(self, stream: AsyncIterator[Any]) -> AsyncIterator[StreamEvent]:
        try:
            async for chunk in stream:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield StreamEvent(type=StreamEventType.TEXT, content=delta.content)
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        yield StreamEvent(type=StreamEventType.TOOL_CALL, data=[tc.model_dump() for tc in delta.tool_calls])
                if hasattr(chunk, 'usage') and chunk.usage:
                    yield StreamEvent(type=StreamEventType.METADATA, data={"usage": {
                        "prompt_tokens": getattr(chunk.usage, 'prompt_tokens', 0),
                        "completion_tokens": getattr(chunk.usage, 'completion_tokens', 0),
                    }})
            yield StreamEvent(type=StreamEventType.DONE)
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, content=str(e))

    async def _wrap_anthropic_stream(self, stream: AsyncIterator[Any]) -> AsyncIterator[StreamEvent]:
        try:
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, 'text'):
                        yield StreamEvent(type=StreamEventType.TEXT, content=event.delta.text)
                elif event.type == "message_start":
                    yield StreamEvent(type=StreamEventType.METADATA, data={"model": getattr(event.message, 'model', '')})
            yield StreamEvent(type=StreamEventType.DONE)
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, content=str(e))

    async def _wrap_gemini_stream(self, stream: AsyncIterator[Any]) -> AsyncIterator[StreamEvent]:
        try:
            async for chunk in stream:
                if hasattr(chunk, 'text'):
                    yield StreamEvent(type=StreamEventType.TEXT, content=chunk.text)
            yield StreamEvent(type=StreamEventType.DONE)
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, content=str(e))

    async def _wrap_ollama_stream(self, stream: AsyncIterator[Any]) -> AsyncIterator[StreamEvent]:
        try:
            async for chunk in stream:
                if isinstance(chunk, dict):
                    if "message" in chunk and "content" in chunk["message"]:
                        yield StreamEvent(type=StreamEventType.TEXT, content=chunk["message"]["content"])
                    if chunk.get("done"):
                        yield StreamEvent(type=StreamEventType.DONE)
                        return
            yield StreamEvent(type=StreamEventType.DONE)
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, content=str(e))

    async def _wrap_generic_stream(self, stream: AsyncIterator[Any]) -> AsyncIterator[StreamEvent]:
        try:
            async for chunk in stream:
                text = str(chunk) if not isinstance(chunk, str) else chunk
                yield StreamEvent(type=StreamEventType.TEXT, content=text)
            yield StreamEvent(type=StreamEventType.DONE)
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, content=str(e))

    async def collect_stream(
        self,
        raw_stream: AsyncIterator[Any],
        provider: str,
    ) -> tuple[str, list[StreamEvent]]:
        """Collect full stream into content string and events."""
        buffer = StreamBuffer()
        async for event in self.wrap_stream(raw_stream, provider):
            buffer.add_event(event)
            if event.type == StreamEventType.TEXT:
                buffer.add_chunk(event.content)
        return buffer.content, buffer.events


# Global instance
streaming_adapter = StreamingAdapter()

__all__ = ["StreamingAdapter", "StreamEvent", "StreamEventType", "StreamBuffer", "streaming_adapter"]
