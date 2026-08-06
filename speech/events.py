"""speech/events.py — Standardized speech event bus.

Events (as specified):

    ListeningStarted / ListeningStopped
    SpeechDetected / SpeechStarted / SpeechEnded
    RecognitionStarted / RecognitionFinished
    PlaybackStarted / PlaybackStopped / PlaybackInterrupted
    SpeechGenerated / SpeechCached
    ResponseStarted / ResponseFinished

Everything is thread-safe: producers are audio threads, consumers may be
async loops or UI threads.
"""

from __future__ import annotations

import time
import threading
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class SpeechEventType(Enum):
    LISTENING_STARTED = auto()
    LISTENING_STOPPED = auto()
    SPEECH_DETECTED = auto()
    SPEECH_STARTED = auto()
    SPEECH_ENDED = auto()
    RECOGNITION_STARTED = auto()
    RECOGNITION_FINISHED = auto()
    SENTENCE_COMPLETED = auto()
    SPEECH_GENERATED = auto()
    SPEECH_CACHED = auto()
    PLAYBACK_STARTED = auto()
    PLAYBACK_STOPPED = auto()
    PLAYBACK_INTERRUPTED = auto()
    RESPONSE_STARTED = auto()
    RESPONSE_FINISHED = auto()


@dataclass
class SpeechEvent:
    type: SpeechEventType
    payload: Any = None
    ts: float = field(default_factory=time.perf_counter)


Handler = Callable[[SpeechEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: Dict[SpeechEventType, List[Handler]] = {}
        self._lock = threading.Lock()
        self._history: List[SpeechEvent] = []
        self._history_limit = 200

    def subscribe(self, event_type: SpeechEventType, handler: Handler) -> Callable[[], None]:
        with self._lock:
            self._subs.setdefault(event_type, []).append(handler)

        def _unsubscribe() -> None:
            with self._lock:
                try:
                    self._subs[event_type].remove(handler)
                except (KeyError, ValueError):
                    pass

        return _unsubscribe

    def publish(self, event_type: SpeechEventType, payload: Any = None) -> SpeechEvent:
        event = SpeechEvent(type=event_type, payload=payload)
        with self._lock:
            handlers = list(self._subs.get(event_type, []))
            self._history.append(event)
            if len(self._history) > self._history_limit:
                self._history = self._history[-self._history_limit:]
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass
        return event

    def history(self, event_type: Optional[SpeechEventType] = None) -> List[SpeechEvent]:
        with self._lock:
            if event_type is None:
                return list(self._history)
            return [e for e in self._history if e.type == event_type]


event_bus = EventBus()
