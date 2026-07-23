import logging
import os
import tempfile
import threading

from speech.generate_agi_audio import generate_agi_audio, _lazy_load

logger = logging.getLogger(__name__)


class ProviderManager:
    def __init__(self):
        self._kokoro_available = None

    def speak(
        self,
        text: str,
        mood_speed: float = 1.0,
        allow_download: bool = False,
        output_path: str | None = None,
    ) -> str | None:
        if output_path is None:
            output_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

        if self._kokoro_available is None:
            self._kokoro_available = _lazy_load()

        if self._kokoro_available:
            logger.info("Generating AGI audio via Kokoro...")
            result = generate_agi_audio(text, output_path)
            if result:
                return result

        logger.info("Kokoro unavailable, trying ElevenLabs...")
        elevenlabs_path = self._try_elevenlabs(text, output_path)
        if elevenlabs_path:
            return elevenlabs_path

        logger.info("Falling back to pyttsx3...")
        self._try_pyttsx3(text)
        return None

    def _try_elevenlabs(self, text: str, output_path: str) -> str | None:
        try:
            import httpx

            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                return None

            voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
            resp = httpx.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={"text": text, "model_id": "eleven_multilingual_v2"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                return None

            import subprocess

            mp3_path = tempfile.mktemp(suffix=".mp3")
            try:
                with open(mp3_path, "wb") as f:
                    f.write(resp.content)
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        mp3_path,
                        "-acodec",
                        "pcm_s16le",
                        "-ar",
                        "24000",
                        "-ac",
                        "1",
                        output_path,
                    ],
                    capture_output=True,
                    timeout=30,
                )
                return output_path
            finally:
                try:
                    os.unlink(mp3_path)
                except OSError:
                    pass
        except Exception as e:
            logger.debug("ElevenLabs fallback failed: %s", e)
        return None

    def _try_pyttsx3(self, text: str) -> bool:
        try:
            import pyttsx3

            tts = pyttsx3.init()
            t = threading.Thread(target=lambda: (tts.say(text), tts.runAndWait()))
            t.daemon = True
            t.start()
            return True
        except Exception as e:
            logger.debug("pyttsx3 fallback failed: %s", e)
        return False


provider_manager = ProviderManager()
