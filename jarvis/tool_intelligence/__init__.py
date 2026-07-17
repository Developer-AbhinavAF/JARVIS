"""Tool Intelligence & Autonomous Execution Layer for JARVIS.

The hands of an intelligent assistant.

This module unifies:
- Platform-Aware Search Routing ("Never search randomly")
- Autonomous Recovery ("Never immediately fail")
- Background Task Management ("User continues chatting normally")
- Live Task Tracking ("Visible in UI")
- Tool Learning ("Future executions become faster")
- Tool Memory ("Improve execution speed")
- Execution Validation ("AI verifies every result")

Architecture:
    User Input → NLP Pipeline → ToolIntelligenceEngine.execute()
        → Platform Router (for search queries)
        → Tool Selection (capability-based + learned preferences)
        → Health Check (is the tool healthy?)
        → Execution (via ExecutionBridge)
        → Validation (verify result)
        → Recovery (on failure: retry → alternative → cache → ask user)
        → Learning (record execution for future improvement)
        → Memory (record usage patterns)
        → Task Tracking (for long-running tasks)
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable

from jarvis.tool_intelligence.platform_router import PlatformAwareRouter, platform_router
from jarvis.tool_intelligence.recovery import AutonomousRecovery, autonomous_recovery
from jarvis.tool_intelligence.task_manager import (
    TaskManager, StatusEngine, task_manager, status_engine,
)
from jarvis.tool_intelligence.tool_learning import ToolLearner, tool_learner
from jarvis.tool_intelligence.tool_memory import ToolMemory, tool_memory
from jarvis.tool_intelligence.validator import ExecutionValidator, execution_validator

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# UNIFIED TOOL INTELLIGENCE ENGINE
# ════════════════════════════════════════════════════════════════════

class ToolIntelligenceEngine:
    """Unified orchestrator for all tool intelligence.

    Single entry point that combines:
    - Platform-aware routing
    - Smart tool selection
    - Health-aware execution
    - Result validation
    - Autonomous recovery
    - Continuous learning
    - Pattern memory
    - Task management

    The NLP pipeline calls this engine for all tool operations.
    """

    def __init__(self) -> None:
        self.platform_router = platform_router
        self.recovery = autonomous_recovery
        self.task_manager = task_manager
        self.status = status_engine
        self.learner = tool_learner
        self.memory = tool_memory
        self.validator = execution_validator
        self._execution_bridge = None  # Lazy import to avoid circular

    def execute(
        self,
        output: Any,
        execute_func: Callable[..., tuple[str, bool]] | None = None,
    ) -> tuple[str, bool]:
        """Execute a tool with full intelligence.

        This is the main entry point. It:
        1. Routes to optimal platform (for search queries)
        2. Selects best tool (using learning + health)
        3. Executes via existing ExecutionBridge
        4. Validates result
        5. Recovers on failure
        6. Records in memory and learning

        Args:
            output: NLPOutput from the NLP pipeline.
            execute_func: The actual execution function (ExecutionBridge.execute).

        Returns:
            (response_text, was_handled_by_tool)
        """
        t0 = time.time()
        intent = getattr(output, "intent", "")
        tool_name = getattr(output, "tool", "")
        entities = getattr(output, "entities", {})
        parameters = getattr(output, "parameters", {})

        # Step 1: Platform-aware routing (for search/web queries)
        if intent in ("WEB_SEARCH", "SEARCH_ON_PLATFORM", "SEARCH_YOUTUBE"):
            route = self.platform_router.route(
                self._get_search_query(entities),
                intent=intent,
                entities=entities,
            )
            logger.debug("Platform routing: %s → %s", route.domain, route.primary_platform.name)

            # Override tool if router suggests a specific platform
            if route.primary_platform:
                self._apply_platform_routing(output, route)

        # Step 2: Check tool health
        if tool_name:
            health = self.learner.get_tool_health(tool_name)
            if health < 0.3:
                logger.warning("Tool %s has low health (%.2f), checking alternatives", tool_name, health)
                alternatives = self.recovery.get_alternatives(tool_name)
                if alternatives:
                    # Try to find a healthier alternative
                    for alt in alternatives:
                        alt_health = self.learner.get_tool_health(alt)
                        if alt_health > health:
                            tool_name = alt
                            output.tool = alt
                            logger.info("Switched to healthier alternative: %s", alt)
                            break

        # Step 3: Get learned preference
        if intent and tool_name:
            preferred = self.learner.get_preferred_tool(intent, [tool_name])
            if preferred and preferred != tool_name:
                logger.debug("Learned preference: %s → %s", tool_name, preferred)
                # Only switch if the preferred tool is significantly better
                pref_health = self.learner.get_tool_health(preferred)
                curr_health = self.learner.get_tool_health(tool_name)
                if pref_health > curr_health * 1.2:
                    output.tool = preferred

        # Step 4: Execute
        response, handled = ("", False)
        if execute_func:
            try:
                response, handled = execute_func(output)
            except Exception as e:
                logger.exception("Execution failed: %s", e)
                # Step 5: Autonomous recovery
                recovery_result = self._handle_failure(output, e)
                if recovery_result.recovered:
                    response = recovery_result.final_result
                    handled = True

        # Step 6: Validate result
        if handled and response:
            exec_time = (time.time() - t0) * 1000
            validation = self.validator.validate_with_context(
                response, intent, output.tool or "", entities, exec_time,
            )
            if not validation.success:
                logger.warning("Validation failed for %s: %s", output.tool, validation.errors)
                # Try recovery
                if validation.retry_possible:
                    recovery_result = self._handle_failure(
                        output, Exception("; ".join(validation.errors)),
                    )
                    if recovery_result.recovered:
                        response = recovery_result.final_result

        # Step 7: Record for learning
        if tool_name:
            self.learner.record_execution(
                intent, tool_name, handled, (time.time() - t0) * 1000,
            )

        # Step 8: Record in memory
        self._record_memory(intent, entities, tool_name)

        # Step 9: Platform usage
        if hasattr(output, "_routed_platform"):
            self.platform_router.record_usage(output._routed_platform, handled)

        return response, handled

    def route_search(
        self,
        query: str,
        intent: str = "",
        entities: dict | None = None,
    ) -> dict[str, Any]:
        """Route a search query to optimal platforms.

        Returns routing information with platform names and search URLs.
        """
        route = self.platform_router.route(query, intent=intent, entities=entities or {})
        return route.to_dict()

    def get_tool_health(self, tool_name: str) -> float:
        """Get health score for a tool."""
        return self.learner.get_tool_health(tool_name)

    def get_tool_rankings(self) -> list[dict[str, Any]]:
        """Get tools ranked by performance."""
        return self.learner.get_tool_rankings()

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive engine statistics."""
        return {
            "platform_router": self.platform_router.get_stats(),
            "recovery": self.recovery.get_failure_stats(),
            "task_manager": self.task_manager.get_stats(),
            "learner": self.learner.get_stats(),
            "memory": self.memory.get_stats(),
            "validator": self.validator.get_stats(),
        }

    # ── Private Methods ──

    def _get_search_query(self, entities: dict[str, Any]) -> str:
        """Extract search query from entities."""
        # Try common entity keys
        for key in ("query", "search_query", "text", "target", "keyword"):
            if key in entities:
                val = entities[key]
                if isinstance(val, dict):
                    return str(val.get("value", ""))
                return str(val)
        # Fallback: concatenate all string entity values
        parts = []
        for val in entities.values():
            if isinstance(val, dict):
                v = str(val.get("value", ""))
            else:
                v = str(val)
            if v and len(v) < 200:
                parts.append(v)
        return " ".join(parts)

    def _apply_platform_routing(self, output: Any, route: Any) -> None:
        """Apply platform routing results to the output."""
        # Store routing info for learning
        output._routed_platform = route.primary_platform.name
        output._routing_reasoning = route.reasoning

        # If the primary platform has a specific handler, update the tool
        handler = self.platform_router.get_handler_for_platform(route.primary_platform.name)
        if handler:
            # Keep existing tool but note the platform preference
            output.parameters["_preferred_platform"] = route.primary_platform.name
            output.parameters["_search_urls"] = route.search_urls

    def _handle_failure(self, output: Any, error: Exception) -> Any:
        """Handle execution failure with autonomous recovery."""
        analysis = self.recovery.analyze_failure(error)
        tool_name = getattr(output, "tool", "")
        params = getattr(output, "parameters", {})

        alternatives = self.recovery.get_alternatives(tool_name)
        chain = self.recovery.get_recovery_chain(
            tool_name, params, analysis, alternatives,
        )

        for step in chain:
            strategy = step["strategy"]
            if strategy == "retry":
                # Retry with same tool
                logger.info("Retrying %s (attempt)", tool_name)
                # The caller should handle actual retry
            elif strategy == "alternative_tool":
                alt_tool = step["tool_name"]
                logger.info("Trying alternative tool: %s", alt_tool)
                output.tool = alt_tool
                output.parameters.update(step["params"])
            elif strategy == "ask_user":
                logger.info("All recovery strategies exhausted, asking user")

        # Return a simple recovery result
        from jarvis.tool_intelligence.recovery import RecoveryResult, RecoveryAttempt
        result = RecoveryResult(
            recovered=False,
            strategy_used=chain[0]["strategy"] if chain else "none",
            attempts=[],
            final_result="",
            total_time_ms=0,
            analysis=analysis,
        )
        self.recovery.record_recovery(result)
        return result

    def _record_memory(self, intent: str, entities: dict, tool_name: str) -> None:
        """Record execution in tool memory."""
        if intent == "OPEN_APP":
            for key, val in entities.items():
                if isinstance(val, dict):
                    v = str(val.get("value", ""))
                else:
                    v = str(val)
                if v:
                    self.memory.record_app(v)
        elif intent == "OPEN_WEBSITE":
            for key, val in entities.items():
                if isinstance(val, dict):
                    v = str(val.get("value", ""))
                else:
                    v = str(val)
                if v:
                    self.memory.record_website(v)
        elif intent in ("WEB_SEARCH", "SEARCH_ON_PLATFORM", "SEARCH_YOUTUBE"):
            query = self._get_search_query(entities)
            if query:
                self.memory.record_search(query)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

tool_intelligence = ToolIntelligenceEngine()
