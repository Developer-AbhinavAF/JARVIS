"""Telephony module — Twilio Voice integration for JARVIS AI OS.

Plug-and-play voice call interface. Every phone call becomes another frontend
exactly like CLI, Desktop, Web UI, or Speech Mode.
"""

from interface.telephony.config import telephony_config
from interface.telephony.session import CallSession
from interface.telephony.call_manager import call_manager
from interface.telephony.speech import SpeechRecognizer, get_recognizer
from interface.telephony.twilio_server import create_voice_app

__all__ = [
    "telephony_config",
    "CallSession",
    "call_manager",
    "SpeechRecognizer",
    "get_recognizer",
    "create_voice_app",
]
