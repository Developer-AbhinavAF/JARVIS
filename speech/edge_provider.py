"""speech/edge_provider.py — Edge-TTS cloud synthesis with local cache.

Primary: Edge-TTS (en-IN-PrabhatNeural).
Fallback: pyttsx3 (offline SAPI5).
Every successful synthesis is also stored through AudioCache so repeated
responses play instantly from disk.
"""

from __future__ import annotations

import asyncio
import time
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from speech.config import cfg
from speech.cache import audio_cache
from speech.events import event_bus, SpeechEventType
from speech.logger import get_logger

logger = get_logger("tts")


class TTSResult:
    def __init__(self, path: Path, provider: str, cached: bool = False, duration_ms: float = 0.0) -> None:
        self.path = path
        self.provider = provider
        self.cached = cached
        self.duration_ms = duration_ms


class _EdgeRunner:
    """Runs edge-tts (async lib) inside a dedicated thread with its own loop."""

    def __init__(self) -> None:
        self._loop = None
        self._lock = threading.Lock()

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            loop = asyncio.new_event_loop()
            self._loop = None  # reset BEFORE starting the worker thread
            threading.Thread(target=self._run_loop, args=(loop,), daemon=True).start()
            deadline = time.perf_counter() + 3.0
            while self._loop is None and time.perf_counter() < deadline:
                time.sleep(0.01)
        return self._loop

    def _run_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        self._loop = loop
        loop.run_forever()

    def run(self, coro):
        with self._lock:
            future = asyncio.run_coroutine_threadsafe(coro, self._get_loop())
            return future.result(timeout=60.0)


_edge_runner = _EdgeRunner()


def _mp3_to_wav(src: Path, dest: Path) -> bool:
    """Decode an MP3 (edge-tts output) into a real PCM WAV file."""
    try:
        import wave
        import miniaudio
        decoded = miniaudio.decode_file(str(src))
        samples = np.asarray(decoded.samples, dtype=np.int16)
        with wave.open(str(dest), "wb") as wf:
            wf.setnchannels(decoded.nchannels)
            wf.setsampwidth(2)
            wf.setframerate(decoded.sample_rate)
            wf.writeframes(samples.tobytes())
        return dest.exists() and dest.stat().st_size > 100
    except Exception as e:
        logger.warning("MP3->WAV decode failed: %s", e)
        return False


class EdgeTTSProvider:
    def __init__(self, voice: Optional[str] = None,
                 rate: Optional[str] = None,
                 pitch: Optional[str] = None,
                 volume: Optional[str] = None) -> None:
        self.voice = voice or cfg.tts_voice
        self.rate = rate or cfg.tts_rate
        self.pitch = pitch or cfg.tts_pitch
        self.volume = volume or cfg.tts_volume

    def is_available(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    async def _synthesize_edge(self, text: str, dest: Path) -> None:
        import edge_tts
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch,
            volume=self.volume,
        )
        cfg.ensure_dirs()
        mp3 = cfg.tts_temp_dir / f"tts_{time.time_ns()}.mp3"
        try:
            await communicate.save(str(mp3))
            if mp3.exists() and not _mp3_to_wav(mp3, dest):
                raise RuntimeError("MP3->WAV conversion produced no valid audio")
        finally:
            try:
                mp3.unlink()
            except OSError:
                pass

    def synthesize(self, text: str, cached_only: bool = False) -> Optional[TTSResult]:
        """Return a WAV path for `text` (cache-first), or None on total failure."""
        if not text.strip():
            return None

        cached = audio_cache.get(text, self.voice, self.rate, self.pitch, self.volume)
        if cached is not None:
            event_bus.publish(SpeechEventType.SPEECH_GENERATED, payload={"text": text, "cached": True})
            return TTSResult(cached, "cache", cached=True, duration_ms=0.0)
        if cached_only:
            return None

        if self.is_available():
            try:
                cfg.ensure_dirs()
                dest = cfg.tts_temp_dir / f"tts_{time.time_ns()}.wav"
                start = time.perf_counter()
                _edge_runner.run(self._synthesize_edge(text, dest))
                duration = (time.perf_counter() - start) * 1000
                cached_path = audio_cache.put(text, self.voice, self.rate, self.pitch, self.volume, dest)
                try:
                    dest.unlink()
                except OSError:
                    pass
                event_bus.publish(SpeechEventType.SPEECH_GENERATED, payload={"text": text})
                return TTSResult(cached_path, "edge-tts", duration_ms=duration)
            except Exception as e:
                logger.warning("Edge-TTS synthesis failed (%s); trying pyttsx3", e)

        return self._synthesize_pyttsx3(text)

    def _synthesize_pyttsx3(self, text: str) -> Optional[TTSResult]:
        try:
            import pyttsx3
            cfg.ensure_dirs()
            dest = cfg.tts_temp_dir / f"tts_py_{time.time_ns()}.wav"
            engine = pyttsx3.init()
            engine.save_to_file(text, str(dest))
            engine.runAndWait()
            if dest.exists() and dest.stat().st_size > 100:
                cached_path = audio_cache.put(text, self.voice, self.rate, self.pitch, self.volume, dest)
                try:
                    dest.unlink()
                except OSError:
                    pass
                event_bus.publish(SpeechEventType.SPEECH_GENERATED, payload={"text": text})
                return TTSResult(cached_path, "pyttsx3", duration_ms=0.0)
        except Exception as e:
            logger.warning("pyttsx3 synthesis failed: %s", e)
        return None

    def prefetch(self, text: str) -> None:
        """Warm the cache in the background without blocking the caller."""
        def _do() -> None:
            try:
                self.synthesize(text)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()


edge_tts_provider = EdgeTTSProvider()