"""Execution Engine — Enforces tool-first execution.

The LLM should NEVER directly answer tool requests.
Every action goes through: NLP → Intent → Tool Selection → Execute → Verify → Respond.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any
from dataclasses import dataclass, field

from .tool_registry import ToolRegistry, ToolDef, ToolResult, ToolCategory, tool_registry
from .verifier import VerificationEngine, VerificationResult, verification_engine

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTrace:
    """Full trace of an execution for debug mode."""
    query: str = ""
    intent: str = ""
    intent_confidence: float = 0.0
    tool_name: str = ""
    tool_score: float = 0.0
    parameters: dict[str, Any] = field(default_factory=dict)
    execution_result: ToolResult | None = None
    verification: VerificationResult | None = None
    state_updated: bool = False
    total_latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "intent_confidence": round(self.intent_confidence, 3),
            "tool_name": self.tool_name,
            "tool_score": round(self.tool_score, 3),
            "parameters": self.parameters,
            "execution": self.execution_result.to_dict() if self.execution_result else None,
            "verification": {
                "verified": self.verification.verified,
                "details": self.verification.details,
                "latency_ms": round(self.verification.latency_ms, 1),
            } if self.verification else None,
            "state_updated": self.state_updated,
            "total_latency_ms": round(self.total_latency_ms, 1),
        }

    def format_debug(self) -> str:
        """Format trace for debug mode display."""
        lines = [
            f"Intent: {self.intent} (confidence={self.intent_confidence:.2f})",
            f"Tool: {self.tool_name} (score={self.tool_score:.2f})",
            f"Parameters: {self.parameters}",
        ]
        if self.execution_result:
            status = "SUCCESS" if self.execution_result.success else "FAILED"
            lines.append(f"Execution: {status} ({self.execution_result.execution_time_ms:.0f}ms)")
            if self.execution_result.error:
                lines.append(f"  Error: {self.execution_result.error}")
        if self.verification:
            vstatus = "PASSED" if self.verification.verified else "FAILED"
            lines.append(f"Verification: {vstatus} ({self.verification.latency_ms:.0f}ms)")
            lines.append(f"  {self.verification.details}")
        lines.append(f"Latency: {self.total_latency_ms:.0f}ms")
        return "\n".join(lines)


# Intent → Tool mapping for common requests
INTENT_TOOL_MAP: dict[str, list[str]] = {
    "open_app": ["open_app", "open_website", "open_browser"],
    "close_app": ["close_app", "close_process"],
    "search": ["web_search", "search_google"],
    "create_file": ["create_file", "write_file"],
    "delete_file": ["delete_file"],
    "rename_file": ["rename_file"],
    "copy_file": ["copy_file"],
    "volume_up": ["adjust_volume"],
    "volume_down": ["adjust_volume"],
    "mute": ["mute_audio"],
    "screenshot": ["take_screenshot"],
    "system_status": ["get_system_stats"],
    "time": ["get_time"],
    "date": ["get_date"],
}


class ExecutionEngine:
    """Executes user requests through verified tool execution.

    NEVER claims an action occurred unless verified.

    Primary path: execute_from_nlp(nlp_output) — uses NLP pipeline output
    directly to find and execute the right tool with correct parameters.

    Fallback path: execute(query) — independent string matching (legacy).

    Usage:
        engine = ExecutionEngine()
        result = engine.execute("open youtube")
        print(result.to_dict())
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        verifier: VerificationEngine | None = None,
    ):
        self.registry = registry or tool_registry
        self.verifier = verifier or verification_engine
        self._traces: list[ExecutionTrace] = []
        self._lock = threading.Lock()
        self._debug_mode = False
        # Intent → tool name mapping for NLP-driven execution
        self._intent_tool_map: dict[str, str] = {
            "OPEN_WEBSITE": "open_app",
            "OPEN_APP": "open_app",
            "CLOSE_APP": "close_app",
            "SEARCH_WEB": "web_search",
            "WEB_SEARCH": "web_search",
            "SEARCH_YOUTUBE": "web_search",
            "SEARCH_ON_PLATFORM": "search_on_platform",
            "PLAY_YOUTUBE": "open_app",
            "PLAY_MUSIC": "open_app",
            "PLAY_SPOTIFY": "open_app",
            "GET_TIME": "get_time",
            "GET_DATE": "get_date",
            "DATETIME": "get_time",
            "SYSTEM_STATUS": "get_system_stats",
            "SCREENSHOT": "take_screenshot",
            "VOLUME_CONTROL": "adjust_volume",
            "ADD_NOTE": "add_note",
            "GET_NOTES": "get_notes",
            "LIST_NOTES": "get_notes",
            "ADD_TODO": "add_todo",
            "GET_TODOS": "get_todos",
            "LIST_TODOS": "get_todos",
            "COMPLETE_TODO": "complete_todo",
            "FILE_MANAGEMENT": "create_file",
            "OPEN_FOLDER": "open_app",
            "CLIPBOARD": "get_time",
            "WINDOW_CONTROL": "list_running_apps",
        }

    @property
    def debug_mode(self) -> bool:
        return self._debug_mode

    @debug_mode.setter
    def debug_mode(self, value: bool):
        self._debug_mode = value

    def execute_from_nlp(self, nlp_output) -> ToolResult:
        """Execute a tool based on NLP pipeline output.

        This is the PRIMARY execution path. Uses the intent, entities,
        and parameters computed by the NLP pipeline to find and execute
        the correct tool. No independent string matching.

        Args:
            nlp_output: NLPOutput from the NLP pipeline with intent,
                       entities, tool, parameters already resolved.

        Returns:
            ToolResult with success/failure and verification.
        """
        start = time.time()
        intent = getattr(nlp_output, "intent", "") or ""
        tool_name = getattr(nlp_output, "tool", "") or ""
        handler = getattr(nlp_output, "handler", "") or ""
        parameters = getattr(nlp_output, "parameters", {}) or {}
        entities = getattr(nlp_output, "entities", {}) or {}
        raw_text = getattr(nlp_output, "raw_text", "")

        trace = ExecutionTrace(
            query=raw_text,
            intent=intent,
            intent_confidence=getattr(nlp_output, "intent_confidence", 0.0),
        )

        # Step 1: Resolve tool name from NLP intent
        resolved_tool = self._intent_tool_map.get(intent, tool_name)
        if not resolved_tool:
            # Try matching tool name directly
            resolved_tool = tool_name

        # Step 2: Find tool in registry
        tool = self.registry.get(resolved_tool)
        if not tool:
            # Try finding by intent name directly
            tool = self.registry.get(intent.lower())
        if not tool:
            # Last resort: try string matching
            tools = self.registry.find_tools(raw_text, limit=1)
            if tools:
                tool, _ = tools[0]
                resolved_tool = tool.name
            else:
                trace.total_latency_ms = (time.time() - start) * 1000
                with self._lock:
                    self._traces.append(trace)
                return ToolResult(
                    success=False,
                    error=f"No tool found for intent '{intent}' (tool='{tool_name}')",
                    tool_name="",
                    execution_time_ms=(time.time() - start) * 1000,
                )

        trace.tool_name = resolved_tool
        trace.tool_score = 1.0

        # Step 3: Build parameters from NLP entities
        params = self._build_params_from_entities(tool, entities, parameters)
        trace.parameters = params

        # Step 4: Execute
        exec_start = time.time()
        try:
            result = tool.execute(**params)
            if not isinstance(result, ToolResult):
                result = ToolResult(
                    success=True,
                    result={"raw": result} if not isinstance(result, dict) else result,
                    tool_name=resolved_tool,
                )
            result.tool_name = resolved_tool
        except Exception as e:
            result = ToolResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                tool_name=resolved_tool,
            )
        result.execution_time_ms = (time.time() - exec_start) * 1000
        trace.execution_result = result

        # Step 5: Verify
        if result.success and tool.verify:
            verify_start = time.time()
            try:
                verified = tool.verify(**params)
                result.verified = bool(verified)
            except Exception as e:
                result.verified = False
                logger.warning("Verification failed for %s: %s", resolved_tool, e)
            result.verification_time_ms = (time.time() - verify_start) * 1000
            trace.verification = VerificationResult(
                verified=result.verified,
                details=f"Verified: {result.verified}",
                latency_ms=result.verification_time_ms,
            )
        elif result.success:
            result.verified = True

        trace.total_latency_ms = (time.time() - start) * 1000

        with self._lock:
            self._traces.append(trace)
            if len(self._traces) > 500:
                self._traces = self._traces[-500:]

        if self._debug_mode:
            logger.info("EXECUTION TRACE:\n%s", trace.format_debug())

        return result

    def _build_params_from_entities(
        self,
        tool: ToolDef,
        entities: dict[str, Any],
        nlp_params: dict[str, Any],
    ) -> dict[str, Any]:
        """Build tool parameters from NLP entities and parameters.

        Maps NLP entity keys to tool parameter names.
        """
        params: dict[str, Any] = {}
        tool_params = tool.parameters

        # Entity key → tool param name mapping
        entity_to_param = {
            "app": "app_name",
            "target": "app_name",
            "website": "app_name",
            "url": "url",
            "query": "query",
            "search_query": "query",
            "path": "file_path",
            "file_path": "file_path",
            "content": "content",
            "task": "task",
            "direction": "direction",
            "amount": "amount",
            "save_path": "save_path",
            "expression": "expression",
            "todo_id": "todo_id",
            "city": "city",
        }

        # Try to map entities to tool parameters
        for entity_key, param_name in entity_to_param.items():
            if param_name in tool_params:
                entity_val = entities.get(entity_key)
                if isinstance(entity_val, dict):
                    entity_val = entity_val.get("value", entity_val.get("raw_value", ""))
                if entity_val is not None:
                    params[param_name] = entity_val

        # Also try direct NLP parameter mapping
        for key, value in nlp_params.items():
            if key in tool_params and key not in params:
                if not key.startswith("_"):
                    params[key] = value

        # Special handling for volume: extract direction from raw text
        if "direction" in tool_params and "direction" not in params:
            raw = nlp_params.get("raw_text", "")
            text_lower = raw.lower() if isinstance(raw, str) else ""
            if "up" in text_lower or "increase" in text_lower:
                params["direction"] = "up"
            elif "down" in text_lower or "decrease" in text_lower or "lower" in text_lower:
                params["direction"] = "down"
            elif "mute" in text_lower:
                params["direction"] = "mute"

        # Special handling for amount in volume
        if "amount" in tool_params and "amount" not in params:
            for key, val in entities.items():
                if isinstance(val, str) and val.isdigit():
                    params["amount"] = int(val)
                    break
                elif isinstance(val, dict):
                    v = val.get("value", "")
                    if isinstance(v, str) and v.isdigit():
                        params["amount"] = int(v)
                        break

        return params

    def execute(self, query: str, context: dict[str, Any] | None = None) -> ToolResult:
        """Execute a user request via string matching. Legacy fallback path.

        Prefer execute_from_nlp() when NLP output is available.
        """
        start = time.time()
        trace = ExecutionTrace(query=query)

        # 1. Find matching tool
        tools = self.registry.find_tools(query, limit=3)
        if not tools:
            return ToolResult(
                success=False,
                error=f"No tool found for: {query}",
                tool_name="",
                execution_time_ms=(time.time() - start) * 1000,
            )

        best_tool, score = tools[0]
        trace.tool_name = best_tool.name
        trace.tool_score = score

        # 2. Extract parameters from query
        params = self._extract_params(query, best_tool, context)
        trace.parameters = params

        # 3. Execute
        exec_start = time.time()
        try:
            result = best_tool.execute(**params)
            if not isinstance(result, ToolResult):
                result = ToolResult(
                    success=True,
                    result={"raw": result} if not isinstance(result, dict) else result,
                    tool_name=best_tool.name,
                )
            result.tool_name = best_tool.name
        except Exception as e:
            result = ToolResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                tool_name=best_tool.name,
            )
        result.execution_time_ms = (time.time() - exec_start) * 1000
        trace.execution_result = result

        # 4. Verify (only if execution succeeded)
        if result.success and best_tool.verify:
            verify_start = time.time()
            try:
                verified = best_tool.verify(**params)
                result.verified = bool(verified)
            except Exception as e:
                result.verified = False
                logger.warning("Verification failed for %s: %s", best_tool.name, e)
            result.verification_time_ms = (time.time() - verify_start) * 1000
            trace.verification = VerificationResult(
                verified=result.verified,
                details=f"Verified: {result.verified}",
                latency_ms=result.verification_time_ms,
            )
        elif result.success:
            result.verified = True

        trace.total_latency_ms = (time.time() - start) * 1000

        with self._lock:
            self._traces.append(trace)
            if len(self._traces) > 500:
                self._traces = self._traces[-500:]

        if self._debug_mode:
            logger.info("EXECUTION TRACE:\n%s", trace.format_debug())

        return result

    def execute_direct(self, tool_name: str, params: dict[str, Any] | None = None) -> ToolResult:
        """Execute a specific tool by name with given parameters."""
        tool = self.registry.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not registered",
                tool_name=tool_name,
            )

        start = time.time()
        try:
            result = tool.execute(**(params or {}))
            if not isinstance(result, ToolResult):
                result = ToolResult(
                    success=True,
                    result={"raw": result} if not isinstance(result, dict) else result,
                    tool_name=tool_name,
                )
            result.tool_name = tool_name
            result.execution_time_ms = (time.time() - start) * 1000
        except Exception as e:
            result = ToolResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                tool_name=tool_name,
                execution_time_ms=(time.time() - start) * 1000,
            )

        # Verify
        if result.success and tool.verify:
            try:
                result.verified = bool(tool.verify(**(params or {})))
            except Exception:
                result.verified = False
        elif result.success:
            result.verified = True

        return result

    def _extract_params(self, query: str, tool: ToolDef, context: dict[str, Any] | None) -> dict[str, Any]:
        """Extract parameters from query based on tool definition."""
        params: dict[str, Any] = {}
        query_lower = query.lower().strip()

        # Common parameter extraction patterns
        if "app_name" in tool.parameters or "name" in tool.parameters:
            # Extract app name from "open X" or "close X"
            for prefix in ["open ", "close ", "launch ", "start ", "run "]:
                if query_lower.startswith(prefix):
                    app = query_lower[len(prefix):].strip()
                    if "app_name" in tool.parameters:
                        params["app_name"] = app
                    if "name" in tool.parameters:
                        params["name"] = app
                    break

        if "query" in tool.parameters or "search_query" in tool.parameters:
            for prefix in ["search for ", "search ", "google ", "look up ", "find "]:
                if query_lower.startswith(prefix):
                    q = query_lower[len(prefix):].strip()
                    if "query" in tool.parameters:
                        params["query"] = q
                    if "search_query" in tool.parameters:
                        params["search_query"] = q
                    break

        if "url" in tool.parameters:
            for prefix in ["open ", "go to ", "navigate to "]:
                if query_lower.startswith(prefix):
                    url = query_lower[len(prefix):].strip()
                    if not url.startswith("http"):
                        url = f"https://{url}"
                    params["url"] = url
                    break

        if "file_path" in tool.parameters:
            # Try to extract file path
            words = query_lower.split()
            for i, word in enumerate(words):
                if "/" in word or "\\" in word or "." in word:
                    params["file_path"] = word
                    break

        if "content" in tool.parameters:
            for prefix in ["add note ", "write down ", "remember that ", "save note "]:
                if query_lower.startswith(prefix):
                    params["content"] = query_lower[len(prefix):].strip()
                    break

        if "task" in tool.parameters:
            for prefix in ["add todo ", "create task ", "new task ", "remember to "]:
                if query_lower.startswith(prefix):
                    params["task"] = query_lower[len(prefix):].strip()
                    break

        # Context override
        if context:
            params.update({k: v for k, v in context.items() if k in tool.parameters})

        return params

    def get_traces(self, limit: int = 20) -> list[ExecutionTrace]:
        with self._lock:
            return list(self._traces[-limit:])

    def get_last_trace(self) -> ExecutionTrace | None:
        with self._lock:
            return self._traces[-1] if self._traces else None

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            traces = list(self._traces)
        total = len(traces)
        success = sum(1 for t in traces if t.execution_result and t.execution_result.success)
        verified = sum(1 for t in traces if t.verification and t.verification.verified)
        avg_latency = sum(t.total_latency_ms for t in traces) / max(total, 1)
        return {
            "total_executions": total,
            "successful": success,
            "verified": verified,
            "success_rate": round(success / max(total, 1), 3),
            "avg_latency_ms": round(avg_latency, 1),
        }


# Global instance
execution_engine = ExecutionEngine()

__all__ = ["ExecutionEngine", "ExecutionTrace", "execution_engine", "INTENT_TOOL_MAP"]
