"""Decision Engine for JARVIS Cognitive Architecture.

Every action receives a score.

Score based on:
- Confidence
- Context
- Memory
- Risk
- Latency
- Tool Health
- Success History

Only highest confidence execution proceeds.

Supports:
- Multiple solution generation
- Decision tree logic
- Internal questions
- Automatic best-choice selection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from jarvis.cognitive.perception import Situation
from jarvis.cognitive.attention import Focus

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# DECISION MODEL
# ════════════════════════════════════════════════════════════════════

@dataclass
class DecisionOption:
    """A single decision option with scoring."""
    name: str = ""
    description: str = ""
    tool: str = ""
    handler: str = ""
    parameters: dict = field(default_factory=dict)
    confidence: float = 0.5
    risk_level: str = "low"       # low, medium, high
    estimated_latency_ms: float = 100.0
    success_probability: float = 0.8
    requires_confirmation: bool = False
    reasoning: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def score(self) -> float:
        """Combined score based on all factors."""
        s = self.confidence * 0.3
        s += self.success_probability * 0.3
        s += (1.0 - min(self.estimated_latency_ms / 5000, 1.0)) * 0.15
        risk_penalty = {"low": 0.0, "medium": 0.1, "high": 0.2}.get(self.risk_level, 0.0)
        s += (1.0 - risk_penalty) * 0.15
        if self.requires_confirmation:
            s *= 0.9
        return round(s, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tool": self.tool,
            "score": self.score,
            "confidence": round(self.confidence, 3),
            "risk": self.risk_level,
            "latency_ms": round(self.estimated_latency_ms, 1),
            "reasoning": self.reasoning,
        }


@dataclass
class Decision:
    """The final decision with ranked options."""
    chosen: DecisionOption
    alternatives: list[DecisionOption]
    all_options: list[DecisionOption]
    reasoning: str
    thinking_mode: str = "fast"   # fast, slow, research, coding
    internal_questions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chosen": self.chosen.to_dict(),
            "alternatives": [a.to_dict() for a in self.alternatives[:3]],
            "reasoning": self.reasoning,
            "thinking_mode": self.thinking_mode,
            "internal_questions": self.internal_questions,
        }


# ════════════════════════════════════════════════════════════════════
# DECISION TREES
# ════════════════════════════════════════════════════════════════════

# Predefined decision trees for common scenarios
_DECISION_TREES: dict[str, dict[str, Any]] = {
    "PLAY_MUSIC": {
        "question": "Is Spotify installed?",
        "yes": {
            "question": "Is Spotify running?",
            "yes": {"action": "play_on_spotify", "tool": "play_music", "params": {"platform": "spotify"}},
            "no": {"action": "launch_and_play_spotify", "tool": "open_app", "params": {"app": "Spotify"}, "then": "play_music"},
        },
        "no": {
            "question": "Is YouTube Music available?",
            "yes": {"action": "play_on_youtube_music", "tool": "play_music", "params": {"platform": "youtube_music"}},
            "no": {"action": "play_on_youtube", "tool": "play_music", "params": {"platform": "youtube"}},
        },
    },
    "OPEN_APP": {
        "question": "Is the app already running?",
        "yes": {"action": "focus_app", "tool": "window_control", "params": {"action": "focus"}},
        "no": {"action": "launch_app", "tool": "open_app"},
    },
    "SEARCH_WEB": {
        "question": "Is this a programming question?",
        "yes": {"action": "search_stackoverflow_github", "tool": "web_search", "params": {"platforms": ["stackoverflow", "github"]}},
        "no": {
            "question": "Is this a current event?",
            "yes": {"action": "search_news", "tool": "web_search", "params": {"platforms": ["news"]}},
            "no": {"action": "search_general", "tool": "web_search", "params": {"platforms": ["google"]}},
        },
    },
    "SYSTEM_POWER": {
        "question": "Is this a destructive action?",
        "yes": {"action": "confirm_shutdown", "requires_confirmation": True},
        "no": {"action": "execute_power", "tool": "system_power"},
    },
}


# ════════════════════════════════════════════════════════════════════
# INTERNAL QUESTIONS
# ════════════════════════════════════════════════════════════════════

_INTERNAL_QUESTIONS = [
    "What does the user actually want?",
    "Do I already know this?",
    "Should memory answer this?",
    "Should internet answer this?",
    "Should a tool answer this?",
    "Should I ask clarification?",
    "Can I automate this?",
    "Can I improve this workflow?",
]


# ════════════════════════════════════════════════════════════════════
# DECISION ENGINE
# ════════════════════════════════════════════════════════════════════

class DecisionEngine:
    """Scores and ranks actions to choose the best solution.

    Core principle: Think before acting.
    Generates multiple solutions, scores them, and picks the best.
    """

    def __init__(self) -> None:
        self._decision_history: list[Decision] = []
        self._tool_health_cache: dict[str, float] = {}
        self._success_history: dict[str, int] = {}
        self._failure_history: dict[str, int] = {}

    def decide(
        self,
        situation: Situation,
        focus: Focus,
        intent: str,
        entities: dict[str, Any] | None = None,
        tool_name: str = "",
        tool_health: float = 1.0,
    ) -> Decision:
        """Generate and rank decision options.

        Args:
            situation: Current situation from perception.
            focus: Filtered focus from attention system.
            intent: Detected intent.
            entities: Extracted entities.
            tool_name: Selected tool (from NLP pipeline).
            tool_health: Tool health score (0-1).

        Returns:
            Decision with chosen option and alternatives.
        """
        entities = entities or {}

        # Step 1: Ask internal questions
        internal_qs = self._ask_internal_questions(situation, focus, intent)

        # Step 2: Generate multiple solutions
        options = self._generate_options(
            situation, focus, intent, entities, tool_name, tool_health,
        )

        # Step 3: Apply decision tree if available
        if intent in _DECISION_TREES:
            tree_options = self._apply_decision_tree(
                intent, entities, tool_name, tool_health,
            )
            options.extend(tree_options)

        # Step 4: If no options generated, create a default
        if not options:
            options = [DecisionOption(
                name="default_execute",
                tool=tool_name,
                confidence=0.5,
                reasoning="No specific decision tree matched",
            )]

        # Step 5: Score and rank
        options.sort(key=lambda o: o.score, reverse=True)

        chosen = options[0]
        alternatives = options[1:4]  # Top 3 alternatives

        # Step 6: Determine thinking mode
        thinking_mode = self._determine_thinking_mode(situation, intent, entities)

        # Step 7: Build reasoning
        reasoning = self._build_reasoning(chosen, situation, focus, internal_qs)

        decision = Decision(
            chosen=chosen,
            alternatives=alternatives,
            all_options=options,
            reasoning=reasoning,
            thinking_mode=thinking_mode,
            internal_questions=internal_qs,
        )

        self._decision_history.append(decision)
        if len(self._decision_history) > 100:
            self._decision_history = self._decision_history[-50:]

        return decision

    def record_outcome(self, decision: Decision, success: bool) -> None:
        """Record the outcome of a decision for learning."""
        tool = decision.chosen.tool
        if tool:
            if success:
                self._success_history[tool] = self._success_history.get(tool, 0) + 1
            else:
                self._failure_history[tool] = self._failure_history.get(tool, 0) + 1

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_decisions": len(self._decision_history),
            "tools_succeeded": dict(self._success_history),
            "tools_failed": dict(self._failure_history),
        }

    # ── Private Methods ──

    @staticmethod
    def _ask_internal_questions(
        situation: Situation, focus: Focus, intent: str,
    ) -> list[str]:
        """Ask internal questions and return relevant ones."""
        relevant = []
        text = situation.user_input.lower()

        # "What does the user actually want?"
        if intent:
            relevant.append(f"What does the user actually want? -> {intent}")

        # "Do I already know this?"
        if situation.recent_memories:
            relevant.append("Do I already know this? -> Check memory")

        # "Should memory answer this?"
        if intent in ("RECALL_MEMORY", "ADD_NOTE", "SAVE_MEMORY"):
            relevant.append("Should memory answer this? -> Yes")

        # "Should internet answer this?"
        if intent in ("WEB_SEARCH", "GET_NEWS", "GET_WEATHER"):
            relevant.append("Should internet answer this? -> Yes")

        # "Can I automate this?"
        if situation.user_activity == "coding" and "debug" in text:
            relevant.append("Can I automate this? -> Consider debugging tools")

        return relevant

    @staticmethod
    def _generate_options(
        situation: Situation,
        focus: Focus,
        intent: str,
        entities: dict[str, Any],
        tool_name: str,
        tool_health: float,
    ) -> list[DecisionOption]:
        """Generate multiple decision options."""
        options = []

        # Option 1: Direct tool execution
        if tool_name:
            options.append(DecisionOption(
                name="direct_execute",
                description=f"Execute {tool_name} directly",
                tool=tool_name,
                confidence=tool_health * 0.9,
                success_probability=tool_health,
                risk_level="low",
                reasoning="Direct tool execution with good health",
            ))

        # Option 2: Alternative approach
        if tool_name:
            alternatives = {
                "web_search": "search_on_platform",
                "open_app": "open_website",
                "play_music": "search_youtube",
            }
            if tool_name in alternatives:
                alt_tool = alternatives[tool_name]
                options.append(DecisionOption(
                    name="alternative_tool",
                    description=f"Use alternative: {alt_tool}",
                    tool=alt_tool,
                    confidence=tool_health * 0.7,
                    success_probability=tool_health * 0.8,
                    risk_level="low",
                    reasoning="Alternative tool as backup",
                ))

        # Option 3: Ask user (for low confidence)
        if focus.attention_confidence < 0.5:
            options.append(DecisionOption(
                name="ask_user",
                description="Ask user for clarification",
                confidence=0.6,
                success_probability=0.9,
                risk_level="low",
                requires_confirmation=False,
                reasoning="Low attention confidence, ask for clarity",
            ))

        # Option 4: Memory lookup (if applicable)
        if situation.recent_memories:
            options.append(DecisionOption(
                name="memory_lookup",
                description="Check memory for answer",
                tool="memory_search",
                confidence=0.5,
                success_probability=0.6,
                risk_level="low",
                reasoning="Recent memories available",
            ))

        # Option 5: Emotional support (if emotional)
        if situation.user_emotion in ("frustrated", "angry", "sad", "tired"):
            options.append(DecisionOption(
                name="emotional_support",
                description="Provide emotional support first",
                confidence=0.7,
                success_probability=0.85,
                risk_level="low",
                reasoning=f"User is {situation.user_emotion}, offer support",
            ))

        return options

    @staticmethod
    def _apply_decision_tree(
        intent: str, entities: dict, tool_name: str, tool_health: float,
    ) -> list[DecisionOption]:
        """Apply predefined decision tree for an intent."""
        tree = _DECISION_TREES.get(intent)
        if not tree:
            return []

        options = []
        # Simplified: just create options from the tree leaves
        def traverse(node: dict, path: str = "") -> None:
            if "action" in node:
                options.append(DecisionOption(
                    name=node["action"],
                    tool=node.get("tool", tool_name),
                    parameters=node.get("params", {}),
                    requires_confirmation=node.get("requires_confirmation", False),
                    confidence=0.75 if tool_health > 0.5 else 0.5,
                    reasoning=f"Decision tree path: {path}",
                ))
            if "yes" in node:
                traverse(node["yes"], path + " -> yes")
            if "no" in node:
                traverse(node["no"], path + " -> no")

        traverse(tree)
        return options

    @staticmethod
    def _determine_thinking_mode(
        situation: Situation, intent: str, entities: dict[str, Any],
    ) -> str:
        """Determine the appropriate thinking mode."""
        # Fast thinking: simple, routine tasks
        fast_intents = {
            "OPEN_APP", "CLOSE_APP", "VOLUME_CONTROL", "BRIGHTNESS_CONTROL",
            "SCREENSHOT", "DATETIME", "CALCULATOR", "GREETING",
        }
        if intent in fast_intents:
            return "fast"

        # Research mode: information-seeking
        research_intents = {"WEB_SEARCH", "GET_NEWS", "GET_WEATHER", "STOCK_QUOTE"}
        if intent in research_intents:
            return "research"

        # Coding mode: programming-related
        coding_intents = {"PROGRAMMING", "VERSION_CONTROL", "DEBUG_CODE"}
        if intent in coding_intents:
            return "coding"

        # Slow thinking: complex, multi-step
        if any(w in situation.user_input.lower() for w in ["analyze", "compare", "explain", "research"]):
            return "slow"

        return "fast"

    @staticmethod
    def _build_reasoning(
        chosen: DecisionOption,
        situation: Situation,
        focus: Focus,
        internal_qs: list[str],
    ) -> str:
        """Build human-readable reasoning for the decision."""
        parts = [
            f"Chose: {chosen.name} (score={chosen.score:.3f})",
            f"Intent: {focus.primary_intent}",
            f"User state: {situation.user_emotion}, activity: {situation.user_activity}",
        ]
        if internal_qs:
            parts.append(f"Internal questions: {len(internal_qs)}")
        if chosen.reasoning:
            parts.append(f"Reasoning: {chosen.reasoning}")
        return " | ".join(parts)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

decision_engine = DecisionEngine()
