"""core/thinking_middleware.py — Centralized Thinking Middleware for JARVIS vNext++.

Intercepts raw token streams from LLMs, extracts `<think>...</think>` reasoning blocks,
and dispatches `ThinkingEvent` objects. User interfaces receive structured events and clean content.
"""

from __future__ import annotations

import re
from typing import AsyncGenerator, Union, Tuple
from core.events import BaseEvent, ThinkingEvent, FinalResponseToken


class ThinkingMiddleware:
    """Parses raw LLM streams and separates reasoning from final response."""

    OPEN_TAG = chr(60) + "think>"          # <think>
    CLOSE_TAG = chr(60) + "/think>"        # </think>

    def __init__(self):
        self._in_think = False
        self._think_buffer = ""

    async def process_stream(
        self, stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[BaseEvent, None]:
        """Convert raw text token stream into BaseEvent stream."""
        buffer = ""
        self._in_think = False
        self._think_buffer = ""

        async for token in stream:
            buffer += token

            while buffer:
                if not self._in_think:
                    think_start = buffer.find(self.OPEN_TAG)
                    if think_start != -1:
                        # Yield text before <think>
                        pre_text = buffer[:think_start]
                        if pre_text:
                            yield FinalResponseToken(token=pre_text)

                        self._in_think = True
                        buffer = buffer[think_start + len(self.OPEN_TAG):]
                    else:
                        # Stray closing tag without an opening <think> — drop it
                        stray_end = buffer.find(self.CLOSE_TAG)
                        if stray_end != -1:
                            buffer = (buffer[:stray_end] + buffer[stray_end + len(self.CLOSE_TAG):]).lstrip()
                            continue
                        # No <think> tag in buffer, check if partial tag at end
                        if "<" in buffer:
                            tag_idx = buffer.rfind("<")
                            if self.OPEN_TAG.startswith(buffer[tag_idx:]):
                                # Hold back potential tag start
                                yield FinalResponseToken(token=buffer[:tag_idx])
                                buffer = buffer[tag_idx:]
                                break

                        yield FinalResponseToken(token=buffer)
                        buffer = ""
                else:
                    think_end = buffer.find(self.CLOSE_TAG)
                    if think_end != -1:
                        # Extract reasoning text (including held chunks)
                        think_text = self._think_buffer + buffer[:think_end]
                        self._think_buffer = ""
                        if think_text:
                            yield ThinkingEvent(text=think_text, phase="Reasoning")

                        self._in_think = False
                        buffer = buffer[think_end + len(self.CLOSE_TAG):]
                    else:
                        # Hold reasoning tokens until the block closes; if it
                        # never closes, they are released as normal text below.
                        self._think_buffer += buffer
                        buffer = ""

        # End of stream: release anything the model left behind.
        if self._in_think:
            # Model never closed the <think> block — treat it as the answer.
            if self._think_buffer:
                yield FinalResponseToken(token=self._think_buffer)
            self._in_think = False
            self._think_buffer = ""
        if buffer:
            yield FinalResponseToken(token=buffer)
