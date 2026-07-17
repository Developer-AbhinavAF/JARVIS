"""Tests for Execution Engine — Tool-first, verified execution.

Tests tool registry, verification engine, execution engine, and core tools.
"""

import os
import time
import tempfile
import pytest
from pathlib import Path

from jarvis.execution.tool_registry import ToolRegistry, ToolDef, ToolResult, ToolCategory, tool_registry
from jarvis.execution.verifier import VerificationEngine, VerificationResult, VerificationType
from jarvis.execution.engine import ExecutionEngine, ExecutionTrace, execution_engine
from jarvis.execution.core_tools import (
    open_app, close_app, web_search, open_url,
    create_file, delete_file, read_file,
    get_time, get_date, get_system_stats, list_running_apps,
    add_note, get_notes, add_todo, get_todos, complete_todo,
    register_all_tools,
)


# ═══════════════════════════════════════════════════════════════════════
# TOOL REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestToolRegistry:
    def setup_method(self):
        self.registry = ToolRegistry()

    def test_register_tool(self):
        self.registry.register("test_tool", lambda: None, description="Test tool")
        assert self.registry.has("test_tool")

    def test_get_tool(self):
        self.registry.register("my_tool", lambda: None, description="My tool")
        tool = self.registry.get("my_tool")
        assert tool is not None
        assert tool.name == "my_tool"

    def test_unregister(self):
        self.registry.register("del_tool", lambda: None)
        self.registry.unregister("del_tool")
        assert not self.registry.has("del_tool")

    def test_find_tools(self):
        self.registry.register("open_chrome", lambda: None, description="Open Chrome browser")
        self.registry.register("close_chrome", lambda: None, description="Close Chrome browser")
        self.registry.register("open_firefox", lambda: None, description="Open Firefox browser")
        results = self.registry.find_tools("open chrome")
        assert len(results) > 0
        assert results[0][0].name == "open_chrome"

    def test_find_best(self):
        self.registry.register("web_search", lambda: None, description="Search the web")
        self.registry.register("local_search", lambda: None, description="Search local files")
        best = self.registry.find_best("search the web")
        assert best is not None
        assert best.name == "web_search"

    def test_get_enabled(self):
        self.registry.register("enabled_tool", lambda: None, enabled=True)
        self.registry.register("disabled_tool", lambda: None, enabled=False)
        enabled = self.registry.get_enabled()
        assert len(enabled) == 1

    def test_get_by_category(self):
        self.registry.register("tool_a", lambda: None, category=ToolCategory.APP)
        self.registry.register("tool_b", lambda: None, category=ToolCategory.FILE)
        app_tools = self.registry.get_by_category(ToolCategory.APP)
        assert len(app_tools) == 1

    def test_stats(self):
        self.registry.register("a", lambda: None, category=ToolCategory.APP)
        self.registry.register("b", lambda: None, category=ToolCategory.FILE)
        stats = self.registry.get_stats()
        assert stats["total"] == 2

    def test_intent_matching(self):
        tool = ToolDef(name="open_app", description="Open an application")
        assert tool.matches_intent("open chrome") > 0
        assert tool.matches_intent("close something") == 0.0

    def test_tool_result(self):
        result = ToolResult(success=True, result={"key": "value"}, tool_name="test")
        d = result.to_dict()
        assert d["success"] is True
        assert d["tool_name"] == "test"


# ═══════════════════════════════════════════════════════════════════════
# VERIFICATION ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestVerificationEngine:
    def setup_method(self):
        self.engine = VerificationEngine()

    def test_verify_process_running(self):
        result = self.engine.verify_process_running("python")
        assert isinstance(result, VerificationResult)
        assert result.latency_ms >= 0

    def test_verify_process_not_found(self):
        result = self.engine.verify_process_running("nonexistent_process_xyz_123")
        assert result.verified is False

    def test_verify_file_exists(self):
        tmp = tempfile.mktemp(suffix=".txt")
        Path(tmp).write_text("test")
        result = self.engine.verify_file_exists(tmp)
        assert result.verified is True
        os.remove(tmp)

    def test_verify_file_not_exists(self):
        result = self.engine.verify_file_exists("/nonexistent/file/path.txt")
        assert result.verified is False

    def test_verify_directory_exists(self):
        result = self.engine.verify_directory_exists(tempfile.gettempdir())
        assert result.verified is True

    def test_verify_file_content(self):
        tmp = tempfile.mktemp(suffix=".txt")
        Path(tmp).write_text("hello world")
        result = self.engine.verify_file_content(tmp, expected="hello")
        assert result.verified is True
        os.remove(tmp)

    def test_verify_file_content_missing(self):
        tmp = tempfile.mktemp(suffix=".txt")
        Path(tmp).write_text("hello world")
        result = self.engine.verify_file_content(tmp, expected="goodbye")
        assert result.verified is False
        os.remove(tmp)

    def test_verify_port_listening(self):
        result = self.engine.verify_port_listening(99999)
        assert result.verified is False

    def test_custom_check(self):
        self.engine.register_custom_check("always_true", lambda: True)
        result = self.engine.verify_custom("always_true")
        assert result.verified is True

    def test_custom_check_not_registered(self):
        result = self.engine.verify_custom("nonexistent")
        assert result.verified is False


# ═══════════════════════════════════════════════════════════════════════
# EXECUTION ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestExecutionEngine:
    def setup_method(self):
        self.registry = ToolRegistry()
        self.verifier = VerificationEngine()
        self.engine = ExecutionEngine(self.registry, self.verifier)

    def test_execute_tool(self):
        self.registry.register("echo", lambda text="": ToolResult(success=True, result={"text": text}), description="Echo text")
        result = self.engine.execute_direct("echo", {"text": "hello"})
        assert result.success is True
        assert result.result["text"] == "hello"

    def test_execute_tool_not_found(self):
        result = self.engine.execute_direct("nonexistent_tool")
        assert result.success is False
        assert "not registered" in result.error

    def test_execute_with_verification(self):
        tmp = tempfile.mktemp(suffix=".txt")

        def create_and_verify(name="test"):
            Path(tmp).write_text("test content")
            return ToolResult(success=True, result={"path": tmp})

        def verify_fn(name="test"):
            return os.path.isfile(tmp)

        self.registry.register("create_test", create_and_verify, verify=verify_fn, description="Create test file")
        result = self.engine.execute_direct("create_test", {"name": "test_exec"})
        assert result.success is True
        try:
            os.remove(tmp)
        except Exception:
            pass

    def test_execute_failure(self):
        def failing_tool():
            raise ValueError("intentional error")
        self.registry.register("fail_tool", failing_tool, description="Always fails")
        result = self.engine.execute_direct("fail_tool")
        assert result.success is False
        assert "intentional error" in result.error

    def test_traces(self):
        self.registry.register("trace_tool", lambda: ToolResult(success=True), description="Trace test")
        self.engine.execute("trace tool")
        traces = self.engine.get_traces()
        assert len(traces) >= 1
        assert traces[-1].tool_name == "trace_tool"

    def test_debug_mode(self):
        self.engine.debug_mode = True
        self.registry.register("debug_tool", lambda: ToolResult(success=True), description="Debug test")
        result = self.engine.execute_direct("debug_tool")
        assert result.success is True

    def test_stats(self):
        self.registry.register("stats_tool", lambda: ToolResult(success=True), description="Stats test")
        self.engine.execute("stats tool")
        stats = self.engine.get_stats()
        assert stats["total_executions"] >= 1
        assert stats["successful"] >= 1

    def test_execute_find_and_run(self):
        self.registry.register("open_youtube", lambda: ToolResult(success=True, result={"url": "youtube.com"}),
                               description="Open YouTube website")
        result = self.engine.execute("open youtube")
        assert result.success is True


# ═══════════════════════════════════════════════════════════════════════
# CORE TOOLS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestCoreTools:
    def test_create_file(self):
        tmp = tempfile.mktemp(suffix=".txt")
        result = create_file(tmp, "hello world")
        assert result.success is True
        assert os.path.exists(tmp)
        os.remove(tmp)

    def test_read_file(self):
        tmp = tempfile.mktemp(suffix=".txt")
        Path(tmp).write_text("test content")
        result = read_file(tmp)
        assert result.success is True
        assert result.result["content"] == "test content"
        os.remove(tmp)

    def test_delete_file(self):
        tmp = tempfile.mktemp(suffix=".txt")
        Path(tmp).write_text("delete me")
        result = delete_file(tmp)
        assert result.success is True
        assert not os.path.exists(tmp)

    def test_delete_nonexistent(self):
        result = delete_file("/nonexistent/file.txt")
        assert result.success is False

    def test_get_time(self):
        result = get_time()
        assert result.success is True
        assert "time" in result.result

    def test_get_date(self):
        result = get_date()
        assert result.success is True
        assert "date" in result.result

    def test_get_system_stats(self):
        result = get_system_stats()
        assert result.success is True
        assert "cpu_percent" in result.result

    def test_list_running_apps(self):
        result = list_running_apps(limit=5)
        assert result.success is True
        assert "apps" in result.result

    def test_add_and_get_notes(self):
        result = add_note("test note for verification")
        assert result.success is True
        notes = get_notes()
        assert notes.success is True
        # Cleanup
        notes_path = Path.home() / ".jarvis" / "notes.json"
        if notes_path.exists():
            import json
            data = json.loads(notes_path.read_text())
            data = [n for n in data if n.get("content") != "test note for verification"]
            notes_path.write_text(json.dumps(data, indent=2))

    def test_add_and_get_todos(self):
        result = add_todo("test todo for verification")
        assert result.success is True
        todos = get_todos()
        assert todos.success is True
        # Cleanup
        todos_path = Path.home() / ".jarvis" / "todos.json"
        if todos_path.exists():
            import json
            data = json.loads(todos_path.read_text())
            data = [t for t in data if t.get("task") != "test todo for verification"]
            todos_path.write_text(json.dumps(data, indent=2))

    def test_register_all_tools(self):
        from jarvis.execution.tool_registry import ToolRegistry
        reg = ToolRegistry()
        register_all_tools()
        stats = tool_registry.get_stats()
        assert stats["total"] >= 15


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_full_pipeline(self):
        """Test: user input → tool selection → execute → verify → respond."""
        from jarvis.execution.tool_registry import ToolRegistry
        from jarvis.execution.verifier import VerificationEngine
        from jarvis.execution.engine import ExecutionEngine

        registry = ToolRegistry()
        verifier = VerificationEngine()
        engine = ExecutionEngine(registry, verifier)

        # Register a tool
        def open_youtube():
            return ToolResult(success=True, result={"url": "https://youtube.com"})
        registry.register("open_youtube", open_youtube, description="Open YouTube")

        # Execute
        result = engine.execute("open youtube")
        assert result.success is True

        # Trace
        trace = engine.get_last_trace()
        assert trace is not None
        assert trace.tool_name == "open_youtube"
        assert trace.execution_result is not None
        assert trace.execution_result.success is True

    def test_tool_result_format(self):
        """Every tool returns standardized ToolResult."""
        result = ToolResult(
            success=True,
            result={"window": "Chrome"},
            error=None,
            execution_time_ms=142.0,
            tool_name="open_app",
            verified=True,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["result"]["window"] == "Chrome"
        assert d["error"] is None
        assert d["verified"] is True


# ═══════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
