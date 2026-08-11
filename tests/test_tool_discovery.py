"""tests/test_tool_discovery.py — Tests for tool discovery, NASA routing, and code execution fallback routing.

Verifies the full pipeline: query → planner → tool classification → tool card retrieval.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.planner import PlannerEngine
from core.tools_registry import UnifiedToolRegistry


planner = PlannerEngine()
registry = UnifiedToolRegistry()


# ── NASA / Visual routing ─────────────────────────────────────────────

NASA_QUERIES = [
    "show me today's NASA picture",
    "show today's astronomy picture",
    "NASA APOD",
    "what is today's astronomy picture?",
    "show me NASA's picture of the day",
    "show me pictures of black holes",
    "show NASA images of Mars",
    "find images of the James Webb telescope",
    "show me Apollo 11 pictures",
    "find pictures of Saturn",
    "show me Artemis images",
    "find NASA videos about black holes",
    "show me space images",
    "find galaxy images",
    "show nebula pictures",
]

NASA_ROUTING = [
    ("show me today's NASA picture", "nasa_apod"),
    ("NASA APOD", "nasa_apod"),
    ("astronomy picture of the day", "nasa_apod"),
    ("nasa image search mars", "nasa_image_search"),
    ("nasa search black holes", "nasa_image_search"),
    ("show nasa images", "nasa_image_search"),
    ("find nasa pictures of saturn", "nasa_image_search"),
]


class TestNasaRouting:
    """Verify NASA queries are routed to NASA tools."""

    def test_nasa_apod_detected_by_planner(self):
        """APOD queries should set requires_tools=True."""
        for q in ["show me today's NASA picture", "NASA APOD", "astronomy picture of the day"]:
            plan = planner.build_plan(q)
            assert plan.requires_tools is True, f"Expected requires_tools for '{q}'"

    def test_nasa_image_search_detected_by_planner(self):
        """Image search queries should set requires_tools=True."""
        for q in ["show NASA images of Mars", "find pictures of black holes", "show me Apollo 11 pictures"]:
            plan = planner.build_plan(q)
            assert plan.requires_tools is True, f"Expected requires_tools for '{q}'"

    def test_nasa_tool_classification(self):
        """NASA queries should classify to NASA tools."""
        for query, expected_tool in NASA_ROUTING:
            tool_name, arg_name, arg_value = registry.classify_input(query)
            assert tool_name == expected_tool, f"'{query}' → expected '{expected_tool}', got '{tool_name}'"

    def test_nasa_tool_exists(self):
        """NASA tools should be registered."""
        assert registry._handlers.get("nasa_apod") is not None
        assert registry._handlers.get("nasa_image_search") is not None

    def test_nasa_tool_cards(self):
        """NASA tools should appear in candidate search."""
        candidates = registry.search_candidates("NASA pictures of black holes", top_k=5)
        names = [c["name"] for c in candidates]
        assert "nasa_image_search" in names or "nasa_apod" in names

    def test_nasa_tool_spec_fields(self):
        """NASA tool specs should have required fields."""
        apod_spec = registry._registry.get("nasa_apod")
        assert apod_spec is not None
        assert apod_spec.name == "nasa_apod"
        assert "APOD" in apod_spec.description or "Astronomy" in apod_spec.description
        assert apod_spec.risk_level == "low"

        search_spec = registry._registry.get("nasa_image_search")
        assert search_spec is not None
        assert search_spec.name == "nasa_image_search"
        assert search_spec.risk_level == "low"

    def test_nasa_all_queries_route_correctly(self):
        """All NASA example queries should route via planner (requires_tools) or tool classification."""
        for q in NASA_QUERIES:
            plan = planner.build_plan(q)
            tool_name, _, _ = registry.classify_input(q)
            # Either planner detects it as tool-requiring OR classify_input finds a tool
            assert plan.requires_tools is True or tool_name != "", f"'{q}' not routed"


# ── Conversation protection ────────────────────────────────────────────

class TestNasaVsConversation:
    """Verify normal conversation does NOT trigger NASA tools."""

    def test_hello_not_nasa(self):
        plan = planner.build_plan("hello")
        tool_name, _, _ = registry.classify_input("hello")
        assert plan.requires_tools is False
        assert tool_name == ""

    def test_explain_nasa_not_search(self):
        """'explain NASA' should NOT trigger tools — it's a knowledge query."""
        plan = planner.build_plan("explain NASA")
        # Knowledge pattern should match, not external action
        assert plan.requires_tools is False

    def test_what_is_nasa_not_search(self):
        """'what is NASA' should NOT trigger tools."""
        plan = planner.build_plan("what is NASA")
        assert plan.requires_tools is False


# ── Existing tool routing still works ──────────────────────────────────

class TestExistingToolRouting:
    def test_open_youtube(self):
        tool_name, _, _ = registry.classify_input("open youtube")
        assert tool_name == "open_application"

    def test_search_google(self):
        tool_name, _, _ = registry.classify_input("search google for python")
        assert tool_name == "web_search"

    def test_search_youtube(self):
        tool_name, _, _ = registry.classify_input("search youtube for cats")
        assert tool_name == "youtube_search"


# ── Code execution fallback routing ────────────────────────────────────

class TestCodeExecutionRouting:
    def test_write_code_not_tool(self):
        """'write python calculator' should go to coding profile, not tools."""
        plan = planner.build_plan("write python calculator for me")
        assert plan.profile == "CODING"
        assert plan.requires_tools is False

    def test_generate_code_not_tool(self):
        plan = planner.build_plan("generate a python script to sort a list")
        assert plan.profile == "CODING"

    def test_create_script_not_tool(self):
        plan = planner.build_plan("create a javascript script for hello world")
        assert plan.profile == "CODING"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
