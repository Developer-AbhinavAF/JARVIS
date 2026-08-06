"""DEPRECATED: core/speech_engine.py — Legacy speech engine.

This module is DEPRECATED and replaced by the production-grade speech engine
in speech/speech_engine.py.

New location:
- Use: from speech.speech_engine import SpeechEngine, speech_engine
- Or: from interface.speech import speech_engine

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
1. Update imports: from speech.speech_engine import speech_engine
2. Public API is compatible: is_available(), listen(), speak(), etc.
3. New features: speak_stream(), speak_from_core_stream()

This file is kept for backward compatibility only and will be removed
in a future version.
"""

from __future__ import annotations

import os
import json
import logging
import asyncio
import threading
import queue
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class TTSEngine(Enum):
    """TTS engine options."""
    LOCAL = "local"
    ELEVENLABS = "elevenlabs"
    PYTTSX3 = "pyttsx3"


class STTEngine(Enum):
    """STT engine options."""
    LOCAL_WHISPER = "local_whisper"
    GROQ = "groq"
    OPENAI = "openai"
    GOOGLE = "google"


class SpeechMode(Enum):
    """Speech mode options."""
    TEXT = "text"
    SPEECH = "speech"


@dataclass
class SpeechConfig:
    """Speech configuration."""
    tts_engine: TTSEngine = TTSEngine.LOCAL
    stt_engine: STTEngine = STTEngine.LOCAL_WHISPER
    speech_mode: SpeechMode = SpeechMode.TEXT
    voice: str = "default"
    speed: float = 1.0
    pitch: float = 1.0
    language: str = "en-US"
    continuous_listening: bool = False
    vad_sensitivity: float = 0.5
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""


@dataclass
class TTSResult:
    """Result of TTS operation."""
    success: bool = False
    audio_file: str = ""
    duration: float = 0.0
    engine: str = ""
    error: str = ""


@dataclass
class STTResult:
    """Result of STT operation."""
    success: bool = False
    text: str = ""
    confidence: float = 0.0
    language: str = ""
    engine: str = ""
    processing_time: float = 0.0
    error: str = ""


class TTSEngineBase:
    """Base class for TTS engines."""
    
    def speak(self, text: str, config: SpeechConfig) -> TTSResult:
        """Speak text synchronously."""
        raise NotImplementedError
    
    async def speak_async(self, text: str, config: SpeechConfig) -> TTSResult:
        """Speak text asynchronously."""
        return self.speak(text, config)
    
    def speak_to_file(self, text: str, output_file: str, config: SpeechConfig) -> TTSResult:
        """Speak text to file."""
        raise NotImplementedError


class LocalTTSEngine(TTSEngineBase):
    """Local TTS engine using OS capabilities."""
    
    def __init__(self):
        self._platform = os.name
    
    def speak(self, text: str, config: SpeechConfig) -> TTSResult:
        """Speak text using local TTS."""
        try:
            if self._platform == "nt":  # Windows
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(text)
                return TTSResult(success=True, engine="local_sapi5")
            
            elif self._platform == "posix":
                # Check for macOS
                if os.uname().sysname == "Darwin":
                    os.system(f'say "{text}"')
                    return TTSResult(success=True, engine="local_nsspeech")
                else:  # Linux
                    try:
                        os.system(f'espeak "{text}"')
                        return TTSResult(success=True, engine="local_espeak")
                    except Exception:
                        # Fallback to pyttsx3
                        import pyttsx3
                        engine = pyttsx3.init()
                        engine.say(text)
                        engine.runAndWait()
                        return TTSResult(success=True, engine="pyttsx3_fallback")
            
            return TTSResult(success=False, error="Unsupported platform")
            
        except ImportError:
            # Fallback to pyttsx3
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
                return TTSResult(success=True, engine="pyttsx3_fallback")
            except Exception as e:
                return TTSResult(success=False, error=str(e))
        except Exception as e:
            return TTSResult(success=False, error=str(e))


class ElevenLabsTTSEngine(TTSEngineBase):
    """ElevenLabs TTS engine (API-based)."""
    
    def __init__(self, api_key: str = "", voice_id: str = ""):
        self._api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
        self._voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "")
        self._client = None
        
        if self._api_key:
            try:
                import httpx
                self._client = httpx.Client(timeout=30.0)
            except ImportError:
                logger.warning("httpx not available for ElevenLabs")
    
    def speak(self, text: str, config: SpeechConfig) -> TTSResult:
        """Speak text using ElevenLabs."""
        if not self._client or not self._api_key:
            return TTSResult(success=False, error="ElevenLabs not configured")
        
        try:
            response = self._client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}",
                headers={"xi-api-key": self._api_key, "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_monolingual_v1"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                # Save to temporary file and play
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(response.content)
                    temp_file = f.name
                
                # Play the file
                if os.name == "nt":
                    os.startfile(temp_file)
                elif os.name == "posix":
                    if os.uname().sysname == "Darwin":
                        os.system(f"afplay {temp_file}")
                    else:
                        os.system(f"mpg123 {temp_file}")
                
                return TTSResult(success=True, audio_file=temp_file, engine="elevenlabs")
            else:
                return TTSResult(success=False, error=f"ElevenLabs API error: {response.status_code}")
                
        except Exception as e:
            return TTSResult(success=False, error=str(e))


class Pyttsx3TTSEngine(TTSEngineBase):
    """pyttsx3 TTS engine (fallback)."""
    
    def speak(self, text: str, config: SpeechConfig) -> TTSResult:
        """Speak text using pyttsx3."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            
            # Set properties
            if config.speed != 1.0:
                engine.setProperty('rate', engine.getProperty('rate') * config.speed)
            
            engine.say(text)
            engine.runAndWait()
            
            return TTSResult(success=True, engine="pyttsx3")
            
        except Exception as e:
            return TTSResult(success=False, error=str(e))


class STTEngineBase:
    """Base class for STT engines."""
    
    def transcribe(self, audio_file: str, config: SpeechConfig) -> STTResult:
        """Transcribe audio file."""
        raise NotImplementedError
    
    async def transcribe_async(self, audio_file: str, config: SpeechConfig) -> STTResult:
        """Transcribe audio file asynchronously."""
        return self.transcribe(audio_file, config)


class LocalWhisperSTTEngine(STTEngineBase):
    """Local Whisper STT engine."""
    
    def __init__(self):
        self._model = None
        self._loaded = False
    
    def _load_model(self):
        """Load Whisper model."""
        if self._loaded:
            return
        
        try:
            import whisper
            self._model = whisper.load_model("base")
            self._loaded = True
            logger.info("Whisper model loaded")
        except ImportError:
            logger.warning("Whisper not available")
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
    
    def transcribe(self, audio_file: str, config: SpeechConfig) -> STTResult:
        """Transcribe using local Whisper."""
        try:
            self._load_model()
            
            if not self._model:
                return STTResult(success=False, error="Whisper model not available")
            
            result = self._model.transcribe(audio_file)
            text = result["text"].strip()
            
            return STTResult(
                success=True,
                text=text,
                confidence=0.9,  # Whisper doesn't provide confidence
                language=result.get("language", "en"),
                engine="local_whisper"
            )
            
        except Exception as e:
            return STTResult(success=False, error=str(e))


class GroqSTTEngine(STTEngineBase):
    """Groq STT engine (uses Whisper via Groq API)."""
    
    def __init__(self):
        self._api_key = os.getenv("GROQ_API_KEY", "")
        self._client = None
        
        if self._api_key:
            try:
                import httpx
                self._client = httpx.Client(timeout=30.0)
            except ImportError:
                logger.warning("httpx not available for Groq STT")
    
    def transcribe(self, audio_file: str, config: SpeechConfig) -> STTResult:
        """Transcribe using Groq API."""
        if not self._client or not self._api_key:
            return STTResult(success=False, error="Groq not configured")
        
        try:
            # Note: Groq doesn't have a dedicated STT API, this is a placeholder
            # In production, you'd use a different provider or implement audio transcription
            return STTResult(success=False, error="Groq STT not implemented")
                
        except Exception as e:
            return STTResult(success=False, error=str(e))


class SpeechEngine:
    """Main speech engine managing TTS and STT."""
    
    def __init__(self, config: SpeechConfig = None):
        self._config = config or SpeechConfig()
        self._tts_engines: Dict[TTSEngine, TTSEngineBase] = {}
        self._stt_engines: Dict[STTEngine, STTEngineBase] = {}
        self._speaking = False
        self._listening = False
        self._audio_queue = queue.Queue()
        self._init_engines()
    
    def _init_engines(self) -> None:
        """Initialize TTS and STT engines."""
        # Initialize TTS engines
        self._tts_engines[TTSEngine.LOCAL] = LocalTTSEngine()
        self._tts_engines[TTSEngine.ELEVENLABS] = ElevenLabsTTSEngine(
            self._config.elevenlabs_api_key,
            self._config.elevenlabs_voice_id
        )
        self._tts_engines[TTSEngine.PYTTSX3] = Pyttsx3TTSEngine()
        
        # Initialize STT engines
        self._stt_engines[STTEngine.LOCAL_WHISPER] = LocalWhisperSTTEngine()
        self._stt_engines[STTEngine.GROQ] = GroqSTTEngine()
        
        logger.info("Speech engines initialized")
    
    def speak(self, text: str, blocking: bool = True) -> TTSResult:
        """Speak text using configured TTS engine."""
        if not text or not text.strip():
            return TTSResult(success=False, error="No text to speak")
        
        self._speaking = True
        
        try:
            # Try engines in priority order
            for engine_type in [TTSEngine.LOCAL, TTSEngine.ELEVENLABS, TTSEngine.PYTTSX3]:
                if engine_type not in self._tts_engines:
                    continue
                
                engine = self._tts_engines[engine_type]
                result = engine.speak(text, self._config)
                
                if result.success:
                    logger.info(f"Spoke using {engine_type.value}")
                    return result
                else:
                    logger.debug(f"{engine_type.value} failed: {result.error}")
            
            # All engines failed
            return TTSResult(success=False, error="All TTS engines failed")
            
        except Exception as e:
            logger.error(f"Speech failed: {e}")
            return TTSResult(success=False, error=str(e))
        finally:
            self._speaking = False
    
    async def speak_async(self, text: str) -> TTSResult:
        """Speak text asynchronously."""
        return await asyncio.to_thread(self.speak, text, blocking=False)
    
    def stop_speaking(self) -> None:
        """Stop current speech."""
        self._speaking = False
        # Implementation depends on the TTS engine
        logger.info("Speech stopped")
    
    def transcribe(self, audio_file: str) -> STTResult:
        """Transcribe audio file using configured STT engine."""
        if not os.path.exists(audio_file):
            return STTResult(success=False, error="Audio file not found")
        
        try:
            # Try engines in priority order
            for engine_type in [STTEngine.LOCAL_WHISPER, STTEngine.GROQ]:
                if engine_type not in self._stt_engines:
                    continue
                
                engine = self._stt_engines[engine_type]
                result = engine.transcribe(audio_file, self._config)
                
                if result.success:
                    logger.info(f"Transcribed using {engine_type.value}")
                    return result
                else:
                    logger.debug(f"{engine_type.value} failed: {result.error}")
            
            return STTResult(success=False, error="All STT engines failed")
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return STTResult(success=False, error=str(e))
    
    async def listen_continuous(self, callback: callable) -> None:
        """Continuous listening with VAD (simplified)."""
        self._listening = True
        
        while self._listening:
            try:
                # In production, implement proper VAD and continuous recording
                # This is a simplified version
                await asyncio.sleep(1)
                
                # Simulate audio input
                # In production, this would capture from microphone
                # and process through VAD
                
            except Exception as e:
                logger.error(f"Continuous listening error: {e}")
                break
    
    def stop_listening(self) -> None:
        """Stop continuous listening."""
        self._listening = False
        logger.info("Listening stopped")
    
    def set_config(self, config: SpeechConfig) -> None:
        """Update speech configuration."""
        self._config = config
        logger.info("Speech configuration updated")
    
    def get_config(self) -> SpeechConfig:
        """Get current speech configuration."""
        return self._config
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._speaking
    
    def is_listening(self) -> bool:
        """Check if currently listening."""
        return self._listening


# Global speech engine instance
speech_engine = SpeechEngine()