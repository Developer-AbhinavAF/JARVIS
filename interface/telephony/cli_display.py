"""CLI display for live phone calls.

Shows real-time call information in the terminal when running in CLI mode.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from typing import Any


def display_incoming_call(caller: str, call_sid: str) -> None:
    print(f"\n{'=' * 56}")
    print(f"  📞 INCOMING CALL")
    print(f"  Caller: {caller}")
    print(f"  SID: {call_sid}")
    print(f"{'=' * 56}\n")


def display_call_active(session: Any) -> None:
    duration = session.duration_sec
    mins, secs = divmod(int(duration), 60)
    print(f"\n{'═' * 56}")
    print(f"  📞 CALL ACTIVE")
    print(f"  Caller:  {session.caller_number}")
    print(f"  Duration: {mins:02d}:{secs:02d}")
    print(f"  State:   {session.audio_state.value}")
    print(f"{'═' * 56}\n")


def display_user_speech(text: str) -> None:
    print(f"{'─' * 56}")
    print(f"  🎤 USER")
    print(f"  {text}")
    print(f"{'─' * 56}\n")


def display_jarvis_response(text: str) -> None:
    print(f"{'─' * 56}")
    print(f"  🤖 JARVIS")
    print(f"  {text}")
    print(f"{'─' * 56}\n")


def display_tool_execution(tool_name: str, success: bool, result: str) -> None:
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f"  🛠 TOOL: {tool_name} — {status}")
    if result:
        print(f"  {result[:200]}")
    print()


def display_latency(stt_ms: float, llm_ms: float, exec_ms: float, tts_ms: float) -> None:
    total = stt_ms + llm_ms + exec_ms + tts_ms
    print(f"  ⚡ LATENCY")
    print(f"  Speech:    {stt_ms:6.0f} ms")
    print(f"  Thinking:  {llm_ms:6.0f} ms")
    print(f"  Execution: {exec_ms:6.0f} ms")
    print(f"  TTS:       {tts_ms:6.0f} ms")
    print(f"  Total:     {total:6.0f} ms")
    print()


def display_call_ended(session: Any) -> None:
    duration = session.duration_sec
    mins, secs = divmod(int(duration), 60)
    turns = len(session.turns)
    print(f"\n{'═' * 56}")
    print(f"  📞 CALL ENDED")
    print(f"  Caller:   {session.caller_number}")
    print(f"  Duration: {mins:02d}:{secs:02d}")
    print(f"  Turns:    {turns}")
    print(f"{'═' * 56}\n")


def display_waiting() -> None:
    print(f"\n  ⏳ WAITING...\n")
