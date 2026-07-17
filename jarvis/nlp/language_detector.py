"""Language detection for JARVIS NLP engine.

Detects the language of user input: English, Hindi, Hinglish, or Mixed.
Uses a lightweight statistical approach based on character patterns
and common word frequencies - no external dependencies required.
"""

from __future__ import annotations

import re
from .utils import Language


# ════════════════════════════════════════════════════════════════════
# CHARACTER RANGE DETECTION
# ════════════════════════════════════════════════════════════════════

# Devanagari Unicode range: U+0900–U+097F
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]+")

# Latin script range
_LATIN_RE = re.compile(r"[a-zA-Z]+")


# ════════════════════════════════════════════════════════════════════
# COMMON WORD FREQUENCIES
# ════════════════════════════════════════════════════════════════════

# High-frequency Hindi words that commonly appear in Hinglish
_HINDI_WORDS: set[str] = {
    "khol", "kholo", "band", "karo", "chalao", "chala", "dhund",
    "dhundho", "batao", "bata", "dikhao", "dikha", "maro", "kar",
    "karna", "hatao", "hatana", "mere", "mera", "meri", "tera",
    "tumhara", "yeh", "woh", "kya", "kab", "kahan", "kyun",
    "kaun", "kaise", "nahi", "haan", "theek", "accha", "bura",
    "badhao", "ghatao", "awaz", "aawaz", "sund", "suno",
    "light", "roshni", "chalu", "bhul", "band",
    "download", "folder", "photo", "music", "gaana", "browser",
    "wifi", "bluetooth", "please", "abhi", "jaldi", "bas",
    "aur", "bhi", "se", "mein", "ko", "ke", "ka", "ki",
    "hai", "hain", "tha", "thi", "the", "ho", "hu", "hun",
    "pe", "par", "us", "is", "ye", "wo",
}

# High-frequency English words
_ENGLISH_WORDS: set[str] = {
    "open", "close", "search", "play", "stop", "pause", "volume",
    "brightness", "screenshot", "weather", "news", "timer", "alarm",
    "remember", "save", "delete", "copy", "paste", "shutdown",
    "restart", "lock", "help", "what", "when", "where", "who",
    "how", "why", "show", "tell", "get", "set", "add", "remove",
    "find", "look", "check", "start", "run", "launch", "go",
    "please", "thanks", "hello", "hey", "good", "morning",
    "evening", "night", "today", "tomorrow", "yesterday",
    "youtube", "google", "chrome", "spotify", "github",
    "the", "and", "for", "with", "from", "that", "this",
    "can", "you", "could", "would", "should", "will",
}


# ════════════════════════════════════════════════════════════════════
# DETECTION
# ════════════════════════════════════════════════════════════════════

def detect_language(text: str) -> Language:
    """Detect the language of user input.

    Uses a multi-signal approach:
    1. Devanagari script presence → Hindi
    2. Latin script with Hindi vocabulary → Hinglish
    3. Latin script with English vocabulary → English
    4. Mixed script → Mixed

    Returns Language enum.
    """
    if not text or not text.strip():
        return Language.UNKNOWN

    text_lower = text.lower().strip()
    words = re.findall(r"[a-zA-Z\u0900-\u097F]+", text_lower)

    if not words:
        return Language.UNKNOWN

    # Signal 1: Check for Devanagari script
    has_devanagari = bool(_DEVANAGARI_RE.search(text))

    # Signal 2: Count Hindi vs English words among Latin tokens
    latin_words = [w for w in words if _LATIN_RE.match(w)]

    if not latin_words and not has_devanagari:
        return Language.UNKNOWN

    hindi_count = sum(1 for w in latin_words if w in _HINDI_WORDS)
    english_count = sum(1 for w in latin_words if w in _ENGLISH_WORDS)

    total_known = hindi_count + english_count
    hindi_ratio = hindi_count / total_known if total_known > 0 else 0.0
    english_ratio = english_count / total_known if total_known > 0 else 0.0

    # Decision logic
    if has_devanagari:
        if english_ratio > 0.3:
            return Language.MIXED
        return Language.HINDI

    if hindi_ratio > 0.4:
        return Language.HINGLISH

    if english_ratio > 0.3 or hindi_ratio < 0.1:
        return Language.ENGLISH

    # Ambiguous - default to English
    if total_known == 0:
        # No known words; check character patterns
        if hindi_ratio > 0.2:
            return Language.HINGLISH
        return Language.ENGLISH

    return Language.ENGLISH


def is_hinglish(text: str) -> bool:
    """Quick check if text contains Hinglish patterns."""
    return detect_language(text) in (Language.HINGLISH, Language.MIXED)


def get_language_confidence(text: str) -> float:
    """Return confidence of language detection (0.0-1.0)."""
    if not text or not text.strip():
        return 0.0

    text_lower = text.lower().strip()
    words = re.findall(r"[a-zA-Z\u0900-\u097F]+", text_lower)

    if not words:
        return 0.0

    latin_words = [w for w in words if _LATIN_RE.match(w)]
    hindi_count = sum(1 for w in latin_words if w in _HINDI_WORDS)
    english_count = sum(1 for w in latin_words if w in _ENGLISH_WORDS)
    total_known = hindi_count + english_count

    if total_known == 0:
        return 0.3  # Low confidence when no known words

    max_ratio = max(hindi_count, english_count) / total_known
    return min(0.5 + max_ratio * 0.5, 1.0)
