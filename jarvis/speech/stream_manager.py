"""Stream Manager — Token-to-audio streaming pipeline.

Connects text generation → sentence splitting → TTS → audio playback.
Speech begins before the full response is generated.
"""

from __future__ import annotations

import re
import time
import queue
import logging
import threading
from typing import Any, Iterator
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StreamSegment:
    """A segment of text ready for TTS."""
    text: str = ""
    emotion: str = "neutral"
    is_final: bool = False


class SentenceBuffer:
    """Accumulates tokens until a complete sentence is ready for TTS."""

    def __init__(self) -> None:
        self._buffer: str = ""
        self._min_chunk_chars: int = 40

    def add_token(self, token: str) -> list[str]:
        """Add a token and return any complete sentences."""
        self._buffer += token
        sentences = self._split_sentences()
        return sentences

    def flush(self) -> str:
        """Return any remaining text in the buffer."""
        remaining = self._buffer.strip()
        self._buffer = ""
        return remaining

    def _split_sentences(self) -> list[str]:
        """Split buffer on sentence boundaries."""
        sentences = []
        # Match sentence endings: . ! ? followed by space or end
        pattern = r'(?<=[.!?])\s+'
        parts = re.split(pattern, self._buffer)

        if len(parts) > 1:
            # Everything except the last part is a complete sentence
            for part in parts[:-1]:
                cleaned = part.strip()
                if cleaned:
                    sentences.append(cleaned)
            # Keep the last (potentially incomplete) part
            self._buffer = parts[-1]
        elif len(self._buffer) > self._min_chunk_chars * 3:
            # Buffer is very long with no sentence boundary — force split
            mid = len(self._buffer) // 2
            space = self._buffer.rfind(' ', 0, mid)
            if space > 0:
                sentences.append(self._buffer[:space].strip())
                self._buffer = self._buffer[space:].strip()

        return sentences


class StreamManager:
    """Manages the token → sentence → TTS → audio pipeline."""

    def __init__(self) -> None:
        self._buffer = SentenceBuffer()
        self._segment_queue: queue.Queue[StreamSegment] = queue.Queue()
        self._is_streaming: bool = False
        self._stream_count: int = 0
        self._total_tokens: int = 0

    @property
    def is_streaming(self) -> bool:
        return self._is_streaming

    def start_stream(self) -> None:
        """Start a new streaming session."""
        self._buffer = SentenceBuffer()
        self._is_streaming = True
        self._stream_count += 1

    def add_token(self, token: str, emotion: str = "neutral") -> StreamSegment | None:
        """Process a token. Returns a segment if a sentence is complete."""
        if not self._is_streaming:
            return None

        self._total_tokens += 1
        sentences = self._buffer.add_token(token)

        if sentences:
            # Return the first complete sentence
            return StreamSegment(
                text=sentences[0],
                emotion=emotion,
                is_final=False,
            )
        return None

    def end_stream(self) -> StreamSegment | None:
        """End the stream and return any remaining text."""
        self._is_streaming = False
        remaining = self._buffer.flush()
        if remaining:
            return StreamSegment(text=remaining, is_final=True)
        return None

    def process_text_stream(
        self,
        token_stream: Iterator[str],
        emotion: str = "neutral",
    ) -> Iterator[StreamSegment]:
        """Process a token stream and yield TTS-ready segments."""
        self.start_stream()

        for token in token_stream:
            segment = self.add_token(token, emotion)
            if segment:
                yield segment

        final = self.end_stream()
        if final:
            yield final

    def get_stats(self) -> dict[str, Any]:
        return {
            "stream_count": self._stream_count,
            "total_tokens": self._total_tokens,
            "is_streaming": self._is_streaming,
        }


stream_manager = StreamManager()
