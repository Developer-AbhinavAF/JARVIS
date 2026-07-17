"""Emotion detection for JARVIS NLP.

Estimates the user's emotional state from text input using keyword
clusters, contextual signals, and linguistic patterns. The detected
emotion influences response style but never assumes facts.

Possible states: happy, excited, calm, focused, confused, frustrated,
angry, curious, tired, sad, motivated, neutral.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# ════════════════════════════════════════════════════════════════════
# EMOTION DEFINITIONS
# ════════════════════════════════════════════════════════════════════

class Emotion:
    HAPPY = "happy"
    EXCITED = "excited"
    CALM = "calm"
    FOCUSED = "focused"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    CURIOUS = "curious"
    TIRED = "tired"
    SAD = "sad"
    MOTIVATED = "motivated"
    NEUTRAL = "neutral"


# Keyword clusters for each emotion
_EMOTION_KEYWORDS: dict[str, list[str]] = {
    Emotion.HAPPY: [
        "happy", "glad", "great", "awesome", "wonderful", "fantastic",
        "amazing", "love", "nice", "perfect", "excellent", "yay",
        "good", "well", "enjoy", "pleased", "delighted", "cheerful",
    ],
    Emotion.EXCITED: [
        "excited", "wow", "incredible", "unbelievable", "insane",
        "epic", "cant wait", "cannot wait", "let's go", "hyped",
        "thrilled", "pumped", "stoked", "amazing", "mind blown",
    ],
    Emotion.CALM: [
        "calm", "relaxed", "peaceful", "chill", "easy", "smooth",
        "fine", "okay", "alright", "no rush", "take your time",
        "gentle", "soothing", "quiet",
    ],
    Emotion.FOCUSED: [
        "focus", "concentrate", "working on", "need to finish",
        "deadline", "important", "serious", "concentrate", "deep work",
        "in the zone", "productive", "let me work", "need coding",
        "coding", "programming", "developing", "building",
    ],
    Emotion.CONFUSED: [
        "confused", "dont understand", "do not understand", "unclear",
        "what do you mean", "huh", "wait what", "lost", "bewildered",
        "puzzled", "baffled", "doesnt make sense", "not sure",
        "i dont get it", "explain", "help me understand",
    ],
    Emotion.FRUSTRATED: [
        "frustrated", "annoying", "annoyed", "this isnt working",
        "this is not working", "keeps failing", "why isnt", "why is not",
        "broken", "stuck", "problem", "issue", "error", "bug",
        "not working", "doesnt work", "wont work", "keeps crashing",
        "so slow", "laggy", "useless", "frustrating", "irritating",
    ],
    Emotion.ANGRY: [
        "angry", "furious", "hate", "terrible", "worst", "stupid",
        "ridiculous", "absurd", "unacceptable", "disgusting",
        "pissed", "mad", "livid", "rage",
    ],
    Emotion.CURIOUS: [
        "curious", "wondering", "how does", "how do", "what is",
        "why does", "why do", "tell me about", "interesting",
        "i wonder", "question", "is it true that", "can you explain",
        "what if", "i want to learn", "show me",
    ],
    Emotion.TIRED: [
        "tired", "exhausted", "sleepy", "drowsy", "fatigued",
        "no energy", "drained", "worn out", "need rest", "need sleep",
        "burned out", "burnt out", "overworked", "need break",
        "i'm tired", "so tired", "bored", "boredom", "nothing to do",
        "can't think", "brain fog", "mentally drained",
    ],
    Emotion.SAD: [
        "sad", "unhappy", "depressed", "down", "blue", "lonely",
        "miss", "missing", "heartbroken", "upset", "disappointed",
        "gloomy", "miserable", "terrible day", "bad day",
    ],
    Emotion.MOTIVATED: [
        "motivated", "ready", "lets do this", "let's do this",
        "going to", "gonna", "determined", "pumped", "on it",
        "bring it", "challenge", "goal", "ambitious", "hustle",
        "grind", "level up",
    ],
}

# Intensifier words that boost emotion score
_INTENSIFIERS: set[str] = {
    "very", "really", "so", "extremely", "incredibly", "absolutely",
    "totally", "completely", "utterly", "highly", "super", "mega",
}

# Negation words that flip emotion
_NEGATIONS: set[str] = {
    "not", "no", "never", "neither", "nobody", "nothing",
    "nowhere", "nor", "dont", "don't", "doesnt", "doesn't",
    "isnt", "isn't", "wasnt", "wasn't", "wont", "won't",
    "cannot", "cant", "can't",
}

# Punctuation / emoji signals
_EXCLAMATION_BONUS = 0.10
_QUESTION_PENALTY = -0.05


@dataclass
class EmotionResult:
    """Result of emotion detection."""
    emotion: str
    confidence: float
    valence: float  # -1.0 (negative) to 1.0 (positive)
    arousal: float  # 0.0 (calm) to 1.0 (excited)
    signals: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "emotion": self.emotion,
            "confidence": round(self.confidence, 3),
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "signals": self.signals,
        }


# Valence and arousal baseline for each emotion
_EMOTION_VALENCE_AROUSAL: dict[str, tuple[float, float]] = {
    Emotion.HAPPY: (0.8, 0.6),
    Emotion.EXCITED: (0.9, 0.9),
    Emotion.CALM: (0.5, 0.2),
    Emotion.FOCUSED: (0.4, 0.5),
    Emotion.CONFUSED: (-0.2, 0.4),
    Emotion.FRUSTRATED: (-0.6, 0.7),
    Emotion.ANGRY: (-0.9, 0.9),
    Emotion.CURIOUS: (0.3, 0.5),
    Emotion.TIRED: (-0.3, 0.1),
    Emotion.SAD: (-0.7, 0.2),
    Emotion.MOTIVATED: (0.7, 0.8),
    Emotion.NEUTRAL: (0.0, 0.3),
}


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

class EmotionDetector:
    """Detects emotional state from text input.

    Uses keyword clusters with intensifier/negation handling,
    punctuation signals, and contextual cues. Returns the dominant
    emotion with confidence, valence, and arousal scores.
    """

    def detect(self, text: str, context: dict[str, Any] | None = None) -> EmotionResult:
        """Detect the dominant emotion in *text*.

        Parameters
        ----------
        text:
            Raw user input.
        context:
            Optional conversation context for emotional continuity.

        Returns
        -------
        EmotionResult with detected emotion, confidence, and
        valence/arousal scores.
        """
        text_lower = text.lower().strip()
        words = text_lower.split()

        if not words:
            return self._make_result(Emotion.NEUTRAL, 0.0, ["empty input"])

        # Score each emotion
        scores: dict[str, float] = {}
        signals: dict[str, list[str]] = {}

        for emotion, keywords in _EMOTION_KEYWORDS.items():
            score, matched = self._score_emotion(text_lower, words, keywords)
            if score > 0:
                scores[emotion] = score
                signals[emotion] = matched

        # Punctuation signals
        exclamation_count = text.count("!")
        question_count = text.count("?")

        if exclamation_count > 0:
            # Boost excited/happy, reduce sad/tired
            for e in (Emotion.EXCITED, Emotion.HAPPY, Emotion.ANGRY):
                if e in scores:
                    scores[e] += _EXCLAMATION_BONUS * min(exclamation_count, 3)

        if question_count > 0:
            # Boost curious, reduce angry
            scores[Emotion.CURIOUS] = scores.get(Emotion.CURIOUS, 0) + 0.15
            scores[Emotion.ANGRY] = scores.get(Emotion.ANGRY, 0) * 0.7

        # Context continuity — if previous emotion was strong, carry over slightly
        if context:
            prev_emotion = context.get("last_emotion", "")
            if prev_emotion and prev_emotion in scores:
                scores[prev_emotion] += 0.05
            elif prev_emotion and prev_emotion not in scores:
                scores[prev_emotion] = 0.05

        # Determine winner
        if not scores:
            result = self._make_result(Emotion.NEUTRAL, 0.3, ["no emotion signals"])
        else:
            best_emotion = max(scores, key=scores.get)  # type: ignore
            best_score = scores[best_emotion]
            total = sum(scores.values())
            confidence = best_score / total if total > 0 else 0.0
            confidence = min(confidence, 1.0)

            if confidence < 0.25:
                result = self._make_result(
                    Emotion.NEUTRAL, 0.4,
                    signals.get(best_emotion, ["weak signal"]),
                )
            else:
                result = self._make_result(
                    best_emotion,
                    confidence,
                    signals.get(best_emotion, ["keyword match"]),
                )

        return result

    def get_response_style(self, emotion: str) -> dict[str, Any]:
        """Return response style guidance for the given emotion.

        Returns a dict with style parameters that the response
        generator can use to adapt its output.
        """
        styles = {
            Emotion.HAPPY: {"tone": "warm", "enthusiasm": 0.7, "brevity": 0.5},
            Emotion.EXCITED: {"tone": "energetic", "enthusiasm": 0.9, "brevity": 0.4},
            Emotion.CALM: {"tone": "gentle", "enthusiasm": 0.3, "brevity": 0.5},
            Emotion.FOCUSED: {"tone": "concise", "enthusiasm": 0.2, "brevity": 0.8},
            Emotion.CONFUSED: {"tone": "patient", "enthusiasm": 0.3, "brevity": 0.3},
            Emotion.FRUSTRATED: {"tone": "empathetic", "enthusiasm": 0.2, "brevity": 0.6},
            Emotion.ANGRY: {"tone": "calm", "enthusiasm": 0.1, "brevity": 0.7},
            Emotion.CURIOUS: {"tone": "informative", "enthusiasm": 0.5, "brevity": 0.4},
            Emotion.TIRED: {"tone": "gentle", "enthusiasm": 0.2, "brevity": 0.7},
            Emotion.SAD: {"tone": "empathetic", "enthusiasm": 0.2, "brevity": 0.5},
            Emotion.MOTIVATED: {"tone": "encouraging", "enthusiasm": 0.7, "brevity": 0.5},
            Emotion.NEUTRAL: {"tone": "standard", "enthusiasm": 0.4, "brevity": 0.5},
        }
        return styles.get(emotion, styles[Emotion.NEUTRAL])

    # ── internals ───────────────────────────────────────────────────

    def _score_emotion(
        self,
        text: str,
        words: list[str],
        keywords: list[str],
    ) -> tuple[float, list[str]]:
        """Score how well text matches an emotion's keyword cluster."""
        score = 0.0
        matched: list[str] = []

        for keyword in keywords:
            if " " in keyword:
                # Multi-word keyword — check substring
                if keyword in text:
                    score += 1.0
                    matched.append(keyword)
            elif keyword in words:
                # Check for negation before the keyword
                idx = words.index(keyword)
                negated = False
                if idx > 0 and words[idx - 1] in _NEGATIONS:
                    negated = True

                if negated:
                    score -= 0.5
                    matched.append(f"NOT {keyword}")
                else:
                    # Check for intensifier before the keyword
                    if idx > 0 and words[idx - 1] in _INTENSIFIERS:
                        score += 1.5
                        matched.append(f"INTENSIFIED {keyword}")
                    else:
                        score += 1.0
                        matched.append(keyword)

        return score, matched

    @staticmethod
    def _make_result(
        emotion: str,
        confidence: float,
        signals: list[str],
    ) -> EmotionResult:
        """Create an EmotionResult with valence/arousal from the baseline."""
        valence, arousal = _EMOTION_VALENCE_AROUSAL.get(emotion, (0.0, 0.3))
        return EmotionResult(
            emotion=emotion,
            confidence=round(min(confidence, 1.0), 3),
            valence=valence,
            arousal=arousal,
            signals=signals,
        )
