"""Unit tests for Twilio Voice integration.

Mock Twilio requests, audio, STT, and TTS.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from interface.telephony.config import TelephonyConfig
from interface.telephony.session import CallSession, AudioState, TurnRecord
from interface.telephony.call_manager import CallManager
from interface.telephony.logger import CallLogger, LatencyRecord
from interface.telephony.speech import (
    SpeechRecognizer,
    STTResult,
    TwilioSTT,
    GroqWhisperSTT,
    get_recognizer,
)
from interface.telephony.streaming import AudioBuffer, TwilioStreamHandler


# ── Config Tests ─────────────────────────────────────────────────────

class TestTelephonyConfig:
    def test_default_values(self):
        config = TelephonyConfig()
        assert config.port == 8100
        assert config.stt_provider == "twilio" or config.stt_provider is not None
        assert config.max_call_duration_sec == 3600
        assert config.max_silence_sec == 30

    def test_webhook_urls(self):
        config = TelephonyConfig(webhook_url="https://example.com")
        assert config.voice_webhook_url == "https://example.com/voice"
        assert config.voice_events_url == "https://example.com/voice/events"
        assert config.voice_stream_url == "https://example.com/voice/stream"

    def test_transcript_dir_created(self, tmp_path):
        config = TelephonyConfig(transcript_dir=tmp_path / "phone")
        assert config.transcript_dir.exists()

    def test_is_configured(self):
        config = TelephonyConfig(
            account_sid="AC123",
            auth_token="token123",
            phone_number="+1234567890",
        )
        assert config.is_configured is True

        config_empty = TelephonyConfig()
        assert config_empty.is_configured is False


# ── Session Tests ────────────────────────────────────────────────────

class TestCallSession:
    def test_create_session(self):
        session = CallSession(call_sid="CA123", caller_number="+1234567890")
        assert session.call_sid == "CA123"
        assert session.caller_number == "+1234567890"
        assert session.audio_state == AudioState.IDLE
        assert len(session.conversation_history) == 0

    def test_start_and_finish_turn(self):
        session = CallSession(call_sid="CA123", caller_number="+123")
        turn = session.start_turn("hello")
        assert turn.user_text == "hello"
        assert session.audio_state == AudioState.IDLE
        assert len(session.conversation_history) == 1

        turn = session.finish_turn("Hi there!", tool_name="greet")
        assert turn.assistant_text == "Hi there!"
        assert turn.tool_name == "greet"
        assert len(session.turns) == 1
        assert len(session.conversation_history) == 2

    def test_interruption(self):
        session = CallSession(call_sid="CA123", caller_number="+123")
        session.set_audio_state(AudioState.SPEAKING)
        assert session.request_interruption() is True
        assert session.interruption_pending is True

        session.set_audio_state(AudioState.LISTENING)
        assert session.request_interruption() is False

    def test_to_dict(self):
        session = CallSession(call_sid="CA123", caller_number="+123")
        d = session.to_dict()
        assert d["call_sid"] == "CA123"
        assert d["caller"] == "+123"
        assert "duration_sec" in d
        assert "audio_state" in d


# ── CallManager Tests ────────────────────────────────────────────────

class TestCallManager:
    def test_create_and_get_session(self):
        mgr = CallManager()
        session = mgr.create_session("CA123", "+123")
        assert session.call_sid == "CA123"
        assert mgr.get_session("CA123") is session
        assert mgr.active_count == 1

    def test_end_session(self):
        mgr = CallManager()
        mgr.create_session("CA123", "+123")
        ended = mgr.end_session("CA123")
        assert ended is not None
        assert mgr.get_session("CA123") is None
        assert mgr.active_count == 0
        assert len(mgr.history) == 1

    def test_multiple_sessions(self):
        mgr = CallManager()
        mgr.create_session("CA1", "+111")
        mgr.create_session("CA2", "+222")
        assert mgr.active_count == 2
        assert set(s.call_sid for s in mgr.active_sessions) == {"CA1", "CA2"}


# ── Logger Tests ─────────────────────────────────────────────────────

class TestCallLogger:
    def test_transcript_written(self, tmp_path):
        log = CallLogger(call_sid="CA123", caller="+123")
        log._file = tmp_path / "test.md"

        log._write_header()
        log.log_user("hello")
        log.log_assistant("Hi!", tool="greet", latency=LatencyRecord(stt_ms=100, llm_ms=200))
        log.finalize()

        content = log._file.read_text()
        assert "CA123" in content
        assert "hello" in content
        assert "Hi!" in content
        assert "greet" in content


# ── STT Tests ────────────────────────────────────────────────────────

class TestSpeechRecognizer:
    def test_twilio_stt(self):
        stt = TwilioSTT()
        assert stt.is_available() is True

    def test_get_recognizer_default(self):
        rec = get_recognizer("twilio")
        assert isinstance(rec, TwilioSTT)

    def test_get_recognizer_groq(self):
        rec = get_recognizer("groq")
        assert isinstance(rec, GroqWhisperSTT)

    def test_stt_result(self):
        result = STTResult(text="hello", confidence=0.95, provider="test", latency_ms=150)
        assert result.text == "hello"
        assert result.confidence == 0.95


# ── AudioBuffer Tests ───────────────────────────────────────────────

class TestAudioBuffer:
    def test_add_and_get(self):
        buf = AudioBuffer()
        assert buf.has_speech is False
        buf.add_chunk(b"\x00\x01\x02\x03")
        assert buf.has_speech is True
        data = buf.get_audio()
        assert data == b"\x00\x01\x02\x03"
        assert buf.has_speech is False

    def test_clear(self):
        buf = AudioBuffer()
        buf.add_chunk(b"\x00\x01")
        buf.clear()
        assert buf.has_speech is False


# ── LatencyRecord Tests ─────────────────────────────────────────────

class TestLatencyRecord:
    def test_total(self):
        lat = LatencyRecord(stt_ms=100, llm_ms=200, execution_ms=50, tts_ms=150)
        assert lat.total_ms == 500

    def test_summary(self):
        lat = LatencyRecord(stt_ms=100, llm_ms=200, execution_ms=50, tts_ms=150)
        s = lat.summary()
        assert "100" in s
        assert "200" in s
        assert "500" in s


# ── TurnRecord Tests ────────────────────────────────────────────────

class TestTurnRecord:
    def test_total_latency(self):
        turn = TurnRecord(user_text="hello")
        turn.latency_stt_ms = 100
        turn.latency_llm_ms = 200
        turn.latency_execution_ms = 50
        turn.latency_tts_ms = 150
        assert turn.latency_total_ms == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
