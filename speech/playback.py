"""speech/playback.py — Event-driven playback worker.

Worker loop:
    queue.get() -> play -> delete temp file -> next

Interrupt:
    interrupt flag set -> stop stream -> queue.clear() -> delete pending
    temp files -> PlaybackInterrupted event.

No sleep() polling: chunked writes with 50 ms granularity and blocking
reads; cancellation is checked between writes and before each item.
"""

from __future__ import annotations

import os
import time
import threading
import numpy as np
from pathlib import Path
from typing import Optional

from speech.config import cfg
from speech.queue import SpeechQueue, SpeechItem
from speech.interrupt_manager import interrupt_manager
from speech.events import event_bus, SpeechEventType
from speech.logger import get_logger

logger = get_logger("playback")


class PlaybackWorker(threading.Thread):
    def __init__(self, queue: SpeechQueue, interrupt=None, start_audio=True) -> None:
        super().__init__(name="speech-playback", daemon=True)
        self._queue = queue
        self._interrupt = interrupt or interrupt_manager
        self._shutdown = threading.Event()
        self._pa = None
        self._stream = None
        self._start_audio = start_audio
        self._busy = threading.Event()

    @property
    def is_playing(self) -> bool:
        return self._busy.is_set()

    # --- lifecycle ---------------------------------------------------------
    def start_worker(self) -> None:
        if self.is_alive():
            return
        if self._start_audio:
            try:
                import pyaudio
                self._pa = pyaudio.PyAudio()
            except Exception as e:
                logger.warning("PyAudio unavailable: %s — playback disabled", e)
                self._pa = None
        self._shutdown.clear()
        super().start()

    def stop_worker(self) -> None:
        self._shutdown.set()
        self._interrupt.request_interrupt()
        self.join(timeout=2.0)
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

    # --- main loop ---------------------------------------------------------
    def run(self) -> None:
        while not self._shutdown.is_set():
            if self._interrupt.cancelled():
                self._flush_after_interrupt()
                continue
            item = self._queue.get(timeout=0.2)
            if item is None:
                continue
            if self._interrupt.cancelled():
                self._cleanup_item(item)
                self._flush_after_interrupt()
                continue
            try:
                self._play(item)
            finally:
                self._queue.task_done()

    def _flush_after_interrupt(self) -> None:
        latency = self._interrupt.record_handled()
        discarded = self._queue.clear()
        for item in discarded:
            self._cleanup_item(item)
        event_bus.publish(SpeechEventType.PLAYBACK_INTERRUPTED,
                          payload={"latency_ms": latency, "dropped": len(discarded)})
        self._interrupt.playback_stopped()
        self._busy.clear()

    @staticmethod
    def _cleanup_item(item: SpeechItem) -> None:
        if item.temp and item.path is not None:
            try:
                os.remove(item.path)
            except OSError:
                pass

    # --- playback ----------------------------------------------------------
    def _play(self, item: SpeechItem) -> None:
        path = Path(item.path)
        if not path.exists():
            self._cleanup_item(item)
            return
        event_bus.publish(SpeechEventType.PLAYBACK_STARTED, payload={"text": item.text, "path": str(path)})
        self._interrupt.playback_started()
        self._busy.set()
        try:
            self._play_wav(path)
        except Exception as e:
            logger.warning("Playback error: %s", e)
        finally:
            event_bus.publish(SpeechEventType.PLAYBACK_STOPPED, payload={"text": item.text})
            self._interrupt.playback_stopped()
            self._busy.clear()
            self._cleanup_item(item)

    def _play_wav(self, path: Path) -> None:
        import wave
        with wave.open(str(path), "rb") as wf:
            rate = wf.getframerate()
            width = wf.getsampwidth()
            channels = wf.getnchannels()
            data = wf.readframes(wf.getnframes())
        if not data:
            return
        frames = np.frombuffer(data, dtype=np.int16 if width == 2 else np.uint8)
        frames = frames.astype(np.float32) / (32768.0 if width == 2 else 255.0)

        if self._pa is None:
            # No audio backend: simulate duration so blocking speaks work.
            simulated_s = len(frames) / rate if rate else 1.0
            self._simulate(simulated_s)
            return

        stream = self._pa.open(
            format=self._pa.get_format_from_width(width),
            channels=channels, rate=rate, output=True,
            output_device_index=cfg.output_device_index,
        )
        self._stream = stream
        chunk = max(int(rate * cfg.play_chunk_s), 1)
        try:
            raw = frames.tobytes()
            for i in range(0, len(raw), chunk * width * channels):
                if self._shutdown.is_set() or self._interrupt.cancelled():
                    break
                stream.write(raw[i:i + chunk * width * channels])
        finally:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
            self._stream = None

    def _simulate(self, duration_s: float) -> None:
        """Playback with no audio backend — honor interrupts, no busy sleep."""
        end = time.perf_counter() + duration_s
        while time.perf_counter() < end:
            if self._shutdown.is_set() or self._interrupt.cancelled():
                break
            time.sleep(cfg.play_chunk_s)


playback = None  # created by SpeechEngine so queue/interrupt wiring is explicit
