"""Speech-to-Text — Listening and voice recognition.

Uses OpenAI Whisper (local) or falls back to other engines.
Includes Voice Activity Detection for natural conversation.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any
from enum import Enum
from dataclasses import dataclass, field

from .config import speech_config

logger = logging.getLogger(__name__)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import webrtcvad
    HAS_VAD = True
except ImportError:
    HAS_VAD = False

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False


class ListeningState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class TranscriptResult:
    """Result from speech recognition."""
    text: str = ""
    confidence: float = 0.0
    language: str = ""
    duration_ms: float = 0.0
    is_final: bool = True


class VoiceActivityDetector:
    """Detects when the user is speaking using WebRTC VAD."""

    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000) -> None:
        self._sample_rate = sample_rate
        self._frame_duration_ms = 30  # 30ms frames
        self._vad: Any = None
        self._is_speaking = False
        self._silence_frames = 0
        self._max_silence_frames = 30  # 30 frames = 900ms of silence = end of speech

        if HAS_VAD:
            try:
                self._vad = webrtcvad.Vad(aggressiveness)
            except Exception as e:
                logger.debug("VAD init failed: %s", e)

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def process_frame(self, audio_frame: bytes) -> bool:
        """Process an audio frame and return True if speech is detected."""
        if not self._vad:
            return len(audio_frame) > 0

        try:
            is_speech = self._vad.is_speech(audio_frame, self._sample_rate)

            if is_speech:
                self._is_speaking = True
                self._silence_frames = 0
            else:
                self._silence_frames += 1
                if self._silence_frames >= self._max_silence_frames:
                    self._is_speaking = False

            return is_speech
        except Exception:
            return False

    def reset(self) -> None:
        self._is_speaking = False
        self._silence_frames = 0


class SpeechToText:
    """Speech-to-text engine with VAD and streaming support."""

    def __init__(self) -> None:
        self._config = speech_config.stt
        self._whisper_model: Any = None
        self._vad: VoiceActivityDetector | None = None
        self._state = ListeningState.IDLE
        self._listen_count: int = 0
        self._total_listen_ms: float = 0.0

        # Initialize VAD
        if HAS_VAD and self._config.use_vad:
            self._vad = VoiceActivityDetector(
                aggressiveness=self._config.vad_aggressiveness,
            )

        # Lazy-load Whisper
        if self._config.engine == "whisper" and HAS_WHISPER:
            self._load_whisper()

    @property
    def state(self) -> ListeningState:
        return self._state

    @property
    def is_listening(self) -> bool:
        return self._state == ListeningState.LISTENING

    def _load_whisper(self) -> None:
        """Load Whisper model (lazy)."""
        if self._whisper_model is not None:
            return
        try:
            logger.info("Loading Whisper model: %s", self._config.whisper_model)
            self._whisper_model = whisper.load_model(self._config.whisper_model)
            logger.info("Whisper model loaded")
        except Exception as e:
            logger.error("Failed to load Whisper: %s", e)

    def listen_once(
        self,
        timeout: float = 10.0,
        phrase_time_limit: float | None = None,
    ) -> TranscriptResult:
        """Listen for a single utterance and return the transcript."""
        if not HAS_SOUNDDEVICE:
            return TranscriptResult()

        self._state = ListeningState.LISTENING
        t0 = time.perf_counter()
        limit = phrase_time_limit or self._config.phrase_time_limit

        try:
            # Record audio
            audio_data = self._record_audio(timeout=timeout, max_duration=limit)
            if audio_data is None or len(audio_data) == 0:
                self._state = ListeningState.IDLE
                return TranscriptResult()

            # Transcribe
            self._state = ListeningState.PROCESSING
            result = self._transcribe(audio_data)

            ms = (time.perf_counter() - t0) * 1000
            self._listen_count += 1
            self._total_listen_ms += ms

            self._state = ListeningState.IDLE
            return result

        except Exception as e:
            logger.error("Listen failed: %s", e)
            self._state = ListeningState.IDLE
            return TranscriptResult()

    def listen_continuous(self, callback) -> None:
        """Listen continuously, calling callback with each transcript."""
        self._state = ListeningState.LISTENING

        def _listen_loop():
            while self._state == ListeningState.LISTENING:
                result = self.listen_once(timeout=5.0)
                if result.text.strip():
                    callback(result)

        thread = threading.Thread(target=_listen_loop, daemon=True)
        thread.start()

    def stop_listening(self) -> None:
        self._state = ListeningState.IDLE

    def _record_audio(
        self,
        timeout: float = 10.0,
        max_duration: float = 10.0,
    ) -> Any:
        """Record audio from microphone with VAD."""
        if not HAS_SOUNDDEVICE or not HAS_NUMPY:
            return None

        sample_rate = 16000  # Whisper expects 16kHz
        channels = 1
        dtype = "int16"
        frame_duration = 0.03  # 30ms frames
        frame_size = int(sample_rate * frame_duration)

        frames = []
        is_speech_started = False
        silence_after_speech = 0
        max_silence = 30  # 30 frames = 900ms

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype=dtype,
                blocksize=frame_size,
            ) as stream:
                start_time = time.time()

                while True:
                    elapsed = time.time() - start_time
                    if elapsed > timeout or elapsed > max_duration:
                        break

                    data, overflowed = stream.read(frame_size)
                    audio_bytes = data.tobytes()

                    # VAD check
                    if self._vad:
                        is_speech = self._vad.process_frame(audio_bytes)
                        if is_speech:
                            is_speech_started = True
                            silence_after_speech = 0
                        elif is_speech_started:
                            silence_after_speech += 1
                            if silence_after_speech >= max_silence:
                                break  # End of utterance
                    else:
                        is_speech_started = True

                    if is_speech_started:
                        frames.append(data)

                    if elapsed > max_duration:
                        break

        except Exception as e:
            logger.debug("Recording error: %s", e)
            return None

        if not frames:
            return None

        return np.concatenate(frames, axis=0)

    def _transcribe(self, audio_data: Any) -> TranscriptResult:
        """Transcribe audio data to text."""
        if self._config.engine == "whisper" and HAS_WHISPER:
            return self._transcribe_whisper(audio_data)
        return TranscriptResult()

    def _transcribe_whisper(self, audio_data: Any) -> TranscriptResult:
        """Transcribe using Whisper."""
        self._load_whisper()
        if not self._whisper_model:
            return TranscriptResult()

        try:
            t0 = time.perf_counter()
            # Ensure float32
            if audio_data.dtype != np.float32:
                audio_float = audio_data.astype(np.float32) / 32768.0
            else:
                audio_float = audio_data

            result = self._whisper_model.transcribe(
                audio_float,
                language=self._config.language,
                fp16=False,
            )

            ms = (time.perf_counter() - t0) * 1000
            text = result.get("text", "").strip()
            lang = result.get("language", "")

            return TranscriptResult(
                text=text,
                confidence=0.9,
                language=lang,
                duration_ms=ms,
                is_final=True,
            )
        except Exception as e:
            logger.error("Whisper transcription failed: %s", e)
            return TranscriptResult()

    def get_stats(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "engine": self._config.engine,
            "whisper_loaded": self._whisper_model is not None,
            "vad_available": self._vad is not None,
            "listen_count": self._listen_count,
            "total_listen_ms": round(self._total_listen_ms, 1),
        }


speech_to_text = SpeechToText()
