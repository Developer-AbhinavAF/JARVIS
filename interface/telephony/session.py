"""CallSession — per-call state container for Twilio Voice.

Every phone call creates a CallSession that holds all conversation state,
memory context, tool history, and audio state for the duration of the call.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AudioState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    EXECUTING = "executing"


@dataclass
class TurnRecord:
    """One user→assistant exchange."""
    user_text: str
    assistant_text: str = ""
    tool_name: str = ""
    tool_result: str = ""
    tool_success: bool = False
    latency_stt_ms: float = 0.0
    latency_llm_ms: float = 0.0
    latency_execution_ms: float = 0.0
    latency_tts_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def latency_total_ms(self) -> float:
        return self.latency_stt_ms + self.latency_llm_ms + self.latency_execution_ms + self.latency_tts_ms


@dataclass
class CallSession:
    """Complete state for a single phone call."""

    call_sid: str
    caller_number: str
    start_time: datetime = field(default_factory=datetime.now)

    # ── Conversation State ──────────────────────────────────────────
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    turns: list[TurnRecord] = field(default_factory=list)
    current_turn: Optional[TurnRecord] = None

    # ── Audio State ─────────────────────────────────────────────────
    audio_state: AudioState = AudioState.IDLE
    is_muted: bool = False
    interruption_pending: bool = False

    # ── Stream State ────────────────────────────────────────────────
    stream_sid: Optional[str] = None
    websocket: Any = None  # websockets.WebSocketServerProtocol
    twilio_buffer: list[bytes] = field(default_factory=list)

    # ── Memory Context ──────────────────────────────────────────────
    memory_context: str = ""
    facts_gathered: dict[str, str] = field(default_factory=dict)

    # ── Tool State ──────────────────────────────────────────────────
    last_tool: str = ""
    last_tool_result: str = ""
    tool_history: list[dict[str, str]] = field(default_factory=list)

    # ── Timing ──────────────────────────────────────────────────────
    last_activity_time: float = field(default_factory=time.time)
    last_user_speech_time: float = 0.0

    @property
    def duration_sec(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def is_active(self) -> bool:
        return self.audio_state != AudioState.IDLE or self.duration_sec < 5

    def start_turn(self, user_text: str) -> TurnRecord:
        """Begin a new conversation turn."""
        self.current_turn = TurnRecord(user_text=user_text)
        self.conversation_history.append({"role": "user", "content": user_text})
        self.last_activity_time = time.time()
        self.last_user_speech_time = time.time()
        return self.current_turn

    def finish_turn(
        self,
        assistant_text: str,
        tool_name: str = "",
        tool_result: str = "",
        tool_success: bool = False,
    ) -> TurnRecord:
        """Complete the current turn."""
        if self.current_turn:
            self.current_turn.assistant_text = assistant_text
            self.current_turn.tool_name = tool_name
            self.current_turn.tool_result = tool_result
            self.current_turn.tool_success = tool_success
            self.turns.append(self.current_turn)
            self.conversation_history.append({"role": "assistant", "content": assistant_text})
            turn = self.current_turn
            self.current_turn = None
            self.last_activity_time = time.time()
            if tool_name:
                self.last_tool = tool_name
                self.last_tool_result = tool_result
                self.tool_history.append({"tool": tool_name, "result": tool_result, "success": str(tool_success)})
            return turn
        return TurnRecord(user_text="", assistant_text=assistant_text)

    def set_audio_state(self, state: AudioState) -> None:
        self.audio_state = state
        self.last_activity_time = time.time()

    def request_interruption(self) -> bool:
        """Request interruption of current TTS. Returns True if interruption is allowed."""
        if self.audio_state == AudioState.SPEAKING:
            self.interruption_pending = True
            return True
        return False

    def clear_interruption(self) -> None:
        self.interruption_pending = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_sid": self.call_sid,
            "caller": self.caller_number,
            "start_time": self.start_time.isoformat(),
            "duration_sec": self.duration_sec,
            "audio_state": self.audio_state.value,
            "turns": len(self.turns),
            "last_tool": self.last_tool,
            "conversation_history": self.conversation_history[-6:],
        }
