"""jarvis.advanced_voice

Advanced voice features: VAD, noise cancellation, multiple wake words, speaker ID.
"""

from __future__ import annotations

import collections
import logging
import time
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)

# Try to import advanced libraries
try:
    import webrtcvad
    HAS_WEBRTC_VAD = True
except ImportError:
    HAS_WEBRTC_VAD = False
    logger.warning("webrtcvad not available, using basic VAD")

try:
    import noisereduce
    HAS_NOISE_REDUCE = True
except ImportError:
    HAS_NOISE_REDUCE = False
    logger.warning("noisereduce not available")


class VoiceActivityDetector:
    """Voice Activity Detection with WebRTC VAD or fallback."""
    
    def __init__(self, mode: int = 3) -> None:
        """
        Initialize VAD.
        mode: 0=quality, 1=low_bitrate, 2=aggressive, 3=very_aggressive
        """
        self.mode = mode
        self.vad = None
        
        if HAS_WEBRTC_VAD:
            try:
                self.vad = webrtcvad.Vad(mode)
            except Exception as e:
                logger.error(f"Failed to initialize VAD: {e}")
    
    def is_speech(self, audio_frame: bytes, sample_rate: int = 16000) -> bool:
        """Check if audio frame contains speech."""
        if self.vad and HAS_WEBRTC_VAD:
            try:
                return self.vad.is_speech(audio_frame, sample_rate)
            except Exception:
                pass
        
        # Fallback: simple energy-based detection
        audio_data = np.frombuffer(audio_frame, dtype=np.int16)
        energy = np.sqrt(np.mean(audio_data ** 2))
        return energy > 500  # Threshold
    
    def detect_speech_segment(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30
    ) -> list[tuple[float, float]]:
        """Detect speech segments in audio."""
        frame_size = int(sample_rate * frame_duration_ms / 1000)
        frames = [audio_data[i:i + frame_size * 2] for i in range(0, len(audio_data), frame_size * 2)]
        
        segments = []
        start_time = None
        
        for i, frame in enumerate(frames):
            if len(frame) < frame_size * 2:
                break
            
            is_speech = self.is_speech(frame, sample_rate)
            timestamp = i * frame_duration_ms / 1000
            
            if is_speech and start_time is None:
                start_time = timestamp
            elif not is_speech and start_time is not None:
                segments.append((start_time, timestamp))
                start_time = None
        
        if start_time is not None:
            segments.append((start_time, len(frames) * frame_duration_ms / 1000))
        
        return segments


class NoiseReducer:
    """Noise reduction using spectral gating."""
    
    def __init__(self) -> None:
        self.noise_profile: np.ndarray | None = None
    
    def learn_noise_profile(self, noise_sample: np.ndarray) -> None:
        """Learn noise profile from silence sample."""
        if HAS_NOISE_REDUCE:
            self.noise_profile = noise_sample
        else:
            # Fallback: store mean for simple subtraction
            self.noise_profile = np.mean(noise_sample)
    
    def reduce_noise(self, audio: np.ndarray) -> np.ndarray:
        """Reduce noise from audio."""
        if HAS_NOISE_REDUCE and self.noise_profile is not None:
            try:
                return noisereduce.reduce_noise(y=audio, y_noise=self.noise_profile)
            except Exception as e:
                logger.error(f"Noise reduction failed: {e}")
        
        # Fallback: simple high-pass filter
        if len(audio) > 1:
            # Simple DC removal
            return audio - np.mean(audio)
        
        return audio


class MultiWakeWord:
    """Support multiple wake words with different actions."""
    
    def __init__(self) -> None:
        self.wake_words: dict[str, dict] = {
            "hello": {"action": "default", "priority": 1},
            "jarvis": {"action": "default", "priority": 1},
            "hey computer": {"action": "default", "priority": 2},
            "wake up": {"action": "wake", "priority": 1},
            "emergency": {"action": "emergency", "priority": 10},
        }
        self.current_priority = 1
    
    def add_wake_word(self, word: str, action: str = "default", priority: int = 1) -> None:
        """Add a custom wake word."""
        self.wake_words[word.lower()] = {"action": action, "priority": priority}
    
    def remove_wake_word(self, word: str) -> None:
        """Remove a wake word."""
        if word.lower() in self.wake_words:
            del self.wake_words[word.lower()]
    
    def check_wake_word(self, text: str) -> tuple[bool, str, str]:
        """
        Check if text contains a wake word.
        Returns: (detected, wake_word, action)
        """
        text_lower = text.lower().strip()
        
        # Sort by priority (highest first)
        sorted_words = sorted(
            self.wake_words.items(),
            key=lambda x: x[1]["priority"],
            reverse=True
        )
        
        for word, config in sorted_words:
            if word in text_lower:
                return True, word, config["action"]
        
        return False, "", ""
    
    def list_wake_words(self) -> list[str]:
        """List all registered wake words."""
        return list(self.wake_words.keys())


class SpeakerIdentifier:
    """Simple speaker identification based on voice characteristics."""
    
    def __init__(self) -> None:
        self.speakers: dict[str, dict] = {}
        self.current_speaker: str | None = None
        self.voice_samples: dict[str, list] = collections.defaultdict(list)
    
    def extract_features(self, audio: np.ndarray) -> dict:
        """Extract voice features from audio."""
        # Simple features: pitch, energy, zero crossing rate
        features = {
            "mean": float(np.mean(audio)),
            "std": float(np.std(audio)),
            "energy": float(np.sum(audio ** 2)),
            "zero_crossings": int(np.sum(np.diff(np.signbit(audio)))),
        }
        return features
    
    def register_speaker(self, name: str, sample_audio: np.ndarray) -> bool:
        """Register a new speaker with voice sample."""
        try:
            features = self.extract_features(sample_audio)
            self.speakers[name] = features
            self.voice_samples[name].append(sample_audio)
            logger.info(f"Registered speaker: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register speaker: {e}")
            return False
    
    def identify_speaker(self, audio: np.ndarray) -> tuple[str | None, float]:
        """
        Identify speaker from audio.
        Returns: (speaker_name, confidence)
        """
        if not self.speakers:
            return None, 0.0
        
        try:
            features = self.extract_features(audio)
            
            # Simple distance-based matching
            best_match = None
            best_score = float('inf')
            
            for name, ref_features in self.speakers.items():
                score = sum(abs(features[k] - ref_features[k]) for k in features)
                if score < best_score:
                    best_score = score
                    best_match = name
            
            # Convert score to confidence (lower score = higher confidence)
            confidence = max(0, 1 - best_score / 1000)
            
            if confidence > 0.7:
                self.current_speaker = best_match
                return best_match, confidence
            
            return None, confidence
            
        except Exception as e:
            logger.error(f"Speaker identification failed: {e}")
            return None, 0.0
    
    def get_current_speaker(self) -> str | None:
        """Get currently identified speaker."""
        return self.current_speaker
    
    def list_speakers(self) -> list[str]:
        """List all registered speakers."""
        return list(self.speakers.keys())


class VoiceRecognitionTrainer:
    """Train voice recognition for accent adaptation."""
    
    def __init__(self) -> None:
        self.accent_samples: dict[str, list] = collections.defaultdict(list)
        self.common_phrases: list[str] = [
            "hello", "open", "close", "play", "stop", "search", "what is", "how to"
        ]
    
    def add_sample(self, text: str, audio: np.ndarray, accent: str = "general") -> None:
        """Add a voice sample for training."""
        self.accent_samples[accent].append({"text": text, "audio": audio})
    
    def get_training_suggestions(self) -> list[str]:
        """Get list of phrases to say for better training."""
        return self.common_phrases.copy()
    
    def estimate_accuracy(self) -> dict[str, float]:
        """Estimate recognition accuracy based on samples."""
        accuracy = {}
        for accent, samples in self.accent_samples.items():
            # More samples = potentially better accuracy
            count_factor = min(1.0, len(samples) / 50)  # Cap at 50 samples
            accuracy[accent] = 0.5 + (count_factor * 0.4)  # Base 50%, up to 90%
        return accuracy


class AdvancedSTT:
    """Advanced speech-to-text with all features."""
    
    def __init__(self) -> None:
        self.vad = VoiceActivityDetector()
        self.noise_reducer = NoiseReducer()
        self.multi_wake = MultiWakeWord()
        self.speaker_id = SpeakerIdentifier()
        self.trainer = VoiceRecognitionTrainer()
        
        self.is_listening = False
        self.noise_learning_frames = 0
    
    def learn_ambient_noise(self, audio: np.ndarray, duration: float = 2.0) -> None:
        """Learn ambient noise profile."""
        self.noise_reducer.learn_noise_profile(audio)
        logger.info("Learned ambient noise profile")
    
    def process_audio(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> dict:
        """
        Process audio with all advanced features.
        Returns dict with detected speech, speaker, etc.
        """
        result = {
            "has_speech": False,
            "speaker": None,
            "speaker_confidence": 0.0,
            "wake_word_detected": False,
            "wake_word": None,
            "action": None,
            "processed_audio": audio,
        }
        
        # 1. Noise reduction
        cleaned_audio = self.noise_reducer.reduce_noise(audio)
        result["processed_audio"] = cleaned_audio
        
        # 2. VAD
        audio_bytes = (cleaned_audio * 32767).astype(np.int16).tobytes()
        result["has_speech"] = self.vad.is_speech(audio_bytes, sample_rate)
        
        if not result["has_speech"]:
            return result
        
        # 3. Speaker identification
        speaker, confidence = self.speaker_id.identify_speaker(cleaned_audio)
        result["speaker"] = speaker
        result["speaker_confidence"] = confidence
        
        return result
    
    def check_wake_word(self, text: str) -> tuple[bool, str, str]:
        """Check for wake words in text."""
        return self.multi_wake.check_wake_word(text)
    
    def add_custom_wake_word(self, word: str, action: str = "default") -> None:
        """Add a custom wake word."""
        self.multi_wake.add_wake_word(word, action)
    
    def register_speaker(self, name: str, sample: np.ndarray) -> bool:
        """Register a speaker."""
        return self.speaker_id.register_speaker(name, sample)


# Global advanced STT instance
advanced_voice = AdvancedSTT()
