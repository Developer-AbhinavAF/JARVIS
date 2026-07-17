"""User profiler for JARVIS NLP.

Gradually learns user preferences, habits, and patterns over time:
- Preferred IDE, browser, search engine, music platform
- Frequently used applications
- Coding languages, study hours, gaming hours
- Daily routine, speech style, typing style
- Common phrases, nicknames, aliases

Never asks repeatedly. Learns naturally from interactions.
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class UserProfile:
    """Complete user profile built over time."""
    # Application preferences
    preferred_ide: str = ""
    preferred_browser: str = ""
    preferred_search_engine: str = ""
    preferred_music_platform: str = ""
    preferred_video_platform: str = ""
    preferred_code_editor: str = ""
    preferred_terminal: str = ""
    preferred_email_client: str = ""
    preferred_chat_app: str = ""

    # Frequently used apps (top 10)
    frequent_apps: dict[str, int] = field(default_factory=dict)

    # Coding preferences
    coding_languages: dict[str, int] = field(default_factory=dict)

    # Time patterns
    study_hours: dict[int, int] = field(default_factory=dict)
    gaming_hours: dict[int, int] = field(default_factory=dict)
    work_hours: dict[int, int] = field(default_factory=dict)

    # Communication style
    speech_style: str = "casual"  # casual | formal | mixed
    common_phrases: dict[str, int] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)

    # Daily routine
    daily_routine: dict[str, str] = field(default_factory=dict)

    # Metadata
    total_interactions: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "preferred_ide": self.preferred_ide,
            "preferred_browser": self.preferred_browser,
            "preferred_search_engine": self.preferred_search_engine,
            "preferred_music_platform": self.preferred_music_platform,
            "preferred_video_platform": self.preferred_video_platform,
            "preferred_code_editor": self.preferred_code_editor,
            "preferred_terminal": self.preferred_terminal,
            "preferred_email_client": self.preferred_email_client,
            "preferred_chat_app": self.preferred_chat_app,
            "frequent_apps": self.frequent_apps,
            "coding_languages": self.coding_languages,
            "study_hours": self.study_hours,
            "gaming_hours": self.gaming_hours,
            "work_hours": self.work_hours,
            "speech_style": self.speech_style,
            "common_phrases": self.common_phrases,
            "aliases": self.aliases,
            "daily_routine": self.daily_routine,
            "total_interactions": self.total_interactions,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ════════════════════════════════════════════════════════════════════
# APP CATEGORY MAPPING
# ════════════════════════════════════════════════════════════════════

_APP_CATEGORIES: dict[str, str] = {
    # IDEs / Editors
    "vscode": "ide", "visual studio code": "ide", "vs code": "ide",
    "pycharm": "ide", "intellij": "ide", "sublime": "ide",
    "atom": "ide", "vim": "ide", "nvim": "ide", "emacs": "ide",
    "cursor": "ide", "webstorm": "ide",
    # Browsers
    "chrome": "browser", "google chrome": "browser", "firefox": "browser",
    "edge": "browser", "safari": "browser", "opera": "browser", "brave": "browser",
    # Music
    "spotify": "music", "youtube music": "music", "apple music": "music",
    "vlc": "music", "foobar2000": "music",
    # Video
    "youtube": "video", "netflix": "video", "twitch": "video", "plex": "video",
    # Chat
    "discord": "chat", "slack": "chat", "teams": "chat",
    "whatsapp": "chat", "telegram": "chat",
    # Email
    "outlook": "email", "gmail": "email", "thunderbird": "email",
    # Terminal
    "cmd": "terminal", "powershell": "terminal", "windows terminal": "terminal",
    "wt": "terminal", "wsl": "terminal", "iterm": "terminal",
    "terminal": "terminal",
}

# Coding language detection from file extensions and project types
_CODING_LANG_INDICATORS: dict[str, list[str]] = {
    "python": [".py", "requirements.txt", "setup.py", "pyproject.toml", "pip"],
    "javascript": [".js", "package.json", "node_modules", "npm", "yarn"],
    "typescript": [".ts", ".tsx", "tsconfig.json"],
    "java": [".java", "pom.xml", "build.gradle"],
    "csharp": [".cs", ".csproj", ".sln"],
    "cpp": [".cpp", ".c", ".h", "cmake", "makefile"],
    "rust": [".rs", "cargo.toml"],
    "go": [".go", "go.mod"],
    "ruby": [".rb", "gemfile"],
    "php": [".php", "composer.json"],
    "swift": [".swift"],
    "kotlin": [".kt", ".kts"],
    "html": [".html", ".css"],
    "sql": [".sql", "database"],
}


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

class UserProfiler:
    """Builds and maintains a user profile from interactions.

    Learns preferences naturally by observing which apps, websites,
    and tools the user uses. Tracks time patterns and communication
    style without ever asking the user directly.
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = (
            Path(data_dir) if data_dir
            else Path(__file__).parent.parent.parent / "data" / "nlp_user_profile"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profile = UserProfile()
        self._load()

    def update_from_interaction(
        self,
        intent: str,
        entities: dict[str, Any],
        tool_name: str,
        success: bool,
    ) -> None:
        """Update the user profile from a completed interaction.

        Called after every command execution. Observes patterns and
        updates the profile without requiring explicit user input.
        """
        now = time.time()
        hour = int(time.strftime("%H", time.localtime(now)))

        if self.profile.first_seen == 0.0:
            self.profile.first_seen = now
        self.profile.last_seen = now
        self.profile.total_interactions += 1

        target = str(entities.get("target", "")).lower()
        platform = str(entities.get("platform", "")).lower()
        query = str(entities.get("query", "")).lower()

        # Track app usage
        if intent == "OPEN_APP" and target:
            self._update_app_preference(target)
            self.profile.frequent_apps[target] = (
                self.profile.frequent_apps.get(target, 0) + 1
            )

        # Track platform preferences
        if intent in ("OPEN_WEBSITE", "SEARCH_ON_PLATFORM") and platform:
            self._update_platform_preference(platform)

        if intent in ("PLAY_MUSIC", "PLAY_SPOTIFY") and platform:
            self.profile.preferred_music_platform = platform

        if intent == "PLAY_YOUTUBE":
            self.profile.preferred_video_platform = "youtube"

        # Track coding languages from file/project context
        if intent in ("OPEN_APP", "OPEN_FOLDER", "PROGRAMMING"):
            self._detect_coding_language(target, query)

        # Track time patterns
        if success:
            self._update_time_patterns(intent, hour)

        # Track speech style from input
        if query:
            self._update_speech_style(query)

        # Track common phrases
        if query and len(query.split()) <= 4:
            self.profile.common_phrases[query] = (
                self.profile.common_phrases.get(query, 0) + 1
            )

        # Periodic save
        if self.profile.total_interactions % 10 == 0:
            self._save()

    def resolve_alias(self, name: str) -> str:
        """Resolve a user alias/nickname to the actual entity.

        For example, if the user calls VS Code "editor", and has
        learned that "editor" → "vscode", this returns "vscode".
        """
        name_lower = name.lower().strip()
        return self.profile.aliases.get(name_lower, name)

    def add_alias(self, alias: str, target: str) -> None:
        """Explicitly add an alias mapping."""
        self.profile.aliases[alias.lower().strip()] = target.lower().strip()
        self._save()

    def get_preference(self, category: str) -> str | None:
        """Get the preferred app for a category."""
        pref_map = {
            "ide": self.profile.preferred_ide,
            "browser": self.profile.preferred_browser,
            "search": self.profile.preferred_search_engine,
            "music": self.profile.preferred_music_platform,
            "video": self.profile.preferred_video_platform,
            "editor": self.profile.preferred_code_editor,
            "terminal": self.profile.preferred_terminal,
            "email": self.profile.preferred_email_client,
            "chat": self.profile.preferred_chat_app,
        }
        return pref_map.get(category) or None

    def get_top_apps(self, n: int = 5) -> list[str]:
        """Return the top N most-used applications."""
        sorted_apps = sorted(
            self.profile.frequent_apps.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [app for app, _ in sorted_apps[:n]]

    def get_coding_languages(self) -> list[str]:
        """Return coding languages sorted by usage frequency."""
        sorted_langs = sorted(
            self.profile.coding_languages.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [lang for lang, _ in sorted_langs]

    def get_profile_summary(self) -> dict[str, Any]:
        """Return a summary of the user profile."""
        return {
            "preferences": {
                "ide": self.profile.preferred_ide,
                "browser": self.profile.preferred_browser,
                "music": self.profile.preferred_music_platform,
                "video": self.profile.preferred_video_platform,
                "terminal": self.profile.preferred_terminal,
            },
            "top_apps": self.get_top_apps(5),
            "coding_languages": self.get_coding_languages()[:5],
            "total_interactions": self.profile.total_interactions,
            "speech_style": self.profile.speech_style,
            "aliases": dict(self.profile.aliases),
        }

    # ── internals ───────────────────────────────────────────────────

    def _update_app_preference(self, app_name: str) -> None:
        """Update preferred app for the detected category."""
        category = _APP_CATEGORIES.get(app_name, "")
        if not category:
            return

        pref_attr = f"preferred_{category}"
        if hasattr(self.profile, pref_attr):
            current = getattr(self.profile, pref_attr)
            if current == app_name:
                # Reinforce — do nothing, already preferred
                return
            elif not current:
                # First time seeing this category
                setattr(self.profile, pref_attr, app_name)

    def _update_platform_preference(self, platform: str) -> None:
        """Update preferred platform for common services."""
        platform_category = {
            "spotify": "preferred_music_platform",
            "youtube": "preferred_video_platform",
            "google": "preferred_search_engine",
            "bing": "preferred_search_engine",
            "duckduckgo": "preferred_search_engine",
            "gmail": "preferred_email_client",
            "outlook": "preferred_email_client",
            "discord": "preferred_chat_app",
            "slack": "preferred_chat_app",
        }
        attr = platform_category.get(platform)
        if attr and hasattr(self.profile, attr):
            if not getattr(self.profile, attr):
                setattr(self.profile, attr, platform)

    def _detect_coding_language(self, target: str, query: str) -> None:
        """Detect coding language from context."""
        combined = f"{target} {query}".lower()
        for lang, indicators in _CODING_LANG_INDICATORS.items():
            for indicator in indicators:
                if indicator in combined:
                    self.profile.coding_languages[lang] = (
                        self.profile.coding_languages.get(lang, 0) + 1
                    )
                    return

    def _update_time_patterns(self, intent: str, hour: int) -> None:
        """Update time-based activity patterns."""
        # Simple heuristic: if user is coding during certain hours
        if intent in ("OPEN_APP", "PROGRAMMING", "OPEN_FOLDER"):
            self.profile.work_hours[hour] = self.profile.work_hours.get(hour, 0) + 1

        if intent in ("PLAY_MUSIC", "PLAY_YOUTUBE", "PLAY_SPOTIFY"):
            self.profile.gaming_hours[hour] = self.profile.gaming_hours.get(hour, 0) + 1

    def _update_speech_style(self, text: str) -> None:
        """Update speech style based on input patterns."""
        # Simple heuristic based on formality indicators
        formal_indicators = ["please", "could you", "would you", "kindly", "thank you"]
        casual_indicators = ["hey", "yo", "sup", "gonna", "wanna", "bruh", "bhai", "yaar"]

        text_lower = text.lower()
        formal_count = sum(1 for w in formal_indicators if w in text_lower)
        casual_count = sum(1 for w in casual_indicators if w in text_lower)

        if formal_count > casual_count:
            self.profile.speech_style = "formal"
        elif casual_count > formal_count:
            self.profile.speech_style = "casual"

    def _save(self) -> None:
        """Persist profile to JSON."""
        try:
            path = self.data_dir / "user_profile.json"
            path.write_text(
                json.dumps(self.profile.to_dict(), indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self) -> None:
        """Load profile from JSON."""
        try:
            path = self.data_dir / "user_profile.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                self.profile = UserProfile.from_dict(data)
        except Exception:
            pass
