"""Interrupt Handler — Immediate stop when user speaks.

Detects user interruption during speech output and immediately:
1. Stops audio playback
2. Stops text generation
3. Starts listening for new input
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any, Callable
from enum import Enum
from dataclasses import dataclass

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


class InterruptState(Enum):
    NONE = "none"
    DETECTING = "detecting"
    INTERRUPTED = "interrupted"


@dataclass
class InterruptEvent:
    """Information about an interrupt."""
    timestamp: float = 0.0
    audio_level: float = 0.0
    duration_ms: float = 0.0
    detected_during: str = ""  # "speaking", "generating", "idle"


class InterruptHandler:
    """Monitors audio input for interruptions during speech output."""

    def __init__(
        self,
        energy_threshold: float = 0.02,
        min_interrupt_duration_ms: float = 200,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled
        self._energy_threshold = energy_threshold
        self._min_duration_ms = min_interrupt_duration_ms
        self._state = InterruptState.NONE
        self._interrupt_count: int = 0
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Callbacks
        self._on_interrupt: Callable[[InterruptEvent], None] | None = None
        self._on_stop_audio: Callable[[], None] | None = None
        self._on_stop_generation: Callable[[], None] | None = None

    @property
    def is_interrupted(self) -> bool:
        return self._state == InterruptState.INTERRUPTED

    @property
    def enabled(self) -> bool:
        return self._enabled

    def configure(
        self,
        on_interrupt: Callable[[InterruptEvent], None] | None = None,
        on_stop_audio: Callable[[], None] | None = None,
        on_stop_generation: Callable[[], None] | None = None,
    ) -> None:
        """Configure interrupt callbacks."""
        self._on_interrupt = on_interrupt
        self._on_stop_audio = on_stop_audio
        self._on_stop_generation = on_stop_generation

    def start_monitoring(self) -> None:
        """Start monitoring for interrupts."""
        if not self._enabled or not HAS_SOUNDDEVICE:
            return

        self._monitoring = True
        self._state = InterruptState.NONE
        self._stop_event.clear()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="interrupt-monitor",
        )
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """Stop monitoring for interrupts."""
        self._monitoring = False
        self._stop_event.set()
        self._state = InterruptState.NONE

    def check_for_interrupt(self, audio_data: bytes | None = None) -> bool:
        """Check if an interrupt is detected in the given audio data."""
        if not self._enabled or audio_data is None:
            return False

        energy = self._calculate_energy(audio_data)
        if energy > self._energy_threshold:
            self._state = InterruptState.INTERRUPTED
            self._trigger_interrupt(energy)
            return True
        return False

    def _monitor_loop(self) -> None:
        """Background thread: monitor microphone for interrupts."""
        if not HAS_SOUNDDEVICE or not HAS_NUMPY:
            return

        sample_rate = 16000
        channels = 1
        frame_size = 480  # 30ms at 16kHz
        silence_threshold = 0.015

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype="int16",
                blocksize=frame_size,
            ) as stream:
                while not self._stop_event.is_set():
                    try:
                        data, _ = stream.read(frame_size)
                        audio_bytes = data.tobytes()

                        energy = self._calculate_energy(audio_bytes)
                        if energy > self._energy_threshold:
                            # Voice detected — this is an interrupt
                            self._trigger_interrupt(energy)
                            break

                    except Exception:
                        pass

        except Exception as e:
            logger.debug("Interrupt monitor error: %s", e)

    def _calculate_energy(self, audio_data: bytes) -> float:
        """Calculate audio energy level."""
        if not HAS_NUMPY:
            return 0.0
        try:
            samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            if len(samples) == 0:
                return 0.0
            return float(np.sqrt(np.mean(samples ** 2)) / 32768.0)
        except Exception:
            return 0.0

    def _trigger_interrupt(self, energy: float) -> None:
        """Trigger an interrupt event."""
        self._state = InterruptState.INTERRUPTED
        self._interrupt_count += 1

        event = InterruptEvent(
            timestamp=time.time(),
            audio_level=energy,
        )

        logger.info("Interrupt detected (energy=%.4f)", energy)

        # Execute callbacks immediately
        if self._on_stop_audio:
            try:
                self._on_stop_audio()
            except Exception as e:
                logger.debug("Stop audio callback error: %s", e)

        if self._on_stop_generation:
            try:
                self._on_stop_generation()
            except Exception as e:
                logger.debug("Stop generation callback error: %s", e)

        if self._on_interrupt:
            try:
                self._on_interrupt(event)
            except Exception as e:
                logger.debug("Interrupt callback error: %s", e)

    def reset(self) -> None:
        """Reset interrupt state."""
        self._state = InterruptState.NONE

    def get_stats(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "state": self._state.value,
            "interrupt_count": self._interrupt_count,
            "monitoring": self._monitoring,
            "threshold": self._energy_threshold,
        }


interrupt_handler = InterruptHandler()
