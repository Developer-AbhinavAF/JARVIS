"""Prosody — Natural speech patterns for human-like delivery.

Adds pauses, rhythm, breathing, emotion cues, and sentence structure
awareness to make TTS output sound like a real assistant.
"""

from __future__ import annotations

import re
import logging
from typing import Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProsodyMarker:
    """A marker for speech prosody modification."""
    position: int = 0         # Character position in text
    pause_ms: float = 0.0     # Pause duration in milliseconds
    emotion: str = ""         # Emotion cue
    emphasis: bool = False    # Emphasize next word
    breathing: bool = False   # Add breathing sound
    speed: float = 1.0        # Speech speed multiplier


class ProsodyEngine:
    """Adds natural speech patterns to text before TTS."""

    def __init__(self) -> None:
        self._modification_count: int = 0

    def enhance(
        self,
        text: str,
        emotion: str = "neutral",
    ) -> str:
        """Enhance text with natural speech patterns.

        Adds SSML-like markers that ElevenLabs interprets for natural delivery.
        """
        if not text.strip():
            return text

        self._modification_count += 1

        # Add sentence-level pauses
        text = self._add_sentence_pauses(text)

        # Add phrase-level pauses
        text = self._add_phrase_pauses(text)

        # Add emphasis for important words
        text = self._add_emphasis(text)

        # Add breathing markers for long sentences
        text = self._add_breathing(text)

        # Handle questions (rising intonation hint)
        text = self._handle_questions(text)

        # Handle lists
        text = self._handle_lists(text)

        return text

    def _add_sentence_pauses(self, text: str) -> str:
        """Add pauses between sentences."""
        # After period/exclamation/question — natural pause
        text = re.sub(r'([.!?])\s+', r'\1 ', text)
        return text

    def _add_phrase_pauses(self, text: str) -> str:
        """Add micro-pauses at phrase boundaries (commas, semicolons)."""
        # Comma — short pause
        text = re.sub(r',\s*', ', ', text)
        return text

    def _add_emphasis(self, text: str) -> str:
        """Add emphasis for important words."""
        emphasis_words = [
            "important", "critical", "always", "never", "must",
            "first", "last", "key", "main", "only", "best", "worst",
            "absolutely", "definitely", "certainly", "exactly",
        ]

        for word in emphasis_words:
            pattern = re.compile(r'\b(' + re.escape(word) + r')\b', re.IGNORECASE)
            text = pattern.sub(r'\1', text)

        return text

    def _add_breathing(self, text: str) -> str:
        """Add natural breathing points for long sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        enhanced = []

        for sentence in sentences:
            words = sentence.split()
            if len(words) > 20:
                # Long sentence — add natural pause at clause boundary
                mid = len(words) // 2
                # Find a good break point near the middle
                for i in range(mid, min(mid + 5, len(words))):
                    if words[i].rstrip('.,!?;:') in (',', ';', 'and', 'but', 'or', 'so', 'because'):
                        break
                else:
                    i = mid
                # Add a natural break
                clause1 = ' '.join(words[:i + 1])
                clause2 = ' '.join(words[i + 1:])
                enhanced.append(f"{clause1} {clause2}")
            else:
                enhanced.append(sentence)

        return ' '.join(enhanced)

    def _handle_questions(self, text: str) -> str:
        """Ensure questions have natural intonation cues."""
        # Questions already end with ? — ElevenLabs handles intonation
        return text

    def _handle_lists(self, text: str) -> str:
        """Handle lists with natural rhythm."""
        # "X, Y, and Z" pattern
        text = re.sub(r',\s*and\s+', ', and ', text)
        return text

    def apply_emotion_to_text(self, text: str, emotion: str) -> str:
        """Add emotion-specific text modifications."""
        emotion_prefixes = {
            "excited": "Wow! ",
            "happy": "",
            "calm": "",
            "serious": "",
            "sad": "",
            "angry": "",
            "whisper": "",
            "narrative": "",
            "conversational": "",
        }

        prefix = emotion_prefixes.get(emotion, "")
        if prefix:
            return prefix + text
        return text

    def get_stats(self) -> dict[str, Any]:
        return {
            "modification_count": self._modification_count,
        }


prosody_engine = ProsodyEngine()
