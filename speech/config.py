"""speech/config.py — Single source of truth for speech-engine settings.

All thresholds are tunable. Values are read once from the environment
(JARVIS_SPEECH_*) so nothing here is hard-wired.
"""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, ""))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, ""))
    except ValueError:
        return default


@dataclass
class SpeechConfig:
    # --- Audio capture -----------------------------------------------------
    sample_rate: int = _env_int("JARVIS_SPEECH_SAMPLE_RATE", 16000)
    frame_ms: int = _env_int("JARVIS_SPEECH_FRAME_MS", 30)          # VAD frame
    channels: int = 1
    device_index: int | None = None

    # --- VAD ---------------------------------------------------------------
    vad_threshold: float = _env_float("JARVIS_SPEECH_VAD_THRESHOLD", 0.5)
    vad_confirm_frames: int = _env_int("JARVIS_SPEECH_VAD_CONFIRM", 3)  # frames of speech to start
    silero_model_path: Path = Path(os.getenv("JARVIS_SPEECH_SILERO", PROJECT_ROOT / "speech" / "models" / "silero_vad.onnx"))
    silero_url: str = (
        "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
    )

    # --- Smart endpoint ----------------------------------------------------
    end_hold_ms: int = _env_int("JARVIS_SPEECH_END_HOLD_MS", 1200)   # trailing silence to end (increased for natural pauses)
    min_speech_ms: int = _env_int("JARVIS_SPEECH_MIN_SPEECH_MS", 250) # minimum speech to start
    max_utterance_s: float = _env_float("JARVIS_SPEECH_MAX_UTTERANCE_S", 60.0) # allow longer monologues
    pre_roll_ms: int = _env_int("JARVIS_SPEECH_PRE_ROLL_MS", 200)    # audio kept before start
    pause_tolerance_ms: int = _env_int("JARVIS_SPEECH_PAUSE_TOLERANCE_MS", 500) # ignore intra-sentence pauses

    # --- Recognition -------------------------------------------------------
    stt_language: str = os.getenv("JARVIS_SPEECH_STT_LANG", "en")  # Auto-detect with multilingual support
    whisper_size: str = os.getenv("JARVIS_SPEECH_WHISPER_SIZE", "small")  # Improved accuracy
    google_language: str = os.getenv("JARVIS_SPEECH_GOOGLE_LANG", "en-IN")  # Indian English
    vosk_model_path: Path = Path(os.getenv("JARVIS_SPEECH_VOSK_MODEL", PROJECT_ROOT / "speech" / "models" / "vosk"))
    # Enable auto-language detection for multilingual support
    whisper_task: str = os.getenv("JARVIS_SPEECH_WHISPER_TASK", "transcribe")

    # --- TTS ---------------------------------------------------------------
    tts_voice: str = os.getenv("JARVIS_SPEECH_VOICE", "en-IN-PrabhatNeural")
    tts_rate: str = os.getenv("JARVIS_SPEECH_RATE", "+0%")
    tts_pitch: str = os.getenv("JARVIS_SPEECH_PITCH", "+0Hz")
    tts_volume: str = os.getenv("JARVIS_SPEECH_VOLUME", "+0%")
    tts_temp_dir: Path = Path(os.getenv("JARVIS_SPEECH_TMP", PROJECT_ROOT / "data" / "speech_tmp"))

    # --- Cache -------------------------------------------------------------
    cache_dir: Path = Path(os.getenv("JARVIS_SPEECH_CACHE", PROJECT_ROOT / "data" / "speech_cache"))
    cache_max_files: int = _env_int("JARVIS_SPEECH_CACHE_MAX", 512)

    # --- Barge-in / echo ---------------------------------------------------
    # Barge-in disabled for natural turn-based conversation
    barge_in_enabled: bool = False
    echo_suppress_ms: int = 0
    barge_confirm_frames: int = 0
    barge_gap_frames: int = 0

    # --- Playback ----------------------------------------------------------
    output_device_index: int | None = None
    play_chunk_s: float = _env_float("JARVIS_SPEECH_PLAY_CHUNK_S", 0.05)
    max_queue_size: int = _env_int("JARVIS_SPEECH_MAX_QUEUE", 64)

    # --- Runtime -----------------------------------------------------------
    enabled: bool = True

    def ensure_dirs(self) -> None:
        for d in (self.cache_dir, self.tts_temp_dir):
            d.mkdir(parents=True, exist_ok=True)


cfg: SpeechConfig = SpeechConfig()
