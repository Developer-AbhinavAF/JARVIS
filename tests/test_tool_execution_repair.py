"""Tool execution repair tests — routing, validation, execution, verification.

Verifies the Tool Execution Contract at the registry level:
- multi-command input reaches the agent loop (no fast-path swallowing)
- structured success/failure result shape
- meaningful verification (never blind success)
- argument normalization
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools_registry import tool_registry
from core.planner import planner_engine


class TestFastPathRouting:
    def test_open_youtube_fast_path(self):
        match = tool_registry.route_fast_path("open youtube")
        assert match is not None
        assert match.tool_name == "open_application"
        assert match.arguments == {"app_name": "youtube"}

    def test_open_notepad_fast_path(self):
        match = tool_registry.route_fast_path("open notepad")
        assert match is not None and match.tool_name == "open_application"

    def test_search_on_google_fast_path(self):
        match = tool_registry.route_fast_path("search gamerfleet on google")
        assert match is not None and match.tool_name == "web_search"
        assert match.arguments["query"] == "gamerfleet"

    def test_search_on_youtube_fast_path(self):
        match = tool_registry.route_fast_path("search gamerfleet on youtube")
        assert match is not None and match.tool_name == "youtube_search"
        assert match.arguments["query"] == "gamerfleet"

    def test_nasa_apod_fast_path(self):
        match = tool_registry.route_fast_path("show me today's NASA picture")
        assert match is not None and match.tool_name == "nasa_apod"

    def test_nasa_image_search_fast_path(self):
        match = tool_registry.route_fast_path("show me NASA images of Mars")
        assert match is not None and match.tool_name == "nasa_image_search"

    def test_multi_command_not_swallowed_by_fast_path(self):
        # "open youtube and search gamerfleet" must NOT be treated as a single
        # open_application call — the agent loop must plan both steps.
        assert tool_registry.route_fast_path(
            "open youtube and search gamerfleet"
        ) is None
        # chained download
        assert tool_registry.route_fast_path(
            "open spotify and play music"
        ) is None

    def test_conversation_never_routed(self):
        for query in ("hello", "how are you", "what is Python", "write an essay"):
            assert tool_registry.route_fast_path(query) is None, query

    def test_system_status_routing(self):
        match = tool_registry.route_fast_path("what is my CPU usage")
        assert match is not None and match.tool_name == "get_system_status"


class TestPlannerRouting:
    def test_conversation_plan_is_plain_response(self):
        plan = planner_engine.build_plan("hello")
        assert not plan.requires_tools

    def test_essay_plan_no_tools(self):
        plan = planner_engine.build_plan(
            "bro write a 400 word essay on how AI thinks"
        )
        assert not plan.requires_tools

    def test_open_plan_requires_tools(self):
        plan = planner_engine.build_plan("open youtube")
        assert plan.requires_tools

    def test_system_status_plan_requires_tools(self):
        plan = planner_engine.build_plan("what is my cpu usage")
        assert plan.requires_tools
        assert plan.steps[0].target == "system_status"

    def test_system_status_not_triggered_by_normal_chat(self):
        plan = planner_engine.build_plan(
            "bro write a 400 word essay on how AI thinks, forget about resources"
        )
        assert not plan.requires_tools


class TestExecutionShape:
    def test_unknown_tool_structured_failure(self):
        result = tool_registry.execute("ghost_tool", app_name="x")
        assert result["success"] is False
        assert result["tool"] == "ghost_tool"
        assert result["verified"] is False
        assert result["error"]
        # contract keys present
        assert {"success", "output", "verified", "error"} <= set(result)

    def test_empty_app_name_structured_failure(self):
        result = tool_registry.execute("open_application", app_name="")
        assert result["success"] is False
        assert result["error"]

    def test_web_search_empty_query_failure(self):
        result = tool_registry.execute("web_search", query="   ")
        assert result["success"] is False
        assert result["verified"] is False

    def test_youtube_search_requires_query(self):
        result = tool_registry.execute("youtube_search", query="")
        assert result["success"] is False

    def test_execute_via_alias(self):
        # "cpu usage" is an alias of get_system_status — no side effects.
        result = tool_registry.execute("cpu usage")
        assert result["success"] is True
        assert result["tool"] == "get_system_status"

    def test_extra_kwargs_do_not_crash_execute(self):
        # validator strips extras; executor must not raise
        ok, _, kwargs = tool_registry.validate_tool_call(
            "get_system_status", {"junk": 1}
        )
        assert ok
        result = tool_registry.execute("get_system_status", **kwargs)
        assert set(result) >= {"success", "verified", "tool"} and result["tool"] == "get_system_status"

    def test_execute_normalizes_int_args(self):
        from core.tools_registry import _safe_int
        assert _safe_int("7", 5) == 7
        assert _safe_int("abc", 5) == 5


class TestVerificationContract:
    def test_verification_requires_evidence(self):
        # A handler result without URL metadata must not verify as url_opened.
        fake = {
            "success": True,
            "output": "searched",
            "metadata": {"query": "x"},
        }
        verified, message = tool_registry.verify_tool_execution(
            "web_search", {"query": "x"}, fake
        )
        assert verified is False
        assert message in ("url_missing", "url_dispatched")

    def test_browser_dispatch_confirms(self):
        fake = {
            "success": True,
            "output": "ok",
            "metadata": {"url": "https://youtube.com", "url_dispatched": True},
        }
        verified, message = tool_registry.verify_tool_execution(
            "web_search", {"query": "x"}, fake
        )
        assert verified is True