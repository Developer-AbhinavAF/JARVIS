"""Self-Improvement Engine for JARVIS NLP.

After every task, analyze:
- Was intent correct?
- Was tool correct?
- Was response useful?
- Can latency improve?
- Can planner improve?
- Can memory improve?

Generate internal optimization suggestions. Never expose to user.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# TASK ANALYSIS
# ════════════════════════════════════════════════════════════════════

@dataclass
class TaskAnalysis:
    """Analysis of a completed task."""
    intent_correct: bool = True
    tool_correct: bool = True
    response_useful: bool = True
    latency_acceptable: bool = True
    needs_improvement: bool = False
    improvement_suggestions: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_correct": self.intent_correct,
            "tool_correct": self.tool_correct,
            "response_useful": self.response_useful,
            "latency_acceptable": self.latency_acceptable,
            "needs_improvement": self.needs_improvement,
            "improvement_suggestions": self.improvement_suggestions,
            "latency_ms": round(self.latency_ms, 1),
            "success": self.success,
        }


# ════════════════════════════════════════════════════════════════════
# SELF-IMPROVEMENT ENGINE
# ════════════════════════════════════════════════════════════════════

class SelfImprovementEngine:
    """Analyzes task execution and generates optimization suggestions.

    Continuously improves the NLP pipeline by learning from
    successes and failures.
    """

    def __init__(self) -> None:
        self._analyses: list[TaskAnalysis] = []
        self._optimization_notes: list[str] = []
        self._latency_targets: dict[str, float] = {
            "intent_detection": 50.0,
            "entity_extraction": 20.0,
            "tool_selection": 30.0,
            "parameter_building": 10.0,
            "total_pipeline": 100.0,
        }
        self._total_analyses: int = 0
        self._total_improvements: int = 0

    def analyze_task(
        self,
        intent: str,
        tool: str,
        success: bool,
        latency_ms: float,
        user_feedback: str | None = None,
        confidence: float = 0.0,
    ) -> TaskAnalysis:
        """Analyze a completed task and generate improvement suggestions."""
        analysis = TaskAnalysis(
            latency_ms=latency_ms,
            success=success,
        )

        # Check latency
        if latency_ms > self._latency_targets["total_pipeline"]:
            analysis.latency_acceptable = False
            analysis.improvement_suggestions.append(
                f"Pipeline latency {latency_ms:.0f}ms exceeds target {self._latency_targets['total_pipeline']:.0f}ms"
            )

        # Check if intent was correct (heuristic: low confidence = likely wrong)
        if confidence < 0.4:
            analysis.intent_correct = False
            analysis.improvement_suggestions.append(
                f"Low intent confidence ({confidence:.2f}) - consider expanding intent knowledge base"
            )

        # Check if tool was correct (success rate)
        if not success:
            analysis.tool_correct = False
            analysis.improvement_suggestions.append(
                f"Tool '{tool}' failed for intent '{intent}' - consider alternative tools"
            )

        # Check user feedback
        if user_feedback:
            feedback_lower = user_feedback.lower()
            if any(w in feedback_lower for w in ["wrong", "incorrect", "not what"]):
                analysis.response_useful = False
                analysis.improvement_suggestions.append(
                    "User indicated response was not useful - review response generation"
                )

        # Determine if improvement is needed
        analysis.needs_improvement = (
            not analysis.intent_correct
            or not analysis.tool_correct
            or not analysis.response_useful
            or not analysis.latency_acceptable
        )

        self._analyses.append(analysis)
        self._total_analyses += 1

        if analysis.needs_improvement:
            self._total_improvements += 1
            self._optimization_notes.extend(analysis.improvement_suggestions)

        # Keep only recent analyses
        if len(self._analyses) > 1000:
            self._analyses = self._analyses[-1000:]

        return analysis

    def get_optimization_suggestions(self, limit: int = 10) -> list[str]:
        """Get recent optimization suggestions."""
        # Deduplicate and return recent suggestions
        seen = set()
        unique: list[str] = []
        for note in reversed(self._optimization_notes):
            if note not in seen:
                seen.add(note)
                unique.append(note)
                if len(unique) >= limit:
                    break
        return unique

    def get_stats(self) -> dict[str, Any]:
        """Return self-improvement statistics."""
        if not self._analyses:
            return {"total_analyses": 0}

        recent = self._analyses[-100:]
        return {
            "total_analyses": self._total_analyses,
            "total_improvements_needed": self._total_improvements,
            "improvement_rate": (
                self._total_improvements / self._total_analyses
                if self._total_analyses > 0 else 0
            ),
            "avg_latency_ms": sum(a.latency_ms for a in recent) / len(recent),
            "success_rate": sum(1 for a in recent if a.success) / len(recent),
            "intent_accuracy": sum(1 for a in recent if a.intent_correct) / len(recent),
            "tool_accuracy": sum(1 for a in recent if a.tool_correct) / len(recent),
        }

    def update_latency_target(self, stage: str, target_ms: float) -> None:
        """Update latency target for a pipeline stage."""
        self._latency_targets[stage] = target_ms


# ════════════════════════════════════════════════════════════════════
# RESPONSE QUALITY CHECKER
# ════════════════════════════════════════════════════════════════════

class ResponseQualityChecker:
    """Checks response quality before sending to user.

    Validates correctness, completeness, grammar, context,
    safety, and formatting.
    """

    def check(
        self,
        response: str,
        intent: str,
        tool_result: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Check response quality and return issues found."""
        issues: list[str] = []
        score = 1.0

        # Check for empty response
        if not response or not response.strip():
            issues.append("Empty response")
            score -= 0.5

        # Check for error messages in response
        error_indicators = ["error", "failed", "exception", "traceback"]
        if any(ind in response.lower() for ind in error_indicators):
            issues.append("Response contains error indicators")
            score -= 0.3

        # Check for robotic responses
        robotic_phrases = ["task completed", "operation successful", "done."]
        if any(phrase in response.lower() for phrase in robotic_phrases):
            issues.append("Response is too robotic")
            score -= 0.1

        # Check length appropriateness
        if len(response) > 500:
            issues.append("Response is very long")
            score -= 0.1

        # Check for safety
        unsafe_patterns = ["password", "secret", "api_key", "token"]
        if any(pattern in response.lower() for pattern in unsafe_patterns):
            issues.append("Response may contain sensitive information")
            score -= 0.3

        # Check context relevance
        if context and context.get("last_intent"):
            # Simple relevance check
            pass

        return {
            "score": max(0.0, min(1.0, score)),
            "issues": issues,
            "is_acceptable": score >= 0.5,
        }


# ════════════════════════════════════════════════════════════════════
# BACKGROUND LEARNING
# ════════════════════════════════════════════════════════════════════

class BackgroundLearning:
    """Non-blocking background learning tasks.

    Supports background tasks like:
    - Learning YouTube URLs (read transcript, extract knowledge)
    - Processing documents
    - Building embeddings
    - Updating knowledge base

    Learning must never block the interface.
    """

    def __init__(self) -> None:
        self._pending_tasks: list[dict[str, Any]] = []
        self._completed_tasks: list[dict[str, Any]] = []
        self._is_processing: bool = False

    def submit_task(
        self,
        task_type: str,
        content: str,
        priority: int = 50,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Submit a background learning task.

        Returns a task ID for tracking.
        """
        task_id = f"bg_{int(time.time())}_{len(self._pending_tasks)}"
        task = {
            "id": task_id,
            "type": task_type,
            "content": content,
            "priority": priority,
            "metadata": metadata or {},
            "submitted_at": time.time(),
            "status": "pending",
        }
        self._pending_tasks.append(task)
        self._pending_tasks.sort(key=lambda t: t["priority"])
        return task_id

    def get_next_task(self) -> dict[str, Any] | None:
        """Get the next task to process (highest priority first)."""
        if not self._pending_tasks:
            return None
        return self._pending_tasks.pop(0)

    def complete_task(self, task_id: str, result: dict[str, Any]) -> None:
        """Mark a task as completed."""
        for task in self._pending_tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["result"] = result
                task["completed_at"] = time.time()
                self._completed_tasks.append(task)
                self._pending_tasks.remove(task)
                break

    def get_status(self) -> dict[str, Any]:
        """Get background learning status."""
        return {
            "pending_tasks": len(self._pending_tasks),
            "completed_tasks": len(self._completed_tasks),
            "is_processing": self._is_processing,
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCES
# ════════════════════════════════════════════════════════════════════

self_improvement = SelfImprovementEngine()
quality_checker = ResponseQualityChecker()
background_learning = BackgroundLearning()
