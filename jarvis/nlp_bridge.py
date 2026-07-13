"""Bridge between NLP pipeline and existing JARVIS tool system.

This module connects the new NLP pipeline to the existing tool handlers,
ensuring the LLM is never called for tool execution decisions.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.nlp.tool_router import NLPToolRouter, ToolRoute, nlp_tool_router

logger = logging.getLogger(__name__)


def execute_nlp_route(route: ToolRoute) -> str:
    """Execute a tool based on NLP routing decision.

    Args:
        route: ToolRoute from NLP pipeline

    Returns:
        Tool execution result as string
    """
    if not route.should_execute:
        if route.should_fallback_to_llm:
            return ""  # Signal to caller to use LLM
        return f"Could not determine how to handle: {route.raw_query}"

    # Handle confirmation required
    if route.requires_confirmation:
        return f"⚠️ This action requires confirmation: {route.tool_name}. Are you sure?"

    # Execute the tool
    try:
        from jarvis.tool_router import ToolAction, execute_tool

        action = ToolAction(
            name=route.tool_name,
            confidence=route.confidence,
            handler=route.tool_name,
            params=route.params,
        )
        result = execute_tool(action)
        return str(result) if result else "Done."
    except Exception as e:
        logger.exception("Tool execution failed: %s", route.tool_name)
        return f"Tool '{route.tool_name}' failed: {e}"


def route_and_execute(query: str) -> tuple[str, bool]:
    """Route user query to tool and execute.

    This is the main entry point for the new NLP pipeline.

    Args:
        query: Raw user input

    Returns:
        Tuple of (response_text, was_handled_by_tool)
    """
    # Step 1: Route through NLP pipeline
    route = nlp_tool_router.route(query)

    # Step 2: Check if we should execute
    if route.should_execute:
        result = execute_nlp_route(route)
        if result:
            return (result, True)
        # If empty result, fall through to LLM

    # Step 3: Check if we should fallback to LLM
    if route.should_fallback_to_llm:
        return ("", False)

    # Step 4: Default - try execution anyway if we have a tool
    if route.tool_name and route.confidence >= 0.70:
        result = execute_nlp_route(route)
        if result:
            return (result, True)

    # Step 5: No tool matched, use LLM
    return ("", False)


# Keep the old interface for backwards compatibility
def route_input_old(text: str):
    """Old route_input interface - delegates to NLP pipeline."""
    from jarvis.tool_router import route_input as old_route_input
    return old_route_input(text)
