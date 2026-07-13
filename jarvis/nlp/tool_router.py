"""NLP-based tool router for JARVIS.

Routes user input to the correct tool using the NLP pipeline.
The LLM is NEVER used for tool selection - only as a fallback for
conversational queries.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .intent_classifier import IntentClassifier, IntentResult, intent_classifier
from .confidence import ConfidenceScorer, ConfidenceResult, confidence_scorer
from .parameter_parser import ParameterParser, ParsedParams, parameter_parser
from .command_parser import CommandParser, CommandChain, command_parser

logger = logging.getLogger(__name__)


@dataclass
class ToolRoute:
    """Complete routing decision for a user query."""
    tool_name: str
    params: dict[str, Any]
    confidence: float
    level: str  # auto_execute, execute, confirm, low, fallback
    intent: str
    reason: str
    should_execute: bool
    requires_confirmation: bool
    should_fallback_to_llm: bool
    raw_query: str = ""
    entities: dict[str, Any] = field(default_factory=dict)
    execution_plan: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"ToolRoute(tool={self.tool_name}, confidence={self.confidence:.2f}, "
            f"level={self.level}, execute={self.should_execute}, "
            f"confirm={self.requires_confirmation}, llm={self.should_fallback_to_llm})"
        )


class NLPToolRouter:
    """Main tool router that orchestrates the NLP pipeline.

    Pipeline:
        1. Normalize text
        2. Parse command chain (handle multi-commands)
        3. Classify intent (rule-based)
        4. Extract entities
        5. Parse parameters
        6. Score confidence
        7. Route to tool or fallback to LLM
    """

    def __init__(self) -> None:
        self.classifier = IntentClassifier()
        self.scorer = ConfidenceScorer()
        self.parser = ParameterParser()
        self.cmd_parser = CommandParser()

    def route(self, query: str) -> ToolRoute:
        """Route a user query to the appropriate tool.

        Args:
            query: Raw user input

        Returns:
            ToolRoute with routing decision
        """
        if not query or not query.strip():
            return ToolRoute(
                tool_name="",
                params={},
                confidence=0.0,
                level="fallback",
                intent="EMPTY",
                reason="Empty query",
                should_execute=False,
                requires_confirmation=False,
                should_fallback_to_llm=False,
                raw_query=query,
            )

        # Step 1: Parse command chain
        chain = self.cmd_parser.parse(query)

        # Step 2: If multi-command, route the first command
        # (multi-command handling is done at a higher level)
        if chain.is_multi and chain.commands:
            first_cmd = chain.commands[0]
            return self._route_single(first_cmd.text, original_query=query, is_multi=True, total_commands=chain.count)

        # Step 3: Route single command
        return self._route_single(query)

    def _route_single(self, text: str, original_query: str = "", is_multi: bool = False, total_commands: int = 1) -> ToolRoute:
        """Route a single command."""
        # Step 1: Classify intent
        intent_result = self.classifier.classify(text)

        # Step 2: Parse parameters from entities
        parsed_params = self.parser.parse(
            intent_result.intent,
            intent_result.entities,
            intent_result.action,
        )

        # Step 3: Score confidence
        confidence_result = self.scorer.score(
            raw_confidence=intent_result.confidence,
            action=parsed_params.tool_name,
            has_entity=len(intent_result.entities.entities) > 0,
        )

        # Step 4: Build execution plan
        execution_plan = self._build_execution_plan(
            intent_result.intent,
            parsed_params.tool_name,
            confidence_result,
        )

        # Step 5: Build route
        route = ToolRoute(
            tool_name=parsed_params.tool_name,
            params=parsed_params.params,
            confidence=confidence_result.score,
            level=confidence_result.level,
            intent=intent_result.intent,
            reason=confidence_result.reason,
            should_execute=confidence_result.should_execute,
            requires_confirmation=confidence_result.requires_confirmation,
            should_fallback_to_llm=confidence_result.should_fallback_to_llm,
            raw_query=original_query or text,
            entities=intent_result.entities.to_dict(),
            execution_plan=execution_plan,
        )

        logger.info("NLP Route: %s → %s (conf=%.2f, level=%s)",
                     text[:50], route.tool_name, route.confidence, route.level)

        return route

    def route_batch(self, queries: list[str]) -> list[ToolRoute]:
        """Route multiple queries."""
        return [self.route(q) for q in queries]

    def _build_execution_plan(self, intent: str, tool: str, confidence: ConfidenceResult) -> list[str]:
        """Build a human-readable execution plan."""
        plan = []

        if confidence.should_execute:
            plan.append(f"Intent: {intent}")
            plan.append(f"Tool: {tool}")
            plan.append(f"Confidence: {confidence.score:.0%}")
            if confidence.requires_confirmation:
                plan.append("Action: Awaiting confirmation (destructive)")
            else:
                plan.append("Action: Auto-executing")
        elif confidence.should_fallback_to_llm:
            plan.append("No matching tool found")
            plan.append("Falling back to LLM for response")
        else:
            plan.append(f"Low confidence: {confidence.score:.0%}")
            plan.append("Requires clarification or LLM fallback")

        return plan

    def get_supported_intents(self) -> list[str]:
        """Get all supported intents."""
        return self.classifier.get_supported_intents()

    def get_tool_for_intent(self, intent: str) -> str | None:
        """Get the default tool name for an intent."""
        result = self.classifier.classify(f"test {intent}")
        return result.action


# Global instance
nlp_tool_router = NLPToolRouter()
