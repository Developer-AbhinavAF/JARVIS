"""speech/queue.py — Thread-safe playback queue.

Sentence1.wav, Sentence2.wav ... are queued FIFO; a worker plays, deletes
(temp files), and moves on. `clear()` flushes pending items so callers can
delete temp files after an interrupt.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from speech.config import cfg


@dataclass
class SpeechItem:
    text: str = ""
    path: Path = None  # type: ignore[assignment]
    temp: bool = False        # True => playback worker deletes it after playing
    created: float = field(default_factory=lambda: __import__("time").perf_counter())


class SpeechQueue:
    def __init__(self, max_size: int = 0) -> None:
        self._max = max_size or cfg.max_queue_size
        self._q: "queue.Queue[SpeechItem]" = queue.Queue(maxsize=self._max)
        self._lock = threading.Lock()
        self._closed = False

    def put(self, item: SpeechItem) -> bool:
        if self._closed:
            return False
        try:
            self._q.put_nowait(item)
            return True
        except queue.Full:
            return False

    def get(self, timeout: float | None = 0.2) -> Optional[SpeechItem]:
        if timeout is None:
            try:
                return self._q.get()
            except queue.Empty:
                return None
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def task_done(self) -> None:
        try:
            self._q.task_done()
        except ValueError:
            pass

    def pending(self) -> List[SpeechItem]:
        with self._lock:
            with self._q.mutex:
                return list(self._q.queue)

    def qsize(self) -> int:
        return self._q.qsize()

    def clear(self) -> List[SpeechItem]:
        """Remove everything queued; returns discarded items for cleanup."""
        discarded: List[SpeechItem] = []
        with self._lock:
            while True:
                try:
                    discarded.append(self._q.get_nowait())
                except queue.Empty:
                    break
        return discarded

    def close(self) -> None:
        self._closed = True
        self.clear()
