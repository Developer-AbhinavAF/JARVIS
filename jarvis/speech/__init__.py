"""JARVIS Speech Engine — Primary interaction layer.

Orchestrates all speech subsystems into a unified pipeline:
  Listen → Think → Speak → Listen (continuous loop)

Pipeline:
  Microphone → STT → NLP → Response Generation → Prosody →
  TTS (ElevenLabs Streaming) → Audio Playback → Listening

Features:
  - Streaming TTS (speech starts before response is complete)
  - Interrupt support (user can interrupt at any time)
  - Continuous conversation (auto-return to listening)
  - Natural speech (pauses, emotion, breathing, rhythm)
  - Environment-based configuration (zero hardcoding)

Usage:
    engine = SpeechEngine()
    engine.start()                    # Start continuous conversation
    engine.speak("Hello!")            # One-shot speech
    result = engine.listen_once()     # One-shot listening
    engine.stop()                     # Stop everything
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any, Callable

from .config import SpeechConfig, speech_config
from .elevenlabs_provider import ElevenLabsProvider, TTSResult, elevenlabs_provider
from .audio_player import AudioPlayer, PlaybackState, audio_player
from .stream_manager import StreamManager, StreamSegment, stream_manager
from .speech_to_text import SpeechToText, TranscriptResult, speech_to_text
from .interrupt_handler import InterruptHandler, InterruptEvent, interrupt_handler
from .prosody import ProsodyEngine, prosody_engine
from .conversation_loop import ConversationLoop, ConversationState, conversation_loop

logger = logging.getLogger(__name__)


class SpeechEngine:
    """The unified speech engine — JARVIS's primary communication layer.

    Orchestrates:
    1. Listening (STT with VAD)
    2. Thinking (NLP processing)
    3. Speaking (Streaming TTS → Audio Playback)
    4. Interrupt handling
    5. Continuous conversation loop
    """

    def __init__(self, config: SpeechConfig | None = None) -> None:
        self._config = config or speech_config

        # Subsystems
        self.tts: ElevenLabsProvider = elevenlabs_provider
        self.audio: AudioPlayer = audio_player
        self.stream: StreamManager = stream_manager
        self.stt: SpeechToText = speech_to_text
        self.interrupts: InterruptHandler = interrupt_handler
        self.prosody: ProsodyEngine = prosody_engine
        self.loop: ConversationLoop = conversation_loop

        # State
        self._is_active = False
        self._speak_count: int = 0
        self._total_speak_ms: float = 0.0

        # Configure interrupt handler
        self.interrupts.configure(
            on_interrupt=self._handle_interrupt,
            on_stop_audio=self._stop_audio,
        )

        # Configure conversation loop
        self.loop.configure(
            on_listen=self._listen_callback,
            on_think=None,  # Set by external NLP
            on_speak=self._speak_callback,
            on_interrupt=self._handle_interrupt,
        )

    @property
    def is_active(self) -> bool:
        return self._is_active

    # ── Public API ──────────────────────────────────────────────────

    def start(self) -> None:
        """Start the speech engine and continuous conversation loop."""
        if self._is_active:
            return

        self._is_active = True

        # Start interrupt monitoring
        if self._config.interrupt_enabled:
            self.interrupts.start_monitoring()

        # Start conversation loop
        if self._config.auto_listening:
            self.loop.start()

        logger.info("Speech engine started")

    def stop(self) -> None:
        """Stop all speech activity."""
        self._is_active = False
        self.audio.stop()
        self.interrupts.stop_monitoring()
        self.loop.stop()
        self.stt.stop_listening()
        logger.info("Speech engine stopped")

    def speak(
        self,
        text: str,
        voice: str | None = None,
        emotion: str = "neutral",
        blocking: bool = True,
    ) -> TTSResult:
        """Speak text aloud using ElevenLabs TTS."""
        t0 = time.perf_counter()

        if not text.strip():
            return TTSResult()

        # Apply prosody
        if self._config.enable_prosody:
            text = self.prosody.enhance(text, emotion)

        # Synthesize and play
        result = self.tts.synthesize(text, voice, emotion)
        if result.audio_data:
            self.audio.play_bytes(result.audio_data, blocking=blocking)

        ms = (time.perf_counter() - t0) * 1000
        self._speak_count += 1
        self._total_speak_ms += ms
        result.duration_ms = ms

        return result

    def speak_streaming(
        self,
        text: str,
        voice: str | None = None,
        emotion: str = "neutral",
    ) -> None:
        """Stream TTS — speech starts before full text is available."""
        if not text.strip():
            return

        # Apply prosody
        if self._config.enable_prosody:
            text = self.prosody.enhance(text, emotion)

        # Start streaming playback
        self.audio.start_streaming()

        # Stream audio chunks
        try:
            for chunk in self.tts.synthesize_stream(text, voice, emotion):
                if self.interrupts.is_interrupted:
                    break
                self.audio.feed_chunk(chunk)
        finally:
            self.audio.stop_streaming()

    def speak_tokens(
        self,
        token_stream,
        voice: str | None = None,
        emotion: str = "neutral",
    ) -> None:
        """Stream speech from a token generator (e.g., LLM output).

        Speech begins as soon as the first complete sentence is available.
        """
        # Start streaming playback
        self.audio.start_streaming()

        try:
            for segment in self.stream.process_text_stream(token_stream, emotion):
                if self.interrupts.is_interrupted:
                    break

                # Apply prosody
                text = self.prosody.enhance(segment.text, segment.emotion)

                # Stream TTS for this segment
                for chunk in self.tts.synthesize_stream(text, voice, segment.emotion):
                    if self.interrupts.is_interrupted:
                        break
                    self.audio.feed_chunk(chunk)

        finally:
            self.audio.stop_streaming()

    def listen_once(
        self,
        timeout: float = 10.0,
    ) -> TranscriptResult:
        """Listen for a single utterance."""
        return self.stt.listen_once(timeout=timeout)

    def say_and_listen(
        self,
        text: str,
        voice: str | None = None,
        emotion: str = "neutral",
        listen_timeout: float = 10.0,
    ) -> tuple[TTSResult, TranscriptResult]:
        """Speak text, then listen for response."""
        tts_result = self.speak(text, voice, emotion, blocking=True)
        stt_result = self.listen_once(timeout=listen_timeout)
        return tts_result, stt_result

    def configure_nlp(self, nlp_process: Callable[[str], Any]) -> None:
        """Configure the NLP processor for the conversation loop."""
        def _think(user_input: str) -> tuple[str, str]:
            result = nlp_process(user_input)
            response = getattr(result, 'response_text', '')
            if hasattr(response, 'text'):
                response = response.text
            emotion = getattr(result, 'emotion', 'neutral')
            return str(response) if response else "", str(emotion)

        self.loop.configure(on_think=_think)

    # ── Internal Callbacks ──────────────────────────────────────────

    def _listen_callback(self) -> str:
        """Called by conversation loop when listening."""
        result = self.stt.listen_once(timeout=5.0)
        return result.text

    def _speak_callback(self, text: str, emotion: str) -> None:
        """Called by conversation loop when speaking."""
        if text:
            self.speak(text, emotion=emotion, blocking=True)

    def _handle_interrupt(self, event: InterruptEvent | None = None) -> None:
        """Handle user interrupt."""
        self.audio.stop()
        self.loop.interrupt()
        logger.info("Interrupt handled")

    def _stop_audio(self) -> None:
        """Stop audio playback immediately."""
        self.audio.stop()

    # ── Capability Queries ──────────────────────────────────────────

    def get_capabilities(self) -> dict[str, Any]:
        """Get available speech capabilities."""
        tts_caps = self.tts.get_capabilities() if self.tts.is_available else {}
        account = self.tts.get_account_info() if self.tts.is_available else None
        return {
            "tts_available": self.tts.is_available,
            "stt_engine": self._config.stt.engine,
            "interrupt_enabled": self._config.interrupt_enabled,
            "auto_listening": self._config.auto_listening,
            "prosody_enabled": self._config.enable_prosody,
            "account_tier": account.tier if account else "unknown",
            "character_limit": account.character_limit if account else 0,
            "character_count": account.character_count if account else 0,
            "tts_capabilities": tts_caps,
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "active": self._is_active,
            "speak_count": self._speak_count,
            "total_speak_ms": round(self._total_speak_ms, 1),
            "tts": self.tts.get_stats(),
            "audio": self.audio.get_stats(),
            "stt": self.stt.get_stats(),
            "stream": self.stream.get_stats(),
            "interrupts": self.interrupts.get_stats(),
            "loop": self.loop.get_stats(),
            "prosody": self.prosody.get_stats(),
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

speech_engine = SpeechEngine()

__all__ = [
    "SpeechEngine",
    "speech_engine",
    "speech_config",
    "elevenlabs_provider",
    "audio_player",
    "stream_manager",
    "speech_to_text",
    "interrupt_handler",
    "prosody_engine",
    "conversation_loop",
]
