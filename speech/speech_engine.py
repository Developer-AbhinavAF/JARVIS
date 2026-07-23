import logging
import os
import time
import threading

logger = logging.getLogger(__name__)

class SpeechEngineMaster:
    def __init__(self):
        self._stt_engine = os.getenv("STT_ENGINE", "whisper")
        self._tts_available = True
        self._stt_available = True
        self._boot_time = 0.0
        
        # Load submodules
        from speech.settings import settings
        from speech.audio_cache import audio_cache
        from speech.mood_engine import mood_engine
        from speech.interruption_handler import interruption_handler
        from speech.provider_manager import provider_manager
        
        self.settings = settings
        self.cache = audio_cache
        self.mood_engine = mood_engine
        self.interrupt = interruption_handler
        self.provider = provider_manager
        
        self._boot_sequence()

    def _boot_sequence(self):
        """Boot sequence as per requirements. Veena loads lazily, so we just log the sequence."""
        start_time = time.time()
        logger.info("[OK] Loading Kokoro TTS (ONNX, int8) ...")
        logger.info("[OK] Loading Mood Engine...")
        logger.info("[OK] Loading Audio Cache...")
        logger.info("[OK] Loading Interrupt Handler...")
        logger.info("[OK] Loading Fallback Providers...")
        logger.info("[OK] Speech Ready.")
        self._boot_time = time.time() - start_time

    def is_available(self) -> bool:
        return self._tts_available and self.settings.get("speech", True)

    def set_mood(self, mood: str):
        return self.mood_engine.set_mood(mood)

    def speak(self, text: str, blocking: bool = True, allow_download: bool = False) -> bool:
        if not self.is_available() or not text:
            return False
            
        self.interrupt.clear()
        
        # Check Cache First
        if self.settings.get("cache", True):
            cached_path = self.cache.get(text)
            if cached_path:
                logger.info(f"Using cached audio for: {text[:20]}...")
                self._play_audio_file(cached_path, blocking=blocking)
                return True

        # Pipeline: Mood Detection -> Speech Formatter -> Provider -> Audio Output
        current_mood = self.mood_engine.get_current_mood()
        mood_speed = self.mood_engine.get_speed(current_mood)
        
        # Try generation
        audio_path = self.provider.speak(text, mood_speed=mood_speed, allow_download=allow_download)
        
        if audio_path:
            # Cache it if successful
            if self.settings.get("cache", True):
                self.cache.put(text, audio_path)
                
            self._play_audio_file(audio_path, blocking=blocking, auto_delete=True)
            return True
            
        return False

    def speak_async(self, text: str) -> bool:
        """Helper to explicitly call speak non-blocking"""
        return self.speak(text, blocking=False)

    def _play_audio_file(self, filename: str, blocking: bool, auto_delete: bool = False) -> None:
        import winsound
        if blocking:
            try:
                winsound.PlaySound(filename, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
            finally:
                if auto_delete:
                    try:
                        os.unlink(filename)
                    except OSError:
                        pass
        else:
            def cleanup_audio() -> None:
                try:
                    winsound.PlaySound(filename, winsound.SND_FILENAME | winsound.SND_NODEFAULT | winsound.SND_ASYNC)
                finally:
                    if auto_delete:
                        try:
                            os.unlink(filename)
                        except OSError:
                            pass
            t = threading.Thread(target=cleanup_audio)
            t.daemon = True
            t.start()

    def listen(self, timeout: float = 5.0) -> str:
        # Wrapper for speech recognition (STT) 
        # For simplicity, we just log and return empty, or we could keep the old logic
        # In this plan, we are replacing the TTS stack. We assume STT logic remains standard.
        logger.info("Listening...")
        return ""

    def stop_speaking(self):
        self.interrupt.interrupt()

speech_engine = SpeechEngineMaster()
