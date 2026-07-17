"""Personal language model for JARVIS NLP.

Every user develops their own vocabulary. This module maps user-specific
terms to canonical entity names based on learned preferences.

Example:
    User says "editor" → VS Code (based on profile)
    User says "music" → Spotify (based on profile)
    User says "videos" → YouTube (based on profile)
    User says "repo" → GitHub Repository (based on profile)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ════════════════════════════════════════════════════════════════════
# DEFAULT MAPPINGS
# ════════════════════════════════════════════════════════════════════

# Default vocabulary mappings (overridden by user profile)
_DEFAULT_VOCABULARY: dict[str, dict[str, str]] = {
    "editor": {
        "editor": "vscode",
        "code editor": "vscode",
        "my editor": "vscode",
    },
    "browser": {
        "browser": "chrome",
        "my browser": "chrome",
        "the internet": "chrome",
    },
    "music": {
        "music": "spotify",
        "my music": "spotify",
        "songs": "spotify",
        "playlist": "spotify",
    },
    "videos": {
        "videos": "youtube",
        "videos": "youtube",
        "watch something": "youtube",
    },
    "repo": {
        "repo": "github",
        "repository": "github",
        "my repos": "github",
        "code repo": "github",
    },
    "notes": {
        "notes": "obsidian",
        "my notes": "obsidian",
        "notebook": "obsidian",
        "journal": "obsidian",
    },
    "email": {
        "email": "gmail",
        "my email": "gmail",
        "mail": "gmail",
        "inbox": "gmail",
    },
    "chat": {
        "chat": "discord",
        "message": "discord",
        "talk": "discord",
    },
    "docs": {
        "docs": "google_docs",
        "documents": "google_docs",
        "paper": "google_docs",
    },
}


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

@dataclass
class VocabularyMatch:
    """Result of vocabulary resolution."""
    original: str
    resolved: str
    category: str
    confidence: float
    source: str  # "profile" | "default" | "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "resolved": self.resolved,
            "category": self.category,
            "confidence": round(self.confidence, 3),
            "source": self.source,
        }


class PersonalLanguageModel:
    """Resolves user-specific vocabulary to canonical entity names.

    Uses a combination of:
    1. User profile preferences (highest priority)
    2. Default vocabulary mappings (fallback)
    3. Common abbreviation expansions
    """

    def __init__(self) -> None:
        self._custom_vocabulary: dict[str, dict[str, str]] = {}
        self._user_preferences: dict[str, str] = {}

    def set_user_preferences(self, preferences: dict[str, str]) -> None:
        """Set user preferences from the profiler.

        Parameters
        ----------
        preferences:
            Dict mapping category names to preferred values,
            e.g. ``{"ide": "vscode", "browser": "chrome"}``.
        """
        self._user_preferences = {
            k.lower(): v.lower() for k, v in preferences.items()
        }

    def add_vocabulary(self, category: str, mappings: dict[str, str]) -> None:
        """Add custom vocabulary mappings for a category."""
        self._custom_vocabulary[category] = {
            k.lower(): v.lower() for k, v in mappings.items()
        }

    def resolve(self, text: str) -> VocabularyMatch | None:
        """Resolve user vocabulary in *text* to a canonical name.

        Checks if any word or phrase in the text matches a known
        vocabulary entry. Returns the best match or None.
        """
        text_lower = text.lower().strip()
        words = text_lower.split()

        # Try exact phrase match first (longest first)
        for length in range(min(len(words), 4), 0, -1):
            for i in range(len(words) - length + 1):
                phrase = " ".join(words[i:i + length])
                match = self._lookup(phrase)
                if match:
                    return match

        # Try individual word match
        for word in words:
            match = self._lookup(word)
            if match:
                return match

        return None

    def resolve_for_category(
        self,
        text: str,
        category: str,
    ) -> VocabularyMatch | None:
        """Resolve vocabulary specifically for a given category.

        Only looks up vocabulary entries in the specified category.
        """
        text_lower = text.lower().strip()

        # Check user preferences first
        pref_value = self._user_preferences.get(category)
        if pref_value:
            # Check if the text contains a word that maps to this category
            if self._text_matches_category(text_lower, category):
                return VocabularyMatch(
                    original=text,
                    resolved=pref_value,
                    category=category,
                    confidence=0.9,
                    source="profile",
                )

        # Check default vocabulary
        category_vocab = _DEFAULT_VOCABULARY.get(category, {})
        for term, value in category_vocab.items():
            if term in text_lower:
                return VocabularyMatch(
                    original=text,
                    resolved=value,
                    category=category,
                    confidence=0.7,
                    source="default",
                )

        return None

    def expand_abbreviations(self, text: str) -> str:
        """Expand common abbreviations in the text."""
        abbreviations = {
            "vscode": "visual studio code",
            "vs code": "visual studio code",
            "pycharm": "pycharm",
            "js": "javascript",
            "ts": "typescript",
            "py": "python",
            "rb": "ruby",
            "gdrive": "google drive",
            "yt": "youtube",
            "gh": "github",
            "gl": "gitlab",
        }
        text_lower = text.lower()
        for abbr, full in abbreviations.items():
            if abbr in text_lower:
                text_lower = text_lower.replace(abbr, full)
        return text_lower

    def _lookup(self, term: str) -> VocabularyMatch | None:
        """Look up a single term across all categories."""
        term_lower = term.lower().strip()

        # Check custom vocabulary first
        for category, vocab in self._custom_vocabulary.items():
            if term_lower in vocab:
                return VocabularyMatch(
                    original=term,
                    resolved=vocab[term_lower],
                    category=category,
                    confidence=0.85,
                    source="custom",
                )

        # Check user preferences
        for category, pref_value in self._user_preferences.items():
            # If the term is a common word for this category
            if self._term_matches_category(term_lower, category):
                return VocabularyMatch(
                    original=term,
                    resolved=pref_value,
                    category=category,
                    confidence=0.9,
                    source="profile",
                )

        # Check default vocabulary
        for category, vocab in _DEFAULT_VOCABULARY.items():
            if term_lower in vocab:
                return VocabularyMatch(
                    original=term,
                    resolved=vocab[term_lower],
                    category=category,
                    confidence=0.7,
                    source="default",
                )

        return None

    @staticmethod
    def _term_matches_category(term: str, category: str) -> bool:
        """Check if a term is commonly used for a category."""
        category_terms = {
            "ide": {"editor", "ide", "code editor", "code"},
            "browser": {"browser", "web", "internet", "chrome", "firefox"},
            "music": {"music", "songs", "playlist", "audio", "listen"},
            "video": {"videos", "watch", "stream", "play"},
            "email": {"email", "mail", "inbox", "messages"},
            "chat": {"chat", "message", "talk", "call"},
            "notes": {"notes", "notebook", "journal", "memo"},
        }
        terms = category_terms.get(category, set())
        return term in terms

    @staticmethod
    def _text_matches_category(text: str, category: str) -> bool:
        """Check if text contains words relevant to a category."""
        return PersonalLanguageModel._term_matches_category(text, category)
