"""SpeechRecognizer — provider-independent STT abstraction.

Supports: Twilio STT, Groq Whisper, OpenAI Whisper, Deepgram.
The active provider is selected via WHISPER_PROVIDER env var.
"""

from __future__ import annotations

import abc
import base64
import io
import json
import logging
import struct
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("jarvis.telephony.stt")


@dataclass
class STTResult:
    text: str
    confidence: float = 0.0
    provider: str = ""
    latency_ms: float = 0.0
    is_final: bool = True


class SpeechRecognizer(abc.ABC):
    """Abstract base class for speech-to-text providers."""

    @abc.abstractmethod
    async def transcribe(self, audio_data: bytes, **kwargs: Any) -> STTResult:
        """Transcribe raw audio bytes to text."""
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and reachable."""
        ...


class TwilioSTT(SpeechRecognizer):
    """Twilio's built-in speech recognition via <Gather> TwiML.

    This is the simplest option — Twilio handles STT server-side and sends
    transcribed text to our webhook. No audio processing needed.
    """

    async def transcribe(self, audio_data: bytes, **kwargs: Any) -> STTResult:
        # Twilio STT is handled server-side; this is called for consistency
        # but the actual transcription comes via the webhook POST body.
        return STTResult(text="", provider="twilio", is_final=False)

    def is_available(self) -> bool:
        return True  # Always available if Twilio is configured


class GroqWhisperSTT(SpeechRecognizer):
    """Groq-hosted Whisper for fast server-side transcription."""

    def __init__(self) -> None:
        self._api_key = ""
        self._base_url = "https://api.groq.com/openai/v1"

    def _ensure_key(self) -> None:
        if not self._api_key:
            from interface.telephony.config import telephony_config
            self._api_key = telephony_config.groq_api_key

    async def transcribe(self, audio_data: bytes, **kwargs: Any) -> STTResult:
        import httpx

        self._ensure_key()
        if not self._api_key:
            return STTResult(text="", provider="groq", latency_ms=0)

        start = time.time()
        model = kwargs.get("model", "whisper-large-v3")
        language = kwargs.get("language", "en")

        # Convert mulaw 8kHz to WAV for the API
        wav_data = self._mulaw_to_wav(audio_data)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {
                    "file": ("audio.wav", io.BytesIO(wav_data), "audio/wav"),
                }
                data = {
                    "model": model,
                    "language": language,
                    "response_format": "json",
                }
                headers = {"Authorization": f"Bearer {self._api_key}"}
                resp = await client.post(
                    f"{self._base_url}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    return STTResult(
                        text=result.get("text", ""),
                        confidence=1.0,
                        provider="groq",
                        latency_ms=(time.time() - start) * 1000,
                    )
                logger.error("Groq STT error %d: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.error("Groq STT failed: %s", e)

        return STTResult(text="", provider="groq", latency_ms=(time.time() - start) * 1000)

    def is_available(self) -> bool:
        self._ensure_key()
        return bool(self._api_key)

    @staticmethod
    def _mulaw_to_wav(mulaw_data: bytes) -> bytes:
        """Convert mulaw 8kHz mono to WAV format."""
        import wave

        # mulaw 8kHz -> linear PCM 16kHz
        pcm_samples = _ulaw_decode(mulaw_data)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(pcm_samples)
        return buf.getvalue()


class WhisperAPISTT(SpeechRecognizer):
    """OpenAI Whisper API for transcription."""

    def __init__(self) -> None:
        self._api_key = ""
        self._base_url = "https://api.openai.com/v1"

    def _ensure_key(self) -> None:
        if not self._api_key:
            import os
            self._api_key = os.getenv("OPENAI_API_KEY", "")

    async def transcribe(self, audio_data: bytes, **kwargs: Any) -> STTResult:
        import httpx

        self._ensure_key()
        if not self._api_key:
            return STTResult(text="", provider="whisper", latency_ms=0)

        start = time.time()
        model = kwargs.get("model", "whisper-1")

        wav_data = GroqWhisperSTT._mulaw_to_wav(audio_data)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"file": ("audio.wav", io.BytesIO(wav_data), "audio/wav")}
                data = {"model": model, "response_format": "json"}
                headers = {"Authorization": f"Bearer {self._api_key}"}
                resp = await client.post(
                    f"{self._base_url}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    return STTResult(
                        text=result.get("text", ""),
                        confidence=1.0,
                        provider="whisper",
                        latency_ms=(time.time() - start) * 1000,
                    )
        except Exception as e:
            logger.error("Whisper API STT failed: %s", e)

        return STTResult(text="", provider="whisper", latency_ms=(time.time() - start) * 1000)

    def is_available(self) -> bool:
        self._ensure_key()
        return bool(self._api_key)


class DeepgramSTT(SpeechRecognizer):
    """Deepgram Nova for real-time and batch transcription."""

    def __init__(self) -> None:
        self._api_key = ""

    def _ensure_key(self) -> None:
        if not self._api_key:
            from interface.telephony.config import telephony_config
            self._api_key = telephony_config.deepgram_api_key

    async def transcribe(self, audio_data: bytes, **kwargs: Any) -> STTResult:
        import httpx

        self._ensure_key()
        if not self._api_key:
            return STTResult(text="", provider="deepgram", latency_ms=0)

        start = time.time()
        model = kwargs.get("model", "nova-2")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Token {self._api_key}",
                    "Content-Type": "audio/wav",
                }
                wav_data = GroqWhisperSTT._mulaw_to_wav(audio_data)
                resp = await client.post(
                    f"https://api.deepgram.com/v1/listen?model={model}&language=en",
                    headers=headers,
                    content=wav_data,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    alternatives = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [])
                    if alternatives:
                        return STTResult(
                            text=alternatives[0].get("transcript", ""),
                            confidence=alternatives[0].get("confidence", 0.0),
                            provider="deepgram",
                            latency_ms=(time.time() - start) * 1000,
                        )
        except Exception as e:
            logger.error("Deepgram STT failed: %s", e)

        return STTResult(text="", provider="deepgram", latency_ms=(time.time() - start) * 1000)

    def is_available(self) -> bool:
        self._ensure_key()
        return bool(self._api_key)


# ── Provider Registry ───────────────────────────────────────────────

_PROVIDERS: dict[str, type[SpeechRecognizer]] = {
    "twilio": TwilioSTT,
    "groq": GroqWhisperSTT,
    "whisper": WhisperAPISTT,
    "deepgram": DeepgramSTT,
}

_recognizer_cache: dict[str, SpeechRecognizer] = {}


def get_recognizer(provider: Optional[str] = None) -> SpeechRecognizer:
    """Get a SpeechRecognizer instance for the given provider."""
    if provider is None:
        from interface.telephony.config import telephony_config
        provider = telephony_config.stt_provider

    if provider not in _recognizer_cache:
        cls = _PROVIDERS.get(provider, TwilioSTT)
        _recognizer_cache[provider] = cls()
        logger.info("STT provider initialized: %s", provider)

    return _recognizer_cache[provider]


# ── Helpers ──────────────────────────────────────────────────────────

def _ulaw_decode(mulaw_data: bytes) -> bytes:
    """Decode mulaw-encoded audio to linear 16-bit PCM."""
    pcm = bytearray(len(mulaw_data) * 2)
    for i, byte in enumerate(mulaw_data):
        mulaw = ~byte & 0xFF
        sign = mulaw & 0x80
        exponent = (mulaw >> 4) & 0x07
        mantissa = mulaw & 0x0F
        sample = ((mantissa << 1) + 33) << (exponent + 2)
        sample -= 0x84
        if sign:
            sample = -sample
        struct.pack_into("<h", pcm, i * 2, max(-32768, min(32767, sample)))
    return bytes(pcm)
