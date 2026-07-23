import os
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AudioCache:
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            from pathlib import Path
            self.cache_dir = Path(__file__).parent / "cache"
        else:
            from pathlib import Path
            self.cache_dir = Path(cache_dir)
            
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = True
        
        # In-memory mapping of text to filename for exact matches
        self._map = {}
        self._load_map()

    def _load_map(self):
        # We could parse filenames or just load a mapping file
        self.map_file = self.cache_dir / "cache_map.json"
        import json
        if self.map_file.exists():
            try:
                with open(self.map_file, "r", encoding="utf-8") as f:
                    self._map = json.load(f)
            except Exception:
                self._map = {}

    def _save_map(self):
        import json
        try:
            with open(self.map_file, "w", encoding="utf-8") as f:
                json.dump(self._map, f)
        except Exception:
            pass

    def get(self, text: str) -> str:
        if not self.enabled:
            return None
            
        text_key = text.strip().lower()
        if text_key in self._map:
            file_path = self.cache_dir / self._map[text_key]
            if file_path.exists():
                return str(file_path)
        
        # Check standard cache files based on intent/common phrases
        if "good morning" in text_key or "namaste" in text_key or "hello" in text_key:
            return None # We'll cache dynamically
            
        return None

    def put(self, text: str, file_path: str) -> None:
        if not self.enabled:
            return

        import shutil
        import wave
        text_key = text.strip().lower()

        # Validate that the source file is a real WAV
        try:
            with wave.open(file_path, 'rb') as wf:
                if wf.getnframes() == 0:
                    logger.warning("Refusing to cache empty WAV file")
                    return
        except (wave.Error, OSError) as e:
            logger.warning("Refusing to cache invalid WAV file: %s", e)
            return

        import hashlib
        h = hashlib.md5(text_key.encode()).hexdigest()
        cached_file = self.cache_dir / f"{h}.wav"

        try:
            shutil.copy2(file_path, cached_file)
            self._map[text_key] = f"{h}.wav"
            self._save_map()
        except Exception as e:
            logger.error("Failed to cache audio: %s", e)

audio_cache = AudioCache()
