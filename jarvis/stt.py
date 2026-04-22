"""jarvis.stt

Speech-to-text engine for JARVIS.

This module implements a wake-word loop and a query capture method using
SpeechRecognition + PyAudio with the Google Web Speech API.
"""

from __future__ import annotations

import logging

import speech_recognition as sr

from jarvis import config

logger = logging.getLogger(__name__)


class STTEngine:
    """Speech-to-text engine with wake-word detection and query capture."""

    def __init__(self) -> None:
        """Initialize the recognizer, microphone, and perform calibration."""

        self.recognizer = sr.Recognizer()

        # These are the knobs you tune first for reliability.
        self.recognizer.energy_threshold = config.STT_ENERGY_THRESHOLD
        self.recognizer.pause_threshold = config.STT_PAUSE_THRESHOLD
        self.recognizer.dynamic_energy_threshold = True

        try:
            self.microphone = sr.Microphone()
        except Exception:
            # If we cannot acquire a mic, it's better to crash early with a clear log.
            logger.exception("Failed to initialize microphone")
            raise

        self._calibrate()

    def _calibrate(self) -> None:
        """Calibrate the recognizer to ambient noise."""

        try:
            with self.microphone as source:
                # A short calibration avoids delaying startup, but improves accuracy.
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            logger.info("STT calibrated. Final energy_threshold=%s", self.recognizer.energy_threshold)
        except Exception:
            logger.exception("STT calibration failed")

    def _listen_and_transcribe(self, timeout: int, phrase_limit: int) -> str | None:
        """Listen from microphone and transcribe using Google's Web Speech API.

        Returns:
            The recognized text (lowercased/stripped), or None if no usable audio/text.
        """

        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit,
                )
        except sr.WaitTimeoutError:
            return None
        except Exception:
            logger.exception("Unexpected error while listening")
            return None

        try:
            text = self.recognizer.recognize_google(audio)
            return text.strip().lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            # Network/API issue; don't crash the assistant.
            logger.exception("STT request to Google failed")
            return None
        except Exception:
            logger.exception("Unexpected error during transcription")
            return None

    def wait_for_wake_word(self) -> bool:
        """Block until the wake word is detected.

        Returns:
            True once the wake word is heard.
        """

        while True:
            # Short phrase_limit keeps wake-word loop CPU-light.
            text = self._listen_and_transcribe(
                timeout=config.STT_WAKE_TIMEOUT,
                phrase_limit=config.STT_WAKE_PHRASE_LIMIT,
            )
            if not text:
                continue

            if config.WAKE_WORD in text:
                logger.info("Wake word detected")
                return True

    def capture_query(self) -> str | None:
        """Capture a single user query after the wake word.
        
        Uses patient listening - waits for natural speech pause
        to capture full sentences without cutting off.
        """

        # Patient listening settings:
        # - Long timeout (60s) so we don't cut off mid-sentence
        # - No phrase limit to capture full speech
        # - Higher pause threshold for natural speech patterns
        
        original_pause = self.recognizer.pause_threshold
        self.recognizer.pause_threshold = 1.2  # Wait 1.2s of silence before processing
        
        try:
            result = self._listen_and_transcribe(
                timeout=60,  # Very long timeout - silence detection will end earlier
                phrase_limit=None,  # No limit - capture everything until silence
            )
            return result
        finally:
            self.recognizer.pause_threshold = original_pause
