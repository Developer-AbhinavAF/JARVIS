"""Audio Player — Low-latency playback with interrupt support.

Uses sounddevice for cross-platform audio output.
Supports streaming playback, immediate stop, and volume control.
"""

from __future__ import annotations

import io
import time
import queue
import struct
import logging
import threading
from typing import Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    import numpy as np
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    logger.warning("sounddevice not installed — audio playback unavailable")

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False


class PlaybackState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPING = "stopping"


@dataclass
class AudioChunk:
    """A chunk of audio data for streaming playback."""
    data: bytes = b""
    format: str = "mp3"
    sample_rate: int = 44100
    channels: int = 1


class AudioPlayer:
    """Low-latency audio player with streaming and interrupt support."""

    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 1,
        output_device: str | None = None,
    ) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._output_device = output_device or None
        self._state = PlaybackState.IDLE
        self._volume: float = 1.0
        self._playback_count: int = 0
        self._total_playback_ms: float = 0.0

        # Streaming queue
        self._audio_queue: queue.Queue[bytes | None] = queue.Queue()
        self._playback_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._stream: Any = None

    @property
    def is_playing(self) -> bool:
        return self._state == PlaybackState.PLAYING

    @property
    def state(self) -> PlaybackState:
        return self._state

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, volume))

    # ── Immediate Playback ──────────────────────────────────────────

    def play_bytes(
        self,
        audio_data: bytes,
        format: str = "mp3",
        blocking: bool = True,
    ) -> bool:
        """Play raw audio bytes immediately."""
        if not HAS_SOUNDDEVICE or not audio_data:
            return False

        self._state = PlaybackState.PLAYING
        self._stop_event.clear()

        try:
            # Decode audio bytes to numpy array
            audio_array = self._decode_audio(audio_data, format)
            if audio_array is None:
                self._state = PlaybackState.IDLE
                return False

            # Apply volume
            if self._volume < 1.0:
                audio_array = audio_array * self._volume

            # Play
            t0 = time.perf_counter()
            if blocking:
                sd.play(audio_array, self._sample_rate, device=self._output_device)
                sd.wait()
            else:
                sd.play(audio_array, self._sample_rate, device=self._output_device)

            ms = (time.perf_counter() - t0) * 1000
            self._playback_count += 1
            self._total_playback_ms += ms
            self._state = PlaybackState.IDLE
            return True

        except Exception as e:
            logger.error("Audio playback failed: %s", e)
            self._state = PlaybackState.IDLE
            return False

    def play_file(
        self,
        file_path: str,
        blocking: bool = True,
    ) -> bool:
        """Play an audio file."""
        if not HAS_SOUNDFILE:
            return False

        try:
            data, sr = sf.read(file_path, dtype='float32')
            self._state = PlaybackState.PLAYING
            self._stop_event.clear()

            if self._volume < 1.0:
                data = data * self._volume

            t0 = time.perf_counter()
            sd.play(data, sr, device=self._output_device)
            if blocking:
                sd.wait()

            ms = (time.perf_counter() - t0) * 1000
            self._playback_count += 1
            self._total_playback_ms += ms
            self._state = PlaybackState.IDLE
            return True

        except Exception as e:
            logger.error("File playback failed: %s", e)
            self._state = PlaybackState.IDLE
            return False

    # ── Streaming Playback ──────────────────────────────────────────

    def start_streaming(self) -> None:
        """Start streaming playback session."""
        self._stop_event.clear()
        self._audio_queue = queue.Queue()
        self._state = PlaybackState.PLAYING

        self._playback_thread = threading.Thread(
            target=self._streaming_loop,
            daemon=True,
            name="audio-stream",
        )
        self._playback_thread.start()

    def feed_chunk(self, audio_bytes: bytes) -> None:
        """Feed audio bytes into the streaming pipeline."""
        if self._state == PlaybackState.PLAYING:
            self._audio_queue.put(audio_bytes)

    def stop_streaming(self) -> None:
        """Stop streaming and play any remaining buffered audio."""
        self._audio_queue.put(None)  # Signal end
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=2.0)
        self._state = PlaybackState.IDLE

    def _streaming_loop(self) -> None:
        """Background thread: decode and play streaming audio chunks."""
        buffer = bytearray()
        try:
            while not self._stop_event.is_set():
                try:
                    chunk = self._audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if chunk is None:
                    # End signal — flush remaining buffer
                    if buffer:
                        self._play_buffer(bytes(buffer))
                    break

                buffer.extend(chunk)

                # Play when buffer has enough data (roughly 100ms of audio)
                min_size = self._sample_rate * self._channels * 2 // 10  # ~100ms for 16-bit
                if len(buffer) >= min_size:
                    self._play_buffer(bytes(buffer))
                    buffer.clear()

        except Exception as e:
            logger.debug("Streaming loop error: %s", e)
        finally:
            self._state = PlaybackState.IDLE

    def _play_buffer(self, data: bytes) -> None:
        """Decode and play a buffer of audio."""
        try:
            audio_array = self._decode_audio(data, "mp3")
            if audio_array is not None and len(audio_array) > 0:
                if self._volume < 1.0:
                    audio_array = audio_array * self._volume
                sd.play(audio_array, self._sample_rate, device=self._output_device, blocking=False)
        except Exception as e:
            logger.debug("Buffer play error: %s", e)

    # ── Interrupt ───────────────────────────────────────────────────

    def stop(self) -> None:
        """Immediately stop all audio playback."""
        self._stop_event.set()
        self._state = PlaybackState.STOPPING
        try:
            sd.stop()
        except Exception:
            pass
        # Clear the queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        self._state = PlaybackState.IDLE

    # ── Decoding ────────────────────────────────────────────────────

    def _decode_audio(self, data: bytes, format: str) -> Any:
        """Decode audio bytes to numpy array."""
        if not HAS_SOUNDFILE:
            # Try raw PCM
            try:
                samples = len(data) // 2  # 16-bit
                audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                return audio
            except Exception:
                return None

        try:
            audio, sr = sf.read(io.BytesIO(data), dtype='float32')
            return audio
        except Exception:
            # Try as raw PCM
            try:
                audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                return audio
            except Exception:
                return None

    # ── Stats ───────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "volume": self._volume,
            "playback_count": self._playback_count,
            "total_playback_ms": round(self._total_playback_ms, 1),
            "has_sounddevice": HAS_SOUNDDEVICE,
            "has_soundfile": HAS_SOUNDFILE,
        }


audio_player = AudioPlayer()
