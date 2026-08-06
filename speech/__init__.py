"""JARVIS Production Speech Engine v5.0.

Full-duplex, event-driven, interruptible conversational voice engine.

Run the full voice conversation:

    python -m speech

Modules:
    config, logger, events, cache, vad, endpoint_detector, recognizer,
    streaming, queue, interrupt_manager, playback, edge_provider,
    speech_engine, benchmark
"""

from speech.speech_engine import SpeechEngine, speech_engine
from speech.events import EventBus, SpeechEvent, SpeechEventType, event_bus
from speech.config import SpeechConfig, cfg
from speech.logger import ConversationView, conversation_view

__all__ = [
    "SpeechEngine",
    "speech_engine",
    "SpeechConfig",
    "cfg",
    "EventBus",
    "SpeechEvent",
    "SpeechEventType",
    "event_bus",
    "ConversationView",
    "conversation_view",
]
