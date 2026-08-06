"""speech/recognizer.py — Speech-to-text with cascading providers.

Order:
    1. faster-whisper   (local — best accuracy/latency/CPU balance)
    2. groq-whisper     (cloud — Whisper large-v3 via Groq, keys in .env)
    3. vosk             (offline fallback)
    4. google           (SpeechRecognition, last-resort cloud fallback)

Recognition is NEVER left running continuously — it is invoked only once
Silero confirms speech completion.
"""

from __future__ import annotations

import io
import os
import time
import wave as wave_mod
import logging
import threading
import numpy as np
from pathlib import Path

from speech.config import cfg
from speech.events import event_bus, SpeechEventType
from speech.logger import get_logger

logger = get_logger("recognizer")


class RecognitionResult:
    def __init__(self, text: str = "", provider: str = "", confidence: float = 0.0,
                 duration_ms: float = 0.0, error: str = "") -> None:
        self.text = text
        self.provider = provider
        self.confidence = confidence
        self.duration_ms = duration_ms
        self.error = error

    @property
    def success(self) -> bool:
        return bool(self.text.strip())


class _Provider:
    def __init__(self, name: str, priority: int, transcribe, available) -> None:
        self.name = name
        self.priority = priority
        self.transcribe = transcribe
        self.available = available


def _dotenv() -> None:
    """Ensure .env keys are in the environment for every entry point."""
    if os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY"):
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(str(Path(__file__).resolve().parent.parent / ".env"))
    except Exception:
        pass


def _pcm16(audio: np.ndarray) -> bytes:
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()


def _pcm16_wav(audio: np.ndarray) -> bytes:
    """Encode float32 mono samples into a valid 16-bit WAV byte string."""
    buf = io.BytesIO()
    with wave_mod.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(cfg.sample_rate)
        wf.writeframes(_pcm16(audio))
    return buf.getvalue()


def _groq_lang(lang: str) -> str:
    return {"english": "en", "en": "en"}.get(lang.strip().lower(), lang)


VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"
VOSK_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODEL_NAME}.zip"
_vosk_download_started = False


def ensure_vosk_model(block: bool = False) -> bool:
    """Download+extract the small Vosk model into cfg.vosk_model_path."""
    global _vosk_download_started
    if cfg.vosk_model_path.exists():
        return True
    if _vosk_download_started and not block:
        return False
    _vosk_download_started = True
    try:
        import zipfile
        import urllib.request
        import tempfile
        tmp = Path(tempfile.gettempdir()) / f"{VOSK_MODEL_NAME}.zip"
        logger.info("Downloading Vosk model %s ...", VOSK_MODEL_NAME)
        urllib.request.urlretrieve(VOSK_URL, str(tmp))
        cfg.vosk_model_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp) as z:
            z.extractall(cfg.vosk_model_path.parent)
        (cfg.vosk_model_path.parent / VOSK_MODEL_NAME).rename(cfg.vosk_model_path)
        try:
            os.remove(tmp)
        except OSError:
            pass
        logger.info("Vosk model ready at %s", cfg.vosk_model_path)
        return True
    except Exception as e:
        logger.warning("Vosk model download failed: %s", e)
        return False


class Recognizer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chain: list[_Provider] = []
        self._fw_model = None
        self._build_chain()

    def _build_chain(self) -> None:
        chain: list[_Provider] = []
        chain.append(_Provider("faster-whisper", 1, self._transcribe_faster_whisper, self._fw_available))
        chain.append(_Provider("groq-whisper", 2, self._transcribe_groq, self._groq_available))
        chain.append(_Provider("vosk", 3, self._transcribe_vosk, self._vosk_available))
        chain.append(_Provider("google", 4, self._transcribe_google, self._google_available))
        self._chain = sorted(chain, key=lambda p: p.priority)

    # --- availability ------------------------------------------------------
    @staticmethod
    def _fw_available() -> bool:
        if not _import("faster_whisper"):
            return False
        try:
            from faster_whisper import WhisperModel
            WhisperModel  # model is loaded lazily on first use
            return True
        except Exception:
            return False

    @staticmethod
    def _google_available() -> bool:
        return bool(_import("speech_recognition"))

    @staticmethod
    def _groq_available() -> bool:
        _dotenv()
        key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_2") or os.getenv("GROQ_API_KEY_3")
        return bool(key and _import("requests"))

    @staticmethod
    def _vosk_available() -> bool:
        return bool(_import("vosk")) and cfg.vosk_model_path.exists()

    # --- transcription -----------------------------------------------------
    def _transcribe_faster_whisper(self, audio: np.ndarray) -> RecognitionResult:
        from faster_whisper import WhisperModel
        if self._fw_model is None:
            self._fw_model = WhisperModel(cfg.whisper_size, device="cpu", compute_type="int8")
        model = self._fw_model
        start = time.perf_counter()
        # Use language=None for auto-detection, support multilingual
        language = None if cfg.stt_language.lower() in ("auto", "none") else cfg.stt_language
        segments, info = model.transcribe(
            audio,
            language=language,
            beam_size=5,
            task=getattr(cfg, "whisper_task", "transcribe"),
            vad_filter=False  # We have our own VAD
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        detected_lang = getattr(info, "language", "unknown") if info else cfg.stt_language
        lang_prob = float(getattr(info, "language_probability", 0.0) if info else 0.0)
        logger.debug("Detected language: %s (confidence: %.2f)", detected_lang, lang_prob)
        return RecognitionResult(
            text=text, provider="faster-whisper",
            confidence=lang_prob,
            duration_ms=(time.perf_counter() - start) * 1000,
        )

    @staticmethod
    def _transcribe_google(audio: np.ndarray) -> RecognitionResult:
        import speech_recognition as sr
        data = sr.AudioData(_pcm16(audio), cfg.sample_rate, 2)
        recognizer = sr.Recognizer()
        start = time.perf_counter()
        text = recognizer.recognize_google(data, language=cfg.google_language)
        return RecognitionResult(text=text.strip(), provider="google",
                                 duration_ms=(time.perf_counter() - start) * 1000)

    @staticmethod
    def _transcribe_groq(audio: np.ndarray) -> RecognitionResult:
        """Whisper large-v3 through Groq (fastest cloud STT today)."""
        _dotenv()
        import requests
        key = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_2")
               or os.getenv("GROQ_API_KEY_3"))
        base = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        wav_bytes = _pcm16_wav(audio)
        start = time.perf_counter()
        resp = requests.post(
            f"{base}/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-large-v3-turbo",
                  "language": _groq_lang(cfg.stt_language),
                  "response_format": "json"},
            timeout=60.0,
        )
        resp.raise_for_status()
        text = (resp.json().get("text") or "").strip()
        return RecognitionResult(text=text, provider="groq-whisper",
                                 duration_ms=(time.perf_counter() - start) * 1000)

    @staticmethod
    def _transcribe_vosk(audio: np.ndarray) -> RecognitionResult:
        import json as _json
        from vosk import Model, KaldiRecognizer
        model = Model(str(cfg.vosk_model_path))
        rec = KaldiRecognizer(model, cfg.sample_rate)
        start = time.perf_counter()
        rec.AcceptWaveform(_pcm16(audio))
        result = _json.loads(rec.FinalResult())
        return RecognitionResult(text=result.get("text", "").strip(), provider="vosk",
                                 duration_ms=(time.perf_counter() - start) * 1000)

    # --- public ------------------------------------------------------------
    def providers(self) -> list[str]:
        return [p.name for p in self._chain if p.available()]

    def transcribe(self, audio: np.ndarray, source: str = "mic") -> RecognitionResult:
        """Transcribe a float32 mono sample buffer through the chain."""
        if audio is None or len(audio) < cfg.sample_rate // 4:
            return RecognitionResult(error="Audio too short")
        with self._lock:
            event_bus.publish(SpeechEventType.RECOGNITION_STARTED, payload={"source": source})
            errors = []
            for provider in self._chain:
                try:
                    if not provider.available():
                        errors.append(f"{provider.name}: unavailable")
                        continue
                    result = provider.transcribe(audio)
                    if result.success:
                        event_bus.publish(SpeechEventType.RECOGNITION_FINISHED,
                                          payload={"text": result.text, "provider": result.provider})
                        return result
                    errors.append(f"{provider.name}: empty")
                except Exception as e:
                    errors.append(f"{provider.name}: {e.__class__.__name__}")
                    continue
            event_bus.publish(SpeechEventType.RECOGNITION_FINISHED, payload={"text": "", "error": "|".join(errors)})
            return RecognitionResult(error="; ".join(errors))


def _import(name: str):
    import importlib.util
    return importlib.util.find_spec(name) is not None


recognizer = Recognizer()