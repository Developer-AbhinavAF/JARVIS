"""DEPRECATED: interface/speech_new.py — Legacy speech interface.

This module is DEPRECATED and replaced by the production-grade speech engine
in speech/speech_engine.py, accessible via interface/speech.py.

New location:
- Use: from interface.speech import speech_engine
- Or: from speech.speech_engine import SpeechEngine, speech_engine

The new speech/ implementation provides:
- Event-driven architecture
- Always-on microphone (no fixed timers)
- Silero VAD with smart endpoint detection
- faster-whisper STT with fallback chain
- Instant barge-in interrupt handling
- Streaming LLM integration
- Edge-TTS with cache
- Comprehensive test suite

Migration guide:
1. Update imports: from interface.speech import speech_engine
2. Public API is compatible: is_available(), listen(), speak(), etc.
3. New features: speak_stream(), speak_from_core_stream()

This file is kept for backward compatibility only and will be removed
in a future version.
"""

from __future__ import annotations

import os
import sys
import time
import logging
import asyncio
from typing import Optional, Callable
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.jarvis_core import get_core

logger = logging.getLogger(__name__)


@dataclass
class SpeechConfig:
    """Speech configuration."""
    stt_engine: str = " pocketsphinx"  # pocketsphinx, whisper, google
    tts_engine: str = "espeak"  # espeak, gtts, azure, aws
    stt_language: str = "en-US"
    tts_language: str = "en"
    tts_voice: str = "default"
    input_device: Optional[str] = None
    output_device: Optional[str] = None


class STTEngine:
    """Speech-to-Text engine."""
    
    def __init__(self, config: SpeechConfig):
        self.config = config
        self._available = False
        self._engine = None
        
        # Try to initialize the engine
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize STT engine."""
        try:
            if self.config.stt_engine == "whisper":
                self._init_whisper()
            elif self.config.stt_engine == "google":
                self._init_google()
            else:
                self._init_pocketsphinx()
        except Exception as e:
            logger.warning(f"Failed to initialize STT engine: {e}")
    
    def _init_whisper(self) -> None:
        """Initialize OpenAI Whisper."""
        try:
            import whisper
            self._engine = whisper.load_model("base")
            self._available = True
            logger.info("Whisper STT initialized")
        except ImportError:
            logger.warning("Whisper not available, install with: pip install openai-whisper")
    
    def _init_google(self) -> None:
        """Initialize Google Speech Recognition."""
        try:
            import speech_recognition as sr
            self._engine = sr.Recognizer()
            self._available = True
            logger.info("Google STT initialized")
        except ImportError:
            logger.warning("Google Speech Recognition not available, install with: pip install SpeechRecognition")
    
    def _init_pocketsphinx(self) -> None:
        """Initialize PocketSphinx."""
        try:
            import speech_recognition as sr
            self._engine = sr.Recognizer()
            self._available = True
            logger.info("PocketSphinx STT initialized")
        except ImportError:
            logger.warning("PocketSphinx not available, install with: pip install SpeechRecognition pocketsphinx")
    
    def is_available(self) -> bool:
        """Check if STT is available."""
        return self._available
    
    def listen(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> str:
        """Listen for speech input."""
        if not self._available:
            logger.warning("STT not available")
            return ""
        
        try:
            import speech_recognition as sr
            
            with sr.Microphone(device_index=self._get_device_index()) as source:
                # Adjust for ambient noise
                self._engine.adjust_for_ambient_noise(source, duration=0.5)
                
                logger.info("Listening...")
                try:
                    audio = self._engine.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=phrase_time_limit
                    )
                    
                    logger.info("Processing speech...")
                    
                    # Try different recognition engines
                    if self.config.stt_engine == "whisper":
                        return self._recognize_whisper(audio)
                    elif self.config.stt_engine == "google":
                        return self._recognize_google(audio)
                    else:
                        return self._recognize_sphinx(audio)
                        
                except sr.WaitTimeoutError:
                    logger.warning("Listening timeout")
                    return ""
                except sr.UnknownValueError:
                    logger.warning("Could not understand audio")
                    return ""
                    
        except Exception as e:
            logger.error(f"STT error: {e}")
            return ""
    
    def _recognize_whisper(self, audio) -> str:
        """Recognize using Whisper."""
        import speech_recognition as sr
        
        # Convert audio to raw data
        raw_data = audio.get_raw_data(convert_rate=16000)
        
        # Use whisper directly
        import whisper
        import io
        import numpy as np
        
        # Convert to numpy array
        audio_array = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Transcribe
        result = self._engine.transcribe(audio_array, language=self.config.stt_language[:2])
        return result["text"].strip()
    
    def _recognize_google(self, audio) -> str:
        """Recognize using Google Speech Recognition."""
        import speech_recognition as sr
        return self._engine.recognize_google(audio, language=self.config.stt_language)
    
    def _recognize_sphinx(self, audio) -> str:
        """Recognize using PocketSphinx."""
        import speech_recognition as sr
        return self._engine.recognize_sphinx(audio, language=self.config.stt_language)
    
    def _get_device_index(self) -> Optional[int]:
        """Get microphone device index."""
        if self.config.input_device:
            try:
                import speech_recognition as sr
                mic_list = sr.Microphone.list_microphone_names()
                for i, name in enumerate(mic_list):
                    if self.config.input_device in name:
                        return i
            except Exception:
                pass
        return None


class TTSEngine:
    """Text-to-Speech engine."""
    
    def __init__(self, config: SpeechConfig):
        self.config = config
        self._available = False
        self._engine = None
        
        # Try to initialize the engine
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize TTS engine."""
        try:
            if self.config.tts_engine == "gtts":
                self._init_gtts()
            elif self.config.tts_engine == "azure":
                self._init_azure()
            elif self.config.tts_engine == "aws":
                self._init_aws()
            else:
                self._init_espeak()
        except Exception as e:
            logger.warning(f"Failed to initialize TTS engine: {e}")
    
    def _init_espeak(self) -> None:
        """Initialize eSpeak."""
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._available = True
            logger.info("eSpeak TTS initialized")
        except ImportError:
            logger.warning("pyttsx3 not available, install with: pip install pyttsx3")
    
    def _init_gtts(self) -> None:
        """Initialize Google TTS."""
        try:
            from gtts import gTTS
            self._engine = gTTS
            self._available = True
            logger.info("Google TTS initialized")
        except ImportError:
            logger.warning("gTTS not available, install with: pip install gTTS")
    
    def _init_azure(self) -> None:
        """Initialize Azure TTS."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            self._engine = speechsdk
            self._available = True
            logger.info("Azure TTS initialized")
        except ImportError:
            logger.warning("Azure TTS not available, install with: pip install azure-cognitiveservices-speech")
    
    def _init_aws(self) -> None:
        """Initialize AWS Polly."""
        try:
            import boto3
            self._engine = boto3.client('polly')
            self._available = True
            logger.info("AWS Polly TTS initialized")
        except ImportError:
            logger.warning("AWS Polly not available, install with: pip install boto3")
    
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self._available
    
    def speak(self, text: str, blocking: bool = True) -> bool:
        """Speak text."""
        if not self._available:
            logger.warning("TTS not available")
            return False
        
        if not text:
            return False
        
        try:
            if self.config.tts_engine == "gtts":
                return self._speak_gtts(text, blocking)
            elif self.config.tts_engine == "azure":
                return self._speak_azure(text, blocking)
            elif self.config.tts_engine == "aws":
                return self._speak_aws(text, blocking)
            else:
                return self._speak_espeak(text, blocking)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False
    
    def _speak_espeak(self, text: str, blocking: bool) -> bool:
        """Speak using eSpeak."""
        self._engine.say(text)
        if blocking:
            self._engine.runAndWait()
        return True
    
    def _speak_gtts(self, text: str, blocking: bool) -> bool:
        """Speak using Google TTS."""
        import pygame
        import tempfile
        import os
        
        # Generate speech
        tts = self._engine(text=text, lang=self.config.tts_language)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            temp_file = f.name
            tts.save(f.name)
        
        try:
            # Play audio
            pygame.mixer.init()
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            if blocking:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            
            return True
        finally:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def _speak_azure(self, text: str, blocking: bool) -> bool:
        """Speak using Azure TTS."""
        speech_config = self._engine.speech.SpeechConfig(
            subscription=os.getenv("AZURE_SPEECH_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION")
        )
        audio_config = self._engine.audio.AudioOutputConfig(use_default_speaker=True)
        
        synthesizer = self._engine.speech.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        result = synthesizer.speak_text_async(text).get()
        
        if blocking:
            import time
            time.sleep(len(text) * 0.1)  # Approximate duration
        
        return result.reason == self._engine.speech.ResultReason.SynthesizingAudioCompleted
    
    def _speak_aws(self, text: str, blocking: bool) -> bool:
        """Speak using AWS Polly."""
        import pygame
        import tempfile
        import os
        
        # Generate speech
        response = self._engine.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=self.config.tts_voice or "Joanna"
        )
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            temp_file = f.name
            f.write(response['AudioStream'].read())
        
        try:
            # Play audio
            pygame.mixer.init()
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            if blocking:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            
            return True
        finally:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def stop_speaking(self) -> None:
        """Stop current speech."""
        if self.config.tts_engine == "espeak" and self._available:
            self._engine.stop()


class SpeechInterface:
    """Complete speech interface using Jarvis Core.
    
    This interface has NO logic. All intelligence is delegated to Jarvis Core.
    Only audio I/O is done here.
    """
    
    def __init__(self, config: Optional[SpeechConfig] = None):
        self.config = config or SpeechConfig()
        self._core = get_core()
        self._stt = STTEngine(self.config)
        self._tts = TTSEngine(self.config)
        self._running = False
        
        logger.info("Speech interface initialized")
    
    def is_available(self) -> dict:
        """Check availability of speech components."""
        return {
            "stt": self._stt.is_available(),
            "tts": self._tts.is_available(),
            "stt_engine": self.config.stt_engine,
            "tts_engine": self.config.tts_engine
        }
    
    async def listen(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> str:
        """Listen for speech input (async wrapper)."""
        # Run STT in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._stt.listen,
            timeout,
            phrase_time_limit
        )
    
    async def speak(self, text: str, blocking: bool = True) -> bool:
        """Speak text (async wrapper)."""
        # Run TTS in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._tts.speak,
            text,
            blocking
        )
    
    def stop_speaking(self) -> None:
        """Stop current speech."""
        self._tts.stop_speaking()
    
    async def process_speech(self, timeout: float = 5.0) -> str:
        """Complete speech processing pipeline.
        
        1. Listen to speech
        2. Process through Jarvis Core
        3. Speak response
        """
        # Listen
        user_input = await self.listen(timeout=timeout)
        
        if not user_input:
            logger.warning("No speech detected")
            return ""
        
        logger.info(f"User said: {user_input}")
        
        # Process through core
        response = await self._core.process(user_input)
        
        if response.success and response.text:
            logger.info(f"Jarvis response: {response.text}")
            
            # Speak response
            await self.speak(response.text)
            
            return response.text
        else:
            logger.error(f"Processing failed: {response.error}")
            return ""
    
    async def run(self, on_response: Optional[Callable[[str], None]] = None) -> None:
        """Main speech interaction loop."""
        if not self._stt.is_available():
            logger.error("STT not available, cannot run speech interface")
            return
        
        if not self._tts.is_available():
            logger.warning("TTS not available, will print responses instead")
        
        self._running = True
        logger.info("Starting speech interface...")
        
        # Boot core if not already booted
        if not self._core._boot_complete:
            self._core.boot()
        
        try:
            while self._running:
                try:
                    # Process speech
                    response_text = await self.process_speech()
                    
                    if response_text and on_response:
                        on_response(response_text)
                    
                    # Small delay between interactions
                    await asyncio.sleep(0.5)
                    
                except KeyboardInterrupt:
                    logger.info("Interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Speech processing error: {e}")
                    await asyncio.sleep(1)
                    
        finally:
            self._running = False
            await self._core.shutdown()
            logger.info("Speech interface stopped")
    
    def stop(self) -> None:
        """Stop speech interface."""
        self._running = False
        self.stop_speaking()


# Global speech interface instance
_global_speech: Optional[SpeechInterface] = None


def get_speech(config: Optional[SpeechConfig] = None) -> SpeechInterface:
    """Get global speech interface instance."""
    global _global_speech
    if _global_speech is None:
        _global_speech = SpeechInterface(config)
    return _global_speech


def set_speech(speech: SpeechInterface) -> None:
    """Set global speech interface instance."""
    global _global_speech
    _global_speech = speech


# For backward compatibility with old interface
speech_engine = SpeechInterface()
