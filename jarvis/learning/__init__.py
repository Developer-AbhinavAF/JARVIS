"""Learning Engine — Master coordinator for all learning.

Makes JARVIS better over time through experience.

Learning Pipeline:
  Experience -> Observation -> Analysis -> Pattern Detection ->
  Learning -> Validation -> Memory Update -> Behavior Change -> Improvement
"""

from __future__ import annotations

import time
import logging
from typing import Any

from .safety import LearningSafety, learning_safety
from .experience_db import ExperienceDB, Experience, ExperienceCategory, Outcome, experience_db
from .preferences import PreferenceLearner, preference_learner
from .habits import HabitLearner, habit_learner
from .workflows import WorkflowLearner, workflow_learner
from .errors import ErrorLearner, error_learner
from .reasoning import ReasoningLearner, reasoning_learner
from .tools import ToolLearner, tool_learner
from .projects import ProjectLearner, project_learner
from .personality import PersonalityLearner, personality_learner
from .knowledge import KnowledgeLearner, knowledge_learner
from .memory_optimizer import MemoryOptimizer, memory_optimizer
from .behavior import BehaviorAdapter, behavior_adapter
from .evaluation import SelfEvaluator, self_evaluator
from .autonomous import AutonomousImprover, autonomous_improver
from .background import BackgroundLearningCoordinator, background_coordinator

logger = logging.getLogger(__name__)


class LearningEngine:
    """Master learning coordinator.

    Every interaction becomes training data.
    JARVIS learns, improves, and adapts continuously.
    """

    def __init__(self) -> None:
        # Safety
        self.safety: LearningSafety = learning_safety

        # Core storage
        self.experiences: ExperienceDB = experience_db

        # Learning modules
        self.preferences: PreferenceLearner = preference_learner
        self.habits: HabitLearner = habit_learner
        self.workflows: WorkflowLearner = workflow_learner
        self.errors: ErrorLearner = error_learner
        self.reasoning: ReasoningLearner = reasoning_learner
        self.tools: ToolLearner = tool_learner
        self.projects: ProjectLearner = project_learner
        self.personality: PersonalityLearner = personality_learner
        self.knowledge: KnowledgeLearner = knowledge_learner

        # Optimization
        self.memory_optimizer: MemoryOptimizer = memory_optimizer
        self.behavior: BehaviorAdapter = behavior_adapter
        self.evaluation: SelfEvaluator = self_evaluator
        self.improvement: AutonomousImprover = autonomous_improver
        self.background: BackgroundLearningCoordinator = background_coordinator

        self._interaction_count: int = 0
        self._learn_count: int = 0

    # ── Main Learning Interface ──────────────────────────────────

    def learn_from_interaction(
        self,
        user_input: str,
        response: str,
        intent: str = "",
        entities: dict | None = None,
        tool_used: str = "",
        tool_success: bool = True,
        latency_ms: float = 0.0,
        emotion: str = "",
    ) -> dict[str, Any]:
        """Process a complete interaction and learn from it."""
        t0 = time.perf_counter()
        self._interaction_count += 1

        # Safety check
        if not self.safety.is_safe(user_input):
            return {"learned": False, "reason": "unsafe_content"}

        # Store experience
        outcome = Outcome.SUCCESS if tool_success else Outcome.FAILURE
        exp = Experience(
            event=user_input,
            context={
                "intent": intent,
                "entities": entities or {},
                "tool_used": tool_used,
                "emotion": emotion,
            },
            decision=f"respond_with:{tool_used}" if tool_used else "respond",
            outcome=outcome,
            confidence=0.8 if tool_success else 0.3,
            category=self._categorize_interaction(intent),
            latency_ms=latency_ms,
        )
        self.experiences.store(exp)

        # Learn preference from repeated tool usage
        if tool_used:
            self.tools.record_use(tool_used, tool_success, latency_ms, intent=intent)

        # Learn habit from action
        if intent:
            self.habits.observe(intent, {"tool": tool_used, "success": tool_success})

        # Record reasoning
        if intent:
            self.reasoning.record(
                steps=[intent],
                decision=tool_used or "direct_response",
                outcome="success" if tool_success else "failure",
                confidence=0.8 if tool_success else 0.3,
                latency_ms=latency_ms,
            )

        # Learn error
        if not tool_success and tool_used:
            self.errors.learn_error(
                error_type="tool_failure",
                error_message=f"{tool_used} failed",
                tool=tool_used,
            )

        # Track performance metrics
        self.improvement.record_metric("latency", latency_ms)
        if self._interaction_count % 10 == 0:
            self.evaluation.update_metric(
                "response_quality",
                self.experiences.success_rate(),
            )

        self._learn_count += 1
        ms = (time.perf_counter() - t0) * 1000

        return {
            "learned": True,
            "experience_id": exp.experience_id,
            "latency_ms": round(ms, 1),
        }

    def learn_preference(self, category: str, key: str, value: Any) -> None:
        """Learn a user preference."""
        if self.safety.is_safe(str(value)):
            self.preferences.learn(category, key, value)

    def learn_from_error(
        self,
        error_type: str,
        error_message: str,
        fix: str = "",
        tool: str = "",
    ) -> None:
        """Learn from an error."""
        self.errors.learn_error(error_type, error_message, fix=fix, tool=tool)

    def learn_knowledge(
        self,
        source_type: str,
        title: str,
        summary: str = "",
        concepts: list[str] | None = None,
    ) -> None:
        """Learn from a knowledge source."""
        self.knowledge.learn(source_type, title, summary=summary, key_concepts=concepts or [])

    # ── Retrieval ────────────────────────────────────────────────

    def get_context(self, intent: str = "", user_input: str = "") -> dict[str, Any]:
        """Get learned context for a query."""
        ctx: dict[str, Any] = {}

        if intent:
            preferred_tool = self.tools.get_preferred_tool(intent)
            if preferred_tool:
                ctx["preferred_tool"] = preferred_tool

        if user_input:
            prediction = self.habits.predict_next(user_input)
            if prediction:
                ctx["predicted_next"] = prediction

        ctx["personality"] = self.personality.get_profile()
        ctx["behavior_settings"] = self.behavior.get_all_settings()

        return ctx

    def should_use_speech(self) -> bool:
        """Check if speech mode should be preferred."""
        return self.behavior.get_setting("prefer_speech", False)

    def get_response_style(self) -> dict[str, Any]:
        """Get the learned response style."""
        return self.personality.get_profile()

    # ── Maintenance ──────────────────────────────────────────────

    def run_optimization(self) -> dict[str, Any]:
        """Run background optimization tasks."""
        return self.memory_optimizer.optimize([])

    def run_evaluation(self) -> dict[str, Any]:
        """Run self-evaluation."""
        return self.evaluation.evaluate()

    def run_improvement_analysis(self) -> list[dict[str, Any]]:
        """Analyze and plan improvements."""
        actions = self.improvement.analyze()
        return [a.to_dict() for a in actions]

    # ── Stats ────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "interactions": self._interaction_count,
            "learn_count": self._learn_count,
            "experiences": self.experiences.get_stats(),
            "preferences": self.preferences.get_stats(),
            "habits": self.habits.get_stats(),
            "workflows": self.workflows.get_stats(),
            "errors": self.errors.get_stats(),
            "reasoning": self.reasoning.get_stats(),
            "tools": self.tools.get_stats(),
            "projects": self.projects.get_stats(),
            "personality": self.personality.get_stats(),
            "knowledge": self.knowledge.get_stats(),
            "memory_optimizer": self.memory_optimizer.get_stats(),
            "behavior": self.behavior.get_stats(),
            "evaluation": self.evaluation.get_stats(),
            "improvement": self.improvement.get_stats(),
            "background": self.background.get_stats(),
        }

    def _categorize_interaction(self, intent: str) -> ExperienceCategory:
        mapping = {
            "code": ExperienceCategory.TECHNICAL,
            "debug": ExperienceCategory.ERROR,
            "research": ExperienceCategory.KNOWLEDGE,
            "chat": ExperienceCategory.CONVERSATION,
            "open": ExperienceCategory.BEHAVIORAL,
            "search": ExperienceCategory.KNOWLEDGE,
        }
        for key, cat in mapping.items():
            if key in intent.lower():
                return cat
        return ExperienceCategory.CONVERSATION


learning_engine = LearningEngine()

__all__ = ["LearningEngine", "learning_engine"]
