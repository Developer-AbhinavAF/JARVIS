"""speech/interrupt_manager.py — Simple cancellation for graceful shutdown.

Provides clean interruption without barge-in for natural turn-based conversation.
"""

from __future__ import annotations

import time
import threading
from typing import Optional

from speech.logger import get_logger

logger = get_logger("interrupt")


class InterruptManager:
    def __init__(self) -> None:
        self._event = threading.Event()
        self._speaking = False
        self._last_interrupt_latency_ms: Optional[float] = None
        self._requested_ts: Optional[float] = None

    # --- playback state ----------------------------------------------------
    def playback_started(self) -> None:
        self._speaking = True

    def playback_stopped(self) -> None:
        self._speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    # --- interrupt ---------------------------------------------------------
    def request_interrupt(self) -> None:
        self._requested_ts = time.perf_counter()
        self._event.set()

    def cancelled(self) -> bool:
        return self._event.is_set()

    def reset(self) -> None:
        self._event.clear()
        self._requested_ts = None

    def record_handled(self) -> float:
        """Latency between interrupt request and worker acknowledgement."""
        if self._requested_ts is not None:
            self._last_interrupt_latency_ms = (time.perf_counter() - self._requested_ts) * 1000
        self.reset()
        return self._last_interrupt_latency_ms or 0.0

    @property
    def last_interrupt_latency_ms(self) -> Optional[float]:
        return self._last_interrupt_latency_ms


interrupt_manager = InterruptManager()
