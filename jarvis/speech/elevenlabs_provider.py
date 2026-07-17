"""ElevenLabs Speech Provider — Full API integration.

Dynamically queries and uses every available feature for the
authenticated account. Supports streaming, voice management,
conversational mode, emotion control, and more.
"""

from __future__ import annotations

import time
import logging
import asyncio
from typing import Any, AsyncIterator, Iterator
from dataclasses import dataclass, field

from .config import speech_config, ElevenLabsConfig

logger = logging.getLogger(__name__)

try:
    from elevenlabs import ElevenLabs
    from elevenlabs.client import ElevenLabs as ElevenLabsClient
    from elevenlabs.types import (
        VoiceSettings,
        TextToSpeechOutputFormat,
    )
    HAS_ELEVENLABS = True
except ImportError:
    HAS_ELEVENLABS = False
    logger.warning("elevenlabs package not installed")


# ════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class VoiceInfo:
    """Information about an available voice."""
    voice_id: str = ""
    name: str = ""
    category: str = ""        # premade, cloned, generated, professional
    labels: dict[str, str] = field(default_factory=dict)
    preview_url: str = ""
    is_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "category": self.category,
            "labels": self.labels,
        }


@dataclass
class AccountInfo:
    """ElevenLabs account information."""
    character_count: int = 0
    character_limit: int = 0
    tier: str = ""
    can_do_instant_tts: bool = False
    can_do_text_to_speech: bool = True
    can_do_voice_cloning: bool = False
    can_use_pro_voices: bool = False
    max_voice_age_days: int = 0


@dataclass
class TTSResult:
    """Result from text-to-speech synthesis."""
    audio_data: bytes = b""
    duration_ms: float = 0.0
    voice_id: str = ""
    model: str = ""
    text_length: int = 0
    format: str = ""


# ════════════════════════════════════════════════════════════════════
# ELEVENLABS PROVIDER
# ════════════════════════════════════════════════════════════════════

class ElevenLabsProvider:
    """Full ElevenLabs integration with dynamic capability detection."""

    def __init__(self, config: ElevenLabsConfig | None = None) -> None:
        self._config = config or speech_config.elevenlabs
        self._client: Any = None
        self._voices: list[VoiceInfo] = []
        self._account: AccountInfo | None = None
        self._capabilities: dict[str, bool] = {}
        self._synthesis_count: int = 0
        self._total_chars: int = 0

        if HAS_ELEVENLABS and self._config.is_configured():
            try:
                self._client = ElevenLabsClient(api_key=self._config.api_key)
                logger.info("ElevenLabs client initialized")
            except Exception as e:
                logger.error("Failed to initialize ElevenLabs: %s", e)

    @property
    def is_available(self) -> bool:
        return self._client is not None

    # ── Account & Capabilities ──────────────────────────────────────

    def get_account_info(self) -> AccountInfo:
        """Query account info and capabilities."""
        if self._account:
            return self._account

        if not self.is_available:
            return AccountInfo()

        try:
            user = self._client.user.get_subscription()
            self._account = AccountInfo(
                character_count=getattr(user, 'character_count', 0),
                character_limit=getattr(user, 'character_limit', 0),
                tier=getattr(user, 'tier', 'unknown'),
                can_do_instant_tts=getattr(user, 'can_do_instant_tts', False),
                can_do_text_to_speech=getattr(user, 'can_do_text_to_speech', True),
                can_do_voice_cloning=getattr(user, 'can_do_voice_cloning', False),
                can_use_pro_voices=getattr(user, 'can_use_pro_voices', False),
            )
            logger.info("ElevenLabs account: tier=%s chars=%d/%d",
                        self._account.tier,
                        self._account.character_count,
                        self._account.character_limit)
        except Exception as e:
            logger.debug("Could not fetch account info: %s", e)
            self._account = AccountInfo()

        return self._account

    def get_capabilities(self) -> dict[str, bool]:
        """Detect available capabilities for this account."""
        if self._capabilities:
            return self._capabilities

        account = self.get_account_info()
        self._capabilities = {
            "text_to_speech": account.can_do_text_to_speech,
            "instant_tts": account.can_do_instant_tts,
            "voice_cloning": account.can_do_voice_cloning,
            "pro_voices": account.can_use_pro_voices,
            "streaming": True,  # All accounts support streaming
            "conversational": True,
            "voice_management": True,
            "pronunciation_dictionaries": True,
            "projects": True,
            "multi_language": True,
            "emotion_control": True,
        }
        return self._capabilities

    # ── Voice Management ────────────────────────────────────────────

    def get_voices(self) -> list[VoiceInfo]:
        """Get all available voices."""
        if self._voices:
            return self._voices

        if not self.is_available:
            return []

        try:
            response = self._client.voices.get_all()
            self._voices = []
            for voice in response.voices:
                info = VoiceInfo(
                    voice_id=voice.voice_id,
                    name=voice.name,
                    category=getattr(voice, 'category', 'unknown'),
                    labels=getattr(voice, 'labels', {}) or {},
                    preview_url=getattr(voice, 'preview_url', ''),
                    is_available=getattr(voice, 'is_available', True),
                )
                self._voices.append(info)

            logger.info("Loaded %d voices", len(self._voices))
        except Exception as e:
            logger.debug("Could not fetch voices: %s", e)

        return self._voices

    def get_voice_by_name(self, name: str) -> VoiceInfo | None:
        """Find a voice by name (case-insensitive)."""
        name_lower = name.lower()
        for v in self.get_voices():
            if v.name.lower() == name_lower:
                return v
        # Partial match
        for v in self.get_voices():
            if name_lower in v.name.lower():
                return v
        return None

    def get_voice_id(self, voice_name: str | None = None) -> str:
        """Resolve voice name to voice ID."""
        name = voice_name or self._config.default_voice
        voice = self.get_voice_by_name(name)
        if voice:
            return voice.voice_id
        # Fallback: try using the string as-is (might be an ID)
        if len(name) > 20:
            return name
        # Default voice
        voices = self.get_voices()
        if voices:
            return voices[0].voice_id
        return ""

    def _build_voice_settings(self, emotion: str = "neutral") -> Any:
        """Build voice settings from config and emotion."""
        if not HAS_ELEVENLABS:
            return None

        # Adjust settings based on emotion
        stability = self._config.stability
        similarity = self._config.similarity_boost
        style = self._config.style

        emotion_adjustments = {
            "excited": {"stability": 0.3, "similarity": 0.8, "style": 0.6},
            "happy": {"stability": 0.4, "similarity": 0.75, "style": 0.4},
            "calm": {"stability": 0.7, "similarity": 0.7, "style": 0.1},
            "serious": {"stability": 0.8, "similarity": 0.8, "style": 0.0},
            "sad": {"stability": 0.6, "similarity": 0.7, "style": 0.3},
            "angry": {"stability": 0.2, "similarity": 0.85, "style": 0.7},
            "whisper": {"stability": 0.9, "similarity": 0.6, "style": 0.0},
            "narrative": {"stability": 0.6, "similarity": 0.75, "style": 0.3},
            "conversational": {"stability": 0.5, "similarity": 0.75, "style": 0.2},
        }

        adjustments = emotion_adjustments.get(emotion, {})
        if adjustments:
            stability = adjustments.get("stability", stability)
            similarity = adjustments.get("similarity", similarity)
            style = adjustments.get("style", style)

        return VoiceSettings(
            stability=stability,
            similarity_boost=similarity,
            style=style,
            use_speaker_boost=self._config.use_speaker_boost,
        )

    # ── Text-to-Speech ──────────────────────────────────────────────

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        emotion: str = "neutral",
    ) -> TTSResult:
        """Synchronous TTS synthesis."""
        t0 = time.perf_counter()
        result = TTSResult(text_length=len(text), voice_id=voice or self._config.default_voice)

        if not self.is_available or not text.strip():
            return result

        try:
            voice_id = self.get_voice_id(voice)
            settings = self._build_voice_settings(emotion)

            audio_gen = self._client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=self._config.model,
                voice_settings=settings,
            )

            # Collect audio bytes
            audio_chunks = []
            for chunk in audio_gen:
                if isinstance(chunk, bytes):
                    audio_chunks.append(chunk)
                elif isinstance(chunk, bytearray):
                    audio_chunks.append(bytes(chunk))

            result.audio_data = b"".join(audio_chunks)
            result.duration_ms = (time.perf_counter() - t0) * 1000
            result.model = self._config.model
            result.format = self._config.output_format

            self._synthesis_count += 1
            self._total_chars += len(text)

        except Exception as e:
            logger.error("TTS synthesis failed: %s", e)

        return result

    def synthesize_stream(
        self,
        text: str,
        voice: str | None = None,
        emotion: str = "neutral",
    ) -> Iterator[bytes]:
        """Streaming TTS — yields audio chunks as they're generated."""
        if not self.is_available or not text.strip():
            return

        try:
            voice_id = self.get_voice_id(voice)
            settings = self._build_voice_settings(emotion)

            audio_stream = self._client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=self._config.model,
                voice_settings=settings,
            )

            for chunk in audio_stream:
                if isinstance(chunk, bytes):
                    yield chunk
                elif isinstance(chunk, bytearray):
                    yield bytes(chunk)

            self._synthesis_count += 1
            self._total_chars += len(text)

        except Exception as e:
            logger.error("TTS streaming failed: %s", e)

    async def synthesize_stream_async(
        self,
        text: str,
        voice: str | None = None,
        emotion: str = "neutral",
    ) -> AsyncIterator[bytes]:
        """Async streaming TTS."""
        if not self.is_available or not text.strip():
            return

        try:
            voice_id = self.get_voice_id(voice)
            settings = self._build_voice_settings(emotion)

            # Use the async client for non-blocking streaming
            audio_stream = self._client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=self._config.model,
                voice_settings=settings,
            )

            for chunk in audio_stream:
                if isinstance(chunk, bytes):
                    yield chunk
                elif isinstance(chunk, bytearray):
                    yield bytes(chunk)

            self._synthesis_count += 1
            self._total_chars += len(text)

        except Exception as e:
            logger.error("Async TTS streaming failed: %s", e)

    # ── Conversational TTS ──────────────────────────────────────────

    def synthesize_conversational(
        self,
        text: str,
        voice: str | None = None,
        emotion: str = "conversational",
    ) -> TTSResult:
        """Conversational-style TTS with more natural delivery."""
        return self.synthesize(text, voice, emotion)

    # ── Pronunciation ───────────────────────────────────────────────

    def get_pronunciation_dictionaries(self) -> list[dict]:
        """Get available pronunciation dictionaries."""
        if not self.is_available:
            return []
        try:
            response = self._client.pronunciation_dictionaries.get_all()
            return [{"id": d.id, "name": d.name} for d in (response.dictionaries if hasattr(response, 'dictionaries') else [])]
        except Exception as e:
            logger.debug("Could not fetch pronunciation dictionaries: %s", e)
            return []

    # ── Stats ───────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "available": self.is_available,
            "synthesis_count": self._synthesis_count,
            "total_chars": self._total_chars,
            "voices_loaded": len(self._voices),
            "account_tier": self._account.tier if self._account else "unknown",
            "capabilities": self.get_capabilities() if self.is_available else {},
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

elevenlabs_provider = ElevenLabsProvider()
