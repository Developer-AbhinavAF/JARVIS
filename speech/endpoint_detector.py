"""speech/endpoint_detector.py — Smart end-of-speech detection.

Stops recording based on the *combination* of VAD confidence, silent
duration, and speech length — never on a single pause. So:

    Hello...  I...  Need...  Your...  Help...

does NOT terminate on the intra-sentence pauses; speech ends only after a
sustained trailing silence (end_hold_ms) once speech was solidly confirmed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from speech.config import cfg
from speech.logger import get_logger

logger = get_logger("endpoint")


class EndpointStatus(Enum):
    LISTENING = auto()      # no speech yet — pre-roll accumulating
    SPEECH = auto()         # speech in progress
    ENDED = auto()          # utterance ready


@dataclass
class EndpointFrame:
    prob: float
    started: bool = False      # transitioned into SPEECH
    ended: bool = False        # transitioned to ENDED
    speech_ms: float = 0.0


class EndpointDetector:
    """Frame-driven state machine. Feed it 30 ms VAD probabilities."""

    def __init__(self, threshold: float | None = None,
                 confirm_frames: int | None = None,
                 end_hold_ms: int | None = None,
                 min_speech_ms: int | None = None,
                 max_utterance_s: float | None = None,
                 pause_tolerance_ms: int | None = None) -> None:
        self.threshold = threshold if threshold is not None else cfg.vad_threshold
        self.confirm_frames = confirm_frames or cfg.vad_confirm_frames
        self.end_hold_ms = end_hold_ms if end_hold_ms is not None else cfg.end_hold_ms
        self.min_speech_ms = min_speech_ms if min_speech_ms is not None else cfg.min_speech_ms
        self.max_utterance_s = max_utterance_s or cfg.max_utterance_s
        self.pause_tolerance_ms = pause_tolerance_ms if pause_tolerance_ms is not None else getattr(cfg, 'pause_tolerance_ms', 500)
        self.frame_s = cfg.frame_ms / 1000.0

        self.status = EndpointStatus.LISTENING
        self._confirm_run = 0          # consecutive speech frames
        self._silent_frames = 0        # consecutive non-speech frames during SPEECH
        self._speech_frames = 0
        self._utterance_start_ts: Optional[float] = None
        self._last_voice_ts: Optional[float] = None
        self._pause_count = 0          # track number of pauses within utterance

    def reset(self) -> None:
        self.status = EndpointStatus.LISTENING
        self._confirm_run = 0
        self._silent_frames = 0
        self._speech_frames = 0
        self._utterance_start_ts = None
        self._last_voice_ts = None
        self._pause_count = 0

    @property
    def in_speech(self) -> bool:
        return self.status == EndpointStatus.SPEECH

    def update(self, prob: float, now: float | None = None) -> EndpointFrame:
        now = now if now is not None else time.perf_counter()
        frame = EndpointFrame(prob=prob)
        is_voice = prob >= self.threshold

        if self.status == EndpointStatus.LISTENING:
            if is_voice:
                self._confirm_run += 1
                # Require enough confirmed speech to be real (rejects blips).
                confirmed_ms = self._confirm_run * self.frame_s * 1000.0
                if self._confirm_run >= self.confirm_frames and confirmed_ms >= self.min_speech_ms:
                    self.status = EndpointStatus.SPEECH
                    self._speech_frames = self._confirm_run
                    self._utterance_start_ts = now
                    self._last_voice_ts = now
                    frame.started = True
                    logger.debug("Speech started")
            else:
                self._confirm_run = 0
            return frame

        if self.status == EndpointStatus.SPEECH:
            self._speech_frames += 1
            if is_voice:
                self._silent_frames = 0
                self._last_voice_ts = now
            else:
                self._silent_frames += 1

            speech_ms = self._speech_frames * self.frame_s * 1000.0
            trailing_silence_ms = self._silent_frames * self.frame_s * 1000.0

            # Count short pauses (within tolerance) but don't end speech
            if trailing_silence_ms >= self.pause_tolerance_ms and trailing_silence_ms < self.end_hold_ms:
                self._pause_count += 1
                # Only reset if this is clearly not the end
                if self._pause_count < 3:  # Allow up to 3 natural pauses
                    self._silent_frames = 0  # Reset to continue listening
                    logger.debug("Natural pause detected, continuing to listen")

            # End on sustained trailing silence (never on a lone pause).
            if (
                speech_ms >= self.min_speech_ms
                and trailing_silence_ms >= self.end_hold_ms
            ):
                self._finish(frame)
                return frame

            # Absolute safety cap (configurable; generous by default), based on
            # frames so behaviour is deterministic.
            if speech_ms >= self.max_utterance_s * 1000.0 and speech_ms >= self.min_speech_ms:
                self._finish(frame)
                return frame

            frame.speech_ms = speech_ms
            return frame

        return frame

    def _finish(self, frame: EndpointFrame) -> None:
        frame.ended = True
        self.status = EndpointStatus.ENDED
        frame.speech_ms = self._speech_frames * self.frame_s * 1000.0
        logger.debug("Speech ended")


endpoint = EndpointDetector()