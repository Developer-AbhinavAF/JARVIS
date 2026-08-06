"""speech/streaming.py — Streaming primitives.

- SentenceSplitter: turns a token stream into complete sentences so TTS can
  start as soon as a sentence is done (while the LLM keeps generating).

- UtteranceGrabber: the microphone NEVER turns off. A dedicated thread reads
  30 ms frames, feeds VAD + endpoint detection, and only emits an utterance
  once Silero confirms speech completion. Between utterances it keeps
  buffering pre-roll audio — no fixed listening timers, no stop/start.
"""

from __future__ import annotations

import re
import threading
import numpy as np
from typing import Callable, Optional

from speech.config import cfg
from speech.vad import vad
from speech.endpoint_detector import EndpointDetector
from speech.events import event_bus, SpeechEventType
from speech.logger import get_logger

logger = get_logger("streaming")

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+")
_SOFT_END = re.compile(r"[.!?…]\s*$")


class SentenceSplitter:
    """Buffers tokens and emits complete sentences via callback."""

    def __init__(self, on_sentence: Callable[[str], None]) -> None:
        self._on_sentence = on_sentence
        self._buffer = ""
        self._lock = threading.Lock()
        self._full_text = ""

    def feed(self, token: str) -> None:
        if not token:
            return
        with self._lock:
            self._buffer += token
            self._full_text += token
            self._emit_complete()

    def _emit_complete(self) -> None:
        text = self._buffer
        matches = list(_SENTENCE_BOUNDARY.finditer(text))
        if not matches:
            return
        last = matches[-1]
        sentence = text[: last.start()]
        if sentence.strip():
            event_bus.publish(SpeechEventType.SENTENCE_COMPLETED, payload={"sentence": sentence.strip()})
            self._on_sentence(sentence.strip())
        self._buffer = text[last.end():]

    def flush(self) -> str:
        with self._lock:
            rest = self._buffer.strip()
            self._buffer = ""
            if rest and _SOFT_END.search(rest) is None:
                rest += "."
            if rest:
                self._on_sentence(rest)
            return rest


class UtteranceGrabber(threading.Thread):
    """Continuous mic capture: VAD -> smart endpoint -> utterance callback."""

    def __init__(self, on_utterance: Callable[[np.ndarray, float], None],
                 on_speech_signal: Optional[Callable[[float], None]] = None,
                 vad_impl=None, endpoint_impl=None, start_audio=True) -> None:
        super().__init__(name="speech-grabber", daemon=True)
        self._on_utterance = on_utterance
        # Barge-in disabled - on_speech_signal ignored
        self._on_speech_signal = None
        self._vad = vad_impl or vad
        self._endpoint = endpoint_impl or EndpointDetector()
        self._start_audio = start_audio
        self._shutdown = threading.Event()
        self._pa = None
        self._stream = None
        self._frame_n = cfg.sample_rate // 1000 * cfg.frame_ms  # 480 @30ms
        self._pre_roll_n = cfg.sample_rate // 1000 * cfg.pre_roll_ms
        self._speech: list[np.ndarray] = []
        self._pre_roll: list[np.ndarray] = []
        self._suppress_until = 0.0

    # --- lifecycle ---------------------------------------------------------
    def _pick_input_device(self, pa, prefer_idx: Optional[int]) -> Optional[int]:
        """Choose a real microphone: skip Stereo Mix/loopback/virtual inputs."""
        if prefer_idx is not None:
            return prefer_idx
        try:
            import re
            candidates = []
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) <= 0:
                    continue
                name = str(info.get("name", ""))
                if re.search(r"stereo mix|loopback|what u hear|virtual|wave out|monitor", name, re.I):
                    continue
                if re.search(r"microphone|mic|array|built.in|usb audio|webcam|headset", name, re.I):
                    candidates.append((i, name))
            if candidates:
                candidates.sort(key=lambda t: (0 if "microphone" in t[1].lower() else 1, t[0]))
                logger.info("Microphone device picked: [%d] %s", candidates[0][0], candidates[0][1])
                return candidates[0][0]
            return None
        except Exception:
            return None

    def start_worker(self) -> None:
        if not self._start_audio:
            self._shutdown.clear()
            super().start()
            return
        try:
            import pyaudio as _pa
            self._pa = _pa.PyAudio()
            device = self._pick_input_device(self._pa, cfg.device_index)
            if device is not None:
                logger.info("Opening microphone on input device %d", device)
            self._stream = self._pa.open(
                format=_pa.paInt16,
                channels=cfg.channels,
                rate=cfg.sample_rate,
                input=True,
                frames_per_buffer=self._frame_n,
                input_device_index=device,
            )
        except Exception as e:
            logger.warning("Microphone unavailable: %s — VAD simulated", e)
            self._pa = None
            self._stream = None
        self._shutdown.clear()
        super().start()

    def stop_worker(self) -> None:
        self._shutdown.set()
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

    def suppress_for(self, ms: float) -> None:
        import time
        self._suppress_until = time.perf_counter() + ms / 1000.0

    @property
    def mic_available(self) -> bool:
        return self._stream is not None

    # --- capture loop ------------------------------------------------------
    def run(self) -> None:
        import time
        event_bus.publish(SpeechEventType.LISTENING_STARTED)
        while not self._shutdown.is_set():
            if self._stream is None:
                if not self._shutdown.wait(0.2):
                    continue
                break
            try:
                raw = self._stream.read(self._frame_n, exception_on_overflow=False)
            except Exception:
                if not self._shutdown.wait(0.05):
                    continue
                break
            if self._shutdown.is_set():
                break
            frame = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            if len(frame) < self._frame_n:
                frame = np.pad(frame, (0, self._frame_n - len(frame)))
            prob = self._vad.process(frame)

            result = self._endpoint.update(prob, now=time.perf_counter())

            if result.started:
                event_bus.publish(SpeechEventType.SPEECH_STARTED)
                self._speech = list(self._pre_roll)
                self._pre_roll = []
            if result.ended:
                self._endpoint.reset()
                event_bus.publish(SpeechEventType.SPEECH_ENDED,
                                  payload={"speech_ms": result.speech_ms})
                utterance = np.concatenate(self._speech + [frame]) if self._speech else frame
                self._speech = []
                event_bus.publish(SpeechEventType.SPEECH_DETECTED,
                                  payload={"frames": len(utterance)})
                try:
                    self._on_utterance(utterance, result.speech_ms)
                except Exception as e:
                    logger.warning("Utterance handler failed: %s", e)
                continue

            if self._endpoint.in_speech:
                self._speech.append(frame)
            else:
                self._pre_roll.append(frame)
                if len(self._pre_roll) * cfg.frame_ms > cfg.pre_roll_ms:
                    self._pre_roll = self._pre_roll[- (self._pre_roll_n // self._frame_n):]

        event_bus.publish(SpeechEventType.LISTENING_STOPPED)
