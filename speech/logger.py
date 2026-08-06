"""speech/logger.py — Terminal-facing logger for the speech subsystem.

Keeps the conversation view clean:

    User:
    Hello

    Jarvis:
    Hello! How can I help—

    [Interrupted]

No debug spam, no stack traces. Library logs (httpx, onnxruntime, ...) stay
filtered; only meaningful speech events reach the terminal.
"""

from __future__ import annotations

import sys
import logging
import threading
from datetime import datetime

_TERMINAL_LOCK = threading.Lock()

_NAME = "speech"


def _setup() -> logging.Logger:
    logger = logging.getLogger(_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[speech] %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    for noisy in ("httpx", "httpcore", "onnxruntime", "urllib3", "edge_tts", "pyaudio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logger


def get_logger(name: str = _NAME) -> logging.Logger:
    return _setup().getChild(name)


class ConversationView:
    """Pretty-prints the User:/Jarvis: conversation exactly like a chat log."""

    def __init__(self, out=sys.stdout) -> None:
        self._out = out
        self._partial_user_text = ""

    def user(self, text: str) -> None:
        with _TERMINAL_LOCK:
            self._out.write(f"\nYou:\n{text}\n")
            self._out.write("-" * 40 + "\n")
            self._out.flush()

    def user_partial(self, text: str) -> None:
        """Show partial transcript while user is speaking."""
        with _TERMINAL_LOCK:
            self._partial_user_text = text
            self._out.write(f"\rYou: {text}...")
            self._out.flush()

    def jarvis(self, text: str) -> None:
        with _TERMINAL_LOCK:
            self._partial_user_text = ""
            self._out.write(f"\nJarvis:\n{text}\n")
            self._out.write("-" * 40 + "\n")
            self._out.flush()

    def interrupted(self) -> None:
        with _TERMINAL_LOCK:
            self._out.write("\n[Interrupted]\n")
            self._out.flush()

    def hint(self, text: str) -> None:
        with _TERMINAL_LOCK:
            self._out.write(f"\n[{text}]\n")
            self._out.flush()


conversation_view = ConversationView()
