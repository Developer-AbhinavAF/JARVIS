"""speech/cache.py — Reusable TTS audio cache.

Key = hash(voice | rate | pitch | sentence). Repeated responses reuse the
cached WAV instead of re-hitting Edge-TTS, and the playback worker must never
delete cached files (only temp files).
"""

from __future__ import annotations

import os
import shutil
import hashlib
import threading
from pathlib import Path
from typing import Optional

from speech.config import cfg
from speech.events import event_bus, SpeechEventType
from speech.logger import get_logger

logger = get_logger("cache")


class AudioCache:
    def __init__(self, cache_dir: Optional[Path] = None, max_files: int = 0) -> None:
        self._dir = Path(cache_dir or cfg.cache_dir)
        self._max_files = max_files or cfg.cache_max_files
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def key(self, sentence: str, voice: str, rate: str, pitch: str, volume: str) -> str:
        raw = f"{voice}|{rate}|{pitch}|{volume}|{sentence}".encode("utf-8")
        return hashlib.sha1(raw).hexdigest()

    def path(self, key: str) -> Path:
        return self._dir / f"{key}.wav"

    def get(self, sentence: str, voice: str, rate: str, pitch: str, volume: str) -> Optional[Path]:
        p = self.path(self.key(sentence, voice, rate, pitch, volume))
        if p.exists() and p.stat().st_size > 100:
            if not self._is_wav(p):
                # Poisoned entry (e.g. MP3 saved as .wav by an older build) — evict.
                try:
                    p.unlink()
                except OSError:
                    pass
                return None
            with self._lock:
                try:
                    os.utime(p)
                except OSError:
                    pass
            return p
        return None

    @staticmethod
    def _is_wav(p: Path) -> bool:
        try:
            with open(p, "rb") as f:
                head = f.read(12)
            return head[:4] == b"RIFF" and head[8:12] == b"WAVE"
        except OSError:
            return False

    def put(self, sentence: str, voice: str, rate: str, pitch: str, volume: str, src: Path) -> Path:
        key = self.key(sentence, voice, rate, pitch, volume)
        dest = self.path(key)
        if dest.exists():
            return dest
        with self._lock:
            shutil.copyfile(src, dest)
            self._evict()
        event_bus.publish(SpeechEventType.SPEECH_CACHED, payload={"key": key, "path": str(dest)})
        return dest

    def _evict(self) -> None:
        files = sorted(self._dir.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
        excess = files[self._max_files:]
        for p in excess:
            try:
                p.unlink()
            except OSError:
                pass

    def clear(self) -> int:
        with self._lock:
            n = 0
            for p in self._dir.glob("*.wav"):
                try:
                    p.unlink()
                    n += 1
                except OSError:
                    pass
            return n


audio_cache = AudioCache()