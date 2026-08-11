"""core/toolcall_parser.py — ToolCallParser + ToolValidator for JARVIS.

One canonical path for turning LLM output into executable ToolCall objects:

    LLM output
       ├── native tool call (structured chunks)   → parse_native
       ├── JSON emitted as text                   → parse_text
       └── normal text                            → (untouched)

Safety rules (mirror of the Tool Execution Contract):
- Only KNOWN registered tools are accepted.
- Arguments must match the registered schema (required args present).
- The parsed object must have the expected tool-call structure.
- Malformed JSON / unknown tools / invalid arguments stay ordinary text.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ToolCallParser:
    """Parses and validates tool calls from any LLM output shape."""

    def __init__(self, registry=None):
        from core.tools_registry import tool_registry

        self._registry = registry or tool_registry

    # ====================================================================
    # TEXT PARSING (JSON emitted as plain text by non-native models)
    # ====================================================================

    @staticmethod
    def _looks_like_tool_call(obj: Any) -> bool:
        """Strict structure check — only JSON with the expected shape."""
        if not isinstance(obj, dict):
            return False

        # OpenAI-style: {"function": {"name": ..., "arguments": ...}}
        if isinstance(obj.get("function"), dict):
            fn = obj["function"]
            return isinstance(fn.get("name"), str) and bool(fn.get("name"))

        # JARVIS-style: {"name": ..., "arguments": ...}
        name = obj.get("name")
        if isinstance(name, str) and name:
            return "arguments" in obj

        return False

    @staticmethod
    def _extract_from_object(obj: Dict[str, Any]) -> Optional[Tuple[str, Any, Optional[str]]]:
        """Normalize one JSON object into (name, arguments, call_id)."""
        call_id = obj.get("id") or None

        if isinstance(obj.get("function"), dict):
            fn = obj["function"]
            name = fn.get("name")
            if not isinstance(name, str) or not name:
                return None
            arguments = fn.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    parsed = json.loads(arguments)
                except json.JSONDecodeError:
                    return None
                arguments = parsed
            return name, arguments, call_id

        name = obj.get("name")
        if not isinstance(name, str) or not name:
            return None
        if "arguments" not in obj:
            return None
        arguments = obj.get("arguments")
        # Models sometimes stringify the arguments payload — parse it back.
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
            except json.JSONDecodeError:
                return None
            arguments = parsed
        return name, arguments, call_id

    def _candidates_from_text(self, text: str) -> List[Tuple[str, Any, Optional[str]]]:
        """Extract candidate tool-call objects from generated text."""
        candidates: List[Tuple[str, Any, Optional[str]]] = []
        stripped = text.strip()

        # 1. Parse top-level JSON (array or single object).
        json_candidates = []
        try:
            parsed = json.loads(stripped)

            def walk(node: Any) -> None:
                if isinstance(node, list):
                    for item in node:
                        walk(item)
                elif isinstance(node, dict):
                    if "tool_calls" in node and isinstance(node["tool_calls"], list):
                        walk(node["tool_calls"])
                        return
                    if self._looks_like_tool_call(node):
                        json_candidates.append(node)

            walk(parsed)
        except (json.JSONDecodeError, ValueError):
            pass

        for obj in json_candidates:
            normalized = self._extract_from_object(obj)
            if normalized:
                candidates.append(normalized)

        # 2. Embedded objects that appear mid-conversation (markdown fences,
        #    leading/trailing chatter). Use brace matching, then JSON-decode.
        if not candidates:
            start = 0
            while True:
                open_pos = stripped.find("{", start)
                if open_pos == -1:
                    break
                depth = 0
                in_string = False
                escape = False
                end_pos = -1
                for i in range(open_pos, len(stripped)):
                    ch = stripped[i]
                    if in_string:
                        if escape:
                            escape = False
                        elif ch == "\\":
                            escape = True
                        elif ch == '"':
                            in_string = False
                        continue
                    if ch == '"':
                        in_string = True
                    elif ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            end_pos = i
                            break
                if end_pos == -1:
                    break
                fragment = stripped[open_pos:end_pos + 1]
                try:
                    obj = json.loads(fragment)
                except json.JSONDecodeError:
                    start = open_pos + 1
                    continue
                if self._looks_like_tool_call(obj):
                    normalized = self._extract_from_object(obj)
                    if normalized:
                        candidates.append(normalized)
                start = open_pos + 1

        # 3. Legacy call syntax: open_application({"app_name": "chrome"})
        #    or open_application("chrome").
        if not candidates:
            for pattern in (
                r'(\w+)\s*\(\s*(\{[^}]+\})\s*\)',
                r'(\w+)\s*\(\s*["\']([^"\']+)["\']\s*\)',
            ):
                match = re.search(pattern, text)
                if not match:
                    continue
                name = match.group(1).lower()
                arg_str = match.group(2)
                arguments: Any = {}
                if arg_str.startswith("{"):
                    try:
                        arguments = json.loads(arg_str)
                    except json.JSONDecodeError:
                        continue
                else:
                    arguments = arg_str
                candidates.append((name, arguments, None))
                break

        return candidates

    def parse_text(self, text: str) -> List[Any]:
        """Parse LLM text output into validated ToolCall objects.

        Every candidate must pass registry + schema validation; anything
        unknown or malformed is ignored (stays ordinary text).
        """
        from core.brain_adapter import ToolCall

        if not text or not text.strip():
            return []

        result: List[ToolCall] = []
        seen: set = set()

        for name, arguments, call_id in self._candidates_from_text(text):
            ok, reason, normalized_args = self.validate(name, arguments)
            if not ok:
                logger.debug(
                    "Tool call ignored (%s): %s — %s", name, reason, arguments
                )
                continue

            key = (name, json.dumps(normalized_args, sort_keys=True))
            if key in seen:
                continue
            seen.add(key)

            result.append(
                ToolCall(name=name, arguments=normalized_args, call_id=call_id)
            )

        return result

    # ====================================================================
    # VALIDATION (ToolValidator)
    # ====================================================================

    def validate(
        self,
        tool_name: str,
        arguments: Any,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Validate a tool call against the registered schema.

        Returns (ok, reason, normalized_kwargs).
        """
        canonical = self._registry.resolve_name(tool_name)
        if not canonical:
            return False, "unknown_tool", None

        spec = self._registry.get(canonical)
        if spec is None:
            return False, "unknown_tool", None

        # Arguments must parse to a dict (or be a plain string that maps to
        # the first declared argument for legacy call syntax).
        normalized: Dict[str, Any] = {}
        if isinstance(arguments, dict):
            normalized = dict(arguments)
        elif isinstance(arguments, str):
            first_arg = next(iter(spec.arguments), "")
            if not first_arg:
                return False, "arguments_missing", None
            normalized = {first_arg: arguments}
        else:
            return False, "arguments_not_object", None

        # Required arguments must be present.
        missing = [
            name
            for name, type_desc in spec.arguments.items()
            if "optional" not in type_desc.lower() and name not in normalized
        ]
        if missing:
            return False, f"missing_arguments:{','.join(missing)}", None

        # Strip unknown/extra keys so handlers never receive unexpected kwargs.
        known = set(spec.arguments)
        for extra in [k for k in normalized if k not in known]:
            logger.debug("Dropping extra argument '%s' for %s", extra, canonical)
            normalized.pop(extra)

        return True, "valid", normalized


tool_call_parser = ToolCallParser()

__all__ = ["ToolCallParser", "tool_call_parser"]