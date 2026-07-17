"""Execution bridge for JARVIS NLP engine.

Connects the NLP pipeline to the tool execution system.
Translates NLP output into executable tool calls.
"""

from __future__ import annotations

import importlib
import logging
import time
from typing import Any, Callable

from .utils import NLPOutput, ExecutionMode

logger = logging.getLogger(__name__)


class ExecutionBridge:
    """Bridges NLP output to tool execution.

    Flow:
        NLPOutput → resolve handler → validate params → execute → return result
    """

    def __init__(self) -> None:
        self._handler_cache: dict[str, Callable[..., Any]] = {}
        self._handler_cache["_webbrowser_open"] = self._webbrowser_open

    def execute(self, output: NLPOutput) -> tuple[str, bool]:
        """Execute the tool determined by the NLP pipeline.

        Args:
            output: Complete NLP pipeline output

        Returns:
            (response_text, was_handled)
        """
        if output.should_fallback_to_llm:
            return ("", False)

        if not output.tool or not output.handler:
            return ("", False)

        # Resolve handler
        handler = self._resolve_handler(output.handler)
        if not handler:
            logger.warning("Could not resolve handler: %s", output.handler)
            return ("", False)

        # Execute with parameters
        try:
            params = self._validate_params(handler, output.parameters)
            result = handler(**params)
            return (str(result) if result else "", True)
        except TypeError as e:
            # Parameter mismatch - try with flexible params
            logger.warning("Parameter mismatch for %s: %s", output.handler, e)
            return self._retry_with_flexible_params(handler, output.parameters)
        except Exception as e:
            logger.exception("Tool execution failed: %s", output.handler)
            return (f"Error: {e}", True)

    def _resolve_handler(self, handler_name: str) -> Callable[..., Any] | None:
        """Resolve a handler function from its dotted module path."""
        if handler_name in self._handler_cache:
            return self._handler_cache[handler_name]

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
        """Filter parameters to match handler signature."""
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
                continue
            else:
                valid[name] = ""
        return valid

    def _retry_with_flexible_params(
        self, handler: Callable, params: dict[str, Any]
    ) -> tuple[str, bool]:
        """Retry execution with only the params the handler accepts."""
        import inspect
        try:
            sig = inspect.signature(handler)
            valid_params = {}
            for param_name, param_obj in sig.parameters.items():
                if param_name in params:
                    valid_params[param_name] = params[param_name]
                elif param_obj.default is not inspect.Parameter.empty:
                    continue
                else:
                    return ("", False)
            result = handler(**valid_params)
            return (str(result) if result else "", True)
        except Exception as e:
            logger.exception("Flexible retry failed: %s", e)
            return ("", False)

    def _webbrowser_open(self, url: str = "", target: str = "") -> str:
        """Open a URL in the default browser."""
        import webbrowser
        open_url = url or target
        if not open_url:
            return "No URL provided."
        webbrowser.open(open_url)
        return f"Opening {open_url}"
