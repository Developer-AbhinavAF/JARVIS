"""interface/speech.py — Public speech facade (v5.0 Production).

This is the CURRENT PRODUCTION speech interface for JARVIS.

This module re-exports the production speech engine from `speech/` so
JarvisCore, CLI, desktop backend, REST and WebSocket keep their existing
public interface.

Production Speech Engine Features:
- Event-driven architecture
- Always-on microphone (no fixed timers)
- Silero VAD with smart endpoint detection
- faster-whisper STT with fallback chain
- Natural turn-based conversation (no barge-in)
- Streaming LLM integration
- Edge-TTS with cache
- Comprehensive test suite

Public API:
    speech_engine.is_available() -> dict(tts, stt, mic, ...)
    speech_engine.listen(timeout=5.0) -> str
    speech_engine.speak(text, blocking=True) -> bool
    speech_engine.speak_async(text)
    speech_engine.stop_speaking()
    speech_engine.run_conversation(handler)   # full-duplex voice loop
    speech_engine.speak_stream(tokens, blocking=False) -> None
    speech_engine.speak_from_core_stream(core_stream, blocking=True) -> None

Legacy files (DEPRECATED):
- core/speech_engine.py (old implementation, use speech/ instead)
- interface/speech_new.py (old implementation, use this file instead)

Documentation:
- docs/speech_report.md - Full architecture report
- docs/events.md - Event system documentation
- docs/benchmark.md - Performance benchmarks
- docs/tests.md - Test suite documentation
"""

from __future__ import annotations

from speech.speech_engine import SpeechEngine, speech_engine
from speech.config import SpeechConfig, cfg
from speech.logger import ConversationView, conversation_view

__all__ = [
    "SpeechEngine",
    "speech_engine",
    "SpeechConfig",
    "cfg",
    "ConversationView",
    "conversation_view",
]
