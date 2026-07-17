"""Experience Learning for JARVIS Cognitive Architecture.

Every execution becomes training data.

Store:
- Intent
- Reasoning Path
- Planner
- Tool
- Execution Time
- Success / Failure
- Recovery
- User Satisfaction

Future reasoning becomes better.
"""

from __future__ import annotations

import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_EXPERIENCE_FILE = _DATA_DIR / "cognitive_experiences.json"


# ════════════════════════════════════════════════════════════════════
# EXPERIENCE MODEL
# ════════════════════════════════════════════════════════════════════

@dataclass
class Experience:
    """A single execution experience."""
    experience_id: str = ""
    intent: str = ""
    tool_used: str = ""
    handler: str = ""

    # Execution details
    success: bool = True
    latency_ms: float = 0.0
    confidence: float = 0.5
    error: str = ""

    # Reasoning path
    reasoning_type: str = ""
    thinking_mode: str = "fast"
    decision_score: float = 0.0

    # Context
    user_emotion: str = "neutral"
    conversation_type: str = ""
    is_followup: bool = False

    # Outcome
    response_quality: float = 0.5
    user_satisfaction: float = 0.5  # Inferred

    # Learning
    should_retry: bool = False
    alternative_used: str = ""
    recovery_strategy: str = ""

    # Metadata
    timestamp: float = 0.0
    session_id: str = ""

    def __post_init__(self) -> None:
        if not self.experience_id:
            self.experience_id = f"exp_{int(time.time() * 1000)}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.experience_id,
            "intent": self.intent,
            "tool": self.tool_used,
            "success": self.success,
            "latency_ms": round(self.latency_ms, 1),
            "confidence": round(self.confidence, 3),
            "thinking_mode": self.thinking_mode,
            "user_emotion": self.user_emotion,
            "response_quality": round(self.response_quality, 3),
            "user_satisfaction": round(self.user_satisfaction, 3),
            "timestamp": self.timestamp,
        }


# ════════════════════════════════════════════════════════════════════
# EXPERIENCE LEARNING ENGINE
# ════════════════════════════════════════════════════════════════════

class ExperienceLearning:
    """Learns from every execution to improve future reasoning.

    Stores experiences and extracts patterns:
    - Which tools work best for which intents
    - What thinking mode is appropriate
    - What recovery strategies work
    - What user preferences emerge
    """

    def __init__(self, max_experiences: int = 2000) -> None:
        self._experiences: list[Experience] = []
        self._max_experiences = max_experiences
        self._intent_tool_stats: dict[str, dict[str, dict[str, int]]] = {}
        self._load()

    def record(
        self,
        intent: str,
        tool_used: str,
        success: bool,
        latency_ms: float = 0.0,
        confidence: float = 0.5,
        thinking_mode: str = "fast",
        user_emotion: str = "neutral",
        response_quality: float = 0.5,
        error: str = "",
        handler: str = "",
        reasoning_type: str = "",
        conversation_type: str = "",
        is_followup: bool = False,
    ) -> Experience:
        """Record a new experience."""
        # Infer user satisfaction from success + emotion + quality
        satisfaction = self._infer_satisfaction(success, user_emotion, response_quality)

        exp = Experience(
            intent=intent,
            tool_used=tool_used,
            handler=handler,
            success=success,
            latency_ms=latency_ms,
            confidence=confidence,
            error=error,
            reasoning_type=reasoning_type,
            thinking_mode=thinking_mode,
            user_emotion=user_emotion,
            conversation_type=conversation_type,
            is_followup=is_followup,
            response_quality=response_quality,
            user_satisfaction=satisfaction,
        )

        self._experiences.append(exp)

        # Update stats
        if intent not in self._intent_tool_stats:
            self._intent_tool_stats[intent] = {}
        if tool_used not in self._intent_tool_stats[intent]:
            self._intent_tool_stats[intent][tool_used] = {"success": 0, "failure": 0, "total_latency": 0}
        stats = self._intent_tool_stats[intent][tool_used]
        if success:
            stats["success"] += 1
        else:
            stats["failure"] += 1
        stats["total_latency"] += latency_ms

        # Trim
        if len(self._experiences) > self._max_experiences:
            self._experiences = self._experiences[-self._max_experiences // 2:]
            self._rebuild_stats()

        # Periodic save
        if len(self._experiences) % 50 == 0:
            self._save()

        return exp

    def get_best_tool(self, intent: str) -> str | None:
        """Get the best tool for an intent based on experience."""
        if intent not in self._intent_tool_stats:
            return None

        tools = self._intent_tool_stats[intent]
        best_tool = None
        best_score = -1.0

        for tool_name, stats in tools.items():
            total = stats["success"] + stats["failure"]
            if total == 0:
                continue
            success_rate = stats["success"] / total
            avg_latency = stats["total_latency"] / total
            score = success_rate * 0.7 + (1.0 - min(avg_latency / 5000, 1.0)) * 0.3
            if score > best_score:
                best_score = score
                best_tool = tool_name

        return best_tool

    def get_thinking_mode_stats(self) -> dict[str, int]:
        """Get usage stats for thinking modes."""
        modes: dict[str, int] = {}
        for exp in self._experiences:
            modes[exp.thinking_mode] = modes.get(exp.thinking_mode, 0) + 1
        return modes

    def get_stats(self) -> dict[str, Any]:
        if not self._experiences:
            return {"total_experiences": 0}
        total = len(self._experiences)
        successes = sum(1 for e in self._experiences if e.success)
        return {
            "total_experiences": total,
            "success_rate": round(successes / total, 3),
            "avg_latency_ms": round(
                sum(e.latency_ms for e in self._experiences) / total, 1,
            ),
            "avg_satisfaction": round(
                sum(e.user_satisfaction for e in self._experiences) / total, 3,
            ),
            "intents_tracked": len(self._intent_tool_stats),
            "thinking_modes": self.get_thinking_mode_stats(),
        }

    def _infer_satisfaction(self, success: bool, emotion: str, quality: float) -> float:
        """Infer user satisfaction from available signals."""
        satisfaction = 0.5
        if success:
            satisfaction += 0.2
        if emotion in ("happy", "excited", "satisfied"):
            satisfaction += 0.2
        elif emotion in ("frustrated", "angry"):
            satisfaction -= 0.2
        satisfaction += quality * 0.1
        return max(0.0, min(1.0, satisfaction))

    def _rebuild_stats(self) -> None:
        """Rebuild intent-tool stats from experiences."""
        self._intent_tool_stats = {}
        for exp in self._experiences:
            if exp.intent not in self._intent_tool_stats:
                self._intent_tool_stats[exp.intent] = {}
            if exp.tool_used not in self._intent_tool_stats[exp.intent]:
                self._intent_tool_stats[exp.intent][exp.tool_used] = {"success": 0, "failure": 0, "total_latency": 0}
            stats = self._intent_tool_stats[exp.intent][exp.tool_used]
            if exp.success:
                stats["success"] += 1
            else:
                stats["failure"] += 1
            stats["total_latency"] += exp.latency_ms

    def _save(self) -> None:
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "experiences": [e.to_dict() for e in self._experiences[-500:]],
                "saved_at": time.time(),
            }
            _EXPERIENCE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("Failed to save experiences: %s", e)

    def _load(self) -> None:
        try:
            if _EXPERIENCE_FILE.exists():
                data = json.loads(_EXPERIENCE_FILE.read_text())
                for exp_data in data.get("experiences", []):
                    exp = Experience(
                        experience_id=exp_data.get("id", ""),
                        intent=exp_data.get("intent", ""),
                        tool_used=exp_data.get("tool", ""),
                        success=exp_data.get("success", True),
                        latency_ms=exp_data.get("latency_ms", 0),
                        confidence=exp_data.get("confidence", 0.5),
                        thinking_mode=exp_data.get("thinking_mode", "fast"),
                        user_emotion=exp_data.get("user_emotion", "neutral"),
                        response_quality=exp_data.get("response_quality", 0.5),
                        user_satisfaction=exp_data.get("user_satisfaction", 0.5),
                        timestamp=exp_data.get("timestamp", 0),
                    )
                    self._experiences.append(exp)
                self._rebuild_stats()
        except Exception as e:
            logger.debug("Failed to load experiences: %s", e)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

experience_learning = ExperienceLearning()
