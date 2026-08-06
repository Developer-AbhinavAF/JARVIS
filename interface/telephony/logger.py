"""Structured logging for Twilio Voice calls.

Every event is logged with timestamps, call metadata, and latency breakdown.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jarvis.telephony")


@dataclass
class LatencyRecord:
    stt_ms: float = 0.0
    llm_ms: float = 0.0
    execution_ms: float = 0.0
    tts_ms: float = 0.0

    @property
    def total_ms(self) -> float:
        return self.stt_ms + self.llm_ms + self.execution_ms + self.tts_ms

    def summary(self) -> str:
        return (
            f"Speech: {self.stt_ms:.0f} ms\n"
            f"Thinking: {self.llm_ms:.0f} ms\n"
            f"Execution: {self.execution_ms:.0f} ms\n"
            f"TTS: {self.tts_ms:.0f} ms\n"
            f"Total: {self.total_ms:.0f} ms"
        )


@dataclass
class TranscriptEntry:
    timestamp: str
    speaker: str  # "user" or "assistant"
    text: str
    tool: str = ""
    result: str = ""
    latency: Optional[LatencyRecord] = None


@dataclass
class CallLogger:
    """Per-call structured logger that writes to both console and transcript file."""

    call_sid: str
    caller: str
    start_time: datetime = field(default_factory=datetime.now)
    entries: list[TranscriptEntry] = field(default_factory=list)
    _file: Optional[Path] = None

    def __post_init__(self) -> None:
        from interface.telephony.config import telephony_config

        date_dir = telephony_config.transcript_dir / self.start_time.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        self._file = date_dir / f"{self.call_sid}.md"
        self._write_header()

    def _write_header(self) -> None:
        header = (
            f"# Call {self.call_sid}\n\n"
            f"- **Caller:** {self.caller}\n"
            f"- **Started:** {self.start_time.isoformat()}\n\n"
            f"---\n\n"
        )
        if self._file:
            self._file.write_text(header, encoding="utf-8")
        logger.info(
            "📞 Incoming Call\n  SID: %s\n  Caller: %s",
            self.call_sid,
            self.caller,
        )

    def log_user(self, text: str, latency: Optional[LatencyRecord] = None) -> None:
        entry = TranscriptEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            speaker="user",
            text=text,
            latency=latency,
        )
        self.entries.append(entry)
        block = f"## USER\n\n{text}\n\n"
        if self._file:
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(block)
        logger.info("🎤 USER\n  %s", text)

    def log_assistant(
        self,
        text: str,
        tool: str = "",
        result: str = "",
        latency: Optional[LatencyRecord] = None,
    ) -> None:
        entry = TranscriptEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            speaker="assistant",
            text=text,
            tool=tool,
            result=result,
            latency=latency,
        )
        self.entries.append(entry)
        parts = [f"## ASSISTANT\n\n{text}\n\n"]
        if tool:
            parts.append(f"## TOOL\n\n**{tool}**\n\n{result}\n\n")
        if latency:
            parts.append(f"## LATENCY\n\n```\n{latency.summary()}\n```\n\n")
        parts.append("---\n\n")
        if self._file:
            with open(self._file, "a", encoding="utf-8") as f:
                f.write("".join(parts))
        logger.info("🤖 JARVIS\n  %s", text)
        if latency:
            logger.info("⚡ LATENCY\n  %s", latency.summary().replace("\n", "\n  "))

    def log_tool(self, tool_name: str, result: str, success: bool) -> None:
        status = "SUCCESS" if success else "FAILED"
        block = f"## TOOL\n\n**{tool_name}** — {status}\n\n{result}\n\n"
        if self._file:
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(block)
        logger.info("🛠 TOOL\n  %s → %s", tool_name, status)

    def log_event(self, event: str, detail: str = "") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        block = f"## EVENT\n\n**{event}** at {ts}\n\n{detail}\n\n" if detail else f"## EVENT\n\n**{event}** at {ts}\n\n"
        if self._file:
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(block)
        logger.info("📋 EVENT: %s %s", event, detail)

    def finalize(self) -> None:
        duration = (datetime.now() - self.start_time).total_seconds()
        footer = (
            f"\n---\n\n"
            f"**Call Duration:** {duration:.0f}s\n"
            f"**Total Turns:** {len(self.entries)}\n"
        )
        if self._file:
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(footer)
        logger.info(
            "📞 Call Ended\n  SID: %s\n  Duration: %.0fs\n  Turns: %d",
            self.call_sid,
            duration,
            len(self.entries),
        )
