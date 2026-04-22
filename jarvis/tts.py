"""jarvis.tts

Threaded text-to-speech engine for JARVIS.

pyttsx3 must be created and run on the same OS thread; this module creates a
dedicated worker thread owning the pyttsx3 engine and exposes a queue-based API
to avoid blocking the main listen loop.
"""

from __future__ import annotations

import logging
import queue
import threading

import pyttsx3

from jarvis import config

logger = logging.getLogger(__name__)


class TTSEngine:
    """Queue-based TTS engine backed by a dedicated worker thread."""

    def __init__(self) -> None:
        """Start the worker thread and initialize the speaking queue."""

        self._queue: queue.Queue[tuple[str | None, threading.Event | None]] = queue.Queue()
        self._speaking = threading.Event()
        self._thread = threading.Thread(target=self._worker, name="JarvisTTS", daemon=True)
        self._thread.start()

    def _worker(self) -> None:
        """Own the pyttsx3 engine event loop on a single OS thread."""

        # pyttsx3 must own its event loop — cannot share across threads.
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", config.TTS_RATE)
            engine.setProperty("volume", config.TTS_VOLUME)

            hint = (config.TTS_VOICE_HINT or "").strip().lower()
            if hint:
                try:
                    for voice in engine.getProperty("voices") or []:
                        name = (getattr(voice, "name", "") or "").lower()
                        voice_id = (getattr(voice, "id", "") or "").lower()
                        if hint in name or hint in voice_id:
                            engine.setProperty("voice", voice.id)
                            break
                except Exception:
                    logger.exception("Failed while applying voice hint")
        except Exception:
            logger.exception("Failed to initialize pyttsx3")
            return

        while True:
            text, done_event = self._queue.get()
            try:
                if text is None:
                    # Sentinel for shutdown.
                    return

                self._speaking.set()
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception:
                    logger.exception("TTS speaking failed")
            finally:
                self._speaking.clear()
                if done_event is not None:
                    done_event.set()
                self._queue.task_done()

    def speak(self, text: str) -> None:
        """Enqueue speech without blocking the caller."""

        try:
            self._queue.put((text, None))
        except Exception:
            logger.exception("Failed to enqueue TTS")

    def speak_sync(self, text: str) -> None:
        """Speak text and block until the utterance has finished."""

        done = threading.Event()
        try:
            self._queue.put((text, done))
        except Exception:
            logger.exception("Failed to enqueue TTS")
            return

        # We wait on the event rather than queue.join() to avoid cross-call coupling.
        done.wait()

    def is_speaking(self) -> bool:
        """Return True if TTS is currently speaking or has backlog."""

        return self._speaking.is_set() or not self._queue.empty()

    def stop(self) -> None:
        """Stop current speech and clear the queue."""
        
        try:
            # Clear the queue of pending speech
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except queue.Empty:
                    break
            logger.info("TTS queue cleared")
        except Exception:
            logger.exception("Failed to clear TTS queue")

    def shutdown(self) -> None:
        """Stop the TTS worker gracefully (for application exit)."""

        try:
            self._queue.put((None, None))
            self._thread.join(timeout=5)
        except Exception:
            logger.exception("Failed to shutdown TTS")
