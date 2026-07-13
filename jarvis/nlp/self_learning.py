"""Self-learning engine for JARVIS NLP pipeline.

Tracks usage patterns, unknown commands, and failed matches to
continuously improve NLP accuracy over time.

Features:
- Unknown command tracking (what users tried but wasn't understood)
- Successful command frequency (what users do most often)
- Failed match analysis (what patterns need improvement)
- Synonym discovery (user vocabulary patterns)
- Usage statistics (peak hours, common queries)
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CommandStats:
    """Statistics for a single command pattern."""
    count: int = 0
    last_used: float = 0.0
    avg_confidence: float = 0.0
    success_rate: float = 1.0
    intent: str = ""
    tool_name: str = ""


@dataclass
class UnknownCommand:
    """A command that wasn't understood."""
    text: str
    normalized: str
    timestamp: float
    suggested_intent: str = ""
    suggested_confidence: float = 0.0


class SelfLearningEngine:
    """Tracks usage patterns and learns from user interactions.

    This engine collects anonymous statistics to improve NLP accuracy:
    - Tracks unknown commands for pattern improvement
    - Records successful/failed command executions
    - Identifies frequently used commands for priority boosting
    - Discovers user vocabulary patterns for synonym expansion
    - Stores data persistently for long-term learning
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent.parent / "data" / "nlp_learning"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # In-memory caches
        self._command_stats: dict[str, CommandStats] = {}
        self._unknown_commands: list[UnknownCommand] = []
        self._intent_frequency: Counter = Counter()
        self._tool_frequency: Counter = Counter()
        self._word_frequency: Counter = Counter()
        self._session_start = time.time()

        # Load existing data
        self._load_data()

    def record_successful_command(
        self,
        text: str,
        normalized: str,
        intent: str,
        tool_name: str,
        confidence: float,
    ) -> None:
        """Record a successfully executed command."""
        key = normalized.lower().strip()
        if key not in self._command_stats:
            self._command_stats[key] = CommandStats()

        stats = self._command_stats[key]
        stats.count += 1
        stats.last_used = time.time()
        stats.intent = intent
        stats.tool_name = tool_name

        # Update running average confidence
        total = stats.count
        stats.avg_confidence = ((stats.avg_confidence * (total - 1)) + confidence) / total

        # Track frequencies
        self._intent_frequency[intent] += 1
        self._tool_frequency[tool_name] += 1

        # Track word frequency
        for word in normalized.split():
            self._word_frequency[word] += 1

        # Auto-save periodically
        if stats.count % 10 == 0:
            self._save_data()

    def record_failed_command(
        self,
        text: str,
        normalized: str,
        suggested_intent: str = "",
        suggested_confidence: float = 0.0,
    ) -> None:
        """Record a command that wasn't understood."""
        unknown = UnknownCommand(
            text=text,
            normalized=normalized,
            timestamp=time.time(),
            suggested_intent=suggested_intent,
            suggested_confidence=suggested_confidence,
        )
        self._unknown_commands.append(unknown)

        # Keep only last 1000 unknowns
        if len(self._unknown_commands) > 1000:
            self._unknown_commands = self._unknown_commands[-1000:]

    def get_frequent_commands(self, top_n: int = 20) -> list[dict[str, Any]]:
        """Get the most frequently used commands."""
        sorted_stats = sorted(
            self._command_stats.items(),
            key=lambda x: x[1].count,
            reverse=True,
        )[:top_n]

        return [
            {
                "text": text,
                "count": stats.count,
                "intent": stats.intent,
                "tool_name": stats.tool_name,
                "avg_confidence": round(stats.avg_confidence, 2),
            }
            for text, stats in sorted_stats
        ]

    def get_unknown_commands(self, top_n: int = 20) -> list[dict[str, Any]]:
        """Get the most recent unknown commands."""
        # Count duplicates
        unknown_counts: Counter = Counter()
        for unknown in self._unknown_commands:
            unknown_counts[unknown.normalized] += 1

        return [
            {"text": norm, "count": count}
            for norm, count in unknown_counts.most_common(top_n)
        ]

    def get_popular_intents(self, top_n: int = 10) -> list[dict[str, Any]]:
        """Get the most popular intents."""
        return [
            {"intent": intent, "count": count}
            for intent, count in self._intent_frequency.most_common(top_n)
        ]

    def get_popular_tools(self, top_n: int = 10) -> list[dict[str, Any]]:
        """Get the most popular tools."""
        return [
            {"tool": tool, "count": count}
            for tool, count in self._tool_frequency.most_common(top_n)
        ]

    def get_vocabulary_stats(self) -> dict[str, Any]:
        """Get vocabulary usage statistics."""
        return {
            "total_words": sum(self._word_frequency.values()),
            "unique_words": len(self._word_frequency),
            "most_common_words": self._word_frequency.most_common(50),
        }

    def get_synonym_suggestions(self) -> list[dict[str, Any]]:
        """Analyze unknown commands to suggest potential synonyms."""
        suggestions = []
        for unknown in self._unknown_commands[-100:]:  # Last 100 unknowns
            # Try to find similar known commands
            for known_text, stats in self._command_stats.items():
                similarity = self._calculate_similarity(unknown.normalized, known_text)
                if 0.5 <= similarity < 1.0:
                    suggestions.append({
                        "unknown": unknown.text,
                        "similar_known": known_text,
                        "similarity": round(similarity, 2),
                        "intent": stats.intent,
                    })
                    break

        return suggestions[:20]

    def get_stats(self) -> dict[str, Any]:
        """Get overall learning statistics."""
        return {
            "total_commands_learned": len(self._command_stats),
            "total_executions": sum(s.count for s in self._command_stats.values()),
            "total_unknowns": len(self._unknown_commands),
            "unique_intents": len(self._intent_frequency),
            "unique_tools": len(self._tool_frequency),
            "session_duration_minutes": round((time.time() - self._session_start) / 60, 1),
        }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate word overlap similarity between two texts."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def _save_data(self) -> None:
        """Save learning data to disk."""
        try:
            # Save command stats
            stats_file = self.data_dir / "command_stats.json"
            stats_data = {
                key: {
                    "count": s.count,
                    "intent": s.intent,
                    "tool_name": s.tool_name,
                    "avg_confidence": s.avg_confidence,
                }
                for key, s in self._command_stats.items()
            }
            stats_file.write_text(json.dumps(stats_data, indent=2), encoding="utf-8")

            # Save unknown commands
            unknowns_file = self.data_dir / "unknown_commands.json"
            unknowns_data = [
                {"text": u.text, "normalized": u.normalized, "timestamp": u.timestamp}
                for u in self._unknown_commands[-500:]  # Keep last 500
            ]
            unknowns_file.write_text(json.dumps(unknowns_data, indent=2), encoding="utf-8")

            # Save frequency data
            freq_file = self.data_dir / "frequencies.json"
            freq_data = {
                "intents": dict(self._intent_frequency.most_common(100)),
                "tools": dict(self._tool_frequency.most_common(100)),
                "words": dict(self._word_frequency.most_common(500)),
            }
            freq_file.write_text(json.dumps(freq_data, indent=2), encoding="utf-8")

        except Exception:
            pass  # Don't crash on save failures

    def _load_data(self) -> None:
        """Load learning data from disk."""
        try:
            # Load command stats
            stats_file = self.data_dir / "command_stats.json"
            if stats_file.exists():
                stats_data = json.loads(stats_file.read_text(encoding="utf-8"))
                for key, data in stats_data.items():
                    self._command_stats[key] = CommandStats(
                        count=data.get("count", 0),
                        intent=data.get("intent", ""),
                        tool_name=data.get("tool_name", ""),
                        avg_confidence=data.get("avg_confidence", 0.0),
                    )

            # Load unknown commands
            unknowns_file = self.data_dir / "unknown_commands.json"
            if unknowns_file.exists():
                unknowns_data = json.loads(unknowns_file.read_text(encoding="utf-8"))
                for data in unknowns_data:
                    self._unknown_commands.append(UnknownCommand(
                        text=data.get("text", ""),
                        normalized=data.get("normalized", ""),
                        timestamp=data.get("timestamp", 0.0),
                    ))

            # Load frequency data
            freq_file = self.data_dir / "frequencies.json"
            if freq_file.exists():
                freq_data = json.loads(freq_file.read_text(encoding="utf-8"))
                self._intent_frequency.update(freq_data.get("intents", {}))
                self._tool_frequency.update(freq_data.get("tools", {}))
                self._word_frequency.update(freq_data.get("words", {}))

        except Exception:
            pass  # Don't crash on load failures


# Global instance
self_learning = SelfLearningEngine()
