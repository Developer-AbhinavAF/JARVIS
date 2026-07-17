"""Speech Engine Configuration — All from environment, zero hardcoding.

Every API key, voice ID, model ID, endpoint, and tuning parameter
is loaded from environment variables with safe fallback defaults.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


def _env(key: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.environ.get(key, default)


def _env_float(key: str, default: float = 0.0) -> float:
    """Get environment variable as float with default."""
    try:
        return float(_env(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_int(key: str, default: int = 0) -> int:
    """Get environment variable as int with default."""
    try:
        return int(_env(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as bool with default."""
    val = _env(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


@dataclass
class ElevenLabsConfig:
    """ElevenLabs API configuration — all from environment."""
    api_key: str = field(default_factory=lambda: _env("ELEVENLABS_API_KEY"))
    default_voice: str = field(default_factory=lambda: _env("ELEVENLABS_DEFAULT_VOICE", "Rachel"))
    model: str = field(default_factory=lambda: _env("ELEVENLABS_MODEL", "eleven_turbo_v2_5"))
    output_format: str = field(default_factory=lambda: _env("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128"))

    # Voice settings
    stability: float = field(default_factory=lambda: _env_float("ELEVENLABS_STABILITY", 0.5))
    similarity_boost: float = field(default_factory=lambda: _env_float("ELEVENLABS_SIMILARITY", 0.75))
    style: float = field(default_factory=lambda: _env_float("ELEVENLABS_STYLE", 0.0))
    use_speaker_boost: bool = field(default_factory=lambda: _env_bool("ELEVENLABS_SPEAKER_BOOST", True))

    # Streaming
    streaming_chunk_size: int = field(default_factory=lambda: _env_int("ELEVENLABS_STREAMING_CHUNK", 2048))
    optimize_streaming_latency: int = field(default_factory=lambda: _env_int("ELEVENLABS_OPTIMIZE_LATENCY", 4))

    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class AudioConfig:
    """Audio playback configuration."""
    sample_rate: int = field(default_factory=lambda: _env_int("AUDIO_SAMPLE_RATE", 44100))
    channels: int = field(default_factory=lambda: _env_int("AUDIO_CHANNELS", 1))
    dtype: str = field(default_factory=lambda: _env("AUDIO_DTYPE", "float32"))
    buffer_size: int = field(default_factory=lambda: _env_int("AUDIO_BUFFER_SIZE", 4096))
    output_device: str = field(default_factory=lambda: _env("AUDIO_OUTPUT_DEVICE", ""))
    input_device: str = field(default_factory=lambda: _env("AUDIO_INPUT_DEVICE", ""))
    output_format: str = field(default_factory=lambda: _env("AUDIO_OUTPUT_FORMAT", "mp3"))


@dataclass
class STTConfig:
    """Speech-to-text configuration."""
    engine: str = field(default_factory=lambda: _env("STT_ENGINE", "whisper"))
    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL", "base"))
    language: str = field(default_factory=lambda: _env("STT_LANGUAGE", "en"))
    energy_threshold: int = field(default_factory=lambda: _env_int("STT_ENERGY_THRESHOLD", 300))
    pause_threshold: float = field(default_factory=lambda: _env_float("STT_PAUSE_THRESHOLD", 0.8))
    phrase_time_limit: int = field(default_factory=lambda: _env_int("STT_PHRASE_TIME_LIMIT", 10))
    use_vad: bool = field(default_factory=lambda: _env_bool("STT_USE_VAD", True))
    vad_aggressiveness: int = field(default_factory=lambda: _env_int("STT_VAD_AGGRESSIVENESS", 2))


@dataclass
class SpeechConfig:
    """Master speech configuration."""
    elevenlabs: ElevenLabsConfig = field(default_factory=ElevenLabsConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)

    # General
    enabled: bool = field(default_factory=lambda: _env_bool("SPEECH_ENABLED", True))
    auto_listening: bool = field(default_factory=lambda: _env_bool("SPEECH_AUTO_LISTEN", True))
    interrupt_enabled: bool = field(default_factory=lambda: _env_bool("SPEECH_INTERRUPT", True))
    voice_start_latency_ms: int = field(default_factory=lambda: _env_int("SPEECH_VOICE_START_MS", 300))

    # Emotion / prosody
    default_emotion: str = field(default_factory=lambda: _env("SPEECH_EMOTION", "neutral"))
    enable_prosody: bool = field(default_factory=lambda: _env_bool("SPEECH_PROSODY", True))

    def validate(self) -> list[str]:
        """Return list of config issues."""
        issues = []
        if not self.elevenlabs.api_key:
            issues.append("ELEVENLABS_API_KEY not set")
        return issues

    def summary(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": "elevenlabs" if self.elevenlabs.is_configured() else "none",
            "model": self.elevenlabs.model,
            "voice": self.elevenlabs.default_voice,
            "stt_engine": self.stt.engine,
            "auto_listening": self.auto_listening,
            "interrupt": self.interrupt_enabled,
            "issues": self.validate(),
        }


speech_config = SpeechConfig()
