"""python -m speech — Full-duplex voice conversation with JARVIS.

Microphone is ALWAYS active. Barge-in works. No buttons, no timers.

    python -m speech
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from speech.speech_engine import speech_engine
from speech.logger import get_logger, conversation_view

logger = get_logger("main")


def build_handler(jarvis):
    def handler(text: str) -> str:
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(jarvis.handle(text))
        finally:
            loop.close()
        if isinstance(result, dict):
            return result.get("response", "")
        return str(result)

    return handler


def main() -> None:
    from interface.app import JARVIS

    jarvis = JARVIS()
    jarvis.boot()

    avail = speech_engine.is_available()
    if not avail.get("stt"):
        conversation_view.hint("No speech-to-text backend available — install faster-whisper")
    if not avail.get("tts"):
        conversation_view.hint("No text-to-speech backend available — install edge-tts")

    speech_engine.run_conversation(build_handler(jarvis))
    conversation_view.hint("Voice conversation started — speak anytime, press Ctrl+C to quit")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        conversation_view.hint("Stopping voice conversation")
    finally:
        speech_engine.stop()
        jarvis.shutdown() if hasattr(jarvis, "shutdown") else None


if __name__ == "__main__":
    main()
