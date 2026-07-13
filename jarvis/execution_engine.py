"""Unified execution engine for JARVIS.

This is the top-level orchestrator that sits between user input and all
tool/LLM processing. It replaces _route_and_execute() in main.py.

Flow:
  User Input
    -> CommandEngine.process()  (pattern matching, NO LLM)
    -> If matched: execute tool, return result
    -> If NOT matched: call LLM, return response

The LLM is ONLY called when no tool matches. This is mandatory.
"""

from __future__ import annotations

import importlib
import logging
import time
from typing import Any, Callable

from jarvis.command_engine import CommandEngine, CommandResult, engine as default_engine
from jarvis.tool_metadata import catalog
from jarvis.nlp.context_memory import context_memory
from jarvis.nlp.self_learning import self_learning

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Top-level execution engine: tool-first, LLM-last."""

    def __init__(self, command_engine: CommandEngine | None = None) -> None:
        self.command_engine = command_engine or default_engine
        self._handler_cache: dict[str, Callable[..., Any]] = {}
        self._handler_cache["_webbrowser_open"] = self._webbrowser_open

    def execute(self, query: str, llm_callable: Callable[..., Any] | None = None) -> tuple[str, bool]:
        """Execute a user query.

        Returns:
            (response_text, was_handled_by_tool)
            If was_handled_by_tool is True, the response came from a tool.
            If False, the response came from the LLM (or no response).
        """
        t0 = time.time()

        print(f"\n{'='*60}")
        print(f"[INPUT] {query}")

        # Phase 1: Run through command engine (pattern matching, NO LLM)
        result = self.command_engine.process(query)

        print(f"[NORMALIZED] {result.normalized_text}")

        if result.matched:
            print(f"[INTENT] {result.tool_name}")
            print(f"[CONFIDENCE] {result.confidence:.0%}")
            print(f"[MATCHED TOOL] {result.tool_name} -> {result.handler_name}")
            print(f"[PARAMS] {result.params}")
            print(f"[MATCH METHOD] {result.match_method}")

            elapsed = (time.time() - t0) * 1000
            logger.info(
                "COMMAND MATCH [%s] tool=%s conf=%.2f method=%s latency=%.1fms",
                query[:40], result.tool_name, result.confidence, result.match_method, elapsed,
            )

            # Execute the tool
            print(f"[EXECUTING] {result.tool_name}({result.params})")
            tool_result = self._execute_tool(result)
            if tool_result is not None:
                print(f"[SUCCESS] {str(tool_result)[:100]}")
                print(f"{'='*60}\n")

                # Update context memory with successful execution
                context_memory.update(
                    intent=result.tool_name,
                    entities=result.params,
                    target=result.handler_name,
                    query=query,
                )

                return (str(tool_result), True)

            # Tool execution failed, still mark as handled (don't fall to LLM)
            print(f"[TOOL_FALLBACK] Using message: {result.message}")
            print(f"{'='*60}\n")
            return (result.message or f"Executed {result.tool_name}.", True)

        print(f"[NO MATCH] Falling through to LLM")

        # Record failed command for self-learning
        self_learning.record_failed_command(
            text=query,
            normalized=result.normalized_text,
            suggested_intent=result.intent_result.intent if result.intent_result else "",
            suggested_confidence=result.intent_result.confidence if result.intent_result else 0.0,
        )

        # Phase 2: No tool matched -> LLM fallback
        if llm_callable:
            elapsed = (time.time() - t0) * 1000
            logger.info("LLM FALLBACK [%s] latency=%.1fms", query[:40], elapsed)
            print(f"[LLM CALL] Sending to LLM...")

            try:
                response = llm_callable(query)
                if isinstance(response, dict):
                    response = response.get("text", str(response))
                response_text = str(response) if response else ""
                print(f"[LLM RESPONSE] {response_text[:100]}")

                # Block forbidden LLM refusal patterns
                if self._is_forbidden_response(response_text):
                    logger.warning("Blocked LLM refusal for: %s", query[:40])
                    print(f"[BLOCKED] LLM refused to handle tool request")
                    print(f"{'='*60}\n")
                    return ("I encountered an issue processing your request. Please try rephrasing.", True)

                # Record successful LLM interaction for learning
                self_learning.record_successful_command(
                    text=query,
                    normalized=result.normalized_text,
                    intent="LLM_FALLBACK",
                    tool_name="llm",
                    confidence=0.5,
                )

                print(f"{'='*60}\n")
                return (response_text, True)
            except Exception as e:
                logger.exception("LLM call failed for: %s", query[:40])
                print(f"[LLM ERROR] {e}")
                print(f"{'='*60}\n")
                return (f"I encountered an issue: {e}", True)

        print(f"{'='*60}\n")
        return ("", False)

    def _execute_tool(self, result: CommandResult) -> Any:
        """Execute a tool based on CommandResult."""
        handler = self._resolve_handler(result.handler_name)
        if not handler:
            logger.warning("Could not resolve handler: %s", result.handler_name)
            return None

        try:
            # Validate parameters against handler signature
            params = self._validate_params(handler, result.params)
            tool_result = handler(**params)
            return tool_result
        except TypeError as e:
            # Parameter mismatch - try with just the params we have
            logger.warning("Parameter mismatch for %s: %s", result.handler_name, e)
            try:
                # Try to call with only the params the function accepts
                import inspect
                sig = inspect.signature(handler)
                valid_params = {}
                for param_name, param_obj in sig.parameters.items():
                    if param_name in result.params:
                        valid_params[param_name] = result.params[param_name]
                    elif param_obj.default is not inspect.Parameter.empty:
                        continue  # Use default
                    else:
                        # Required param missing - skip
                        return None
                return handler(**valid_params)
            except Exception as e2:
                logger.exception("Tool execution failed (param fix): %s", result.handler_name)
                return None
        except Exception as e:
            logger.exception("Tool execution failed: %s", result.handler_name)
            return None

    def _resolve_handler(self, handler_name: str) -> Callable[..., Any] | None:
        """Resolve a handler function from its dotted path, with caching."""
        if handler_name in self._handler_cache:
            return self._handler_cache[handler_name]

        # Special case: webbrowser open
        if handler_name == "webbrowser.open":
            return self._webbrowser_open

        try:
            parts = handler_name.rsplit(".", 1)
            if len(parts) != 2:
                return None
            module_path, func_name = parts
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            self._handler_cache[handler_name] = func
            return func
        except Exception as e:
            logger.warning("Failed to import %s: %s", handler_name, e)
            return None

    def _validate_params(self, handler: Callable, params: dict[str, Any]) -> dict[str, Any]:
        """Validate and filter parameters to match handler signature."""
        import inspect
        try:
            sig = inspect.signature(handler)
        except (TypeError, ValueError):
            return params

        valid = {}
        for name, param in sig.parameters.items():
            if name.startswith("_"):
                continue
            if name in params:
                valid[name] = params[name]
            elif param.default is not inspect.Parameter.empty:
                continue  # Will use default
            else:
                # Required param missing - provide empty string as fallback
                valid[name] = ""
        return valid

    def _webbrowser_open(self, url: str = "", target: str = "") -> str:
        """Open a URL in the default browser."""
        import webbrowser
        open_url = url or target
        if not open_url:
            return "No URL provided."
        webbrowser.open(open_url)
        return f"Opening {open_url}"

    def _is_forbidden_response(self, text: str) -> bool:
        """Check if the LLM response is a forbidden refusal pattern."""
        if not text:
            return False
        lower = text.lower()
        forbidden = [
            "i can't open", "i cannot open", "i'm unable to open",
            "i can't control", "i cannot control", "i'm unable to control",
            "i can't access", "i cannot access", "i'm unable to access",
            "i don't have access", "i do not have access",
            "i'm only a language model", "i am only a language model",
            "i'm just a language model", "i am just a language model",
            "i can only provide information", "i can only provide text",
            "as an ai", "as a language model",
            "i don't have the ability", "i do not have the ability",
            "i'm not able to", "i am not able to",
            "i don't have hands", "i cannot physically",
            "i can't physically", "i'm not a physical",
        ]
        return any(pattern in lower for pattern in forbidden)


# Global engine instance
execution_engine = ExecutionEngine()
