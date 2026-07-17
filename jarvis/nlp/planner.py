"""Execution planner for JARVIS NLP.

Creates execution plans (lists of PlanStep) for single and multi-step
user commands, handling decomposition, dependency detection, and
lightweight optimisation.
"""

from __future__ import annotations

import re
from typing import Any

from .utils import GoalCategory, PlanStep


# ════════════════════════════════════════════════════════════════════
# CONSTANTS
# ════════════════════════════════════════════════════════════════════

# Patterns that indicate compound commands
_COMPOUND_SEPARATORS: list[re.Pattern[str]] = [
    re.compile(r"\band\b", re.IGNORECASE),
    re.compile(r"\bthen\b", re.IGNORECASE),
    re.compile(r"\bafter that\b", re.IGNORECASE),
    re.compile(r"\balso\b", re.IGNORECASE),
    re.compile(r"\bwhile\b", re.IGNORECASE),
    re.compile(r"\b,\s*", re.IGNORECASE),
]

# Intent → default (tool, handler) mapping
_INTENT_TOOL_MAP: dict[str, tuple[str, str]] = {
    "open_app": ("system", "open_application"),
    "close_app": ("system", "close_application"),
    "open_vscode": ("system", "open_application"),
    "open_terminal": ("system", "open_application"),
    "open_chrome": ("system", "open_application"),
    "open_browser": ("system", "open_application"),
    "play_music": ("media", "play_music"),
    "play_song": ("media", "play_music"),
    "play_artist": ("media", "play_music"),
    "play_album": ("media", "play_music"),
    "play_video": ("media", "play_video"),
    "pause_media": ("media", "pause"),
    "next_track": ("media", "next_track"),
    "previous_track": ("media", "previous_track"),
    "search_web": ("search", "web_search"),
    "web_search": ("search", "web_search"),
    "search": ("search", "web_search"),
    "search_product": ("search", "product_search"),
    "set_reminder": ("productivity", "create_reminder"),
    "create_reminder": ("productivity", "create_reminder"),
    "set_alarm": ("productivity", "create_alarm"),
    "create_alarm": ("productivity", "create_alarm"),
    "take_note": ("productivity", "create_note"),
    "create_note": ("productivity", "create_note"),
    "manage_task": ("productivity", "create_task"),
    "create_task": ("productivity", "create_task"),
    "send_message": ("communication", "send_message"),
    "send_email": ("communication", "send_email"),
    "make_call": ("communication", "make_call"),
    "reply_message": ("communication", "send_message"),
    "adjust_volume": ("system", "set_volume"),
    "adjust_brightness": ("system", "set_brightness"),
    "toggle_wifi": ("system", "toggle_wifi"),
    "toggle_bluetooth": ("system", "toggle_bluetooth"),
    "change_setting": ("system", "change_setting"),
    "screenshot": ("system", "screenshot"),
    "lock_screen": ("system", "lock_screen"),
    "shutdown": ("system", "shutdown"),
    "restart": ("system", "restart"),
    "stock_price": ("finance", "get_stock_price"),
    "portfolio": ("finance", "get_portfolio"),
    "crypto_price": ("finance", "get_crypto_price"),
    "market_data": ("finance", "get_market_data"),
    "tell_joke": ("entertainment", "tell_joke"),
    "play_game": ("entertainment", "launch_game"),
    "define": ("information", "define"),
    "explain": ("information", "explain"),
    "how_to": ("information", "search_web"),
    "what_is": ("information", "search_web"),
    "lookup": ("information", "search_web"),
    "find_course": ("education", "search_courses"),
    "tutorial": ("education", "search_tutorials"),
    "health_info": ("health", "health_search"),
    "exercise_plan": ("health", "exercise_plan"),
    "symptom_check": ("health", "symptom_check"),
    "check_social_feed": ("social", "check_feed"),
    "post_content": ("social", "post"),
}

# Sequencing hints: second step depends on first result
_SEQUENTIAL_KEYWORDS: set[str] = {
    "then", "after that", "and search", "and find",
    "and open", "and show", "and summarize", "and summarize",
}

# Keywords that suggest the second step needs output from the first
_NEEDS_RESULT_KEYWORDS: set[str] = {
    "summarize", "summarise", "translate", "convert",
    "analyze", "analyse", "rewrite", "format",
    "extract", "compare", "review",
}


# ════════════════════════════════════════════════════════════════════
# PLANNER
# ════════════════════════════════════════════════════════════════════

class Planner:
    """Creates execution plans from classified intents and entities.

    Breaks compound commands into steps, resolves dependencies between
    steps, and applies lightweight plan optimisation (merging, reordering).
    """

    def plan(
        self,
        intent: str,
        entities: dict[str, Any],
        context: dict[str, Any],
        goal: GoalCategory,
    ) -> list[PlanStep]:
        """Create an execution plan for the given command.

        Args:
            intent: The classified intent string.
            entities: Extracted entities from the NER stage.
            context: Session context (previous commands, user prefs, etc.).
            goal: The detected goal category.

        Returns:
            An ordered list of PlanSteps to execute.
        """
        full_text = context.get("raw_text", "") or context.get("normalized_text", "")
        sub_intents = context.get("sub_intents", [])

        # Compound detection via sub_intents or text splitting
        sub_texts: list[str] = []
        if sub_intents:
            sub_texts = sub_intents
        elif full_text:
            sub_texts = self._decompose_compound(full_text)

        # Simple single-step command
        if len(sub_texts) <= 1:
            step = self._build_step(
                intent, entities, step_id=0,
                description=full_text or intent,
            )
            return [step]

        # Multi-step: build a step per sub-command
        steps: list[PlanStep] = []
        for idx, sub_text in enumerate(sub_texts):
            sub_entities = self._extract_sub_entities(sub_text, entities)
            sub_intent = self._infer_sub_intent(sub_text, intent)
            step = self._build_step(
                sub_intent,
                sub_entities,
                step_id=idx,
                description=sub_text.strip(),
            )
            steps.append(step)

        steps = self._detect_step_dependencies(steps)
        steps = self._optimize_plan(steps)
        return steps

    # ──────────────────────────────────────────────────────────────
    # Decomposition
    # ──────────────────────────────────────────────────────────────

    def _decompose_compound(self, text: str) -> list[str]:
        """Split a compound command into individual sub-commands.

        Examples:
            "open chrome and search X on GitHub"
                → ["open chrome", "search X on GitHub"]
            "Play Believer and lower volume"
                → ["Play Believer", "lower volume"]

        Args:
            text: The full normalized command text.

        Returns:
            A list of sub-command strings (length >= 1).
        """
        text = text.strip()
        if not text:
            return [text]

        # Try each separator pattern
        for pattern in _COMPOUND_SEPARATORS:
            if pattern.search(text):
                parts = pattern.split(text, maxsplit=1)
                if len(parts) == 2:
                    left = parts[0].strip().rstrip(",;")  # noqa: E501
                    right = parts[1].strip().lstrip(",;")  # noqa: E501
                    if left and right:
                        # Recurse on each half for deeply compound commands
                        left_parts = self._decompose_compound(left)
                        right_parts = self._decompose_compound(right)
                        return left_parts + right_parts

        return [text]

    # ──────────────────────────────────────────────────────────────
    # Step building
    # ──────────────────────────────────────────────────────────────

    def _build_step(
        self,
        intent: str,
        entities: dict[str, Any],
        step_id: int,
        description: str = "",
    ) -> PlanStep:
        """Create a single PlanStep from intent and entities.

        Args:
            intent: The intent for this step.
            entities: Entities relevant to this step.
            step_id: Unique step identifier (0-based).
            description: Human-readable step description.

        Returns:
            A populated PlanStep.
        """
        tool, handler = _INTENT_TOOL_MAP.get(
            intent.lower(), ("unknown", "fallback")
        )
        return PlanStep(
            step_id=step_id,
            intent=intent,
            tool=tool,
            handler=handler,
            parameters=dict(entities),
            depends_on=[],
            description=description or intent,
        )

    # ──────────────────────────────────────────────────────────────
    # Dependency detection
    # ──────────────────────────────────────────────────────────────

    def _detect_step_dependencies(self, steps: list[PlanStep]) -> list[PlanStep]:
        """Add dependency info between sequential steps.

        Rules:
        - If a step description contains keywords that suggest it needs
          a previous result (summarize, translate, etc.), it depends on
          the immediately preceding step.
        - "then" and "after that" create a strict chain.

        Args:
            steps: The list of steps (with no dependencies yet).

        Returns:
            The same list with ``depends_on`` populated.
        """
        if len(steps) <= 1:
            return steps

        for idx in range(1, len(steps)):
            desc_lower = steps[idx].description.lower()
            prev_desc = steps[idx - 1].description.lower()

            needs_result = any(kw in desc_lower for kw in _NEEDS_RESULT_KEYWORDS)
            is_sequential = any(kw in prev_desc for kw in ("then", "after that"))

            if needs_result or is_sequential:
                steps[idx].depends_on = [steps[idx - 1].step_id]

        return steps

    # ──────────────────────────────────────────────────────────────
    # Plan optimisation
    # ──────────────────────────────────────────────────────────────

    def _optimize_plan(self, steps: list[PlanStep]) -> list[PlanStep]:
        """Lightweight plan optimisation.

        - Merge duplicate consecutive steps with the same handler.
        - Remove steps whose dependency was removed.
        - Reorder independent steps by estimated execution cost.

        Args:
            steps: The dependency-resolved step list.

        Returns:
            An optimised step list.
        """
        if len(steps) <= 1:
            return steps

        # 1. Merge consecutive duplicates
        merged: list[PlanStep] = []
        for step in steps:
            if (
                merged
                and step.handler == merged[-1].handler
                and not step.depends_on
            ):
                # Merge parameters
                merged[-1].parameters.update(step.parameters)
                merged[-1].description += f"; {step.description}"
            else:
                merged.append(step)

        # 2. Re-index step IDs after merging
        for new_id, step in enumerate(merged):
            step.step_id = new_id

        # 3. Fix dependency references after re-indexing
        # Build old_id → new_id map
        old_ids = [s.step_id for s in steps]
        id_map = {}
        for old_id in old_ids:
            for new_id, new_step in enumerate(merged):
                if new_step.description == steps[old_id].description:
                    id_map[old_id] = new_id
                    break

        for step in merged:
            step.depends_on = [
                id_map.get(dep, dep) for dep in step.depends_on
            ]
            # Remove self-references and invalid refs
            step.depends_on = [
                d for d in step.depends_on
                if d != step.step_id and d < len(merged)
            ]

        return merged

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    def _extract_sub_entities(
        self,
        sub_text: str,
        all_entities: dict[str, Any],
    ) -> dict[str, Any]:
        """Heuristically assign entities to a sub-command.

        Checks if entity values appear in the sub-command text.
        Entities whose values match tokens in the sub-text are assigned.

        Args:
            sub_text: The sub-command string.
            all_entities: All entities from the original command.

        Returns:
            A dict of entities relevant to this sub-command.
        """
        if not all_entities:
            return {}

        sub_lower = sub_text.lower()
        relevant: dict[str, Any] = {}

        for key, value in all_entities.items():
            val_str = str(value).lower()
            # Direct substring match or individual token match
            if val_str in sub_lower:
                relevant[key] = value
            else:
                # Check individual tokens
                val_tokens = val_str.split()
                if any(tok in sub_lower for tok in val_tokens if len(tok) > 1):
                    relevant[key] = value

        # If nothing matched, return all entities for the first step only
        if not relevant:
            return dict(all_entities)

        return relevant

    def _infer_sub_intent(self, sub_text: str, parent_intent: str) -> str:
        """Infer the intent for a sub-command fragment.

        Uses simple keyword matching against the known intent-tool map.

        Args:
            sub_text: The sub-command text.
            parent_intent: The original parent intent (fallback).

        Returns:
            The inferred intent string for this sub-command.
        """
        sub_lower = sub_text.lower()
        keywords_hint: dict[str, str] = {
            "open": "open_app",
            "launch": "open_app",
            "start": "open_app",
            "close": "close_app",
            "quit": "close_app",
            "play": "play_music",
            "listen": "play_music",
            "search": "search_web",
            "find": "search_web",
            "look up": "search_web",
            "google": "search_web",
            "summarize": "explain",
            "summarise": "explain",
            "translate": "explain",
            "set": "set_reminder",
            "remind": "set_reminder",
            "alarm": "set_alarm",
            "volume": "adjust_volume",
            "bright": "adjust_brightness",
            "send": "send_message",
            "email": "send_email",
            "call": "make_call",
            "message": "send_message",
            "screenshot": "screenshot",
            "shutdown": "shutdown",
            "restart": "restart",
            "buy": "search_product",
            "price": "search_product",
            "stock": "stock_price",
            "joke": "tell_joke",
            "game": "play_game",
        }

        for keyword, intent in keywords_hint.items():
            if keyword in sub_lower:
                return intent

        return parent_intent

    # ──────────────────────────────────────────────────────────────
    # V3: Dependency graph & topological sort
    # ──────────────────────────────────────────────────────────────

    def build_dependency_graph(self, steps: list[PlanStep]) -> dict[int, list[int]]:
        """Build an adjacency list representation of step dependencies.

        Returns a dict mapping step_id → list of step_ids that depend on it.
        """
        graph: dict[int, list[int]] = {s.step_id: [] for s in steps}
        for step in steps:
            for dep_id in step.depends_on:
                if dep_id in graph:
                    graph[dep_id].append(step.step_id)
        return graph

    def topological_sort(self, steps: list[PlanStep]) -> list[PlanStep]:
        """Return steps in valid execution order using Kahn's algorithm.

        Detects cycles and raises ValueError if found.
        """
        graph = self.build_dependency_graph(steps)
        step_map = {s.step_id: s for s in steps}
        in_degree = {s.step_id: 0 for s in steps}
        for step in steps:
            for dep in step.depends_on:
                if dep in in_degree:
                    in_degree[step.step_id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        sorted_ids: list[int] = []

        while queue:
            current = queue.pop(0)
            sorted_ids.append(current)
            for neighbor in graph.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_ids) != len(steps):
            raise ValueError("Cycle detected in execution plan")

        return [step_map[sid] for sid in sorted_ids]

    def detect_parallel_groups(self, steps: list[PlanStep]) -> list[list[int]]:
        """Detect groups of steps that can run in parallel.

        Returns a list of groups, where each group is a list of step_ids
        that have no dependencies between them.
        """
        groups: list[list[int]] = []
        remaining = {s.step_id: s for s in steps}
        executed: set[int] = set()

        while remaining:
            ready = [
                sid for sid, s in remaining.items()
                if all(dep in executed for dep in s.depends_on)
            ]
            if not ready:
                break
            groups.append(ready)
            executed.update(ready)
            for sid in ready:
                del remaining[sid]

        return groups

    def get_execution_order(self, steps: list[PlanStep]) -> list[dict[str, Any]]:
        """Get a detailed execution order with parallel groups.

        Returns a list of execution phases, where each phase contains
        steps that can run in parallel.
        """
        groups = self.detect_parallel_groups(steps)
        step_map = {s.step_id: s for s in steps}
        order = []

        for phase_idx, group in enumerate(groups):
            phase_steps = []
            for sid in group:
                step = step_map[sid]
                phase_steps.append({
                    "step_id": step.step_id,
                    "intent": step.intent,
                    "tool": step.tool,
                    "handler": step.handler,
                    "description": step.description,
                })
            order.append({
                "phase": phase_idx + 1,
                "parallel": len(group) > 1,
                "steps": phase_steps,
            })

        return order
