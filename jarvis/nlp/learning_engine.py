"""Self-learning engine for user preferences in JARVIS NLP pipeline.

Tracks which apps, websites, and tools the user prefers for each category,
builds synonym mappings from failures, and detects time-based usage patterns.

Distinct from ``SelfLearningEngine`` (self_learning.py) which tracks raw
command frequency and unknown commands.  This module focuses on *preference
resolution* — given a category like "browser", which app does the user
actually want?
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class UserPreference:
    """A single learned user preference."""
    key: str
    value: str
    confidence: float = 0.5
    usage_count: int = 0
    last_used: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserPreference:
        """Deserialize from a dict."""
        return cls(
            key=data.get("key", ""),
            value=data.get("value", ""),
            confidence=data.get("confidence", 0.5),
            usage_count=data.get("usage_count", 0),
            last_used=data.get("last_used", 0.0),
        )


@dataclass
class ToolUsageRecord:
    """Tracks how a tool is used for a given intent."""
    tool_name: str
    count: int = 0
    successes: int = 0
    failures: int = 0
    last_used: float = 0.0

    @property
    def success_rate(self) -> float:
        """Fraction of successful executions."""
        if self.count == 0:
            return 0.0
        return self.successes / self.count

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "count": self.count,
            "successes": self.successes,
            "failures": self.failures,
            "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolUsageRecord:
        return cls(
            tool_name=data.get("tool_name", ""),
            count=data.get("count", 0),
            successes=data.get("successes", 0),
            failures=data.get("failures", 0),
            last_used=data.get("last_used", 0.0),
        )


@dataclass
class FailedCommand:
    """A command that failed, kept for synonym/pattern discovery."""
    text: str
    intent: str
    entities: dict[str, Any]
    timestamp: float
    tool_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "intent": self.intent,
            "entities": self.entities,
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailedCommand:
        return cls(
            text=data.get("text", ""),
            intent=data.get("intent", ""),
            entities=data.get("entities", {}),
            timestamp=data.get("timestamp", 0.0),
            tool_name=data.get("tool_name", ""),
        )


@dataclass
class TimePattern:
    """A detected time-based usage pattern."""
    category: str
    value: str
    hour_start: int  # 0-23
    hour_end: int
    count: int = 0
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimePattern:
        return cls(
            category=data.get("category", ""),
            value=data.get("value", ""),
            hour_start=data.get("hour_start", 0),
            hour_end=data.get("hour_end", 0),
            count=data.get("count", 0),
            confidence=data.get("confidence", 0.0),
        )


# ════════════════════════════════════════════════════════════════════
# INITIAL SYNONYM SUGGESTIONS
# ════════════════════════════════════════════════════════════════════

# Seed mappings — these grow as the user teaches the system.
SYNONYM_SUGGESTIONS: dict[str, dict[str, str]] = {
    "editor": {
        "vscode": "vscode",
        "vs code": "vscode",
        "visual studio code": "vscode",
        "cursor": "cursor",
        "sublime": "sublime",
        "intellij": "intellij",
        "pycharm": "pycharm",
    },
    "browser": {
        "chrome": "chrome",
        "google chrome": "chrome",
        "firefox": "firefox",
        "mozilla": "firefox",
        "edge": "edge",
        "microsoft edge": "edge",
    },
    "music_app": {
        "spotify": "spotify",
        "youtube music": "youtube_music",
        "apple music": "apple_music",
        "vlc": "vlc",
    },
    "video_app": {
        "youtube": "youtube",
        "netflix": "netflix",
        "vlc": "vlc",
        "plex": "plex",
    },
    "chat_app": {
        "discord": "discord",
        "slack": "slack",
        "teams": "teams",
        "whatsapp": "whatsapp",
        "telegram": "telegram",
    },
    "email_app": {
        "outlook": "outlook",
        "gmail": "gmail",
        "thunderbird": "thunderbird",
    },
    "terminal": {
        "cmd": "cmd",
        "command prompt": "cmd",
        "powershell": "powershell",
        "wt": "wt",
        "windows terminal": "wt",
        "wsl": "wsl",
    },
}

# Category → keyword hints used when auto-detecting preferences from entities.
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "browser": ["browser", "chrome", "firefox", "edge", "open website", "browse"],
    "editor": ["editor", "code", "vscode", "ide", "develop", "edit"],
    "music_app": ["music", "spotify", "song", "playlist", "listen", "play"],
    "video_app": ["youtube", "netflix", "video", "watch", "stream"],
    "chat_app": ["discord", "slack", "teams", "whatsapp", "telegram", "chat"],
    "email_app": ["email", "outlook", "gmail", "mail", "inbox"],
    "terminal": ["terminal", "cmd", "powershell", "console", "shell"],
}


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

class LearningEngine:
    """Learns user preferences, app mappings, and usage patterns over time.

    Records every interaction and derives:
    - Preferred apps/websites per category (e.g. browser → chrome)
    - Tool-intent mapping with success rates
    - Time-of-day usage patterns
    - Growing synonym suggestions from failed commands

    All data persists to JSON under *data_dir*.
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = (
            Path(data_dir) if data_dir
            else Path(__file__).parent.parent.parent / "data" / "nlp_learning"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Core data
        self._preferences: dict[str, UserPreference] = {}
        self._tool_usage: dict[str, dict[str, ToolUsageRecord]] = defaultdict(dict)
        self._command_frequency: Counter = Counter()
        self._failed_commands: list[FailedCommand] = []
        self._time_patterns: list[TimePattern] = []
        self._learned_synonyms: dict[str, dict[str, str]] = {}

        self._load_data()

    # ── Recording ──────────────────────────────────────────────────

    def record_interaction(
        self,
        intent: str,
        entities: dict[str, Any],
        tool_name: str,
        success: bool,
    ) -> None:
        """Record the outcome of an executed interaction.

        This is the main entry-point called by the pipeline after every
        command execution.  It updates preferences, tool usage stats,
        command frequency counters, and time-pattern data.
        """
        now = time.time()
        hour = int(time.strftime("%H", time.localtime(now)))

        # --- Tool-intent tracking ---
        intent_tools = self._tool_usage[intent]
        if tool_name not in intent_tools:
            intent_tools[tool_name] = ToolUsageRecord(tool_name=tool_name)
        record = intent_tools[tool_name]
        record.count += 1
        record.last_used = now
        if success:
            record.successes += 1
        else:
            record.failures += 1

        # --- Command frequency ---
        cmd_text = entities.get("query", "") or entities.get("target", "") or ""
        if cmd_text:
            self._command_frequency[cmd_text.lower().strip()] += 1

        # --- Auto-learn preferences from entities ---
        self._auto_detect_preference(intent, entities, tool_name, success, now)

        # --- Time patterns ---
        if success:
            self._record_time_pattern(intent, entities, tool_name, hour)

        # --- Failed commands for synonym discovery ---
        if not success and cmd_text:
            self._failed_commands.append(
                FailedCommand(
                    text=cmd_text,
                    intent=intent,
                    entities=entities,
                    timestamp=now,
                    tool_name=tool_name,
                )
            )
            # Cap at 500
            if len(self._failed_commands) > 500:
                self._failed_commands = self._failed_commands[-500:]

        # Periodic save
        total_records = sum(r.count for tools in self._tool_usage.values() for r in tools.values())
        if total_records % 10 == 0:
            self._save_data()

    # ── Preference API ─────────────────────────────────────────────

    def get_preference(self, key: str) -> str | None:
        """Return the preferred *value* for *key*, or ``None``."""
        pref = self._preferences.get(key)
        if pref is None:
            return None
        # Only return if confidence is above a minimum threshold
        if pref.confidence < 0.3:
            return None
        return pref.value

    def set_preference(self, key: str, value: str) -> None:
        """Explicitly set a preference (e.g. user said 'use chrome')."""
        now = time.time()
        if key in self._preferences:
            pref = self._preferences[key]
            pref.value = value
            pref.usage_count += 1
            pref.last_used = now
            # Boost confidence for explicit overrides
            pref.confidence = min(pref.confidence + 0.2, 1.0)
        else:
            self._preferences[key] = UserPreference(
                key=key,
                value=value,
                confidence=0.8,
                usage_count=1,
                last_used=now,
            )
        self._save_data()

    def get_preferred_app(self, category: str) -> str | None:
        """Return the preferred app name for *category* (e.g. ``"browser"``)."""
        return self.get_preference(f"app:{category}")

    def get_preferred_website(self, category: str) -> str | None:
        """Return the preferred website for *category* (e.g. ``"news"``)."""
        return self.get_preference(f"website:{category}")

    # ── Analytics ──────────────────────────────────────────────────

    def get_frequent_commands(self, top_n: int = 10) -> list[dict[str, Any]]:
        """Return the *top_n* most frequently used commands."""
        return [
            {"command": cmd, "count": count}
            for cmd, count in self._command_frequency.most_common(top_n)
        ]

    def get_unknown_commands(self) -> list[dict[str, Any]]:
        """Return failed commands grouped by normalized text."""
        counts: Counter = Counter()
        last_seen: dict[str, float] = {}
        intents: dict[str, str] = {}
        for fc in self._failed_commands:
            key = fc.text.lower().strip()
            counts[key] += 1
            last_seen[key] = max(last_seen.get(key, 0), fc.timestamp)
            if key not in intents:
                intents[key] = fc.intent

        results = [
            {
                "text": text,
                "fail_count": count,
                "intent": intents.get(text, ""),
                "last_seen": last_seen.get(text, 0),
            }
            for text, count in counts.most_common(30)
        ]
        return results

    def get_synonym_suggestions(self) -> list[dict[str, Any]]:
        """Suggest new synonyms by comparing failed commands to known commands.

        If a failed command is *similar* to a known command but uses
        different words, we suggest mapping those words as synonyms.
        """
        suggestions: list[dict[str, Any]] = []

        for fc in self._failed_commands[-100:]:
            fc_text = fc.text.lower().strip()
            if not fc_text:
                continue

            for cmd_text, freq in self._command_frequency.items():
                similarity = self._text_similarity(fc_text, cmd_text)
                if 0.4 <= similarity < 1.0:
                    # Find differing words as potential synonyms
                    fc_words = set(fc_text.split())
                    cmd_words = set(cmd_text.split())
                    new_words = fc_words - cmd_words
                    if new_words:
                        suggestions.append({
                            "failed_text": fc.text,
                            "similar_known": cmd_text,
                            "similarity": round(similarity, 2),
                            "suggested_synonyms": sorted(new_words),
                            "intent": fc.intent,
                        })
                    break

        # Deduplicate and cap
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for s in suggestions:
            key = s["failed_text"]
            if key not in seen:
                seen.add(key)
                unique.append(s)
        return unique[:20]

    def get_time_patterns(self) -> list[dict[str, Any]]:
        """Return detected time-based patterns sorted by confidence."""
        sorted_patterns = sorted(
            self._time_patterns, key=lambda p: p.confidence, reverse=True
        )
        return [p.to_dict() for p in sorted_patterns[:20]]

    def get_all_preferences(self) -> dict[str, str]:
        """Return all preferences with confidence >= threshold."""
        return {
            key: pref.value
            for key, pref in self._preferences.items()
            if pref.confidence >= 0.3
        }

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate learning statistics."""
        return {
            "total_preferences": len(self._preferences),
            "high_confidence_preferences": sum(
                1 for p in self._preferences.values() if p.confidence >= 0.7
            ),
            "total_unique_commands": len(self._command_frequency),
            "total_failed_commands": len(self._failed_commands),
            "total_time_patterns": len(self._time_patterns),
            "tool_intents_tracked": len(self._tool_usage),
            "learned_synonym_categories": len(self._learned_synonyms),
        }

    # ── Internals ──────────────────────────────────────────────────

    def _auto_detect_preference(
        self,
        intent: str,
        entities: dict[str, Any],
        tool_name: str,
        success: bool,
        now: float,
    ) -> None:
        """Try to infer user preferences from the interaction entities."""
        target = str(entities.get("target", "")).lower()
        platform = str(entities.get("platform", "")).lower()
        query = str(entities.get("query", "")).lower()

        # Category detection based on intent + entities
        detected_categories = self._detect_categories(intent, entities, target, platform, query)

        for category, value in detected_categories:
            if not value:
                continue
            pref_key = f"app:{category}"
            if pref_key not in self._preferences:
                self._preferences[pref_key] = UserPreference(
                    key=pref_key, value=value, confidence=0.4
                )
            pref = self._preferences[pref_key]
            if pref.value == value:
                # Reinforce existing preference
                pref.usage_count += 1
                pref.last_used = now
                pref.confidence = min(pref.confidence + 0.05, 1.0)
            elif success and pref.confidence < 0.6:
                # User switched — if the old preference has low confidence,
                # start transitioning
                pref.usage_count += 1
                pref.last_used = now
                # Gradually shift confidence
                pref.confidence = max(pref.confidence - 0.05, 0.1)

        # Website preferences from open_website / search_on_platform
        if intent in ("OPEN_WEBSITE", "SEARCH_ON_PLATFORM") and platform:
            website_key = f"website:{platform}"
            if website_key not in self._preferences:
                self._preferences[website_key] = UserPreference(
                    key=website_key, value=platform, confidence=0.5
                )
            wpref = self._preferences[website_key]
            wpref.usage_count += 1
            wpref.last_used = now
            wpref.confidence = min(wpref.confidence + 0.03, 1.0)

    def _detect_categories(
        self,
        intent: str,
        entities: dict[str, Any],
        target: str,
        platform: str,
        query: str,
    ) -> list[tuple[str, str]]:
        """Return (category, value) pairs detected from the interaction."""
        results: list[tuple[str, str]] = []

        # Open app intent → infer category from app name
        if intent == "OPEN_APP" and target:
            resolved = self._resolve_app_category(target)
            if resolved:
                results.append(resolved)

        # Play music → music_app category
        if intent in ("PLAY_MUSIC", "PLAY_SPOTIFY") and platform:
            results.append(("music_app", platform))
        elif intent == "PLAY_MUSIC" and target:
            results.append(("music_app", target))

        # Play YouTube → video_app category
        if intent in ("PLAY_YOUTUBE",) and platform:
            results.append(("video_app", platform))

        # Search on platform → infer from platform
        if intent == "SEARCH_ON_PLATFORM" and platform:
            if platform in ("spotify", "youtube_music", "apple_music"):
                results.append(("music_app", platform))
            elif platform in ("youtube", "netflix", "twitch"):
                results.append(("video_app", platform))

        return results

    def _resolve_app_category(self, app_name: str) -> tuple[str, str] | None:
        """Map an app name to a (category, value) pair using synonyms."""
        app_lower = app_name.lower().strip()
        for category, mapping in SYNONYM_SUGGESTIONS.items():
            if app_lower in mapping:
                return (category, mapping[app_lower])
        return None

    def _record_time_pattern(
        self,
        intent: str,
        entities: dict[str, Any],
        tool_name: str,
        hour: int,
    ) -> None:
        """Update time-based usage patterns."""
        target = str(entities.get("target", "")).lower()
        category = self._resolve_time_category(intent, entities)
        if not category or not target:
            return

        # Find existing pattern in same hour range
        for pattern in self._time_patterns:
            if (
                pattern.category == category
                and pattern.value == target
                and pattern.hour_start <= hour <= pattern.hour_end
            ):
                pattern.count += 1
                pattern.confidence = min(pattern.count / 10.0, 1.0)
                return

        # New pattern: create with a ±1 hour window
        self._time_patterns.append(
            TimePattern(
                category=category,
                value=target,
                hour_start=max(hour - 1, 0),
                hour_end=min(hour + 1, 23),
                count=1,
                confidence=0.1,
            )
        )

    def _resolve_time_category(self, intent: str, entities: dict[str, Any]) -> str:
        """Map intent/entities to a time-pattern category."""
        platform = str(entities.get("platform", "")).lower()
        if intent in ("PLAY_MUSIC", "PLAY_SPOTIFY"):
            return "music_app"
        if intent == "PLAY_YOUTUBE":
            return "video_app"
        if intent in ("OPEN_WEBSITE", "SEARCH_WEB"):
            return "website"
        if intent == "OPEN_APP":
            return "app"
        return ""

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """Simple word-overlap Jaccard similarity."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    # ── Persistence ────────────────────────────────────────────────

    def _save_data(self) -> None:
        """Persist all learning data to JSON files."""
        try:
            prefs_file = self.data_dir / "user_preferences.json"
            prefs_data = {k: v.to_dict() for k, v in self._preferences.items()}
            prefs_file.write_text(json.dumps(prefs_data, indent=2), encoding="utf-8")

            tools_file = self.data_dir / "tool_usage.json"
            tools_data: dict[str, Any] = {}
            for intent, tools in self._tool_usage.items():
                tools_data[intent] = {
                    name: rec.to_dict() for name, rec in tools.items()
                }
            tools_file.write_text(json.dumps(tools_data, indent=2), encoding="utf-8")

            freq_file = self.data_dir / "command_frequency.json"
            freq_file.write_text(
                json.dumps(dict(self._command_frequency.most_common(500)), indent=2),
                encoding="utf-8",
            )

            failed_file = self.data_dir / "failed_commands.json"
            failed_data = [fc.to_dict() for fc in self._failed_commands[-500:]]
            failed_file.write_text(json.dumps(failed_data, indent=2), encoding="utf-8")

            patterns_file = self.data_dir / "time_patterns.json"
            patterns_data = [p.to_dict() for p in self._time_patterns]
            patterns_file.write_text(json.dumps(patterns_data, indent=2), encoding="utf-8")

        except Exception:
            pass  # Never crash on save failures

    def _load_data(self) -> None:
        """Load persisted learning data from JSON files."""
        try:
            prefs_file = self.data_dir / "user_preferences.json"
            if prefs_file.exists():
                raw = json.loads(prefs_file.read_text(encoding="utf-8"))
                for key, data in raw.items():
                    self._preferences[key] = UserPreference.from_dict(data)

            tools_file = self.data_dir / "tool_usage.json"
            if tools_file.exists():
                raw = json.loads(tools_file.read_text(encoding="utf-8"))
                for intent, tools in raw.items():
                    for name, rec_data in tools.items():
                        self._tool_usage[intent][name] = ToolUsageRecord.from_dict(rec_data)

            freq_file = self.data_dir / "command_frequency.json"
            if freq_file.exists():
                raw = json.loads(freq_file.read_text(encoding="utf-8"))
                self._command_frequency.update(raw)

            failed_file = self.data_dir / "failed_commands.json"
            if failed_file.exists():
                raw = json.loads(failed_file.read_text(encoding="utf-8"))
                for data in raw:
                    self._failed_commands.append(FailedCommand.from_dict(data))

            patterns_file = self.data_dir / "time_patterns.json"
            if patterns_file.exists():
                raw = json.loads(patterns_file.read_text(encoding="utf-8"))
                for data in raw:
                    self._time_patterns.append(TimePattern.from_dict(data))

        except Exception:
            pass  # Never crash on load failures


# Global instance
learning_engine = LearningEngine()
